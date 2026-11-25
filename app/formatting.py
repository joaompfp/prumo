"""Portuguese presentation of stored values, periods and timestamps.

Reader values use at most four significant figures. This presentation boundary never
changes stored tokens, calculation inputs, plot coordinates or CSV exports. Small
nonzero values retain relative precision instead of being rounded to zero.
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
DISPLAY_SIGNIFICANT_FIGURES = 4


def _localize_fixed(text: str) -> str:
    """Apply PT separators to a fixed-point token without changing its digits."""
    sign = "-" if text.startswith("-") else ""
    body = text.lstrip("+-")
    integer, _, decimals = body.partition(".")
    grouped = f"{int(integer):,}".replace(",", NBSP)
    return sign + grouped + ("," + decimals if decimals else "")


def _trim_fraction(text: str) -> str:
    """Remove fractional padding, never the place-value zeros of an integer."""
    return text.rstrip("0").rstrip(".") if "." in text else text


def _rounded_display(value: Decimal, *, small_exponent: int = -6) -> str:
    if not value:
        return "0"
    # Decimal's general format rounds significant figures independently of context
    # precision/exponent limits. Keep that rounding separate from PT localization.
    with localcontext() as context:
        context.rounding = ROUND_HALF_UP
        rounded = Decimal(format(value, f".{DISPLAY_SIGNIFICANT_FIGURES}g"))
    # Bound text length without rescaling units or suppressing tiny nonzero values.
    if rounded.adjusted() < small_exponent or rounded.adjusted() >= 12:
        mantissa, exponent = format(rounded, "E").split("E")
        return _localize_fixed(_trim_fraction(mantissa)) + "e" + str(int(exponent))
    return _localize_fixed(_trim_fraction(format(rounded, "f")))


def format_value(token: str) -> str:
    """Round reader text to at most four significant figures, never calculation inputs.

    Half ties round away from zero. CSV and original-value evidence bypass this helper.
    """
    text = token.strip()
    if not _NUMBER.fullmatch(text):
        return token
    value = decimal_or_none(text)
    if value is None:
        return token
    return _rounded_display(value)


def format_axis(value: Decimal) -> str:
    """Share reader precision, using scientific notation on very small ticks."""
    return _rounded_display(value, small_exponent=-2)


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
