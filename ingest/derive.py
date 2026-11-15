"""Derived layer (project 3): calculated series over verified served observations.

Pure Decimal formulas (`compute`) and the run orchestration (`run_derive`); SQL stays in
ingest/db.py, the independent recomputation in ingest/derive_verify.py."""
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, InvalidOperation, Overflow
from typing import TYPE_CHECKING, Literal

from ingest.derive_verify import verify_run
from ingest.models import parse_decimal

if TYPE_CHECKING:
    from ingest.db import Db

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


def _canonical_ids(input_ids: tuple[int, ...]) -> tuple[int, ...]:
    """Stored input id list: formula order, duplicates collapsed (a rebase at its own base
    period is (t, t) from `compute` and is stored as [t]; migration 0014 refuses duplicates)."""
    return tuple(dict.fromkeys(input_ids))


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
    input_ids: tuple[int, ...] = ()  # canonical (current, reference) ids; () when none


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
                skips.append(Skip(period, "zero_denominator",
                                  _canonical_ids((obs_id, base_id))))
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
                skips.append(Skip(period, "zero_denominator", (cur_id, ref_id)))
                continue
            text = format_fixed(CONTEXT.multiply(CONTEXT.divide(diff, ref), _HUNDRED), PCT_SCALE)
            scale = PCT_SCALE
        else:
            scale = max(_decimals(cur_text), _decimals(ref_text))
            text = format_fixed(diff, scale)
        values.append(DerivedValue(period, text, scale, (cur_id, ref_id)))
    return values, skips


# --- run orchestration -------------------------------------------------------------------------

@dataclass(frozen=True)
class DeriveReport:
    run_id: int
    state: Literal["verified", "failed"]
    n_series: int
    n_written: int    # new derived rows (unchanged values are not rewritten)
    n_skipped: int    # NEW formula refusals recorded as events (zero_denominator,
    #                   missing_base_period); one already recorded by a verified run with the
    #                   same inputs is not repeated
    n_mismatch: int   # rows the independent recomputation refused
    n_errors: int = 0  # series whose formula raised (derived_event 'compute_error')


def _select(db: "Db", keys: list[str] | None, base_series: set[str] | None) -> list[dict]:
    if keys is not None and base_series is not None:
        raise ValueError("pick derived series by keys or by base series, not both")
    active = db.derived_series_rows()
    if keys is not None:
        known = {r["key"] for r in active}
        bad = sorted(set(keys) - known)
        if bad:
            raise ValueError(f"unknown or inactive derived series: {bad}")
        return [r for r in active if r["key"] in set(keys)]
    if base_series is not None:
        return [r for r in active if r["base_series_id"] in base_series]
    return active


def _evaluate(db: "Db", run_id: int, series: list[dict], at: str) -> tuple[int, int, int]:
    """Compute every selected series, write its NEW values as pending rows and its formula
    refusals as events. Returns (n_written, n_skipped, n_errors)."""
    n_written = n_skipped = n_errors = 0
    for s in series:
        try:
            values, skips = compute(s["formula"], s["params"], s["frequency"],
                                    db.served_fetched_inputs(s["base_series_id"]))
        except (ValueError, ArithmeticError) as e:  # never a silent skip: the run fails
            db.add_derived_event(at, run_id, s["id"], None, "compute_error",
                                 {"error": f"{type(e).__name__}: {e}"})
            n_errors += 1
            continue
        known = {(p, tuple(json.loads(ids))) for p, ids in db.derived_known_inputs(s["id"])}
        rows = []
        for v in values:
            ids = _canonical_ids(v.input_ids)
            if (v.period, ids) not in known:
                rows.append((s["id"], v.period, v.value_text, v.scale, json.dumps(list(ids))))
        db.write_derived_observations(run_id, at, rows)
        known_skips = db.derived_known_skips(s["id"])
        new_skips = [sk for sk in skips
                     if (sk.period, sk.reason, sk.input_ids) not in known_skips]
        for sk in new_skips:
            db.add_derived_event(at, run_id, s["id"], sk.period, sk.reason,
                                 {"input_ids": list(sk.input_ids)})
        n_written += len(rows)
        n_skipped += len(new_skips)
    return n_written, n_skipped, n_errors


def run_derive(db: "Db", *, keys: list[str] | None = None, base_series: set[str] | None = None,
               trigger: Literal["cli", "scheduler"],
               now: Callable[[], datetime]) -> DeriveReport | None:
    """One derived run over the ACTIVE derived series (all, those named in `keys`, or those
    whose base series is in `base_series`); None, with no run row, when nothing is selected.
    ValueError (no run row) on an unknown/inactive key or when both selectors are given.

    begin -> compute (values already held as 'match' in a verified run with the same inputs
    are not rewritten) -> pending rows + skip events -> verify_run sets each row's verdict ->
    finish 'verified' only with no mismatch and no compute error, else 'failed' (nothing from
    a failed run is served). All of it is ONE transaction. An exception after the run row is
    written finishes the run 'failed' (committed) and is re-raised; when the run cannot be
    recorded (SQLite already rolled back, or finishing fails) everything rolls back and the
    original exception is re-raised."""
    series = _select(db, keys, base_series)
    if not series:
        return None
    failure: BaseException | None = None
    with db.transaction():
        run_id = db.begin_derived_run(now().isoformat(), trigger, [s["key"] for s in series])
        try:
            at = now().isoformat()
            n_written, n_skipped, n_errors = _evaluate(db, run_id, series, at)
            outcome = verify_run(db, run_id, at)
            state = "verified" if outcome.n_mismatch == 0 and n_errors == 0 else "failed"
            db.finish_derived_run(run_id, state, now().isoformat(), n_written=n_written,
                                  n_checked=outcome.n_checked, n_mismatch=outcome.n_mismatch)
        except Exception as e:
            if not db.conn.in_transaction:
                raise  # SQLite already rolled the run back itself: nothing left to record
            try:  # record the failure in the same transaction ...
                db.finish_derived_run(run_id, "failed", now().isoformat(),
                                      n_written=len(db.derived_observations_of_run(run_id)),
                                      n_checked=0, n_mismatch=0)
            except Exception:
                raise e from None  # ... or roll the whole run back; the ORIGINAL error wins
            failure = e
    if failure is not None:
        raise failure
    return DeriveReport(run_id, state, len(series), n_written, n_skipped, outcome.n_mismatch,
                        n_errors)
