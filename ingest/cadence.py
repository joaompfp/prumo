"""Refresh-cadence knowledge - the ONE authoritative copy of 'how often we try to refresh a
series' (extracted from ingest.status in Task 18A so the status projection and the scheduler
share it; previously private to status.py).

This is OUR refresh-policy interval, never a claimed publisher release cadence:
- a series' explicit registry `schedule` ('12h', '1d', '7d' - Ruling G) wins when present and
  parseable; an unparseable schedule raises (fail fast: a malformed registry value must
  surface loudly, never be silently ignored);
- otherwise the frequency default applies (A/S = 30d, Q = 7d, M/D/PT15M = 1d).

ingest.status derives staleness from it; ingest.scheduler derives due/backoff from it.
The retry backoff after a failed or interrupted scheduler attempt (1h, 4h, then 12h) and the
resulting next-eligible time live here too, so `status` reports exactly the time the
scheduler will use (Task 23, D-M4).
"""
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from ingest.models import SeriesSpec

# Frequency-based refresh defaults. Kept semantics-identical to the pre-extraction
# status.DEFAULT_STALE_AFTER (status re-exports it under that compatible alias).
DEFAULT_INTERVAL: dict[str, timedelta] = {
    "A": timedelta(days=30), "S": timedelta(days=30), "Q": timedelta(days=7),
    "M": timedelta(days=1), "D": timedelta(days=1), "PT15M": timedelta(days=1),
}

_SCHEDULE_UNITS = {"h": timedelta(hours=1), "d": timedelta(days=1),
                   "w": timedelta(weeks=1)}


def series_interval(spec: SeriesSpec) -> timedelta:
    """The refresh-policy interval of ONE series: explicit `schedule` ('12h'/'1d'/'7d') when
    set (its integer count must be positive and its unit one of h/d/w, else ValueError), else
    the frequency default."""
    if spec.schedule:
        unit = _SCHEDULE_UNITS.get(spec.schedule[-1])
        if unit and spec.schedule[:-1].isdigit() and int(spec.schedule[:-1]) > 0:
            return int(spec.schedule[:-1]) * unit
        raise ValueError(f"series {spec.id!r}: unparseable schedule {spec.schedule!r}")
    return DEFAULT_INTERVAL[spec.frequency]


def group_interval(specs: Iterable[SeriesSpec]) -> timedelta:
    """The refresh interval of ONE authoritative dataset group (operations.DatasetGroup.specs):
    the MINIMUM over its member series - a group runs whole, so its most frequent member
    drives how often the group is refreshed. Requires a non-empty group."""
    return min(series_interval(s) for s in specs)


# Retry backoff after a failed or interrupted scheduler attempt, by failure streak (capped).
BACKOFF = (timedelta(hours=1), timedelta(hours=4), timedelta(hours=12))


def _utc(value: datetime) -> datetime:
    # Stored timestamps without an offset are naive UTC, never the host's local timezone.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def next_eligible_at(interval: timedelta, *, failure_streak: int, last_attempt_at: str,
                     last_finished_at: str | None, last_success_at: str | None) -> datetime | None:
    """When a dataset group with persisted scheduler state may next be attempted; None means
    immediately (no success recorded and no failure streak).

    A failure streak waits BACKOFF[streak] from the attempt's finish, or from its start when
    the process died mid-attempt (no finish recorded). Otherwise the healthy refresh interval
    runs from the last success (inclusive boundary)."""
    if failure_streak:
        anchor = datetime.fromisoformat(last_finished_at or last_attempt_at)
        return _utc(anchor) + BACKOFF[min(failure_streak, len(BACKOFF)) - 1]
    if last_success_at is None:
        return None
    return _utc(datetime.fromisoformat(last_success_at)) + interval
