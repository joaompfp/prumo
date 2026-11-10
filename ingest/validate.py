"""Row validation and quarantine decisions. Pure: no DB, no I/O."""
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from ingest.models import Observation, SeriesSpec, normalize_period

BAD_PERIOD = "bad_period"
NON_NUMERIC = "non_numeric"
UNIT_MISMATCH = "unit_mismatch"
DUPLICATE_PERIOD = "duplicate_period"


@dataclass(frozen=True)
class RawRow:
    period_raw: str
    value_raw: str
    unit_raw: str | None = None
    flag_raw: str | None = None


@dataclass(frozen=True)
class Rejection:
    period_raw: str
    value_raw: str
    reason: str


def _blank_to_none(s: str | None) -> str | None:
    return s if s and s.strip() else None


def validate(spec: SeriesSpec, rows: Iterable[RawRow]) -> tuple[list[Observation], list[Rejection]]:
    """Split rows into observations and rejections, both in input order.

    Per-row reason precedence: bad_period, non_numeric, unit_mismatch. No conversion happens:
    the number format comes from `spec.decimal`, and the unit must match `spec.unit` exactly
    (a missing unit means the source did not say, so `spec.unit` is authoritative).
    """
    # Each entry is (row, Observation | reason); duplicates are decided after the first pass.
    checked: list[tuple[RawRow, Observation | str]] = []
    for row in rows:
        checked.append((row, _check(spec, row)))

    # A period appearing more than once in one payload is a format anomaly we cannot arbitrate,
    # so every occurrence is rejected, even when the values are identical.
    counts = Counter(r.period for _, r in checked if isinstance(r, Observation))

    accepted: list[Observation] = []
    rejected: list[Rejection] = []
    for row, result in checked:
        if isinstance(result, Observation) and counts[result.period] > 1:
            result = DUPLICATE_PERIOD
        if isinstance(result, Observation):
            accepted.append(result)
        else:
            rejected.append(Rejection(row.period_raw, row.value_raw, result))
    return accepted, rejected


def _check(spec: SeriesSpec, row: RawRow) -> Observation | str:
    try:
        period = normalize_period(row.period_raw, spec.frequency)
    except ValueError:
        return BAD_PERIOD
    value_text = row.value_raw.strip()
    try:
        obs = Observation.from_raw(spec.id, period, value_text, decimal=spec.decimal,
                                   status_flag=_blank_to_none(row.flag_raw))
    except ValueError:
        return NON_NUMERIC
    unit = _blank_to_none(row.unit_raw)
    if unit is not None and unit.strip() != spec.unit:
        return UNIT_MISMATCH
    return obs
