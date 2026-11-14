"""Backoffice v1, Task 1: read-only queries on Db (docs/superpowers/plans/
2026-11-14-backoffice-v1.md). Data is written through the real Db/registry paths used by
test_task20_serving.py; the reads must never expose SQL rows, only plain dicts."""
from ingest.models import Observation
from ingest.registry import sync_registry
from tests.ingest.fakes import spec
from tests.ingest.test_task20_serving import _direct_verified

NOV01 = "2026-11-01T00:00:00+00:00"
NOV13 = "2026-11-13T00:00:00+00:00"


def _pending(db, sid, period, value, fetched_at, key, *, started_at=None):
    """A fetched vintage still pending verification (not served)."""
    run = db.begin_run("fake", key, started_at or fetched_at)
    fid = db.record_raw_fetch(source_name="fake", run_id=run, url=f"http://x/{key}",
                              params_json=None, fetched_at=fetched_at, http_status=200,
                              sha256=f"sha-{key}", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(sid, period, value), fid, fetched_at)])
    db.set_run_state(run, "pending-verification")
    return run


def _legacy(db, sid, period, value, fetched_at="2025-01-01T00:00:00Z"):
    run = db.legacy_run("fake", "legacy:fake", fetched_at)
    db.write_legacy_observations(run, [(Observation.from_raw(sid, period, value), fetched_at)])
    return run


def test_series_observations_total_and_newest_first(db):
    sync_registry(db, [spec("s1")])
    run = db.begin_run("fake", "k", NOV13)
    fid = db.record_raw_fetch(source_name="fake", run_id=run, url="http://x/k",
                              params_json=None, fetched_at=NOV13, http_status=200,
                              sha256="sha-k", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw("s1", p, v), fid, NOV13)
                                for p, v in (("2021", "0.10"), ("2022", "-0.50"),
                                             ("2023", "3"))])
    db.set_run_state(run, "verified")
    total, rows = db.series_observations("s1", limit=2)
    assert total == 3
    assert [r["period"] for r in rows] == ["2023", "2022"]
    assert rows[1] == {"period": "2022", "value_text": "-0.50", "status_flag": None,
                       "run_id": run, "fetched_at": NOV13, "raw_sha": "sha-k",
                       "origin": "fetched"}
    total, rows = db.series_observations("s1", limit=2, offset=2)
    assert total == 3 and [(r["period"], r["value_text"]) for r in rows] == [("2021", "0.10")]
    # unknown / never-fetched series: zero, not an error
    assert db.series_observations("nope", limit=10) == (0, [])


def test_series_observations_marks_legacy_origin(db):
    sync_registry(db, [spec("s1")])
    _legacy(db, "s1", "2019", "7.5")
    db.conn.execute("UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
    _direct_verified(db, "s1", "2020", "8", NOV01, "k")
    total, rows = db.series_observations("s1", limit=10)
    assert total == 2
    assert [(r["period"], r["origin"], r["raw_sha"]) for r in rows] == [
        ("2020", "fetched", "sha-k"), ("2019", "legacy", None)]


def test_series_vintages_marks_only_served_version(db):
    sync_registry(db, [spec("s1")])
    _legacy(db, "s1", "2024", "0.5")
    db.conn.execute("UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
    old = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    new = _direct_verified(db, "s1", "2024", "2.0", NOV13, "k2")
    rows = db.series_vintages("s1", "2024")
    assert [(r["run_id"], r["value_text"], r["served"]) for r in rows][1:] == [
        (old, "1.0", False), (new, "2.0", True)]
    assert rows[0]["origin"] == "legacy" and rows[0]["served"] is False
    assert sum(r["served"] for r in rows) == 1
    assert db.series_vintages("s1", "1999") == []


def test_series_vintages_includes_withdrawn_and_pending_runs(db):
    sync_registry(db, [spec("s1")])
    good = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    bad = _direct_verified(db, "s1", "2024", "9.9", "2026-11-05T00:00:00+00:00", "k2")
    db.withdraw_run(bad, "unit defect", "2026-11-06T00:00:00+00:00")
    pend = _pending(db, "s1", "2024", "1.1", NOV13, "k3")
    rows = db.series_vintages("s1", "2024")
    assert [(r["run_id"], r["run_state"], r["served"]) for r in rows] == [
        (good, "verified", True), (bad, "withdrawn", False),
        (pend, "pending-verification", False)]
    assert rows[1]["fetched_at"] == "2026-11-05T00:00:00+00:00"
    assert rows[1]["status_flag"] is None and rows[1]["origin"] == "fetched"


def test_series_quarantine_and_items_empty_for_unknown_series(db):
    assert db.series_quarantine("nope") == []
    assert db.series_verification_items("nope") == []
    assert db.series_raw_fetches("nope") == []


def test_series_quarantine_items_and_raw_fetches(db):
    from ingest.validate import Rejection
    sync_registry(db, [spec("s1"), spec("s2")])
    run = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    db.write_quarantine(run, "s1", [Rejection("2023", "n/a", "non_numeric")], NOV01)
    db.write_quarantine(run, "s2", [Rejection("2023", "x", "non_numeric")], NOV01)
    assert db.series_quarantine("s1") == [
        {"run_id": run, "period": "2023", "raw_value": "n/a", "reason": "non_numeric",
         "created_at": NOV01}]
    vid = db.add_verification(run, 7, 1, True, NOV13, sample_procedure="prumo-sample-v2",
                              sample_design={}, input_origin="live", verifier_channel="live")
    item = {c: None for c in db._ITEM_COLUMNS}
    item.update(series_id="s1", period="2024", expected_text="1.0", observed_text="1.0",
                evidence_url="https://e/<b>", match=True, reason="latest")
    db.add_verification_item(vid, item)
    [got] = db.series_verification_items("s1")
    assert got == {"item_id": got["item_id"], "verification_id": vid, "run_id": run,
                   "period": "2024", "expected_text": "1.0", "observed_text": "1.0",
                   "evidence_url": "https://e/<b>", "match": True, "reason": "latest",
                   "created_at": NOV13}
    assert db.series_verification_items("s2") == []
    assert db.series_raw_fetches("s1") == [
        {"sha256": "sha-k1", "url": "http://x", "fetched_at": NOV01, "http_status": 200,
         "run_id": run}]


def test_series_quarantine_respects_limit_newest_first(db):
    from ingest.validate import Rejection
    sync_registry(db, [spec("s1")])
    run = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    db.write_quarantine(run, "s1", [Rejection(str(y), "x", "non_numeric")
                                    for y in (2020, 2021, 2022)], NOV01)
    assert [r["period"] for r in db.series_quarantine("s1", limit=2)] == ["2022", "2021"]


def test_recent_events_filters_by_kind_and_since_and_parses_detail(db):
    sync_registry(db, [spec("s1")])
    run = _direct_verified(db, "s1", "2024", "1.0", NOV01, "k1")
    db.add_event("2026-11-01T00:00:00+00:00", "verification_failure", run, {"n": 1})
    db.add_event("2026-11-10T00:00:00+00:00", "revision", run,
                 {"series_id": "s1", "period": "2024"})
    db.add_event("2026-11-12T00:00:00+00:00", "verification_failure", run,
                 {"why": "<script>x</script>"})
    db.add_event("2026-11-13T00:00:00+00:00", "refetch", None, None)
    got = db.recent_events("2026-11-05T00:00:00+00:00", ["verification_failure"], 10)
    assert [(e["ts"], e["kind"], e["run_id"], e["detail"]) for e in got] == [
        ("2026-11-12T00:00:00+00:00", "verification_failure", run,
         {"why": "<script>x</script>"})]
    assert isinstance(got[0]["id"], int)
    allk = db.recent_events(None, None, 10)
    assert [e["kind"] for e in allk] == ["refetch", "verification_failure", "revision",
                                         "verification_failure"]  # newest first
    assert allk[0]["detail"] == {} and allk[0]["run_id"] is None
    assert len(db.recent_events(None, None, 2)) == 2
    assert db.recent_events(None, [], 10) == []


def test_runs_in_state_older_than(db):
    sync_registry(db, [spec("s1")])
    old = _pending(db, "s1", "2024", "1", NOV01, "k1", started_at="2026-11-01T00:00:00+00:00")
    young = _pending(db, "s1", "2025", "1", NOV13, "k2", started_at="2026-11-13T00:00:00+00:00")
    _direct_verified(db, "s1", "2023", "1", NOV01, "k3")
    got = db.runs_in_state("pending-verification")
    assert [r["run_id"] for r in got] == [old, young]
    assert got[0] == {"run_id": old, "source": "fake", "dataset_key": "k1",
                      "state": "pending-verification",
                      "started_at": "2026-11-01T00:00:00+00:00", "finished_at": None,
                      "input_origin": "live"}
    assert [r["run_id"] for r in db.runs_in_state(
        "pending-verification", older_than="2026-11-12T00:00:00+00:00")] == [old]
    assert db.runs_in_state("withdrawn") == []


def test_reads_work_on_a_read_only_handle(tmp_path):
    from ingest.db import open_db, read_db_readonly
    path = tmp_path / "ro.db"
    d = open_db(path)
    sync_registry(d, [spec("s1")])
    run = _direct_verified(d, "s1", "2024", "1.0", NOV01, "k1")
    d.close()

    def read(db):
        return (db.series_observations("s1", 10), db.series_vintages("s1", "2024"),
                db.series_quarantine("s1"), db.series_verification_items("s1"),
                db.series_raw_fetches("s1"), db.recent_events(None, None, 5),
                db.runs_in_state("verified"))
    obs, vint, quar, items, raws, evs, runs = read_db_readonly(path, read)
    assert obs[0] == 1 and vint[0]["served"] and quar == [] and items == []
    assert raws[0]["run_id"] == run and evs == [] and [r["run_id"] for r in runs] == [run]
