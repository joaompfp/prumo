"""Task 20: final-review fixes A-I1, A-I2, A-M1, A-M2 (docs/superpowers/handoff/reports/
final-review/part-A-core.md).

- I1: serving follows DATA time (fetched_at, then id), never insertion order alone, and the
  recorded-replay stale guard also counts runs still pending verification.
- I2: fetched rows of an inactive series are not served; registry sync deactivates series that
  left the registry (with an event); a verified vintage can be withdrawn through ONE reviewed
  Db function that records the reason, and withdrawn runs are never served.
- M1: a run interrupted by an exception (or SIGTERM -> SystemExit) never stays 'running';
  the scheduler closes orphans left by a hard kill when it starts.
- M2: a 'database is locked' write error is an operational failure, not a format change.
"""
import json
import signal
import sqlite3
from datetime import datetime, timezone

import pytest

import ingest.db as dbmod
from ingest import cli
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.models import Observation
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec

NOV13 = datetime(2026, 11, 13, tzinfo=timezone.utc)
NOV01 = "2026-11-01T00:00:00+00:00"


class Recorded(FakeSource):
    """One recorded response carrying its ORIGINAL receipt time (a replayed bundle)."""

    def __init__(self, body: bytes, receipt: str):
        super().__init__()
        self.body, self.receipt = body, receipt

    def fetch(self, specs, http):
        yield RawResponse(url="http://fake/data/1", params={"page": 1}, status=200,
                          body=self.body, fetched_at=self.receipt)


def served(db):
    return db.conn.execute("SELECT series_id, period, value_text FROM served_observation "
                           "ORDER BY series_id, period").fetchall()


def events(db, kind):
    return [(r, json.loads(d) if d else None) for r, d in db.conn.execute(
        "SELECT dataset_run_id, detail_json FROM event WHERE kind = ? ORDER BY id", (kind,))]


def _direct_verified(db, sid, period, value, fetched_at, key):
    """A verified fetched vintage written straight through Db (no pipeline guard), exactly
    as a racing writer could leave it."""
    run = db.begin_run("fake", key, fetched_at)
    fid = db.record_raw_fetch(source_name="fake", run_id=run, url="http://x", params_json=None,
                              fetched_at=fetched_at, http_status=200,
                              sha256=f"sha-{key}", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(sid, period, value), fid, fetched_at)])
    db.set_run_state(run, "verified")
    return run


# --- I1: data time, not insertion order -------------------------------------------------------

def test_older_replay_cannot_displace_newer_live_data_pending_verification(db, tmp_path):
    """The review probe: live run 2026-11-13 pending; a 2026-11-01 bundle is replayed; both
    get verified; the 2026-11-13 value must be what is served."""
    sp = spec("s1")
    sync_registry(db, [sp])
    store = RawStore(tmp_path / "raw")
    live = run_dataset(db, store, FakeSource(), [sp],
                       FakeHttp(ok(payload({"s1": [["2024", "2.0"]]}))), now=lambda: NOV13)
    assert live.state == "pending-verification"
    old = run_dataset(db, store, Recorded(payload({"s1": [["2024", "1.0"]]}), NOV01), [sp],
                      None, now=lambda: NOV13, input_origin="recorded")
    # the guard now counts the pending newer run: the old bundle is refused atomically
    assert old.state == "blocked-stale" and old.n_written == 0
    for r in (live, old):
        db.transition_run_state(r.run_id, "pending-verification", "verified")
    assert served(db) == [("s1", "2024", "2.0")]


def test_view_tie_break_is_fetched_at_then_id(db):
    """Even when an older vintage is INSERTED last (overlapping writers committing in the
    reverse of their fetch order) and both are verified, the newer data time is served."""
    sync_registry(db, [spec("s1")])
    _direct_verified(db, "s1", "2024", "2.0", "2026-11-13T00:00:00+00:00", "new")
    _direct_verified(db, "s1", "2024", "1.0", NOV01, "old")  # higher id, older data
    assert served(db) == [("s1", "2024", "2.0")]
    # equal data time: the later insertion (higher id) still wins, as before
    _direct_verified(db, "s1", "2024", "3.0", "2026-11-13T00:00:00+00:00", "same")
    assert served(db) == [("s1", "2024", "3.0")]


# --- I2: inactive series, registry removal, withdrawal ----------------------------------------

def test_fetched_rows_of_inactive_series_are_not_served(db):
    sp = spec("s1")
    sync_registry(db, [sp])
    _direct_verified(db, "s1", "2024", "2.0", NOV01, "k")
    assert served(db) == [("s1", "2024", "2.0")]
    sync_registry(db, [sp.model_copy(update={"active": False})])
    assert served(db) == []
    sync_registry(db, [sp])  # reactivation: history was never deleted
    assert served(db) == [("s1", "2024", "2.0")]


def test_inactive_fetched_rows_stay_hidden_under_global_legacy_switch(db):
    sp = spec("s1")
    sync_registry(db, [sp.model_copy(update={"active": False})])
    _direct_verified(db, "s1", "2024", "2.0", NOV01, "k")
    db.conn.execute("UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
    assert served(db) == []


def test_registry_sync_deactivates_series_absent_from_registry_with_event(db):
    a, b = spec("a"), spec("b")
    sync_registry(db, [a, b])
    _direct_verified(db, "b", "2024", "5", NOV01, "kb")
    sync_registry(db, [a])  # b left the registry
    assert db.conn.execute("SELECT active FROM series WHERE id = 'b'").fetchone() == (0,)
    assert served(db) == []
    assert events(db, "series_deactivated") == [
        (None, {"series_id": "b", "reason": "absent_from_registry"})]
    sync_registry(db, [a])  # idempotent: no second event for an already inactive series
    assert len(events(db, "series_deactivated")) == 1
    # history kept
    assert db.conn.execute("SELECT COUNT(*) FROM observation WHERE series_id='b'"
                           ).fetchone() == (1,)


def test_withdrawn_vintage_is_not_served_and_older_vintage_returns(db):
    sync_registry(db, [spec("s1")])
    older = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    wrong = _direct_verified(db, "s1", "2024", "9.9", "2026-11-13T00:00:00+00:00", "k2")
    assert served(db) == [("s1", "2024", "9.9")]
    db.withdraw_run(wrong, "unit defect: registry unit is %, publisher is per mille",
                    "2026-11-13T10:00:00+00:00")
    assert db.run_state(wrong) == "withdrawn"
    assert served(db) == [("s1", "2024", "1.0")]
    assert events(db, "withdrawal") == [
        (wrong, {"reason": "unit defect: registry unit is %, publisher is per mille",
                 "previous_state": "verified"})]
    assert db.conn.execute("SELECT COUNT(*) FROM observation").fetchone() == (2,)
    assert db.run_state(older) == "verified"
    # withdrawn data never counts as held data for the stale guard
    assert db.max_held_fetched_at(["s1"]) == NOV01


def test_withdrawal_is_reviewed_terminal_and_only_through_db_function(db):
    sync_registry(db, [spec("s1")])
    run = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    with pytest.raises(ValueError, match="reason"):
        db.withdraw_run(run, "   ", "t")
    # a direct state change without the recorded withdrawal event is refused by the DB
    with pytest.raises(sqlite3.IntegrityError, match="withdraw"):
        db.set_run_state(run, "withdrawn")
    with pytest.raises(sqlite3.IntegrityError, match="withdraw"):
        db.transition_run_state(run, "verified", "withdrawn")
    pending = db.begin_run("fake", "k2", "t")
    db.set_run_state(pending, "pending-verification")
    with pytest.raises(ValueError, match="verified"):
        db.withdraw_run(pending, "bad", "t")
    assert events(db, "withdrawal") == []  # refused attempts leave nothing behind
    db.withdraw_run(run, "defect", "t")
    with pytest.raises(sqlite3.IntegrityError, match="withdrawn"):
        db.set_run_state(run, "verified")  # terminal
    with pytest.raises(ValueError, match="verified"):
        db.withdraw_run(run, "again", "t")
    legacy = db.legacy_run("fake", "legacy:fake", "t")
    with pytest.raises(ValueError, match="legacy"):
        db.withdraw_run(legacy, "no", "t")


def test_same_bytes_after_withdrawal_are_reprocessed_not_short_circuited(db, tmp_path):
    """Documented behaviour: withdrawal removes ONE vintage; identical publisher bytes are
    re-ingested as a new run (the short-circuit only follows a VERIFIED previous run)."""
    sp = spec("s1")
    sync_registry(db, [sp])
    store = RawStore(tmp_path / "raw")
    body = payload({"s1": [["2024", "2.0"]]})
    first = run_dataset(db, store, FakeSource(), [sp], FakeHttp(ok(body)), now=lambda: NOV13)
    db.transition_run_state(first.run_id, "pending-verification", "verified")
    db.withdraw_run(first.run_id, "publisher glitch", "t")
    again = run_dataset(db, store, FakeSource(), [sp], FakeHttp(ok(body)), now=lambda: NOV13)
    assert again.state == "pending-verification" and again.n_written == 1


def test_cli_withdraw_command(tmp_path, capsys):
    dbp = tmp_path / "c.db"
    reg = tmp_path / "core.yaml"
    reg.write_text("sources:\n  fake:\n    licence: CC-BY-4.0\n    licence_url: http://l\n"
                   "    attribution: Fake\n    redistribution_ok: true\nseries: []\n")
    d = open_db(dbp)
    sync_registry(d, [spec("s1")])
    run = _direct_verified(d, "s1", "2024", "1.0", NOV01, "k1")
    d.close()
    base = ["--db", str(dbp), "--raw-dir", str(tmp_path / "raw"), "--registry", str(reg)]
    with pytest.raises(SystemExit):  # --reason is mandatory
        cli.main([*base, "withdraw", str(run)])
    capsys.readouterr()
    assert cli.main([*base, "withdraw", str(run), "--reason", "wrong unit"]) == 0
    assert f"run {run} withdrawn" in capsys.readouterr().out
    assert cli.main([*base, "withdraw", str(run), "--reason", "again"]) == 2
    d = open_db(dbp)
    assert d.run_state(run) == "withdrawn"
    d.close()


# --- M1: no orphan 'running' runs ---------------------------------------------------------------

@pytest.mark.parametrize("exc", [OSError("disk full"), SystemExit(143)])
def test_interrupted_run_is_closed_as_operational_failure(db, tmp_path, exc):
    sync_registry(db, [spec("s1")])

    class Store(RawStore):
        def save(self, source, body):
            raise exc

    with pytest.raises(type(exc)):
        run_dataset(db, Store(tmp_path / "raw"), FakeSource(), [spec("s1")],
                    FakeHttp(ok(payload({"s1": [["2024", "1"]]}))), now=lambda: NOV13)
    (run_id, state), = db.conn.execute("SELECT id, state FROM dataset_run").fetchall()
    assert state == "failed-operational"
    (rid, detail), = events(db, "operational_failure")
    assert rid == run_id and detail["stage"] == "interrupted" and repr(exc) in detail["error"]


def test_close_orphan_runs_marks_running_runs_failed_with_event(db):
    sync_registry(db, [spec("s1")])
    orphan = db.begin_run("fake", "k", "2026-11-13T00:00:00+00:00")
    done = db.begin_run("fake", "k2", "2026-11-13T00:00:00+00:00")
    db.set_run_state(done, "pending-verification")
    # Task 24 (re-review 1 M-1): a run with no scheduler marker is swept only once it is
    # older than ORPHAN_MIN_AGE (6 h); a younger one may be a live manual CLI run
    assert db.close_orphan_runs("2026-11-13T01:00:00+00:00") == []
    assert db.close_orphan_runs("2026-11-13T07:00:00+00:00") == [orphan]
    assert db.run_state(orphan) == "failed-operational"
    assert db.run_state(done) == "pending-verification"
    assert events(db, "operational_failure") == [
        (orphan, {"stage": "orphaned", "swept_because": "older_than_min_age",
                  "error": "run left 'running' by an interrupted "
                           "process (closed at scheduler start)"})]
    assert db.close_orphan_runs("2026-11-13T08:00:00+00:00") == []


def test_scheduler_start_closes_orphans_and_sigterm_raises_systemexit(tmp_path, monkeypatch):
    from ingest import scheduler
    reg = tmp_path / "core.yaml"
    reg.write_text("sources:\n  fake:\n    licence: CC-BY-4.0\n    licence_url: http://l\n"
                   "    attribution: Fake\n    redistribution_ok: true\nseries: []\n")
    dbp = tmp_path / "s.db"
    d = open_db(dbp)
    sync_registry(d, [spec("s1")])
    # the previous scheduler process marked its attempt, then died mid-run (Task 24: such a
    # run is closed at start whatever its age)
    d.scheduler_attempt_started("k", "fake", "g", "2026-11-13T00:00:00+00:00")
    orphan = d.begin_run("fake", "k", "2026-11-13T00:00:00+00:00")
    d.close()
    seen = {}

    def fake_tick(db, store, specs, **kw):
        seen["state"] = db.run_state(orphan)
        seen["handler"] = signal.getsignal(signal.SIGTERM)
        return []

    monkeypatch.setattr(scheduler, "tick", fake_tick)
    before = signal.getsignal(signal.SIGTERM)
    assert scheduler.main(["--once", "--db", str(dbp), "--raw-dir", str(tmp_path / "raw"),
                           "--registry", str(reg)], now=lambda: NOV13) == 0
    assert seen["state"] == "failed-operational"
    with pytest.raises(SystemExit) as e:
        seen["handler"](signal.SIGTERM, None)
    assert e.value.code == 128 + signal.SIGTERM
    assert signal.getsignal(signal.SIGTERM) == before  # restored after main


# --- M2: lock contention is operational ---------------------------------------------------------

def test_database_locked_write_is_operational_not_format_change(db, tmp_path, monkeypatch):
    sync_registry(db, [spec("s1")])

    def locked(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "write_observations", locked)
    r = run_dataset(db, RawStore(tmp_path / "raw"), FakeSource(), [spec("s1")],
                    FakeHttp(ok(payload({"s1": [["2024", "1"]]}))), now=lambda: NOV13)
    assert r.state == "failed-operational" and r.n_written == 0
    assert events(db, "format_change") == []
    (_rid, detail), = events(db, "operational_failure")
    assert detail["stage"] == "write" and "database is locked" in detail["error"]


def test_open_db_sets_explicit_busy_timeout(tmp_path):
    d = open_db(tmp_path / "t.db")
    assert d.conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 30000
    d.close()


# --- migration 0011 on a populated 0010 database -------------------------------------------

def _migrations_up_to_0010(tmp_path):
    mig = tmp_path / "mig10"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem < "0011":
            (mig / f.name).write_bytes(f.read_bytes())
    return mig


TABLES = ("source", "series", "dataset_run", "raw_fetch", "observation", "quarantine",
          "verification", "verification_item", "event", "setting", "scheduler_state")


def _snapshot(d):
    return {t: d.conn.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall() for t in TABLES}


def test_0011_upgrades_populated_0010_and_preserves_every_row(tmp_path, monkeypatch):
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", _migrations_up_to_0010(tmp_path))
    p = tmp_path / "old.db"
    d = open_db(p)
    assert not [v for (v,) in d.conn.execute("SELECT version FROM schema_migration")
                if v.startswith("0011")]
    sync_registry(d, [spec("s1"), spec("s2")])
    store = RawStore(tmp_path / "raw")
    r1 = run_dataset(d, store, FakeSource(), [spec("s1"), spec("s2")],
                     FakeHttp(ok(payload({"s1": [["2024", "2.0"]], "s2": [["2024", "x"]]}))),
                     now=lambda: NOV13)
    d.transition_run_state(r1.run_id, "pending-verification", "verified")
    vid = d.conn.execute("INSERT INTO verification(dataset_run_id, seed, sample_size, passed, "
                         "created_at) VALUES (?, 7, 1, 1, 't')", (r1.run_id,)).lastrowid
    d.conn.execute("INSERT INTO verification_item(verification_id, series_id, period, "
                   "expected_text, match) VALUES (?, 's1', '2024', '2.0', 1)", (vid,))
    # older vintage inserted LAST (the I1 shape), a failed run, an orphan running run
    _direct_verified(d, "s1", "2024", "1.0", NOV01, "late-old")
    d.set_run_state(d.begin_run("fake", "f", "t"), "failed-fetch")
    d.begin_run("fake", "orphan", "t")
    leg = d.legacy_run("fake", "legacy:fake", "t")
    d.write_legacy_observations(leg, [(Observation.from_raw("s1", "2020", "7"), "2026-02-01Z")])
    d.scheduler_attempt_started("k", "fake", "g", "t")
    assert served(d) == [("s1", "2024", "1.0")]  # the pre-0011 defect, reproduced
    before = _snapshot(d)
    d.close()

    upto11 = tmp_path / "mig11"  # this test pins the 0011 upgrade (0012 is tested in task21)
    upto11.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem < "0012":
            (upto11 / f.name).write_bytes(f.read_bytes())
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", upto11)
    d = open_db(p)
    try:
        assert any(v.startswith("0011") for (v,) in
                   d.conn.execute("SELECT version FROM schema_migration"))
        assert _snapshot(d) == before  # every row byte-identical; nothing rewritten
        assert served(d) == [("s1", "2024", "2.0")]  # data time now decides
        assert d.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert d.conn.execute("PRAGMA foreign_key_check").fetchall() == []
        names = {n for (n,) in d.conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('index','trigger')")}
        assert {"dataset_run_key", "observation_period_ins", "observation_period_upd"} <= names
    finally:
        d.close()
    d = open_db(p)  # reopen is idempotent
    assert _snapshot(d) == before
    d.close()
