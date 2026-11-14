"""Backoffice v1, Task 2: the review queue is a pure derivation from the status report,
data-lag hits, recent events and SQL aggregates (no DB access, no stored state)."""
from datetime import datetime, timezone

from backoffice.queue import QueueItem, derive_queue
from ingest.data_lag import Lagging
from ingest.status import DatasetStatus, PendingRun, SchedulerView, SourceStatus, StatusReport

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def _source(name, *, stale=0, stale_series=(), blockers=(), pending_runs=(), datasets=()):
    return SourceStatus(
        name=name, verifiable="not_verifiable" not in blockers,
        redistribution_ok="licence_withheld" not in blockers, blockers=tuple(blockers),
        active_series=3, inactive_series=0, latest_attempt=None, latest_attempt_state=None,
        last_verified=None, real_data_fetched_at=None, last_confirmed_current=None,
        stale=stale, never_fetched=0, never_verified=0, stale_series=tuple(stale_series),
        events={}, events_24h={}, events_7d={}, scheduler_retrying=0, scheduler_running=0,
        scheduler_max_streak=0, pending_runs=tuple(pending_runs), datasets=tuple(datasets),
        series=())


def _report(*sources):
    return StatusReport(generated_at=NOW.isoformat(), sources=tuple(sources), totals={})


def _event(id, kind, ts="2026-11-14T00:00:00+00:00", run_id=7, detail=None):
    return {"id": id, "ts": ts, "kind": kind, "run_id": run_id, "detail": detail or {}}


def _pending(run_id, started_at="2026-11-12T00:00:00+00:00", stale=True):
    return PendingRun(run_id, "eurostat:abc", "eurostat", started_at, "live", stale)


def _dataset(label, streak):
    view = SchedulerView("2026-11-14T00:00:00+00:00", "failed-fetch", None, None, streak, None)
    return DatasetStatus(label, "failed-fetch", "2026-11-14T00:00:00+00:00", "live", view)


def test_empty_inputs_give_empty_queue():
    assert derive_queue(_report(), [], now=NOW) == []


def test_failed_verification_event_is_high():
    items = derive_queue(_report(), [], [
        _event(1, "verification_failure", detail={"mismatches": 2}),
        _event(2, "verification_escalated", run_id=8)], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("verification_escalated", "high", "run:8"),
        ("verification_failed", "high", "run:7")]
    assert items[1].detail["event_id"] == 1
    assert items[1].detail["detail"] == {"mismatches": 2}
    assert all(isinstance(i, QueueItem) and i.summary for i in items)


def test_events_older_than_7_days_ignored():
    old = _event(1, "verification_failure", ts="2026-11-07T11:59:59+00:00")
    edge = _event(2, "verification_failure", ts="2026-11-07T12:00:00+00:00", run_id=9)
    items = derive_queue(_report(), [], [old, edge], now=NOW)
    assert [i.ref for i in items] == ["run:9"]


def test_stuck_pending_is_high_and_comes_from_the_status_report():
    """The report's own PendingRun.stale (status.PENDING_STALE_AFTER) decides, so the queue
    and the overview's pending_stuck total can never disagree."""
    report = _report(_source("eurostat", pending_runs=[_pending(42), _pending(43, stale=False)]))
    [item] = derive_queue(report, [], now=NOW)
    assert (item.kind, item.severity, item.ref) == ("stuck_pending", "high", "run:42")
    assert "python -m ingest verify 42" in item.summary
    assert item.detail["started_at"] == "2026-11-12T00:00:00+00:00"


def test_stale_and_lagging_are_medium():
    report = _report(_source("ine", stale=2, stale_series=("ine.a", "ine.b")), _source("bp"))
    lag = [Lagging("wb.x", "A", "2019", 7, 3)]
    items = derive_queue(report, lag, now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("lagging_series", "medium", "wb.x"), ("stale_series", "medium", "ine")]
    assert items[1].detail["stale_series"] == ["ine.a", "ine.b"]
    assert items[0].detail == {"frequency": "A", "latest_period": "2019", "lag": 7,
                               "max_lag": 3}


def test_blocked_sources_are_info_only():
    report = _report(_source("fred", blockers=("licence_withheld",)),
                     _source("dgeg", blockers=("not_verifiable", "licence_withheld")),
                     _source("ine"))
    items = derive_queue(report, [], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("blocked_source", "info", "dgeg"), ("blocked_source", "info", "fred")]
    assert items[0].detail["blockers"] == ["not_verifiable", "licence_withheld"]


def test_revision_burst_is_info_per_run_at_threshold():
    """Counts come pre-aggregated per run (Db.event_counts_by_run), never as events."""
    items = derive_queue(_report(), [], revisions={5: 100, 6: 99, 7: 150}, now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("revision_burst", "info", "run:5"), ("revision_burst", "info", "run:7")]
    assert items[0].detail["revisions"] == 100
    assert items[1].summary == "150 revisions in one run"


def test_sorting_is_severity_then_kind_then_ref():
    report = _report(_source("zz", stale=1, stale_series=("zz.1",), pending_runs=[_pending(2)]),
                     _source("aa", blockers=("licence_withheld",)))
    items = derive_queue(
        report, [Lagging("b", "M", "2020-01", 70, 6), Lagging("a", "M", "2020-01", 70, 6)],
        [_event(1, "verification_failure", run_id=3)], now=NOW)
    assert [(i.severity, i.kind, i.ref) for i in items] == [
        ("high", "stuck_pending", "run:2"), ("high", "verification_failed", "run:3"),
        ("medium", "lagging_series", "a"), ("medium", "lagging_series", "b"),
        ("medium", "stale_series", "zz"), ("info", "blocked_source", "aa")]


def test_detail_strings_are_not_interpreted():
    evil = {"reason": "<script>alert(1)</script>", "url": "javascript:alert(1)"}
    [item] = derive_queue(_report(), [], [_event(1, "verification_escalated", detail=evil)],
                          now=NOW)
    assert item.detail["detail"] == evil  # verbatim data; escaping is the template's job


def test_unrelated_event_kinds_are_ignored():
    evs = [_event(1, "refetch"), _event(2, "new_periods"), _event(3, "withdrawal"),
           _event(4, "revision"), _event(5, "series_deactivated")]
    assert derive_queue(_report(), [], evs, now=NOW) == []


def test_format_change_and_stale_refusal_are_high():
    """format_change includes the per-series no_valid_observations event emitted inside an
    otherwise successful run (pipeline Ruling M): a series silently stopped receiving data."""
    empty = {"series_id": "s9", "reason": "no_valid_observations", "n_raw_rows": 4,
             "n_quarantined": 4}
    items = derive_queue(_report(), [], [
        _event(1, "format_change", run_id=3, detail=empty),
        _event(2, "stale_refusal", run_id=4, detail={"error": "older bundle"})], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("format_change", "high", "run:3"), ("stale_refusal", "high", "run:4")]
    assert items[0].detail["detail"] == empty
    assert "s9" in items[0].summary and "no_valid_observations" in items[0].summary


def test_operational_failure_and_unescalated_verifier_outage_are_medium():
    items = derive_queue(_report(), [], [
        _event(1, "operational_failure", run_id=3, detail={"stage": "orphaned"}),
        _event(2, "verifier_outage", run_id=4, detail={"error": "503"}),
        _event(3, "verifier_outage", run_id=5, detail={"error": "503"}),
        _event(4, "verification_escalated", run_id=5,
               detail={"reason": "verifier_outage"})], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("verification_escalated", "high", "run:5"),
        ("operational_failure", "medium", "run:3"), ("verifier_outage", "medium", "run:4")]


def test_fetch_failure_and_scheduler_streaks_are_medium():
    report = _report(_source("ine", datasets=[_dataset("ine:a", 2), _dataset("ine:b", 1)]))
    streaks = [{"dataset_key": "ine:k", "source": "ine", "streak": 3, "last_run_id": 9,
                "last_started_at": "2026-11-14T00:00:00+00:00"}]
    items = derive_queue(report, [], fetch_streaks=streaks, now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("fetch_failure_streak", "medium", "ine:k"), ("scheduler_streak", "medium", "ine:a")]
    assert "3 consecutive" in items[0].summary
    assert items[1].detail["failure_streak"] == 2 and items[1].detail["source"] == "ine"


def test_new_period_gaps_are_info_and_need_a_known_frequency():
    spans = [
        {"event_id": 1, "ts": "x", "run_id": 3, "series_id": "a", "n": 2, "first": "2020",
         "last": "2023"},                                           # 2 holes
        {"event_id": 2, "ts": "x", "run_id": 3, "series_id": "m", "n": 3, "first": "2024-01",
         "last": "2024-03"},                                        # contiguous
        {"event_id": 3, "ts": "x", "run_id": 3, "series_id": "q", "n": 2, "first": "2024-Q1",
         "last": "2024-Q4"},                                        # 2 holes
        {"event_id": 4, "ts": "x", "run_id": 3, "series_id": "e", "n": 2,
         "first": "2024-01-01T00:00", "last": "2024-01-03T00:00"},  # PT15M: not judged
        {"event_id": 5, "ts": "x", "run_id": 3, "series_id": "zz", "n": 2, "first": "1",
         "last": "9"}]                                              # not in the registry
    freq = {"a": "A", "m": "M", "q": "Q", "e": "PT15M"}
    items = derive_queue(_report(), [], new_periods=spans, frequency_of=freq, now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("new_period_gap", "info", "a"), ("new_period_gap", "info", "q")]
    assert items[0].detail["holes"] == 2 and items[0].detail["run_id"] == 3


def test_quarantine_is_info_per_source_and_reason():
    rows = [{"source": "eurostat", "reason": "non_numeric", "rows": 40, "series": 3, "runs": 2,
             "last_created_at": "2026-11-14T00:00:00+00:00"}]
    [item] = derive_queue(_report(), [], quarantine=rows, now=NOW)
    assert (item.kind, item.severity, item.ref) == ("quarantine", "info", "eurostat")
    assert "40 rows" in item.summary and "non_numeric" in item.summary
    assert item.detail == rows[0]
