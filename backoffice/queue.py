"""Review queue: the events and states that need a human, derived at read time.

A pure function of the status report (ingest.status.build_status), the data-lag hits
(ingest.data_lag.lagging_series), recent events (Db.recent_events) and stuck pending runs
(Db.runs_in_state). Nothing is stored and nothing is read here: v1 keeps no queue state.

Detail values are passed through verbatim as data (publisher strings and event details are
untrusted); escaping them is the template's job.
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from ingest.data_lag import Lagging
from ingest.status import StatusReport

Severity = Literal["high", "medium", "info"]

EVENT_WINDOW = timedelta(days=7)    # events older than this no longer open an item
REVISION_BURST = 100                # revision events in one run that make it worth a look
STUCK_PENDING_AFTER = timedelta(hours=24)  # caller's cut-off for Db.runs_in_state(older_than=)

_VERIFICATION_KINDS = {"verification_failure": "verification_failed",
                       "verification_escalated": "verification_escalated"}
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


def derive_queue(report: StatusReport, lagging: list[Lagging], events: list[dict],
                 stuck_pending: list[dict], now: datetime | None = None) -> list[QueueItem]:
    """Queue items sorted by severity (high, medium, info), then kind, then ref.

    - verification_failed / verification_escalated (high): one per such event in the last
      EVENT_WINDOW (an event whose ts cannot be parsed is kept: its age is unknown);
    - stuck_pending (high): one per run in `stuck_pending` (the caller selects runs pending
      verification for more than STUCK_PENDING_AFTER);
    - stale_series (medium): one per source with stale active series;
    - lagging_series (medium): one per data-lag hit;
    - blocked_source (info): one per source with a licence/verifiability blocker;
    - revision_burst (info): one per run with >= REVISION_BURST revision events in the window.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - EVENT_WINDOW
    recent = [e for e in events if (t := _ts(e["ts"])) is None or t >= cutoff]
    items: list[QueueItem] = []

    for e in recent:
        kind = _VERIFICATION_KINDS.get(e["kind"])
        if kind is not None:
            items.append(QueueItem(
                kind, "high", _run_ref(e["run_id"], e["id"]),
                f"{e['kind']} at {e['ts']}",
                {"event_id": e["id"], "ts": e["ts"], "run_id": e["run_id"],
                 "detail": e["detail"]}))

    for r in stuck_pending:
        items.append(QueueItem(
            "stuck_pending", "high", f"run:{r['run_id']}",
            f"pending verification since {r['started_at']}; remedy: "
            f"python -m ingest verify {r['run_id']}", dict(r)))

    for s in report.sources:
        if s.stale > 0:
            items.append(QueueItem(
                "stale_series", "medium", s.name, f"{s.stale} stale active series",
                {"stale": s.stale, "stale_series": list(s.stale_series)}))
        if s.blockers:
            items.append(QueueItem(
                "blocked_source", "info", s.name, f"blocked: {', '.join(s.blockers)}",
                {"blockers": list(s.blockers)}))

    for g in lagging:
        items.append(QueueItem(
            "lagging_series", "medium", g.series_id,
            f"newest period {g.latest_period} is {g.lag} periods behind (allowance "
            f"{g.max_lag})",
            {"frequency": g.frequency, "latest_period": g.latest_period, "lag": g.lag,
             "max_lag": g.max_lag}))

    revisions = Counter(e["run_id"] for e in recent if e["kind"] == "revision")
    for run_id, n in revisions.items():
        if n >= REVISION_BURST:
            items.append(QueueItem(
                "revision_burst", "info", f"run:{run_id}", f"{n} revisions in one run",
                {"run_id": run_id, "revisions": n}))

    return sorted(items, key=lambda i: (_SEVERITY_ORDER[i.severity], i.kind, i.ref))
