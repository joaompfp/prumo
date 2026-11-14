"""Task 24: re-review 1 fixes (docs/superpowers/handoff/reports/final-review/
rereview-1-serving-migrations.md).

- I-1: withdrawal and the identical-payload short-circuit. A short-circuit run holds no rows,
  so withdrawing it is refused; withdrawing the run that holds the rows also withdraws the
  later verified short-circuit runs that vouched for it, so the next identical fetch is
  re-ingested and status stops crediting them as "confirmed current".
- M-1: the pipeline leaves 'running' only by compare-and-set; a run closed meanwhile by the
  orphan sweep is detected and aborted cleanly (event), never resurrected. The sweep closes
  only runs older than ORPHAN_MIN_AGE, or runs the scheduler itself started.
- M-2: INSERT OR REPLACE cannot resurrect a withdrawn run id.
- M-5: fetched observation rows must carry the '+00:00' UTC spelling (migration 0013).
"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import ingest.db as dbmod
from ingest.db import MIGRATIONS_DIR, ORPHAN_MIN_AGE, open_db
from ingest.models import Observation
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.status import build_status
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)


def _ts(dt):
    return dt.astimezone(timezone.utc).isoformat()


def served(db):
    return db.conn.execute("SELECT series_id, period, value_text FROM served_observation "
                           "ORDER BY series_id, period").fetchall()


def events(db, kind):
    return [(r, json.loads(d) if d else None) for r, d in db.conn.execute(
        "SELECT dataset_run_id, detail_json FROM event WHERE kind = ? ORDER BY id", (kind,))]


@pytest.fixture
def pipe(db, tmp_path):
    sp = spec("s1")
    sync_registry(db, [sp])
    store = RawStore(tmp_path / "raw")

    def run(value: str, at: datetime, verify: bool = True):
        r = run_dataset(db, store, FakeSource(), [sp],
                        FakeHttp(ok(payload({"s1": [["2024", value]]}))), now=lambda: at)
        if verify and r.state == "pending-verification":
            assert db.transition_run_state(r.run_id, "pending-verification", "verified")
        return r
    return db, run


# --- I-1 -----------------------------------------------------------------------------------

def test_review_sequence_withdrawal_reaches_the_short_circuit_and_reingests(pipe):
    """The review's probe A/A2: a (9.9) verified, b identical -> short-circuit. Withdrawing b
    is refused (it holds no rows); withdrawing a also withdraws b, the older vintage is served
    again, and the next identical fetch c is re-ingested instead of short-circuiting onto b."""
    db, run = pipe
    old = run("1.0", T0)
    a = run("9.9", T0 + timedelta(hours=1))
    b = run("9.9", T0 + timedelta(hours=2))
    assert b.state == "verified" and b.n_written == 0
    assert served(db) == [("s1", "2024", "9.9")]

    with pytest.raises(ValueError, match="no observations"):
        db.withdraw_run(b.run_id, "wrong vintage", _ts(T0 + timedelta(hours=3)))
    assert db.run_state(b.run_id) == "verified" and events(db, "withdrawal") == []

    db.withdraw_run(a.run_id, "wrong vintage", _ts(T0 + timedelta(hours=3)))
    assert db.run_state(a.run_id) == "withdrawn"
    assert db.run_state(b.run_id) == "withdrawn"
    assert db.run_state(old.run_id) == "verified"
    assert events(db, "withdrawal") == [
        (a.run_id, {"reason": "wrong vintage", "previous_state": "verified"}),
        (b.run_id, {"reason": "wrong vintage", "previous_state": "verified",
                    "cascaded_from": a.run_id})]
    assert served(db) == [("s1", "2024", "1.0")]

    c = run("9.9", T0 + timedelta(hours=4), verify=False)
    assert c.state == "pending-verification" and c.n_written == 1


def test_status_no_longer_credits_the_withdrawn_short_circuits(pipe):
    db, run = pipe
    run("1.0", T0)
    a = run("9.9", T0 + timedelta(hours=1))
    run("9.9", T0 + timedelta(hours=20))  # short-circuit onto a
    db.withdraw_run(a.run_id, "wrong vintage", _ts(T0 + timedelta(hours=21)))
    report = build_status(db, [spec("s1")], now=lambda: T0 + timedelta(hours=22))
    s = next(x for src in report.sources for x in src.series if x.id == "s1")
    assert s.last_confirmed_current == _ts(T0)  # only the 1.0 vintage still confirms


def test_cascade_stops_at_the_next_run_that_wrote_rows_or_left_verified(pipe):
    db, run = pipe
    a = run("9.9", T0)
    b = run("9.9", T0 + timedelta(hours=1))           # short-circuit onto a
    d = run("2.0", T0 + timedelta(hours=2))           # wrote rows: a new vintage
    e = run("2.0", T0 + timedelta(hours=3))           # short-circuit onto d
    db.withdraw_run(a.run_id, "defect", _ts(T0 + timedelta(hours=4)))
    assert [db.run_state(r.run_id) for r in (a, b, d, e)] == [
        "withdrawn", "withdrawn", "verified", "verified"]
    assert served(db) == [("s1", "2024", "2.0")]


def test_cascade_stops_at_a_failed_run_in_between(pipe):
    db, run = pipe
    a = run("9.9", T0)
    db.set_run_state(db.begin_run("fake", db.run_info(a.run_id)[2], _ts(T0)), "failed-fetch")
    later = run("9.9", T0 + timedelta(hours=1))        # previous is failed: reprocessed
    assert later.n_written == 1
    db.withdraw_run(a.run_id, "defect", _ts(T0 + timedelta(hours=2)))
    assert db.run_state(later.run_id) == "verified"


# --- M-1 -----------------------------------------------------------------------------------

def test_run_swept_mid_fetch_is_not_resurrected(db, tmp_path):
    """Probe D: a second connection sweeps the run while it fetches; the pipeline must not
    overwrite 'failed-operational' with 'pending-verification' (nor commit rows)."""
    sp = spec("s1")
    sync_registry(db, [sp])
    other = open_db(db.conn.execute("PRAGMA database_list").fetchone()[2])

    class Sweeping(FakeSource):
        def fetch(self, specs, http):
            for resp in super().fetch(specs, http):
                assert other.close_orphan_runs(_ts(T0 + ORPHAN_MIN_AGE + timedelta(hours=1)))
                yield resp

    r = run_dataset(db, RawStore(tmp_path / "raw"), Sweeping(), [sp],
                    FakeHttp(ok(payload({"s1": [["2024", "1"]]}))), now=lambda: T0)
    other.close()
    assert r.state == "failed-operational" and r.n_written == 0
    assert db.run_state(r.run_id) == "failed-operational"
    assert db.conn.execute("SELECT COUNT(*) FROM observation").fetchone() == (0,)
    stages = [d["stage"] for rid, d in events(db, "operational_failure") if rid == r.run_id]
    assert stages == ["orphaned", "closed_elsewhere"]


@pytest.mark.parametrize("body,expected", [
    (b"", "failed-fetch"),                                   # finish() path
    (payload({"s1": [["2024", "1"]]}), "pending-verification"),  # write-transaction path
])
def test_every_exit_from_running_is_compare_and_set(db, tmp_path, monkeypatch, body, expected):
    sp = spec("s1")
    sync_registry(db, [sp])
    real = db.transition_run_state
    seen = []

    def spy(run_id, from_state, to_state, **kw):
        seen.append((from_state, to_state))
        return real(run_id, from_state, to_state, **kw)

    monkeypatch.setattr(db, "transition_run_state", spy)
    monkeypatch.setattr(db, "set_run_state", lambda *a, **k: pytest.fail("unconditional"))
    r = run_dataset(db, RawStore(tmp_path / "raw"), FakeSource(), [sp], FakeHttp(ok(body)),
                    now=lambda: T0)
    assert r.state == expected and seen == [("running", expected)]


def test_sweep_spares_a_young_manual_run_and_closes_old_or_scheduler_ones(db):
    sync_registry(db, [spec("s1")])
    now = T0 + timedelta(hours=10)
    young = db.begin_run("fake", "k-young", _ts(now - timedelta(hours=1)))
    old = db.begin_run("fake", "k-old", _ts(now - ORPHAN_MIN_AGE - timedelta(minutes=1)))
    # a scheduler attempt marker for the key: the scheduler started this run itself
    db.scheduler_attempt_started("k-sched", "fake", "g", _ts(now - timedelta(minutes=30)))
    sched = db.begin_run("fake", "k-sched", _ts(now - timedelta(minutes=29)))
    assert db.close_orphan_runs(_ts(now)) == [old, sched]
    assert db.run_state(young) == "running"
    reasons = {rid: d["swept_because"] for rid, d in events(db, "operational_failure")}
    assert reasons == {old: "older_than_min_age", sched: "scheduler_attempt_interrupted"}
    assert ORPHAN_MIN_AGE == timedelta(hours=6)


# --- M-2 / M-5: migration 0013 triggers ------------------------------------------------------

def _verified_run_with_row(db, fetched_at=None):
    fetched_at = fetched_at or _ts(T0)
    run = db.begin_run("fake", "k", _ts(T0))
    fid = db.record_raw_fetch(source_name="fake", run_id=run, url="http://x", params_json=None,
                              fetched_at=fetched_at, http_status=200, sha256="s", path="p",
                              n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw("s1", "2024", "1"), fid, fetched_at)])
    db.set_run_state(run, "verified")
    return run


def test_insert_or_replace_cannot_resurrect_a_withdrawn_run(db):
    sync_registry(db, [spec("s1")])
    run = _verified_run_with_row(db)
    db.withdraw_run(run, "defect", "t")
    src = db.conn.execute("SELECT source_id FROM dataset_run WHERE id = ?", (run,)).fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError, match="withdrawn"):
        db.conn.execute("INSERT OR REPLACE INTO dataset_run(id, source_id, started_at, state, "
                        "dataset_key) VALUES (?, ?, 't', 'verified', 'k')", (run, src))
    assert db.run_state(run) == "withdrawn" and served(db) == []
    # an ordinary replace of a non-withdrawn row is unaffected
    other = db.begin_run("fake", "k2", "t")
    db.conn.execute("INSERT OR REPLACE INTO dataset_run(id, source_id, started_at, state, "
                    "dataset_key) VALUES (?, ?, 't', 'failed-fetch', 'k2')", (other, src))


@pytest.mark.parametrize("bad", ["2026-11-13T00:00:00Z", "2026-11-13T00:00:00",
                                 "2026-11-13T01:00:00+01:00", "t", "2026-11-13 00:00:00+00:00"])
def test_fetched_rows_must_use_the_utc_plus_00_00_spelling(db, bad):
    sync_registry(db, [spec("s1")])
    with pytest.raises(sqlite3.IntegrityError, match="fetched_at"):
        _verified_run_with_row(db, fetched_at=bad)
    run = db.legacy_run("fake", "legacy:fake", "t")  # legacy rows are exempt
    db.write_legacy_observations(run, [(Observation.from_raw("s1", "2020", "7"), bad)])


@pytest.mark.parametrize("good", ["2026-11-13T00:00:00+00:00",
                                  "2026-11-13T00:00:00.123456+00:00"])
def test_fetched_rows_accept_both_isoformat_spellings(db, good):
    sync_registry(db, [spec("s1")])
    _verified_run_with_row(db, fetched_at=good)
    with pytest.raises(sqlite3.IntegrityError, match="fetched_at"):
        db.conn.execute("UPDATE observation SET fetched_at = '2026-11-13T00:00:00Z'")


# --- upgrade path: 0013 on a populated 0012 database -----------------------------------------

def _migrations_up_to(tmp_path, last: str):
    mig = tmp_path / f"mig{last}"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem[:4] <= last:
            (mig / f.name).write_bytes(f.read_bytes())
    return mig


TABLES = ("source", "series", "dataset_run", "raw_fetch", "observation", "quarantine",
          "verification", "verification_item", "verification_spec", "event", "setting",
          "scheduler_state")


def test_0013_upgrades_a_populated_0012_database_without_changing_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", _migrations_up_to(tmp_path, "0012"))
    p = tmp_path / "old.db"
    d = open_db(p)
    sync_registry(d, [spec("s1"), spec("s2")])
    store = RawStore(tmp_path / "raw")
    r1 = run_dataset(d, store, FakeSource(), [spec("s1"), spec("s2")],
                     FakeHttp(ok(payload({"s1": [["2024", "2.0"]], "s2": [["2024", "x"]]}))),
                     now=lambda: T0)
    d.transition_run_state(r1.run_id, "pending-verification", "verified")
    vid = d.add_verification(r1.run_id, 7, 1, True, _ts(T0), sample_procedure="prumo-sample-v2",
                             sample_design={"n": 1}, input_origin="live",
                             verifier_channel="live")
    d.add_verification_spec(vid, "s1", "{}")
    d.add_verification_item(vid, {c: None for c in d._ITEM_COLUMNS} | {
        "series_id": "s1", "period": "2024", "expected_text": "2.0", "match": True,
        "reason": "latest"})
    d.withdraw_run(r1.run_id, "defect", _ts(T0))
    d.begin_run("fake", "orphan", "t")
    leg = d.legacy_run("fake", "legacy:fake", "t")
    d.write_legacy_observations(leg, [(Observation.from_raw("s1", "2020", "7"), "2026-02-01Z")])
    d.scheduler_attempt_started("k", "fake", "g", "t")
    before = {t: d.conn.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall() for t in TABLES}
    schema_before = {n for (n,) in d.conn.execute("SELECT name FROM sqlite_master")}
    d.close()

    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)
    d = open_db(p)
    after = {t: d.conn.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall() for t in TABLES}
    assert after == before
    assert d.conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert d.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    schema_after = {n for (n,) in d.conn.execute("SELECT name FROM sqlite_master")}
    assert schema_before <= schema_after
    assert any(v.startswith("0013") for (v,) in d.conn.execute(
        "SELECT version FROM schema_migration"))
    d.close()
    assert open_db(p).conn.execute("SELECT COUNT(*) FROM schema_migration").fetchone()[0] == 13
