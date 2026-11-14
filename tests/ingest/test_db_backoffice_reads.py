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


def _run(db, key, state, started_at=NOV01):
    run = db.begin_run("fake", key, started_at)
    if state != "running":
        db.set_run_state(run, state)
    return run


def test_event_counts_by_run_aggregates_in_sql(db):
    """Revision bursts are counted per run by GROUP BY, never by loading the events."""
    sync_registry(db, [spec("s1")])
    a, b = _run(db, "k1", "verified"), _run(db, "k2", "verified")
    for i in range(150):
        db.add_event(NOV13, "revision", a, {"series_id": "s1", "period": str(1900 + i)})
    for _ in range(3):
        db.add_event(NOV13, "revision", b, {})
    db.add_event(NOV01, "revision", b, {})          # before `since`
    db.add_event(NOV13, "new_periods", a, {})        # another kind
    db.add_event(NOV13, "revision", None, {})        # no run
    since = "2026-11-05T00:00:00+00:00"
    assert db.event_counts_by_run(since, "revision") == {a: 150, b: 3, None: 1}
    assert db.event_counts_by_run(since, "withdrawal") == {}
    assert db.event_counts_by_run(since, "revision", min_count=3) == {a: 150, b: 3}
    assert db.event_counts_by_run(since, "revision", limit=1) == {a: 150}


def test_failed_fetch_streaks_count_trailing_failed_fetch_runs_per_dataset(db):
    sync_registry(db, [spec("s1")])
    _run(db, "k1", "verified")
    _run(db, "k1", "failed-fetch", "2026-11-02T00:00:00+00:00")
    k1_last = _run(db, "k1", "failed-fetch", "2026-11-03T00:00:00+00:00")
    _run(db, "k2", "failed-fetch")
    _run(db, "k2", "verified")                        # streak broken by a later success
    for d in ("04", "05", "06"):
        k3_last = _run(db, "k3", "failed-fetch", f"2026-11-{d}T00:00:00+00:00")
    _run(db, "k3", "running", "2026-11-07T00:00:00+00:00")  # in flight: not a breaker
    _run(db, "k4", "failed-fetch")                    # streak 1: under the threshold
    assert db.failed_fetch_streaks(2) == [
        {"dataset_key": "k1", "source": "fake", "streak": 2, "last_run_id": k1_last,
         "last_started_at": "2026-11-03T00:00:00+00:00"},
        {"dataset_key": "k3", "source": "fake", "streak": 3, "last_run_id": k3_last,
         "last_started_at": "2026-11-06T00:00:00+00:00"}]
    assert [s["dataset_key"] for s in db.failed_fetch_streaks(1)] == ["k1", "k3", "k4"]


def test_new_period_spans_summarise_multi_period_events(db):
    sync_registry(db, [spec("s1"), spec("s2")])
    run = _run(db, "k1", "verified")
    db.add_event(NOV13, "new_periods", run, {"series_id": "s1",
                                             "periods": ["2021", "2024", "2022"]})
    db.add_event(NOV13, "new_periods", run, {"series_id": "s2", "periods": ["2024"]})
    db.add_event(NOV01, "new_periods", run, {"series_id": "s2", "periods": ["1", "3"]})
    since = "2026-11-05T00:00:00+00:00"
    [got] = db.new_period_spans(since, 10)
    assert got == {"event_id": got["event_id"], "ts": NOV13, "run_id": run,
                   "series_id": "s1", "n": 3, "first": "2021", "last": "2024"}
    assert db.new_period_spans(since, 0) == []


def test_quarantine_summary_groups_by_source_and_reason(db):
    from ingest.validate import Rejection
    sync_registry(db, [spec("s1"), spec("s2")])
    r1 = _run(db, "k1", "verified")
    r2 = _run(db, "k2", "failed-validation")
    db.write_quarantine(r1, "s1", [Rejection("2023", "n/a", "non_numeric"),
                                   Rejection("2022", "x", "non_numeric")], NOV13)
    db.write_quarantine(r2, "s2", [Rejection("2021", "y", "non_numeric")],
                        "2026-11-14T00:00:00+00:00")
    db.write_quarantine(r2, "s2", [Rejection("??", "1", "bad_period")], NOV13)
    db.write_quarantine(r1, "s1", [Rejection("1999", "z", "non_numeric")], NOV01)  # too old
    got = db.quarantine_summary("2026-11-05T00:00:00+00:00", 10)
    assert got == [
        {"source": "fake", "reason": "bad_period", "rows": 1, "series": 1, "runs": 1,
         "last_created_at": NOV13},
        {"source": "fake", "reason": "non_numeric", "rows": 3, "series": 2, "runs": 2,
         "last_created_at": "2026-11-14T00:00:00+00:00"}]
    assert len(db.quarantine_summary("2026-11-05T00:00:00+00:00", 1)) == 1


def test_series_periods_lists_every_stored_period_any_run_state(db):
    sync_registry(db, [spec("s1")])
    _direct_verified(db, "s1", "2022", "1", NOV01, "k1")
    bad = _direct_verified(db, "s1", "2023", "9", "2026-11-05T00:00:00+00:00", "k2")
    db.withdraw_run(bad, "unit defect", "2026-11-06T00:00:00+00:00")
    _pending(db, "s1", "2024", "1.1", NOV13, "k3")
    _pending(db, "s1", "2022", "1.5", NOV13, "k4")
    total, rows = db.series_periods("s1", 10)
    assert total == 3
    assert rows == [{"period": "2024", "rows": 1, "served": False},
                    {"period": "2023", "rows": 1, "served": False},
                    {"period": "2022", "rows": 2, "served": True}]
    assert db.series_periods("s1", 1) == (3, rows[:1])
    assert db.series_periods("nope", 10) == (0, [])


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
                db.event_counts_by_run(None, "revision"), db.failed_fetch_streaks(1),
                db.new_period_spans(None, 5), db.quarantine_summary(None, 5),
                db.series_periods("s1", 5))
    obs, vint, quar, items, raws, evs, counts, streaks, spans, qsum, periods = \
        read_db_readonly(path, read)
    assert obs[0] == 1 and vint[0]["served"] and quar == [] and items == []
    assert raws[0]["run_id"] == run and evs == [] and counts == {} and streaks == []
    assert spans == [] and qsum == [] and periods == (1, [{"period": "2024", "rows": 1,
                                                           "served": True}])
