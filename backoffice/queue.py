"""Review queue: the events and states that need a human, derived at read time.

A pure function of the status report (ingest.status.build_status), the data-lag hits
(ingest.data_lag.lagging_series), recent events of the per-event kinds (Db.recent_events) and
SQL aggregates (Db.event_counts_by_run, Db.failed_fetch_streaks, Db.new_period_spans,
Db.quarantine_summary). Nothing is stored and nothing is read here: v1 keeps no queue state.

Event kinds the pipeline emits and what the queue does with them:
- verification_failure, verification_escalated, format_change, stale_refusal: high, one item
  per event (format_change includes the per-series `no_valid_observations` event written inside
  an otherwise successful run: that series silently stopped receiving data);
- operational_failure, verifier_outage: medium, one item per event; a verifier_outage whose run
  also has a verification_escalated event is already covered by that high item;
- fetch_failure: medium, as a streak (STREAK_ALERT or more consecutive failed-fetch runs of one
  dataset, Db.failed_fetch_streaks); a single failure is retried by the scheduler;
- revision: info, per run at REVISION_BURST or more (counted in SQL);
- new_periods: info, when the periods one event added are not contiguous (new_period_gap);
  PT15M series are not judged (their day-level ordinal cannot count quarter-hours);
- refetch, withdrawal, series_deactivated: not queued (each is the record of an action already
  taken; the overview's per-source event counts show them).
State-derived items: stuck_pending (high, the report's PendingRun.stale), scheduler_streak
(medium, a dataset's scheduler failure_streak >= STREAK_ALERT), stale_series and lagging_series
(medium), blocked_source and quarantine (info: quarantine is routine data hygiene, worth a look
when a reason or a count is new).

Detail values are passed through verbatim as data (publisher strings and event details are
untrusted); escaping them is the template's job.
"""
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from ingest.data_lag import Lagging, period_index
from ingest.status import StatusReport

Severity = Literal["high", "medium", "info"]

EVENT_WINDOW = timedelta(days=7)    # events older than this no longer open an item
REVISION_BURST = 100                # revision events in one run that make it worth a look
STREAK_ALERT = 2                    # consecutive failures of one dataset that need a human

# per-event kinds: event kind -> (queue item kind, severity)
EVENT_RULES: dict[str, tuple[str, Severity]] = {
    "verification_failure": ("verification_failed", "high"),
    "verification_escalated": ("verification_escalated", "high"),
    "format_change": ("format_change", "high"),
    "stale_refusal": ("stale_refusal", "high"),
    "operational_failure": ("operational_failure", "medium"),
    "verifier_outage": ("verifier_outage", "medium"),
}
_GAP_FREQUENCIES = {"A", "S", "Q", "M", "D"}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "info": 2}


@dataclass(frozen=True)
class QueueItem:
    kind: str
    severity: Severity
    ref: str
    summary: str
    detail: dict = field(default_factory=dict)


def _ts(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _run_ref(run_id: int | None, event_id: int) -> str:
    return f"run:{run_id}" if run_id is not None else f"event:{event_id}"


def _event_summary(e: dict) -> str:
    d = e["detail"] if isinstance(e["detail"], dict) else {}
    what = " ".join(str(d[k]) for k in ("series_id", "reason", "stage") if d.get(k))
    return f"{e['kind']} at {e['ts']}" + (f": {what}" if what else "")


def _gap(span: dict, frequency: str | None) -> int | None:
    """Periods between the first and last added period that this addition did not add."""
    if frequency not in _GAP_FREQUENCIES:
        return None
    try:
        width = period_index(frequency, span["last"]) - period_index(frequency, span["first"])
    except (TypeError, ValueError):
        return None
    return width + 1 - span["n"]


def derive_queue(report: StatusReport, lagging: list[Lagging], events: Iterable[dict] = (), *,
                 revisions: Mapping[int | None, int] | None = None,
                 fetch_streaks: Iterable[dict] = (), new_periods: Iterable[dict] = (),
                 quarantine: Iterable[dict] = (),
                 frequency_of: Mapping[str, str] | None = None,
                 now: datetime | None = None) -> list[QueueItem]:
    """Queue items sorted by severity (high, medium, info), then kind, then ref (rules in the
    module docstring). `events` are events of the EVENT_RULES kinds; one whose ts is older
    than EVENT_WINDOW is dropped (an unparseable ts is kept: its age is unknown).
    `revisions` is run id -> revision events in the window; `frequency_of` maps series id to
    registry frequency for the new-period gap check."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - EVENT_WINDOW
    recent = [e for e in events if (t := _ts(e["ts"])) is None or t >= cutoff]
    escalated = {e["run_id"] for e in recent if e["kind"] == "verification_escalated"}
    items: list[QueueItem] = []

    for e in recent:
        rule = EVENT_RULES.get(e["kind"])
        if rule is None or (e["kind"] == "verifier_outage" and e["run_id"] in escalated):
            continue
        items.append(QueueItem(
            rule[0], rule[1], _run_ref(e["run_id"], e["id"]), _event_summary(e),
            {"event_id": e["id"], "ts": e["ts"], "run_id": e["run_id"], "detail": e["detail"]}))

    for s in report.sources:
        for p in s.pending_runs:
            if p.stale:
                items.append(QueueItem(
                    "stuck_pending", "high", f"run:{p.run_id}",
                    f"pending verification since {p.started_at}; remedy: "
                    f"python -m ingest verify {p.run_id}", asdict(p)))
        for d in s.datasets:
            if d.scheduler is not None and d.scheduler.failure_streak >= STREAK_ALERT:
                items.append(QueueItem(
                    "scheduler_streak", "medium", d.label,
                    f"{d.scheduler.failure_streak} consecutive scheduler attempts not verified "
                    f"(last {d.scheduler.last_attempt_state} at {d.scheduler.last_attempt_at})",
                    {"source": s.name, **asdict(d.scheduler)}))
        if s.stale > 0:
            items.append(QueueItem(
                "stale_series", "medium", s.name, f"{s.stale} stale active series",
                {"stale": s.stale, "stale_series": list(s.stale_series)}))
        if s.blockers:
            items.append(QueueItem(
                "blocked_source", "info", s.name, f"blocked: {', '.join(s.blockers)}",
                {"blockers": list(s.blockers)}))

    for f in fetch_streaks:
        if f["streak"] >= STREAK_ALERT:
            items.append(QueueItem(
                "fetch_failure_streak", "medium", f["dataset_key"],
                f"{f['streak']} consecutive failed fetches (last run {f['last_run_id']} at "
                f"{f['last_started_at']})", dict(f)))

    for g in lagging:
        items.append(QueueItem(
            "lagging_series", "medium", g.series_id,
            f"newest period {g.latest_period} is {g.lag} periods behind (allowance "
            f"{g.max_lag})",
            {"frequency": g.frequency, "latest_period": g.latest_period, "lag": g.lag,
             "max_lag": g.max_lag}))

    for run_id, n in (revisions or {}).items():
        if n >= REVISION_BURST:
            items.append(QueueItem(
                "revision_burst", "info", f"run:{run_id}", f"{n} revisions in one run",
                {"run_id": run_id, "revisions": n}))

    for span in new_periods:
        holes = _gap(span, (frequency_of or {}).get(span["series_id"]))
        if holes:
            items.append(QueueItem(
                "new_period_gap", "info", span["series_id"],
                f"run {span['run_id']} added {span['n']} periods {span['first']}..{span['last']}"
                f", not contiguous: {holes} periods between them were not in this addition "
                "(already held, or missing)", {**span, "holes": holes}))

    for q in quarantine:
        items.append(QueueItem(
            "quarantine", "info", q["source"],
            f"{q['rows']} rows quarantined ({q['reason']}) in {q['series']} series over "
            f"{q['runs']} runs, last {q['last_created_at']}", dict(q)))

    return sorted(items, key=lambda i: (_SEVERITY_ORDER[i.severity], i.kind, i.ref))
