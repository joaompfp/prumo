"""Review fix Important 2: the /queue read is bounded. Revision bursts are counted in SQL and
every other event kind is read with a small per-kind limit, so a week of heavy revisions or
failures can never load an unbounded number of event rows into the backoffice."""
from backoffice import reads
from backoffice.queue import EVENT_RULES
from ingest.db import Db, read_db_readonly
from ingest.validate import Rejection
from tests.backoffice.conftest import NOW
from tests.ingest.test_task20_serving import _direct_verified

RECENT = "2026-11-14T00:00:00+00:00"


class _CountingCursor:
    def __init__(self, cur, counter):
        self._cur, self._counter = cur, counter

    def _seen(self, rows):
        self._counter[0] += len(rows)
        return rows

    def fetchall(self):
        return self._seen(self._cur.fetchall())

    def fetchone(self):
        row = self._cur.fetchone()
        self._seen([row] if row is not None else [])
        return row

    def __iter__(self):
        return iter(self.fetchall())


class _CountingConn:
    """Counts every row any statement that reads the event table hands back to Python."""

    def __init__(self, conn):
        self._conn, self.event_rows = conn, [0]

    def execute(self, sql, *args):
        cur = self._conn.execute(sql, *args)
        return _CountingCursor(cur, self.event_rows) if "FROM event" in sql else cur

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _queue_counting(env):
    def read(db):
        counting = _CountingConn(db.conn)
        report = reads.status_report(db, env.specs, NOW)
        q = reads.queue(Db(counting), env.specs, report, NOW)
        return q, counting.event_rows[0]
    return read_db_readonly(env.db_path, read)


def test_queue_reads_a_bounded_number_of_event_rows(env):
    db = env.db()
    run = _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    with db.transaction():
        for i in range(3000):
            db.add_event(RECENT, "revision", run, {"series_id": "s1", "period": str(i)})
        for kind in EVENT_RULES:
            for _ in range(reads.EVENTS_PER_KIND + 50):
                db.add_event(RECENT, kind, run, {"series_id": "s1"})
        for _ in range(reads.NEW_PERIOD_LIMIT + 50):
            db.add_event(RECENT, "new_periods", run, {"series_id": "s1",
                                                      "periods": ["2020", "2023"]})
        db.write_quarantine(run, "s1", [Rejection(str(i), "x", "non_numeric")
                                        for i in range(2000)], RECENT)
    db.close()
    q, rows = _queue_counting(env)
    assert reads.EVENTS_PER_KIND * len(EVENT_RULES) <= rows <= reads.QUEUE_EVENT_ROW_BOUND
    assert reads.QUEUE_EVENT_ROW_BOUND <= 3000  # far below the old 200k ceiling
    kinds = [i.kind for i in q.items]
    assert kinds.count("revision_burst") == 1
    burst = next(i for i in q.items if i.kind == "revision_burst")
    assert burst.detail["revisions"] == 3000  # exact count, not a lower bound
    assert set(q.truncated) == set(EVENT_RULES) | {"new_periods"}
    assert kinds.count("quarantine") == 1


def test_150_revisions_in_one_run_make_one_burst_with_the_exact_count(env):
    db = env.db()
    run = _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    other = _direct_verified(db, "s1", "2023", "1.0", RECENT, "k2")
    for i in range(150):
        db.add_event(RECENT, "revision", run, {"series_id": "s1", "period": str(1900 + i)})
    for i in range(99):
        db.add_event(RECENT, "revision", other, {})
    db.add_event("2026-11-01T00:00:00+00:00", "revision", other, {})  # outside the window
    db.close()
    q, _rows = _queue_counting(env)
    bursts = [(i.ref, i.detail["revisions"]) for i in q.items if i.kind == "revision_burst"]
    assert bursts == [(f"run:{run}", 150)]
    assert q.truncated == ()


def test_queue_covers_failures_streaks_gaps_and_quarantine_from_the_db(env):
    db = env.db()
    ok = _direct_verified(db, "s1", "2024", "1.0", RECENT, "k1")
    db.add_event(RECENT, "format_change", ok, {"series_id": "s1",
                                               "reason": "no_valid_observations"})
    db.add_event(RECENT, "stale_refusal", ok, {"error": "older"})
    db.add_event(RECENT, "operational_failure", ok, {"stage": "orphaned"})
    db.add_event(RECENT, "verifier_outage", ok, {"error": "503"})
    db.add_event(RECENT, "new_periods", ok, {"series_id": "s1", "periods": ["2019", "2024"]})
    db.write_quarantine(ok, "s1", [Rejection("2023", "n/a", "non_numeric")], RECENT)
    for _ in range(2):
        r = db.begin_run("fake", "kf", RECENT)
        db.set_run_state(r, "failed-fetch")
    db.close()
    q, _rows = _queue_counting(env)
    got = {(i.kind, i.severity) for i in q.items}
    assert {("format_change", "high"), ("stale_refusal", "high"),
            ("operational_failure", "medium"), ("verifier_outage", "medium"),
            ("fetch_failure_streak", "medium"), ("new_period_gap", "info"),
            ("quarantine", "info")} <= got
