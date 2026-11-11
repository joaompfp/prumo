"""Domain models and period normalization. No I/O."""
import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

Frequency = Literal["A", "S", "Q", "M", "D"]


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


_MONTHS = {_fold(n): i for i, n in enumerate(
    ["janeiro", "fevereiro", "marco", "abril", "maio", "junho",
     "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"], 1)}

_PATTERNS: dict[str, list[re.Pattern]] = {
    "A": [re.compile(r"(?P<y>\d{4})$")],
    "S": [re.compile(r"(?P<y>\d{4})-?S(?P<s>\d)$", re.I),
          re.compile(r"(?P<s>\d)\.?o? semestre de (?P<y>\d{4})$")],
    "Q": [re.compile(r"(?P<y>\d{4})-?Q(?P<q>\d)$", re.I),
          # '3º Trimestre de 2025' and INE's '3.º Trimestre de 2025' (º folds to 'o')
          re.compile(r"(?P<q>\d)\.?o? ?trimestre de (?P<y>\d{4})$")],
    "M": [re.compile(r"(?P<y>\d{4})-?M?(?P<m>\d{2})$", re.I),
          re.compile(r"(?P<mn>[a-z]+) de (?P<y>\d{4})$")],
    "D": [re.compile(r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})$")],
}


def normalize_period(raw: str, frequency: str) -> str:
    """Canonical period string for `frequency`; raises ValueError rather than guessing."""
    if frequency not in _PATTERNS:
        raise ValueError(f"unknown frequency {frequency!r}")
    text = _fold(raw)
    for pat in _PATTERNS[frequency]:
        m = pat.match(text)
        if not m:
            continue
        g = m.groupdict()
        y = g["y"]
        if frequency == "A":
            return y
        if frequency == "S" and g["s"] in "12":
            return f"{y}-S{g['s']}"
        if frequency == "Q" and g["q"] in "1234":
            return f"{y}-Q{g['q']}"
        if frequency == "M":
            mm = _MONTHS.get(g["mn"]) if "mn" in g else int(g["m"])
            if mm and 1 <= mm <= 12:
                return f"{y}-{mm:02d}"
        if frequency == "D":
            try:
                return date(int(y), int(g["m"]), int(g["d"])).isoformat()
            except ValueError:
                pass
        break
    raise ValueError(f"cannot normalize period {raw!r} as frequency {frequency}")


_SPACES = " \u00a0\u202f"


def _number_re(decimal: str) -> re.Pattern:
    dec = re.escape(decimal)
    thousands = (",") if decimal == "." else "."
    sep = re.escape(thousands) + _SPACES
    return re.compile(
        rf"[+-]?(?:[0-9]{{1,3}}(?P<t>[{sep}])[0-9]{{3}}(?:(?P=t)[0-9]{{3}})*|[0-9]+)"
        rf"(?:{dec}[0-9]+)?")


_NUMBER_RES = {".": _number_re("."), ",": _number_re(",")}


def _canonical_number(text: str, decimal: str) -> str:
    """The number in `text` as a plain '[+-]digits[.digits]' string (strict rules below)."""
    if decimal not in _NUMBER_RES:
        raise ValueError(f"decimal must be '.' or ',', got {decimal!r}")
    s = str(text).strip(_SPACES)
    m = _NUMBER_RES[decimal].fullmatch(s)
    if not m:
        raise ValueError(f"not a number (decimal={decimal!r}): {text!r}")
    return re.sub(rf"[^0-9{re.escape(decimal)}+-]", "", s).replace(decimal, ".")


def parse_decimal(text: str, decimal: str = ".") -> Decimal:
    """Same strict rules as parse_number, but exact: for comparisons that must not use float."""
    return Decimal(_canonical_number(text, decimal))


def parse_number(text: str, decimal: str = ".") -> float:
    """Strict: `decimal` is declared, never guessed. The other of ',' / '.' and spaces are
    accepted only as thousands separators in groups of exactly 3 digits."""
    v = float(_canonical_number(text, decimal))
    if not math.isfinite(v):
        raise ValueError(f"not finite: {text!r}")
    return v


class Observation(BaseModel):
    """value is always the parse of value_text; build with from_raw (or pass a consistent pair)."""
    series_id: str
    period: str
    value_text: str  # verbatim source text
    value: float
    status_flag: str | None = None
    released_at: datetime | None = None
    # Provenance hint, not data: index of the source response (page) the row came from.
    # The pipeline maps it to that response's raw_fetch row; excluded from dumps.
    response_index: int = Field(default=0, ge=0, exclude=True)

    @classmethod
    def from_raw(cls, series_id: str, period: str, value_text: str, decimal: str = ".",
                 status_flag: str | None = None, released_at: datetime | None = None,
                 response_index: int = 0) -> "Observation":
        return cls.model_validate(
            dict(series_id=series_id, period=period, value_text=value_text,
                 value=parse_number(value_text, decimal),
                 status_flag=status_flag, released_at=released_at,
                 response_index=response_index),
            context={"decimal": decimal})

    @field_validator("value", mode="before")
    @classmethod
    def _numeric_only(cls, v):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("value must be a number; use Observation.from_raw to parse text")
        return v

    @model_validator(mode="after")
    def _value_matches_text(self, info: ValidationInfo):
        decimal = (info.context or {}).get("decimal", ".")
        if parse_number(self.value_text, decimal) != self.value:
            raise ValueError("value does not match value_text")
        return self


class SourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    licence: str
    licence_url: str
    attribution: str
    redistribution_ok: bool

    @field_validator("name", "licence", "licence_url", "attribution")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be non-empty")
        return v


class SeriesSpec(BaseModel):
    """Registry row: mirrors `series` plus its source and scheduling hints (not stored in SQL)."""
    model_config = ConfigDict(extra="forbid")
    id: str
    source: SourceSpec
    indicator_key: str
    role: Literal["primary", "cross_check"]
    theme: Literal["economy", "demography", "energy"]
    geography: str
    frequency: Frequency
    unit: str
    multiplier: float | None = None
    seasonal_adjustment: str | None = None
    base_year: int | None = None
    native_code: str | None = None
    url: str | None = None
    active: bool = True
    schedule: str | None = None  # interval like "1d"/"7d"; None = default by frequency
    throttle_rps: float = 1.0
    decimal: Literal[".", ","] = "."  # declared decimal separator of the source's numbers

    @field_validator("unit")
    @classmethod
    def _unit(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("unit must be non-empty")
        return v
