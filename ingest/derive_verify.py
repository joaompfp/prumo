"""Independent recomputation of a derived run (project 3, spec s4.5).

Its value is independence from `ingest.derive`: its own token parser, period arithmetic,
`fractions.Fraction` arithmetic and fixed-point formatter. It imports neither `ingest.derive`
nor `decimal` nor `ingest.models` (pinned by tests/ingest/test_derive_verify.py)."""
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ingest.db import Db

_FIXED_SCALE = {"period_change_pct": 4, "yoy_change_pct": 4, "rebase_100": 4}
_ABS = ("period_change", "yoy_change")
_SPACES = " \u00a0\u202f"
# A thousands separator (',' or a space) only between groups of the integer part: 1-3 digits,
# then groups of exactly 3 digits, one separator throughout. '.' is the decimal point.
_TOKEN = re.compile(r"(?P<sign>[+-]?)(?:(?P<grouped>[0-9]{1,3}(?P<sep>[, \u00a0\u202f])"
                    r"[0-9]{3}(?:(?P=sep)[0-9]{3})*)|(?P<plain>[0-9]+))(?P<frac>\.[0-9]+)?")


def _parse(token: str) -> tuple[Fraction, int]:
    """(exact value, fractional digits) of a '.'-decimal token; ValueError if not a number."""
    m = _TOKEN.fullmatch(token.strip(_SPACES))
    if not m:
        raise ValueError(f"not a number: {token!r}")
    integer = m["plain"] or m["grouped"].replace(m["sep"], "")
    frac = m["frac"] or ""
    return Fraction(f"{m['sign']}{integer}{frac}"), max(len(frac) - 1, 0)


def _fixed(value: Fraction, scale: int) -> str:
    """Half-even at `scale`, plain fixed-point, no '+', '-' only for a non-zero result."""
    n = round(value * 10**scale)  # Fraction.__round__ is half-even
    digits = str(abs(n)).rjust(scale + 1, "0")
    text = f"{digits[:-scale]}.{digits[-scale:]}" if scale else digits
    return f"-{text}" if n < 0 else text


def expected_text(formula: str, current: str, reference: str) -> tuple[str, int]:
    """(canonical text, scale) of one derived value; ZeroDivisionError on a zero denominator."""
    cur, cur_digits = _parse(current)
    ref, ref_digits = _parse(reference)
    if formula in _ABS:
        scale = max(cur_digits, ref_digits)
        return _fixed(cur - ref, scale), scale
    if formula not in _FIXED_SCALE:
        raise ValueError(f"unknown formula {formula!r}")
    scale = _FIXED_SCALE[formula]
    if formula == "rebase_100":
        return _fixed(cur / ref * 100, scale), scale
    return _fixed((cur - ref) / ref * 100, scale), scale


# --- own period arithmetic (M, Q, A) -------------------------------------------------------------

_PERIOD = {"M": re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])"),
           "Q": re.compile(r"([0-9]{4})-Q([1-4])"),
           "A": re.compile(r"([0-9]{4})")}
_PER_YEAR = {"M": 12, "Q": 4, "A": 1}


def _shift(period: str, frequency: str, steps: int) -> str:
    """`period` moved back by `steps` sub-periods of `frequency`."""
    m = _PERIOD[frequency].fullmatch(period) if frequency in _PERIOD else None
    if m is None:
        raise ValueError(f"bad {frequency!r} period {period!r}")
    per_year = _PER_YEAR[frequency]
    sub = int(m.group(2)) if frequency != "A" else 1
    year, sub0 = divmod(int(m.group(1)) * per_year + sub - 1 - steps, per_year)
    if frequency == "M":
        return f"{year:04d}-{sub0 + 1:02d}"
    if frequency == "Q":
        return f"{year:04d}-Q{sub0 + 1}"
    return f"{year:04d}"


def _reference_period(formula: str, params: dict, period: str, frequency: str) -> str:
    if formula == "rebase_100":
        return params["base_period"]
    if formula.startswith("period_"):
        return _shift(period, frequency, 1)
    return _shift(period, frequency, _PER_YEAR[frequency])


# --- verify_run ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class VerifyOutcome:
    n_checked: int
    n_mismatch: int
    mismatches: list[dict]


class _Mismatch(Exception):
    def __init__(self, reason: str, expected=None):
        super().__init__(reason)
        self.reason, self.expected = reason, expected


def _check_row(row: dict, obs: dict[int, dict]) -> None:
    """Raise _Mismatch on the first defect of one derived row; return if it reproduces."""
    ref_period = _reference_period(row["formula"], row["params"], row["period"],
                                   row["frequency"])
    ids = row["input_ids"]
    # canonical id list: [current, reference]; a rebase at its own base period stores [t]
    n_expected = 1 if ref_period == row["period"] else 2
    if len(ids) != n_expected:
        raise _Mismatch("input_count")
    periods = [row["period"], ref_period][:n_expected]
    for i in ids:
        if i not in obs:
            raise _Mismatch("input_missing")
    for i in ids:
        if obs[i]["kind"] != "fetched" or not obs[i]["served"]:
            raise _Mismatch("input_not_served")
    for i in ids:
        if obs[i]["series_id"] != row["base_series_id"]:
            raise _Mismatch("input_wrong_series")
    if [obs[i]["period"] for i in ids] != periods:
        raise _Mismatch("input_wrong_period")
    current = obs[ids[0]]["value_text"]
    reference = obs[ids[-1]]["value_text"]
    try:
        text, scale = expected_text(row["formula"], current, reference)
    except ZeroDivisionError:
        raise _Mismatch("zero_denominator") from None
    except ValueError:
        raise _Mismatch("unparseable_input") from None
    if text != row["value_text"]:
        raise _Mismatch("value", text)
    if scale != row["scale"]:
        raise _Mismatch("scale", scale)


def verify_run(db: "Db", run_id: int, at: str) -> VerifyOutcome:
    """Recompute every row of a derived run from its stored input ids; set each row
    'match'/'mismatch' and write one derived_event(mismatch) per mismatch. The caller owns
    the transaction and finishing the run."""
    rows = db.derived_observations_of_run(run_id)
    obs = db.observations_by_ids(sorted({i for r in rows for i in r["input_ids"]}))
    states: list[tuple[int, str]] = []
    mismatches: list[tuple[dict, dict]] = []
    for row in rows:
        try:
            _check_row(row, obs)
        except _Mismatch as m:
            stored = row["scale"] if m.reason == "scale" else row["value_text"]
            mismatches.append((row, {"row_id": row["id"], "key": row["key"],
                                     "period": row["period"], "reason": m.reason,
                                     "stored": stored, "expected": m.expected}))
            states.append((row["id"], "mismatch"))
        else:
            states.append((row["id"], "match"))
    db.set_derived_row_states(states)
    for row, detail in mismatches:
        db.add_derived_event(at, run_id, row["derived_series_id"], row["period"], "mismatch",
                             detail)
    return VerifyOutcome(len(rows), len(mismatches), [d for _, d in mismatches])
