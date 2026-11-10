"""Domain models and period normalization. No I/O."""
import math
import re
import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

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
          re.compile(r"(?P<q>\d)[o.]? ?trimestre de (?P<y>\d{4})$")],
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


def parse_number(text: str) -> float:
    """'1 234,5' -> 1234.5. Rejects blanks, markers (':' '..' 'n/d'), inf and nan."""
    cleaned = re.sub(r"[\s  ]", "", str(text)).replace(",", ".")
    if not re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)", cleaned):
        raise ValueError(f"not a number: {text!r}")
    v = float(cleaned)
    if not math.isfinite(v):
        raise ValueError(f"not finite: {text!r}")
    return v


class Observation(BaseModel):
    series_id: str
    period: str
    value_text: str  # verbatim source text
    value: float
    status_flag: str | None = None
    released_at: datetime | None = None

    @field_validator("value", mode="before")
    @classmethod
    def _parse_value(cls, v):
        return parse_number(v) if isinstance(v, str) else v

    @field_validator("value")
    @classmethod
    def _finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("value must be finite")
        return v

    @field_validator("value_text")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("value_text must be non-empty")
        return v


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

    @field_validator("unit")
    @classmethod
    def _unit(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("unit must be non-empty")
        return v
