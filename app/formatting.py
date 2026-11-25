"""Portuguese presentation of stored values, periods and timestamps.

Reader values use at most two decimal places. This presentation boundary never changes
stored tokens, calculation inputs, plot coordinates or CSV exports. Very small nonzero
values are shown as bounds rather than being mistaken for zero.
"""
import re
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

NBSP = "\u00a0"
MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro")
MONTHS_SHORT = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov",
                "dez")
_NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", re.ASCII)
DISPLAY_DECIMAL_PLACES = 2
_DISPLAY_QUANTUM = Decimal("0.01")


def _localize_fixed(text: str) -> str:
    """Apply PT separators to a fixed-point token without changing its digits."""
    sign = "-" if text.startswith("-") else ""
    body = text.lstrip("+-")
    integer, _, decimals = body.partition(".")
    grouped = f"{int(integer):,}".replace(",", NBSP)
    return sign + grouped + ("," + decimals if decimals else "")


def _scientific(value: Decimal) -> str:
    """Keep very small ticks distinct without a long fractional part."""
    with localcontext() as context:
        context.rounding = ROUND_HALF_UP
        mantissa, exponent = format(value, f".{DISPLAY_DECIMAL_PLACES}E").split("E")
    return _localize_fixed(mantissa.rstrip("0").rstrip(".")) + "e" + str(int(exponent))


def _rounded_display(value: Decimal) -> str:
    if not value:
        return "0"
    # Avoid expanding an extreme exponent or depending on a caller's Decimal precision.
    if value.adjusted() > 1000:
        return _scientific(value)
    with localcontext() as context:
        context.prec = max(28, value.adjusted() + DISPLAY_DECIMAL_PLACES + 2)
        rounded = value.quantize(_DISPLAY_QUANTUM, rounding=ROUND_HALF_UP)
    return _localize_fixed(format(rounded, "f").rstrip("0").rstrip("."))


def format_value(token: str) -> str:
    """Round reader text to at most two places; never use it as a calculation input.

    Half ties round away from zero. CSV and original-value evidence bypass this helper.
    """
    text = token.strip()
    if not _NUMBER.fullmatch(text):
        return token
    value = decimal_or_none(text)
    if value is None:
        return token
    if value and value.copy_abs() < Decimal("0.005"):
        return "> -0,01" if value.is_signed() else "< 0,01"
    return _rounded_display(value)


def format_axis(value: Decimal) -> str:
    """Bounded PT tick text; scientific notation prevents false zero on tiny axes."""
    if value and value.copy_abs() < _DISPLAY_QUANTUM:
        return _scientific(value)
    return _rounded_display(value)


def format_count(n: int) -> str:
    return f"{int(n):,}".replace(",", NBSP)


def format_period(period: str, frequency: str) -> str:
    """A stored period as reader text. Unknown shapes fall back to the stored string."""
    if frequency == "A" and re.fullmatch(r"\d{4}", period):
        return period
    if frequency == "M" and re.fullmatch(r"\d{4}-\d{2}", period):
        year, month = period.split("-")
        number = int(month)
        if 1 <= number <= 12:
            return f"{MONTHS[number - 1]} de {year}"
        return period
    if frequency == "Q" and re.fullmatch(r"\d{4}-Q[1-4]", period):
        year, quarter = period.split("-Q")
        return f"{quarter}.º trimestre de {year}"
    if frequency == "S" and re.fullmatch(r"\d{4}-S[12]", period):
        year, semester = period.split("-S")
        return f"{semester}.º semestre de {year}"
    if "T" in period and len(period) >= 16:  # 15-minute / daily ISO timestamp
        parsed = _parse(period)
        if parsed is not None:
            return f"{parsed:%d/%m/%Y, %H:%M} UTC"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", period):
        return f"{period[8:10]}/{period[5:7]}/{period[0:4]}"
    return period


def short_period(period: str, frequency: str) -> str:
    """A compact axis label: the year for long series, the full period for short ones."""
    if frequency in ("M", "Q", "S", "A") and len(period) >= 4 and period[:4].isdigit():
        return period[:4]
    return format_period(period, frequency)


def _parse(iso: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(
        timezone.utc)


def format_datetime(iso: str | None) -> str:
    parsed = _parse(iso) if iso else None
    return f"{parsed:%d/%m/%Y, %H:%M} UTC" if parsed else (iso or "")


def format_date(iso: str | None) -> str:
    parsed = _parse(iso) if iso else None
    return f"{parsed:%d/%m/%Y}" if parsed else (iso or "")


def decimal_or_none(token: str) -> Decimal | None:
    try:
        value = Decimal(token)
    except (InvalidOperation, TypeError, ValueError):
        return None
    # "NaN"/"Infinity" parse but cannot be plotted or scaled; treat them as no value.
    return value if value.is_finite() else None
