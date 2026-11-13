"""Refresh-cadence knowledge - the ONE authoritative copy of 'how often we try to refresh a
series' (extracted from ingest.status in Task 18A so the status projection and the scheduler
share it; previously private to status.py).

This is OUR refresh-policy interval, never a claimed publisher release cadence:
- a series' explicit registry `schedule` ('12h', '1d', '7d' - Ruling G) wins when present and
  parseable; an unparseable schedule raises (fail fast: a malformed registry value must
  surface loudly, never be silently ignored);
- otherwise the frequency default applies (A/S = 30d, Q = 7d, M/D/PT15M = 1d).

ingest.status derives staleness from it; ingest.scheduler derives due/backoff from it.
"""
from collections.abc import Iterable
from datetime import timedelta

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
