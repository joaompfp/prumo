"""Pure annual harmonisation and scale/base transformations.

The module knows reviewed indicator-family policies, not the registry loader.
Inputs are immutable raw tokens; outputs retain the original input references.
Every calculated number is produced with local 60-digit Decimal arithmetic and
independently checked by exact rational arithmetic with half-even rounding to
six decimal places.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from fractions import Fraction

from analysis.periods import period_start

PLACES = 6
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_MAX_ADJUSTED = 1000


class AnalysisUnavailable(ValueError):
    """A statically explainable refusal.  ``code`` is the stable copy key."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


@dataclass(frozen=True)
class InputValue:
    """One raw publisher observation.  ``value_text`` is the exact source token."""

    series_id: str
    period: str
    value_text: str
    status_flag: str | None = None


@dataclass(frozen=True)
class AnalyticalValue:
    """One annual value plus the raw inputs that justify it."""

    period: str
    value_text: str
    inputs: tuple[InputValue, ...]
    method: str
    base_inputs: tuple[InputValue, ...] = ()
    transformation: str = "original"


@dataclass(frozen=True)
class AnnualSeries:
    """One series' annual values, oldest first, and the years left out."""

    values: tuple[AnalyticalValue, ...]
    method: str
    dropped_years: tuple[str, ...]


_IPI_UNITS = frozenset({"index_2021=100", "I21"})
_MEAN_MONTHLY = {
    "hicp_yoy": frozenset({"%"}),
    "ine_ipc_yoy": frozenset({"%"}),
    "unemployment_rate": frozenset({"%"}),
    "euribor_1m": frozenset({"%"}),
    "euribor_3m": frozenset({"%"}),
    "euribor_6m": frozenset({"%"}),
    "euribor_12m": frozenset({"%"}),
    "pt_10y": frozenset({"%"}),
    "de_10y": frozenset({"%"}),
    "ipi_total": _IPI_UNITS,
    "ipi_manufacturing": _IPI_UNITS,
    "ipi_c20_c21": _IPI_UNITS,
    "ipi_c22": _IPI_UNITS,
    "ipi_c28": _IPI_UNITS,
    "ipi_c29_c30": _IPI_UNITS,
    "eurostat_ipi_total": _IPI_UNITS,
    "eurostat_metals": _IPI_UNITS,
}
_YEAR_END_MONTHLY = {
    "credit_housing": frozenset({"MEUR"}),
    "credit_consumer": frozenset({"MEUR"}),
    "deposits_households": frozenset({"MEUR"}),
}
_INE_IPI_PREFIX = "ine_ipi_seasonal_cae_"
_INE_IPI_SUFFIXES = frozenset({
    "08", "10", "11", "13", "14", "15", "16", "17", "18", "20", "21",
    "23", "24", "25", "26", "27", "29", "30", "31", "32", "33", "35",
    "38", "B", "D", "E",
})
_LEVEL_UNITS = {
    "eurostat_gdp_per_capita_eur": frozenset({"EUR per capita"}),
    "worldbank_gdp_per_capita": frozenset({"USD"}),
    "worldbank_gdp_usd": frozenset({"USD"}),
    "worldbank_population": frozenset({"hab."}),
    "ine_population": frozenset({"N.º"}),
    "credit_housing": frozenset({"MEUR"}),
    "credit_consumer": frozenset({"MEUR"}),
    "deposits_households": frozenset({"MEUR"}),
    "eurostat_hourly_labour_cost_index": frozenset({"index 2020=100"}),
    **{family: frozenset({"I10_2010"}) for family in (
        "eurostat_labour_productivity_hour",
        "eurostat_labour_productivity_hour_real",
        "eurostat_labour_productivity_per_hour",
        "eurostat_labour_productivity_person_real",
        "eurostat_unit_labour_cost",
        "eurostat_unit_labour_cost_hour",
        "eurostat_unit_labour_cost_person",
    )},
    **{family: _IPI_UNITS for family in _MEAN_MONTHLY
       if family.startswith(("ipi_", "eurostat_ipi_", "eurostat_metals"))},
}
_RATE_UNITS = {
    "hicp_yoy": frozenset({"%"}),
    "ine_ipc_yoy": frozenset({"%"}),
    "unemployment_rate": frozenset({"%"}),
    "euribor_1m": frozenset({"%"}),
    "euribor_3m": frozenset({"%"}),
    "euribor_6m": frozenset({"%"}),
    "euribor_12m": frozenset({"%"}),
    "pt_10y": frozenset({"%"}),
    "de_10y": frozenset({"%"}),
}


def _family(indicator_key: str) -> str:
    return indicator_key.split(".", 1)[0] if isinstance(indicator_key, str) else ""


def _year_token(year: int) -> str:
    return f"{year:04d}"


_YEAR_HINT = re.compile(r"([0-9]{4})(?:[-/.]|$)")


def _year_hint(period: str) -> int | None:
    """Recover the year of a non-canonical token, so only that year is omitted."""
    if not isinstance(period, str):
        return None
    match = _YEAR_HINT.match(period)
    if match is None:
        return None
    year = int(match.group(1))
    return year if 1 <= year <= 9999 else None


def _monthly_method(family: str, unit: str) -> str | None:
    if family.startswith(_INE_IPI_PREFIX):
        suffix = family[len(_INE_IPI_PREFIX):]
        return "mean" if suffix in _INE_IPI_SUFFIXES and unit == "index_2021=100" else None
    if unit in _MEAN_MONTHLY.get(family, ()):
        return "mean"
    if unit in _YEAR_END_MONTHLY.get(family, ()):
        return "year_end"
    return None


def _level_unit_ok(family: str, unit: str) -> bool:
    if family.startswith(_INE_IPI_PREFIX):
        suffix = family[len(_INE_IPI_PREFIX):]
        return suffix in _INE_IPI_SUFFIXES and unit == "index_2021=100"
    return unit in _LEVEL_UNITS.get(family, ())


def _parse_decimal(text: str) -> Decimal:
    if not isinstance(text, str):
        raise AnalysisUnavailable("invalid_value", "value is not text")
    token = text.strip()
    if not token or _NUMBER.fullmatch(token) is None:
        raise AnalysisUnavailable("invalid_value", f"not a decimal: {text!r}")
    try:
        value = Decimal(token)
    except InvalidOperation as error:
        raise AnalysisUnavailable("invalid_value", f"not a decimal: {text!r}") from error
    if not value.is_finite():
        raise AnalysisUnavailable("invalid_value", f"not finite: {text!r}")
    if value and abs(value.adjusted()) > _MAX_ADJUSTED:
        raise AnalysisUnavailable("invalid_value", f"magnitude out of range: {text!r}")
    try:
        drawable = float(value)
    except (OverflowError, ValueError) as error:
        raise AnalysisUnavailable("invalid_value", f"not drawable: {text!r}") from error
    if not math.isfinite(drawable):
        raise AnalysisUnavailable("invalid_value", f"not drawable: {text!r}")
    return value


def _fraction(text: str) -> Fraction:
    return Fraction(_parse_decimal(text))


def _decimal_token(value: Decimal, places: int = PLACES) -> str:
    if not value.is_finite():
        raise AnalysisUnavailable("verification_failed", "non-finite result")
    with localcontext() as context:
        context.prec = max(60, abs(value.adjusted()) + places + 10)
        rounded = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    if rounded == 0:
        rounded = abs(rounded)
    return format(rounded, "f")


def _rational_token(value: Fraction, places: int = PLACES) -> str:
    """Independent half-even rounding with integer divmod, no Decimal path."""
    scale = 10 ** places
    negative = value.numerator < 0
    quotient, remainder = divmod(abs(value.numerator) * scale, value.denominator)
    twice = 2 * remainder
    if twice > value.denominator or (twice == value.denominator and quotient % 2):
        quotient += 1
    whole, fraction = divmod(quotient, scale)
    sign = "-" if negative and quotient else ""
    if places == 0:
        return f"{sign}{whole}"
    return f"{sign}{whole}.{fraction:0{places}d}"


def verify_result(calculated: Decimal, exact: Fraction, places: int = PLACES) -> str:
    """Compare the Decimal result with an independently rounded exact result."""
    left = _decimal_token(calculated, places)
    right = _rational_token(exact, places)
    if left != right:
        raise AnalysisUnavailable(
            "verification_failed", f"decimal {left} disagrees with exact {right}")
    return left


def _annual_native(values: tuple[InputValue, ...]) -> AnnualSeries:
    groups: dict[int, list[InputValue]] = {}
    invalid: set[int] = set()
    for item in values:
        start = period_start(item.period, "A")
        if start is None:
            year = _year_hint(item.period)
            if year is None:
                raise AnalysisUnavailable(
                    "invalid_period", f"not an annual token: {item.period!r}")
            invalid.add(year)
            continue
        groups.setdefault(start.year, []).append(item)
    output: list[AnalyticalValue] = []
    dropped: list[str] = []
    for year in sorted(set(groups) | invalid):
        if year in invalid:
            dropped.append(_year_token(year))
            continue
        entries = groups[year]
        if len(entries) != 1:
            dropped.append(_year_token(year))
            continue
        item = entries[0]
        if item.status_flag == "break":
            dropped.append(_year_token(year))
            continue
        try:
            _parse_decimal(item.value_text)
        except AnalysisUnavailable:
            dropped.append(_year_token(year))
            continue
        output.append(AnalyticalValue(item.period, item.value_text, (item,), "native"))
    return AnnualSeries(tuple(output), "native", tuple(dropped))


def annualise(indicator_key: str, frequency: str, unit: str,
              values: tuple[InputValue, ...]) -> AnnualSeries:
    """Harmonise a series to annual values by a reviewed family policy."""
    if frequency == "A":
        return _annual_native(values)
    if frequency != "M":
        raise AnalysisUnavailable(
            "unsupported_annual", f"frequency {frequency!r} cannot be annualised")
    family = _family(indicator_key)
    method = _monthly_method(family, unit)
    if method is None:
        raise AnalysisUnavailable(
            "unsupported_annual", f"no reviewed method for {family!r} in {unit!r}")
    groups: dict[int, list[tuple[int, InputValue]]] = {}
    invalid: set[int] = set()
    for item in values:
        start = period_start(item.period, "M")
        if start is None:
            year = _year_hint(item.period)
            if year is None:
                raise AnalysisUnavailable(
                    "invalid_period", f"not a monthly token: {item.period!r}")
            invalid.add(year)
            continue
        groups.setdefault(start.year, []).append((start.month, item))
    output: list[AnalyticalValue] = []
    dropped: list[str] = []
    for year in sorted(set(groups) | invalid):
        if year in invalid:
            dropped.append(_year_token(year))
            continue
        entries = groups[year]
        if any(item.status_flag == "break" for _, item in entries):
            dropped.append(_year_token(year))
            continue
        by_month: dict[int, InputValue] = {}
        duplicate = False
        for month, item in entries:
            if month in by_month:
                duplicate = True
            by_month[month] = item
        if duplicate or set(by_month) != set(range(1, 13)):
            dropped.append(_year_token(year))
            continue
        ordered = tuple(by_month[month] for month in range(1, 13))
        try:
            parsed = tuple(_parse_decimal(item.value_text) for item in ordered)
        except AnalysisUnavailable:
            dropped.append(_year_token(year))
            continue
        if method == "mean":
            with localcontext() as context:
                context.prec = 60
                calculated = sum(parsed, Decimal(0)) / Decimal(12)
            exact = sum((Fraction(value) for value in parsed), Fraction(0)) / 12
            token = verify_result(calculated, exact)
        else:
            token = ordered[11].value_text
        output.append(AnalyticalValue(_year_token(year), token, ordered, method))
    return AnnualSeries(tuple(output), method, tuple(dropped))


def _mean_inputs(value: AnalyticalValue) -> tuple[InputValue, ...]:
    if len(value.inputs) != 12:
        raise AnalysisUnavailable("invalid_inputs", "a complete year needs twelve inputs")
    months = []
    for item in value.inputs:
        start = period_start(item.period, "M")
        if start is None:
            raise AnalysisUnavailable("invalid_inputs", "mean inputs must be monthly")
        months.append(start.month)
    if set(months) != set(range(1, 13)):
        raise AnalysisUnavailable("invalid_inputs", "mean inputs must cover twelve months")
    return value.inputs


def _december(items: tuple[InputValue, ...]) -> InputValue:
    december = []
    for item in items:
        start = period_start(item.period, "M")
        if start is None:  # _mean_inputs already guarantees this
            raise AnalysisUnavailable("invalid_inputs", "mean inputs must be monthly")
        if start.month == 12:
            december.append(item)
    if len(december) != 1:
        raise AnalysisUnavailable("invalid_inputs", "year_end needs exactly one December")
    return december[0]


def _exact_fraction(value: AnalyticalValue) -> Fraction:
    if value.method == "native":
        if len(value.inputs) > 1:
            raise AnalysisUnavailable("invalid_inputs", "native value has many inputs")
        token = value.inputs[0].value_text if value.inputs else value.value_text
        return _fraction(token)
    if value.method not in {"mean", "year_end"}:
        raise AnalysisUnavailable("unsupported_method", f"method {value.method!r}")
    items = _mean_inputs(value)
    if value.method == "mean":
        return sum((_fraction(item.value_text) for item in items), Fraction(0)) / 12
    return _fraction(_december(items).value_text)


def _exact_decimal(value: AnalyticalValue) -> Decimal:
    if value.method == "native":
        if len(value.inputs) > 1:
            raise AnalysisUnavailable("invalid_inputs", "native value has many inputs")
        token = value.inputs[0].value_text if value.inputs else value.value_text
        return _parse_decimal(token)
    if value.method not in {"mean", "year_end"}:
        raise AnalysisUnavailable("unsupported_method", f"method {value.method!r}")
    items = _mean_inputs(value)
    if value.method == "mean":
        with localcontext() as context:
            context.prec = 60
            return sum((_parse_decimal(item.value_text) for item in items), Decimal(0)) / 12
    return _parse_decimal(_december(items).value_text)


def normalise(values: tuple[AnalyticalValue, ...], *, indicator_key: str,
              unit: str, mode: str, base_year: str) -> tuple[AnalyticalValue, ...]:
    """Recompute exact annual values and apply base100 or percentage points."""
    family = _family(indicator_key)
    if mode == "base100":
        if not _level_unit_ok(family, unit):
            raise AnalysisUnavailable(
                "unsupported_base100", f"no reviewed level for {family!r} in {unit!r}")
    elif mode == "pp":
        if unit not in _RATE_UNITS.get(family, ()):
            raise AnalysisUnavailable(
                "unsupported_pp", f"no reviewed rate for {family!r} in {unit!r}")
    else:
        raise AnalysisUnavailable("unknown_mode", f"mode {mode!r}")
    base_start = period_start(base_year, "A")
    if base_start is None or base_year != f"{base_start.year:04d}":
        raise AnalysisUnavailable("invalid_base", f"base year {base_year!r}")
    seen: set[str] = set()
    for item in values:
        if period_start(item.period, "A") is None:
            raise AnalysisUnavailable("annual_required", f"period {item.period!r}")
        if item.period in seen:
            raise AnalysisUnavailable("duplicate_period", f"period {item.period!r}")
        seen.add(item.period)
    by_period = {item.period: item for item in values}
    base = by_period.get(base_year)
    if base is None:
        raise AnalysisUnavailable("missing_base", f"base year {base_year!r} is absent")
    base_exact = _exact_fraction(base)
    if mode == "base100" and base_exact <= 0:
        raise AnalysisUnavailable("base_not_positive", "base100 needs a positive base")
    base_decimal = _exact_decimal(base)
    output = []
    for item in sorted(values, key=lambda value: int(value.period)):
        exact = _exact_fraction(item)
        with localcontext() as context:
            context.prec = 60
            if mode == "base100":
                calculated = Decimal(100) * _exact_decimal(item) / base_decimal
                expected = Fraction(100) * exact / base_exact
            else:
                calculated = _exact_decimal(item) - base_decimal
                expected = exact - base_exact
        token = verify_result(calculated, expected)
        output.append(AnalyticalValue(
            item.period, token, tuple(item.inputs), item.method,
            tuple(base.inputs), mode))
    return tuple(output)
