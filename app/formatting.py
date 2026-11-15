"""Portuguese presentation of stored values, periods and timestamps.

Values keep the publisher's token and precision: this module only changes separators, never
rounds, rescales or converts. Axis ticks in `charts` are the one place where a number is
rounded, and they are not values.
"""
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

NBSP = "\u00a0"
MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro")
MONTHS_SHORT = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov",
                "dez")
_NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?")


def format_value(token: str) -> str:
    """`1234567.80` -> `1 234 567,80`. Unparseable tokens are returned unchanged: the stored
    text is the authority, never a reformatted guess."""
    text = token.strip()
    if not _NUMBER.fullmatch(text):
        return token
    sign = "-" if text.startswith("-") else ""
    body = text.lstrip("+-")
    integer, _, decimals = body.partition(".")
    grouped = f"{int(integer):,}".replace(",", NBSP)
    return sign + grouped + ("," + decimals if decimals else "")


def format_axis(value: Decimal) -> str:
    """A rounded axis tick, at most two decimals, with PT separators."""
    if value == value.to_integral():
        text = str(int(value))
    else:
        text = format(value.normalize(), "f")
        integer, _, decimals = text.partition(".")
        decimals = decimals[:2].rstrip("0")
        text = integer + ("," + decimals if decimals else "")
    integer, _, decimals = text.partition(",")
    sign = "-" if integer.startswith("-") else ""
    digits = integer.lstrip("-")
    grouped = f"{int(digits):,}".replace(",", NBSP) if digits else digits
    return sign + grouped + ("," + decimals if decimals else "")


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
        return Decimal(token)
    except (InvalidOperation, TypeError, ValueError):
        return None
