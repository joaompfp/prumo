"""Page data assembled from one read-only Db handle (no SQL here: every query is a Db method).

Each function takes the open Db first so the app can pass it to ingest.db.read_db_readonly,
which opens the database strictly read-only and retries once on a concurrent writer.
"""
from dataclasses import dataclass
from datetime import datetime

from backoffice.queue import (
    EVENT_RULES,
    EVENT_WINDOW,
    REVISION_BURST,
    STREAK_ALERT,
    QueueItem,
    derive_queue,
)
from ingest.data_lag import lagging_series
from ingest.db import Db
from ingest.models import SeriesSpec
from ingest.status import SeriesStatus, SourceStatus, StatusReport, build_status

# The queue never loads events in bulk: revisions are counted per run in SQL
# (Db.event_counts_by_run), new_periods are summarised in SQL (Db.new_period_spans) and every
# per-event kind is read newest first with its own small limit. A kind that hits its limit is
# named on the page (its items may then be incomplete).
EVENTS_PER_KIND = 200
NEW_PERIOD_LIMIT = 500
REVISION_RUN_LIMIT = 200   # burst runs listed (largest first)
QUARANTINE_LIMIT = 200     # (source, reason) aggregate rows
QUEUE_EVENT_ROW_BOUND = (EVENTS_PER_KIND * len(EVENT_RULES) + NEW_PERIOD_LIMIT
                         + REVISION_RUN_LIMIT)  # most event-table rows one /queue read loads
OBSERVATION_CAP = 200   # newest served rows shown on a series page (the total is always shown)
DETAIL_LIST_CAP = 200   # quarantine rows / verification items shown on a series page
PERIOD_CAP = 200        # newest stored periods listed on a series page


def status_report(db: Db, specs: list[SeriesSpec], now: datetime) -> StatusReport:
    """The full-registry `ingest status` report: the one status every page shows."""
    return build_status(db, specs, now=lambda: now)


@dataclass(frozen=True)
class Queue:
    items: list[QueueItem]
    truncated: tuple[str, ...]  # reads that hit their limit (event kinds, 'new_periods',
                                # 'revision', 'quarantine')


def queue(db: Db, specs: list[SeriesSpec], report: StatusReport, now: datetime) -> Queue:
    since = (now - EVENT_WINDOW).isoformat()
    truncated: list[str] = []

    def capped(name: str, rows, limit: int):
        if len(rows) >= limit:
            truncated.append(name)
        return rows

    events = [e for kind in EVENT_RULES
              for e in capped(kind, db.recent_events(since, [kind], EVENTS_PER_KIND),
                              EVENTS_PER_KIND)]
    items = derive_queue(
        report, lagging_series(specs, db.latest_fetched_periods(), now.date()), events,
        revisions=capped("revision", db.event_counts_by_run(
            since, "revision", min_count=REVISION_BURST, limit=REVISION_RUN_LIMIT),
            REVISION_RUN_LIMIT),
        fetch_streaks=db.failed_fetch_streaks(STREAK_ALERT),
        new_periods=capped("new_periods", db.new_period_spans(since, NEW_PERIOD_LIMIT),
                           NEW_PERIOD_LIMIT),
        quarantine=capped("quarantine", db.quarantine_summary(since, QUARANTINE_LIMIT),
                          QUARANTINE_LIMIT),
        frequency_of={s.id: s.frequency for s in specs}, now=now)
    return Queue(items, tuple(truncated))


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
