"""Derived layer (project 3): calculated series over verified served observations."""
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, InvalidOperation, Overflow
from typing import Literal

from ingest.models import parse_decimal

CONTEXT = Context(prec=60, rounding=ROUND_HALF_EVEN,
                  traps=[InvalidOperation, DivisionByZero, Overflow])
PCT_SCALE = 4
INDEX_SCALE = 4
_HUNDRED = Decimal(100)

_LABELS = {
    "period_change": "Variação face ao período anterior (diferença), calculada pelo Prumo "
                     "a partir de {base}",
    "period_change_pct": "Variação face ao período anterior (%), calculada pelo Prumo "
                         "a partir de {base}",
    "yoy_change": "Variação homóloga (diferença), calculada pelo Prumo a partir de {base}",
    "yoy_change_pct": "Variação homóloga (%), calculada pelo Prumo a partir de {base}",
    "rebase_100": "Índice rebaseado ({base_period} = 100), calculado pelo Prumo "
                  "a partir de {base}",
}


def formula_label_pt(formula: str, params: dict[str, str], base_series_id: str) -> str:
    """The Portuguese reader-facing description of how a derived value was calculated."""
    if formula not in _LABELS:
        raise ValueError(f"unknown formula {formula!r}")
    if formula == "rebase_100" and "base_period" not in params:
        raise ValueError("rebase_100 needs params['base_period']")
    return _LABELS[formula].format(base=base_series_id, **params)


def _split(period: str, frequency: str) -> tuple[int, int]:
    """(year, sub-period index); sub-period count per year is 12 (M), 4 (Q) or 1 (A)."""
    try:
        if frequency == "M":
            y, m = period.split("-")
            return int(y), int(m)
        if frequency == "Q":
            y, q = period.split("-Q")
            return int(y), int(q)
        if frequency == "A":
            return int(period), 1
    except ValueError:
        raise ValueError(f"bad {frequency} period {period!r}") from None
    raise ValueError(f"derived formulas do not support frequency {frequency!r}")


def _join(year: int, sub: int, frequency: str) -> str:
    if frequency == "M":
        return f"{year:04d}-{sub:02d}"
    if frequency == "Q":
        return f"{year:04d}-Q{sub}"
    return f"{year:04d}"


def previous_period(period: str, frequency: str) -> str:
    year, sub = _split(period, frequency)
    if frequency == "A":
        return _join(year - 1, 1, frequency)
    if sub == 1:
        return _join(year - 1, 12 if frequency == "M" else 4, frequency)
    return _join(year, sub - 1, frequency)


def year_ago(period: str, frequency: str) -> str:
    year, sub = _split(period, frequency)
    return _join(year - 1, sub, frequency)


def format_fixed(value: Decimal, scale: int) -> str:
    """Canonical text: plain fixed-point, exactly `scale` fractional digits, no exponent,
    no '+', '-' only for a non-zero rounded value."""
    q = value.quantize(Decimal(1).scaleb(-scale), context=CONTEXT)
    if q == 0:
        q = abs(q)
    return format(q, "f")


@dataclass(frozen=True)
class DerivedValue:
    period: str
    value_text: str
    scale: int
    input_ids: tuple[int, int]  # (current, reference)


@dataclass(frozen=True)
class Skip:
    period: str | None
    reason: Literal["zero_denominator", "missing_base_period"]


def _decimals(token: str) -> int:
    exp = parse_decimal(token, ".").as_tuple().exponent
    return max(-exp, 0)


def compute(formula: str, params: dict[str, str], frequency: str,
            inputs: dict[str, tuple[int, str]]) -> tuple[list[DerivedValue], list[Skip]]:
    """Derived values of one base series; `inputs` maps period -> (observation id, text)."""
    if formula not in _LABELS:
        raise ValueError(f"unknown formula {formula!r}")
    values: list[DerivedValue] = []
    skips: list[Skip] = []
    if formula == "rebase_100":
        base_period = params["base_period"]
        if base_period not in inputs:
            return [], [Skip(None, "missing_base_period")]
        base_id, base_text = inputs[base_period]
        base = parse_decimal(base_text, ".")
        for period in sorted(inputs):
            obs_id, text = inputs[period]
            if base == 0:
                skips.append(Skip(period, "zero_denominator"))
                continue
            v = CONTEXT.multiply(CONTEXT.divide(parse_decimal(text, "."), base), _HUNDRED)
            values.append(DerivedValue(period, format_fixed(v, INDEX_SCALE), INDEX_SCALE,
                                       (obs_id, base_id)))
        return values, skips
    ref_of = previous_period if formula.startswith("period_") else year_ago
    for period in sorted(inputs):
        ref_period = ref_of(period, frequency)
        if ref_period not in inputs:
            continue
        cur_id, cur_text = inputs[period]
        ref_id, ref_text = inputs[ref_period]
        cur, ref = parse_decimal(cur_text, "."), parse_decimal(ref_text, ".")
        diff = CONTEXT.subtract(cur, ref)
        if formula.endswith("_pct"):
            if ref == 0:
                skips.append(Skip(period, "zero_denominator"))
                continue
            text = format_fixed(CONTEXT.multiply(CONTEXT.divide(diff, ref), _HUNDRED), PCT_SCALE)
            scale = PCT_SCALE
        else:
            scale = max(_decimals(cur_text), _decimals(ref_text))
            text = format_fixed(diff, scale)
        values.append(DerivedValue(period, text, scale, (cur_id, ref_id)))
    return values, skips
