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
    """The publisher's tokens, verbatim. None in period_raw/value_raw means "no data" in the source."""
    period_raw: str | None
    value_raw: str | None
    unit_raw: str | None = None
    flag_raw: str | None = None
    # Index (in fetch order) of the response this row was parsed from; 0 for single-response
    # sources. Carried to the Observation so the pipeline links it to that exact raw payload.
    response_index: int = 0

    def __post_init__(self):
        ri = self.response_index
        if isinstance(ri, bool) or not isinstance(ri, int) or ri < 0:
            raise TypeError(f"RawRow.response_index must be an int >= 0, got {ri!r}")
        # Numbers are never coerced to str here: that would silently lose formatting ("1.10" -> "1.1").
        for name in ("period_raw", "value_raw", "unit_raw", "flag_raw"):
            v = getattr(self, name)
            if v is not None and not isinstance(v, str):
                raise TypeError(
                    f"RawRow.{name} must be str or None, got {type(v).__name__}: adapters must pass "
                    "the publisher's token as a str (e.g. json.loads(..., parse_float=str, parse_int=str))")


@dataclass(frozen=True)
class Rejection:
    period_raw: str | None
    value_raw: str | None
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

    # Deliberate: duplicates are evaluated only among rows that otherwise passed, so a copy that
    # fails another check keeps that reason and does not make its valid twin a duplicate.
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
    if row.period_raw is None:
        return BAD_PERIOD
    try:
        period = normalize_period(row.period_raw, spec.frequency)
    except ValueError:
        return BAD_PERIOD
    if row.value_raw is None:
        return NON_NUMERIC
    value_text = row.value_raw.strip()
    try:
        obs = Observation.from_raw(spec.id, period, value_text, decimal=spec.decimal,
                                   status_flag=_blank_to_none(row.flag_raw),
                                   response_index=row.response_index)
    except ValueError:
        return NON_NUMERIC
    unit = _blank_to_none(row.unit_raw)
    if unit is not None and unit.strip() != spec.unit:
        return UNIT_MISMATCH
    return obs
