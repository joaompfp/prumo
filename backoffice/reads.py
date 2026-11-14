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
from ingest.status import StatusReport, build_status

# Revision bursts are counted per run from the events themselves: one Eurostat run alone
# emits ~150 revision events, so the page reads every queue-relevant event of the window and
# says so when even this ceiling is reached (the counts would then be a lower bound).
QUEUE_EVENT_KINDS = ["verification_failure", "verification_escalated", "revision"]
QUEUE_EVENT_LIMIT = 200_000
OBSERVATION_CAP = 200   # newest served rows shown on a series page (the total is always shown)
DETAIL_LIST_CAP = 200   # quarantine rows / verification items shown on a series page


def overview(db: Db, specs: list[SeriesSpec], now: datetime) -> StatusReport:
    return build_status(db, specs, now=lambda: now)


@dataclass(frozen=True)
class Queue:
    items: list[QueueItem]
    truncated: bool  # the event read hit QUEUE_EVENT_LIMIT


def queue(db: Db, specs: list[SeriesSpec], now: datetime) -> Queue:
    report = build_status(db, specs, now=lambda: now)
    lagging = lagging_series(specs, db.latest_fetched_periods(), now.date())
    events = db.recent_events((now - EVENT_WINDOW).isoformat(), QUEUE_EVENT_KINDS,
                              QUEUE_EVENT_LIMIT)
    stuck = db.runs_in_state("pending-verification",
                             older_than=(now - STUCK_PENDING_AFTER).isoformat())
    return Queue(derive_queue(report, lagging, events, stuck, now=now),
                 len(events) >= QUEUE_EVENT_LIMIT)
