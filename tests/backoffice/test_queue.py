"""Backoffice v1, Task 2: the review queue is a pure derivation from the status report,
data-lag hits, recent events and stuck pending runs (no DB access, no stored state)."""
from datetime import datetime, timezone

from backoffice.queue import QueueItem, derive_queue
from ingest.data_lag import Lagging
from ingest.status import SourceStatus, StatusReport

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def _source(name, *, stale=0, stale_series=(), blockers=()):
    return SourceStatus(
        name=name, verifiable="not_verifiable" not in blockers,
        redistribution_ok="licence_withheld" not in blockers, blockers=tuple(blockers),
        active_series=3, inactive_series=0, latest_attempt=None, latest_attempt_state=None,
        last_verified=None, real_data_fetched_at=None, last_confirmed_current=None,
        stale=stale, never_fetched=0, never_verified=0, stale_series=tuple(stale_series),
        events={}, events_24h={}, events_7d={}, scheduler_retrying=0, scheduler_running=0,
        scheduler_max_streak=0, pending_runs=(), datasets=(), series=())


def _report(*sources):
    return StatusReport(generated_at=NOW.isoformat(), sources=tuple(sources), totals={})


def _event(id, kind, ts="2026-11-14T00:00:00+00:00", run_id=7, detail=None):
    return {"id": id, "ts": ts, "kind": kind, "run_id": run_id, "detail": detail or {}}


def _pending(run_id, started_at="2026-11-12T00:00:00+00:00"):
    return {"run_id": run_id, "source": "eurostat", "dataset_key": "eurostat:abc",
            "state": "pending-verification", "started_at": started_at, "finished_at": None,
            "input_origin": "live"}


def test_empty_inputs_give_empty_queue():
    assert derive_queue(_report(), [], [], [], now=NOW) == []


def test_failed_verification_event_is_high():
    items = derive_queue(_report(), [], [
        _event(1, "verification_failure", detail={"mismatches": 2}),
        _event(2, "verification_escalated", run_id=8)], [], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("verification_escalated", "high", "run:8"),
        ("verification_failed", "high", "run:7")]
    assert items[1].detail["event_id"] == 1
    assert items[1].detail["detail"] == {"mismatches": 2}
    assert all(isinstance(i, QueueItem) and i.summary for i in items)


def test_events_older_than_7_days_ignored():
    old = _event(1, "verification_failure", ts="2026-11-07T11:59:59+00:00")
    edge = _event(2, "verification_failure", ts="2026-11-07T12:00:00+00:00", run_id=9)
    items = derive_queue(_report(), [], [old, edge], [], now=NOW)
    assert [i.ref for i in items] == ["run:9"]


def test_stuck_pending_is_high():
    [item] = derive_queue(_report(), [], [], [_pending(42)], now=NOW)
    assert (item.kind, item.severity, item.ref) == ("stuck_pending", "high", "run:42")
    assert "python -m ingest verify 42" in item.summary
    assert item.detail["started_at"] == "2026-11-12T00:00:00+00:00"


def test_stale_and_lagging_are_medium():
    report = _report(_source("ine", stale=2, stale_series=("ine.a", "ine.b")), _source("bp"))
    lag = [Lagging("wb.x", "A", "2019", 7, 3)]
    items = derive_queue(report, lag, [], [], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("lagging_series", "medium", "wb.x"), ("stale_series", "medium", "ine")]
    assert items[1].detail["stale_series"] == ["ine.a", "ine.b"]
    assert items[0].detail == {"frequency": "A", "latest_period": "2019", "lag": 7,
                               "max_lag": 3}


def test_blocked_sources_are_info_only():
    report = _report(_source("fred", blockers=("licence_withheld",)),
                     _source("dgeg", blockers=("not_verifiable", "licence_withheld")),
                     _source("ine"))
    items = derive_queue(report, [], [], [], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [
        ("blocked_source", "info", "dgeg"), ("blocked_source", "info", "fred")]
    assert items[0].detail["blockers"] == ["not_verifiable", "licence_withheld"]


def test_revision_burst_is_info_per_run_at_threshold():
    revs = [_event(i, "revision", run_id=5) for i in range(100)]
    revs += [_event(1000 + i, "revision", run_id=6) for i in range(99)]
    revs += [_event(2000, "revision", ts="2026-11-01T00:00:00+00:00", run_id=6)]  # too old
    items = derive_queue(_report(), [], revs, [], now=NOW)
    assert [(i.kind, i.severity, i.ref) for i in items] == [("revision_burst", "info", "run:5")]
    assert items[0].detail["revisions"] == 100


def test_sorting_is_severity_then_kind_then_ref():
    report = _report(_source("zz", stale=1, stale_series=("zz.1",)),
                     _source("aa", blockers=("licence_withheld",)))
    items = derive_queue(
        report, [Lagging("b", "M", "2020-01", 70, 6), Lagging("a", "M", "2020-01", 70, 6)],
        [_event(1, "verification_failure", run_id=3)], [_pending(2)], now=NOW)
    assert [(i.severity, i.kind, i.ref) for i in items] == [
        ("high", "stuck_pending", "run:2"), ("high", "verification_failed", "run:3"),
        ("medium", "lagging_series", "a"), ("medium", "lagging_series", "b"),
        ("medium", "stale_series", "zz"), ("info", "blocked_source", "aa")]


def test_detail_strings_are_not_interpreted():
    evil = {"reason": "<script>alert(1)</script>", "url": "javascript:alert(1)"}
    [item] = derive_queue(_report(), [], [_event(1, "verification_escalated", detail=evil)],
                          [], now=NOW)
    assert item.detail["detail"] == evil  # verbatim data; escaping is the template's job


def test_unrelated_event_kinds_are_ignored():
    evs = [_event(1, "refetch"), _event(2, "new_periods"), _event(3, "withdrawal")]
    assert derive_queue(_report(), [], evs, [], now=NOW) == []
