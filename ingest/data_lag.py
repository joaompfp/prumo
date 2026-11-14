"""Data-time lag: is an ACTIVE series' newest fetched period far behind today? (final review
C-I1, widening Ruling W beyond 'last value < 2024 with a newer-base sibling').

This is about DATA time (the newest period the publisher gave us), not retrieval time
(ingest.status 'stale' = our refresh policy) and not a publisher release calendar. A series
can be fetched and verified every day and still sit on a dataset the publisher froze
(prc_hicp_midx stopped at 2025-12 when Eurostat moved the HICP to ECOICOP ver.2).

Allowance (MAX_LAG, whole periods between today's period and the newest fetched period).
Chosen to sit above normal publication delays, so a hit means 'investigate', never 'wrong':
- A 3 years   (World Bank / Eurostat annual tables publish t-1..t-2; surveys like Gini are sparser)
- S 3 halves  (Eurostat bi-annual prices appear ~4-5 months after the half)
- Q 4 quarters
- M 6 months  (monthly releases lag 1-3 months)
- D 30 days, PT15M 7 days (daily/quarter-hour feeds lag hours to days)
A flagged series is reported, never deactivated automatically: deactivation needs evidence
that the publisher discontinued or froze the dataset (registry/unmapped-<source>.md).
"""
from dataclasses import dataclass
from datetime import date

from ingest.models import SeriesSpec

MAX_LAG: dict[str, int] = {"A": 3, "S": 3, "Q": 4, "M": 6, "D": 30, "PT15M": 7}


def _index(frequency: str, period: str) -> int:
    """Ordinal of a canonical period (ingest.models.normalize_period spelling)."""
    try:
        if frequency == "A" and len(period) == 4:
            return int(period)
        if frequency == "S" and period[4:6] == "-S" and period[6:] in ("1", "2"):
            return int(period[:4]) * 2 + int(period[6:]) - 1
        if frequency == "Q" and period[4:6] == "-Q" and period[6:] in ("1", "2", "3", "4"):
            return int(period[:4]) * 4 + int(period[6:]) - 1
        if frequency == "M" and len(period) == 7 and 1 <= int(period[5:]) <= 12:
            return int(period[:4]) * 12 + int(period[5:]) - 1
        if frequency in ("D", "PT15M"):
            return date.fromisoformat(period[:10]).toordinal()
    except ValueError:
        pass
    raise ValueError(f"not a canonical {frequency} period: {period!r}")


def _today(frequency: str, today: date) -> int:
    return {"A": today.year, "S": today.year * 2 + (today.month - 1) // 6,
            "Q": today.year * 4 + (today.month - 1) // 3,
            "M": today.year * 12 + today.month - 1}.get(frequency, today.toordinal())


def period_lag(frequency: str, latest_period: str, today: date) -> int:
    """Whole periods between today's period and `latest_period` (0 = today's period)."""
    return _today(frequency, today) - _index(frequency, latest_period)


@dataclass(frozen=True)
class Lagging:
    series_id: str
    frequency: str
    latest_period: str
    lag: int
    max_lag: int


def lagging_series(specs: list[SeriesSpec], latest: dict[str, str], today: date) -> list[Lagging]:
    """Active series whose newest fetched period lags beyond MAX_LAG, by id. Series without
    fetched data are not judged here (the caller lists them separately)."""
    out = []
    for s in sorted((s for s in specs if s.active and s.id in latest), key=lambda s: s.id):
        lag = period_lag(s.frequency, latest[s.id], today)
        if lag > MAX_LAG[s.frequency]:
            out.append(Lagging(s.id, s.frequency, latest[s.id], lag, MAX_LAG[s.frequency]))
    return out
