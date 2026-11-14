"""Page data assembled from one read-only Db handle (no SQL here: every query is a Db method).

Each function takes the open Db first so the app can pass it to ingest.db.read_db_readonly,
which opens the database strictly read-only and retries once on a concurrent writer.
"""
from dataclasses import dataclass
from datetime import datetime

from backoffice.queue import EVENT_WINDOW, STUCK_PENDING_AFTER, QueueItem, derive_queue
from ingest.data_lag import lagging_series
from ingest.db import Db
from ingest.models import SeriesSpec
from ingest.status import SeriesStatus, SourceStatus, StatusReport, build_status

# Revision bursts are counted per run from the events themselves: one Eurostat run alone
# emits ~150 revision events, so the page reads every queue-relevant event of the window and
# says so when even this ceiling is reached (the counts would then be a lower bound).
QUEUE_EVENT_KINDS = ["verification_failure", "verification_escalated", "revision"]
QUEUE_EVENT_LIMIT = 200_000
OBSERVATION_CAP = 200   # newest served rows shown on a series page (the total is always shown)
DETAIL_LIST_CAP = 200   # quarantine rows / verification items shown on a series page


def status_report(db: Db, specs: list[SeriesSpec], now: datetime) -> StatusReport:
    """The full-registry `ingest status` report: the one status every page shows."""
    return build_status(db, specs, now=lambda: now)


@dataclass(frozen=True)
class Queue:
    items: list[QueueItem]
    truncated: bool  # the event read hit QUEUE_EVENT_LIMIT


def queue(db: Db, specs: list[SeriesSpec], report: StatusReport, now: datetime) -> Queue:
    lagging = lagging_series(specs, db.latest_fetched_periods(), now.date())
    events = db.recent_events((now - EVENT_WINDOW).isoformat(), QUEUE_EVENT_KINDS,
                              QUEUE_EVENT_LIMIT)
    stuck = db.runs_in_state("pending-verification",
                             older_than=(now - STUCK_PENDING_AFTER).isoformat())
    return Queue(derive_queue(report, lagging, events, stuck, now=now),
                 len(events) >= QUEUE_EVENT_LIMIT)


def status_label(st: SeriesStatus) -> str:
    """One honest word for a series' state, from ingest.status (never re-derived here)."""
    if st.stale_reason == "never_fetched":
        return "never fetched"
    if st.stale_reason == "never_verified":
        return "never verified"
    if st.availability == "legacy-unverified":
        return "legacy only (unverified)"
    if st.stale_reason == "pinned_bundle_only":
        return "stale (pinned bundle only)"
    return "stale" if st.stale else "verified, current"


def series_statuses(report: StatusReport) -> dict[str, SeriesStatus]:
    return {st.id: st for src in report.sources for st in src.series}


@dataclass(frozen=True)
class SeriesDetail:
    status: SeriesStatus
    source: SourceStatus
    total: int
    observations: list[dict]
    raw_fetches: list[dict]
    quarantine: list[dict]
    items: list[dict]
    vintages: list[dict] | None  # only when a period was asked for


def series_detail(db: Db, spec: SeriesSpec, report: StatusReport,
                  period: str | None) -> SeriesDetail:
    source = next(s for s in report.sources if s.name == spec.source.name)
    status = next(s for s in source.series if s.id == spec.id)
    total, rows = db.series_observations(spec.id, OBSERVATION_CAP)
    return SeriesDetail(
        status, source, total, rows, db.series_raw_fetches(spec.id),
        db.series_quarantine(spec.id, DETAIL_LIST_CAP),
        db.series_verification_items(spec.id, DETAIL_LIST_CAP),
        db.series_vintages(spec.id, period) if period else None)


PAGE_SIZE = 100  # series per list page


def filter_specs(specs: list[SeriesSpec], *, source: str = "", theme: str = "",
                 geography: str = "", frequency: str = "", active: str = "",
                 q: str = "") -> list[SeriesSpec]:
    """Registry series matching every non-empty filter, by id. active is 'yes', 'no' or ''
    (any); q is a case-insensitive substring of id, indicator key or native code."""
    needle = q.strip().lower()
    out = [s for s in specs
           if (not source or s.source.name == source) and (not theme or s.theme == theme)
           and (not geography or s.geography == geography)
           and (not frequency or s.frequency == frequency)
           and (not active or s.active == (active == "yes"))
           and (not needle or any(needle in (v or "").lower()
                                  for v in (s.id, s.indicator_key, s.native_code)))]
    return sorted(out, key=lambda s: s.id)
