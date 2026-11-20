"""Canonical native-period calendar positions.

Only the canonical ASCII spellings are accepted: ``YYYY``, ``YYYY-Sn``,
``YYYY-Qn``, ``YYYY-MM`` and ``YYYY-MM-DD`` for A/S/Q/M/D respectively.
Aliases such as ``2024-M01``, Portuguese month names, Unicode digits,
negative years or a zero year are not guessed at: they return ``None``.
"""
from __future__ import annotations

import re
from datetime import date

_FREQUENCY_PATTERNS = {
    "A": re.compile(r"([0-9]{4})"),
    "S": re.compile(r"([0-9]{4})-S([12])"),
    "Q": re.compile(r"([0-9]{4})-Q([1-4])"),
    "M": re.compile(r"([0-9]{4})-([0-9]{2})"),
    "D": re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})"),
}


def _match(period: str, frequency: str):
    if not isinstance(period, str) or not isinstance(frequency, str):
        return None
    pattern = _FREQUENCY_PATTERNS.get(frequency)
    if pattern is None:
        return None
    match = pattern.fullmatch(period)
    if match is None:
        return None
    try:
        year = int(match.group(1))
    except (TypeError, ValueError):
        return None
    if not 1 <= year <= 9999:
        return None
    return match


def period_start(period: str, frequency: str) -> date | None:
    """First Gregorian day of a canonical native period, or ``None``.

    Semester, quarter and month starts are calendar starts; a date is itself.
    Daily tokens are validated as real Gregorian dates (leap days included).
    """
    match = _match(period, frequency)
    if match is None:
        return None
    groups = match.groups()
    try:
        if frequency == "A":
            return date(int(groups[0]), 1, 1)
        if frequency == "S":
            return date(int(groups[0]), 1 if groups[1] == "1" else 7, 1)
        if frequency == "Q":
            return date(int(groups[0]), 3 * (int(groups[1]) - 1) + 1, 1)
        if frequency == "M":
            return date(int(groups[0]), int(groups[1]), 1)
        return date(int(groups[0]), int(groups[1]), int(groups[2]))
    except ValueError:
        return None


def period_index(period: str, frequency: str) -> int | None:
    """A strictly increasing ordinal, one integer per native period.

    Consecutive native periods differ by one, so a difference greater than
    one is a missing-period break.  Indices from different frequencies are
    not comparable and must not be mixed.
    """
    start = period_start(period, frequency)
    if start is None:
        return None
    if frequency == "A":
        return start.year
    if frequency == "S":
        return start.year * 2 + (0 if start.month == 1 else 1)
    if frequency == "Q":
        return start.year * 4 + (start.month - 1) // 3
    if frequency == "M":
        return start.year * 12 + start.month - 1
    return start.toordinal()
