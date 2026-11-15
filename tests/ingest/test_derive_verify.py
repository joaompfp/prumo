"""Task 4 (derived layer v1): independent Fraction recomputation of a derived run."""
import ast
import json
from pathlib import Path

import pytest

from ingest import derive, derive_verify
from ingest.derive_verify import VerifyOutcome, expected_text, verify_run
from ingest.models import FORMULAS, parse_decimal
from ingest.registry import sync_derived, sync_registry
from tests.ingest.derived_helpers import derived_spec, verified_values
from tests.ingest.fakes import spec

T1 = "2026-11-01T00:00:00+00:00"
T2 = "2026-11-02T00:00:00+00:00"
NOW = "2026-11-14T00:00:00+00:00"
FORBIDDEN = {"decimal", "ingest.derive", "ingest.models"}


# --- independence -------------------------------------------------------------------------------

def _imported_modules(tree: ast.Module) -> set[str]:
    """Every module an import statement names, incl. `from ingest import derive` -> ingest.derive."""
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import in derive_verify"
            base = node.module or ""
            out.add(base)
            out |= {f"{base}.{a.name}" for a in node.names}
    return out


def test_independence_static():
    path = Path(derive_verify.__file__)
    mods = _imported_modules(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    bad = {m for m in mods if any(m == f or m.startswith(f + ".") for f in FORBIDDEN)}
    assert bad == set()
    assert "float(" not in path.read_text(encoding="utf-8")


def test_static_guard_catches_every_import_form():
    for src in ("import decimal", "from decimal import Decimal", "from ingest import derive",
                "from ingest.models import parse_decimal", "import ingest.derive",
                "from ingest import models as m"):
        mods = _imported_modules(ast.parse(src))
        assert any(m == f or m.startswith(f + ".") for m in mods for f in FORBIDDEN), src


# --- expected_text --------------------------------------------------------------------------------

GRID = [  # (current, reference): Task 3 ties and negative-zero cases first
    ("100.00005", "100"), ("100.00015", "100"), ("99.99999", "100"), ("5", "5"),
    ("1.50", "1.2"), ("103.5", "100"), ("-50", "-100"), ("0", "7"), ("-0.001", "3"),
    ("1,234.5", "1 000"), ("1 234.50", "999.999"), ("+12", "0.0001"), ("1", "3"),
    ("2", "3"), ("-2", "3"), ("123456789.123456", "0.000001"), ("0.00", "-0.5"),
    ("100.000050", "100.0"), ("-100.00005", "-100"),
]


@pytest.mark.parametrize("formula", FORMULAS)
def test_expected_text_agrees_with_derive_on_grid(formula):
    for cur, ref in GRID:
        params = {"base_period": "2025-01"} if formula == "rebase_100" else {}
        rp = "2024-02" if formula.startswith("yoy_") else "2025-01"
        vals, skips = derive.compute(formula, params, "M", {rp: (1, ref), "2025-02": (2, cur)})
        assert skips == []
        [v] = [v for v in vals if v.period == "2025-02"]
        assert expected_text(formula, cur, ref) == (v.value_text, v.scale), (formula, cur, ref)


def test_expected_text_review_focus_ties_verbatim():
    assert expected_text("period_change_pct", "100.00005", "100") == ("0.0000", 4)
    assert expected_text("period_change_pct", "100.00015", "100") == ("0.0002", 4)
    assert expected_text("period_change_pct", "99.99999", "100") == ("0.0000", 4)
    assert expected_text("period_change", "5", "5") == ("0", 0)
    assert expected_text("yoy_change", "1.50", "1.2") == ("0.30", 2)
    assert expected_text("rebase_100", "50", "50") == ("100.0000", 4)
    assert expected_text("period_change", "-0.5", "0") == ("-0.5", 1)


@pytest.mark.parametrize("formula", ["period_change_pct", "yoy_change_pct", "rebase_100"])
def test_expected_text_zero_denominator_propagates(formula):
    with pytest.raises(ZeroDivisionError):
        expected_text(formula, "5", "0.000")


@pytest.mark.parametrize("bad", ["", "abc", "1e3", "1.", ".5", "1.2.3", "--1", "NaN", "inf",
                                 "1_000", "0x10"])
def test_expected_text_refuses_unparseable_tokens(bad):
    with pytest.raises(ValueError):
        expected_text("period_change", bad, "1")


@pytest.mark.parametrize("bad", ["1,23", "1,2345", "12,34,567", "1 23", "1234,567",
                                 ",123", "1,234,", "1.2,3", "1.234,5", "1,234 567",
                                 "1\u00a0234,567", "1,234.5 6", " 5\n", "\t5"])
def test_expected_text_refuses_misplaced_thousands_separators(bad):
    """Review M5: a separator is accepted only between thousands groups of the integer part
    (1-3 digits, then groups of exactly 3, one separator throughout), as parse_decimal."""
    with pytest.raises(ValueError):
        expected_text("period_change", bad, "1")
    with pytest.raises(ValueError):
        parse_decimal(bad)


def test_token_parsers_agree_on_acceptance_and_value():
    """The verifier's own parser accepts exactly the tokens parse_decimal accepts, with the
    same value (fuzzed over the characters that matter)."""
    import random
    from decimal import Decimal
    from fractions import Fraction
    rng = random.Random(20261115)
    alphabet = "0123456789" * 3 + ",. +-\u00a0\u202f"
    tokens = {"".join(rng.choice(alphabet) for _ in range(rng.randint(1, 12)))
              for _ in range(60000)}
    tokens |= {f"{a},{b:03d}" for a in range(0, 1200, 7) for b in (0, 5, 999)}
    accepted = 0
    for tok in sorted(tokens):
        try:
            want = parse_decimal(tok)
        except (ValueError, ArithmeticError):
            want = None
        try:
            got = derive_verify._parse(tok)[0]
        except ValueError:
            got = None
        if want is None:
            assert got is None, tok
        else:
            accepted += 1
            assert got == Fraction(Decimal(want)), tok
    assert accepted > 1000


def test_expected_text_unknown_formula():
    with pytest.raises(ValueError):
        expected_text("ratio", "1", "2")


# --- verify_run -----------------------------------------------------------------------------------

def _setup(db, formula="period_change", values=None, params=None, key="derived.s1_x"):
    sync_registry(db, [spec("s1", frequency="M"), spec("s2", frequency="M")])
    verified_values(db, "s1", values or {"2024-12": "100", "2025-01": "102.5",
                                         "2025-02": "99"}, T1, "k1")
    verified_values(db, "s2", {"2024-12": "1", "2025-01": "2", "2025-02": "3"}, T1, "k2")
    sync_derived(db, [derived_spec(key, "s1", formula, params=params or {})])
    return next(r["id"] for r in db.derived_series_rows() if r["key"] == key)


def _honest_rows(db, dsid, formula, params=None):
    """derive.compute over the served inputs, with Task 5's canonical id rule ((t,t) -> [t])."""
    vals, _ = derive.compute(formula, params or {}, "M", db.served_fetched_inputs("s1"))
    return [(dsid, v.period, v.value_text, v.scale,
             json.dumps(list(dict.fromkeys(v.input_ids)))) for v in vals]


def _run(db, rows):
    run = db.begin_derived_run(NOW, "cli", ["derived.s1_x"])
    db.write_derived_observations(run, NOW, rows)
    return run


def _states(db, run):
    return [s for (s,) in db.conn.execute(
        "SELECT state FROM derived_observation WHERE run_id = ? ORDER BY id", (run,))]


def _events(db, run):
    return [(k, p, json.loads(d)) for k, p, d in db.conn.execute(
        "SELECT kind, period, detail_json FROM derived_event WHERE run_id = ? ORDER BY id",
        (run,))]


@pytest.mark.parametrize("formula,params", [
    ("period_change", None), ("period_change_pct", None),
    ("rebase_100", {"base_period": "2025-01"})])
def test_verify_marks_all_rows_match(db, formula, params):
    dsid = _setup(db, formula, params=params)
    rows = _honest_rows(db, dsid, formula, params)
    assert rows
    run = _run(db, rows)
    out = verify_run(db, run, NOW)
    assert out == VerifyOutcome(n_checked=len(rows), n_mismatch=0, mismatches=[])
    assert _states(db, run) == ["match"] * len(rows)
    assert _events(db, run) == []
    db.finish_derived_run(run, "verified", NOW, n_written=len(rows), n_checked=out.n_checked,
                          n_mismatch=0)


def test_rebase_base_period_row_holds_one_input_id(db):
    params = {"base_period": "2025-01"}
    dsid = _setup(db, "rebase_100", params=params)
    rows = _honest_rows(db, dsid, "rebase_100", params)
    base_row = next(r for r in rows if r[1] == "2025-01")
    assert len(json.loads(base_row[4])) == 1 and base_row[2] == "100.0000"
    assert verify_run(db, _run(db, rows), NOW).n_mismatch == 0


def test_tampered_value_is_mismatch(db):
    dsid = _setup(db)
    rows = _honest_rows(db, dsid, "period_change")
    good, tampered = rows[0], rows[1]
    rows[1] = (*tampered[:2], "-3.6", *tampered[3:])  # honest: 99 - 102.5 = -3.5
    run = _run(db, rows)
    out = verify_run(db, run, NOW)
    assert (out.n_checked, out.n_mismatch) == (2, 1)
    [m] = out.mismatches
    ids = [r["id"] for r in db.derived_observations_of_run(run)]
    assert m == {"row_id": ids[1], "key": "derived.s1_x", "period": "2025-02",
                 "reason": "value", "stored": "-3.6", "expected": "-3.5"}
    assert _states(db, run) == ["match", "mismatch"]
    assert _events(db, run) == [("mismatch", "2025-02", m)]
    assert good[2] == "2.5"
    with pytest.raises(ValueError):
        db.finish_derived_run(run, "verified", NOW, n_written=2, n_checked=2, n_mismatch=1)


def test_wrong_scale_is_mismatch(db):
    dsid = _setup(db, values={"2024-12": "1.2", "2025-01": "1.50"})
    [row] = _honest_rows(db, dsid, "period_change")
    assert row[2:4] == ("0.30", 2)
    run = _run(db, [(*row[:3], 3, row[4])])
    [m] = verify_run(db, run, NOW).mismatches
    assert (m["reason"], m["stored"], m["expected"]) == ("scale", 3, 2)


def test_tampered_input_list_is_mismatch(db):
    dsid = _setup(db)
    rows = _honest_rows(db, dsid, "period_change")
    a, b = json.loads(rows[0][4])
    c, _ = json.loads(rows[1][4])
    run = _run(db, [
        (*rows[0][:4], json.dumps([b, a])),     # swapped: current/reference order
        (*rows[0][:4], json.dumps([a])),        # reference dropped
        (*rows[0][:4], json.dumps([a, b, c])),  # one id too many
        (*rows[1][:4], json.dumps([c, b])),     # reference two periods back
    ])
    reasons = [m["reason"] for m in verify_run(db, run, NOW).mismatches]
    assert reasons == ["input_wrong_period", "input_count", "input_count",
                       "input_wrong_period"]
    assert _states(db, run) == ["mismatch"] * 4


def test_rebase_base_period_with_two_ids_is_mismatch(db):
    params = {"base_period": "2025-01"}
    dsid = _setup(db, "rebase_100", params=params)
    ids = db.served_fetched_inputs("s1")
    run = _run(db, [(dsid, "2025-01", "100.0000", 4,
                     json.dumps([ids["2025-01"][0], ids["2024-12"][0]]))])
    [m] = verify_run(db, run, NOW).mismatches
    assert m["reason"] == "input_count"


def test_input_no_longer_served_is_mismatch(db):
    dsid = _setup(db)
    rows = _honest_rows(db, dsid, "period_change")
    verified_values(db, "s1", {"2025-01": "102.6"}, T2, "k1b")  # revises 2025-01's vintage
    run = _run(db, rows)
    out = verify_run(db, run, NOW)
    assert [m["reason"] for m in out.mismatches] == ["input_not_served", "input_not_served"]
    assert _states(db, run) == ["mismatch", "mismatch"]
    assert len(_events(db, run)) == 2


def test_withdrawn_input_is_mismatch(db):
    sync_registry(db, [spec("s1", frequency="M")])
    verified_values(db, "s1", {"2024-12": "100", "2025-01": "102"}, T1, "k1")
    new = verified_values(db, "s1", {"2024-12": "100", "2025-01": "103"}, T2, "k1b")
    sync_derived(db, [derived_spec("derived.s1_x", "s1", "period_change")])
    dsid = db.derived_series_rows()[0]["id"]
    rows = _honest_rows(db, dsid, "period_change")
    db.withdraw_run(new, "defect", NOW)
    [m] = verify_run(db, _run(db, rows), NOW).mismatches
    assert m["reason"] == "input_not_served"


def test_input_from_other_series_or_wrong_period_is_mismatch(db):
    dsid = _setup(db)
    s1, s2 = db.served_fetched_inputs("s1"), db.served_fetched_inputs("s2")
    run = _run(db, [
        (dsid, "2025-01", "2.5", 1, json.dumps([s2["2025-01"][0], s1["2024-12"][0]])),
        (dsid, "2025-01", "2.5", 1, json.dumps([s1["2025-01"][0], s2["2024-12"][0]])),
        (dsid, "2025-02", "2.5", 1, json.dumps([s1["2025-01"][0], s1["2024-12"][0]])),
    ])
    reasons = [m["reason"] for m in verify_run(db, run, NOW).mismatches]
    assert reasons == ["input_wrong_series", "input_wrong_series", "input_wrong_period"]


def test_zero_denominator_row_is_mismatch(db):
    dsid = _setup(db, "period_change_pct", values={"2024-12": "0", "2025-01": "5"})
    ids = db.served_fetched_inputs("s1")
    run = _run(db, [(dsid, "2025-01", "0.0000", 4,
                     json.dumps([ids["2025-01"][0], ids["2024-12"][0]]))])
    [m] = verify_run(db, run, NOW).mismatches
    assert (m["reason"], m["expected"]) == ("zero_denominator", None)


def test_unparseable_input_is_mismatch(db):
    dsid = _setup(db)
    rows = _honest_rows(db, dsid, "period_change")
    [cur, _] = json.loads(rows[0][4])
    # a stored token our parser refuses (the DB holds verbatim text; never written by ingest)
    trig = db.conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' "
                           "AND tbl_name = 'observation'").fetchall()
    for (name,) in trig:
        db.conn.execute(f"DROP TRIGGER {name}")
    db.conn.execute("UPDATE observation SET value_text = '1e3' WHERE id = ?", (cur,))
    [m, _] = verify_run(db, _run(db, rows), NOW).mismatches
    assert m["reason"] == "unparseable_input"


def test_verify_covers_every_row_of_the_run(db):
    dsid = _setup(db, values={f"2024-{m:02d}": str(m * 7) for m in range(1, 13)})
    rows = _honest_rows(db, dsid, "period_change")
    other = _run(db, rows[:2])  # a different run's rows are not this run's
    run = _run(db, rows)
    out = verify_run(db, run, NOW)
    assert out.n_checked == len(rows) == 11 and out.n_mismatch == 0
    assert _states(db, run) == ["match"] * 11
    assert _states(db, other) == ["pending", "pending"]


def test_empty_run_checks_nothing(db):
    _setup(db)
    run = _run(db, [])
    assert verify_run(db, run, NOW) == VerifyOutcome(0, 0, [])


# --- period rollovers (Dec / Q4 / year) through verify_run ---------------------------------------

ROLLOVERS = [  # (frequency, formula, params, periods, {row period: reference period})
    ("M", "period_change", {}, ["2024-11", "2024-12", "2025-01"],
     {"2024-12": "2024-11", "2025-01": "2024-12"}),
    ("M", "yoy_change_pct", {}, ["2023-12", "2024-01", "2024-12", "2025-01"],
     {"2024-12": "2023-12", "2025-01": "2024-01"}),
    ("Q", "period_change_pct", {}, ["2024-Q3", "2024-Q4", "2025-Q1"],
     {"2024-Q4": "2024-Q3", "2025-Q1": "2024-Q4"}),
    ("Q", "yoy_change", {}, ["2023-Q4", "2024-Q1", "2024-Q4", "2025-Q1"],
     {"2024-Q4": "2023-Q4", "2025-Q1": "2024-Q1"}),
    ("Q", "rebase_100", {"base_period": "2024-Q4"}, ["2024-Q3", "2024-Q4", "2025-Q1"],
     {"2024-Q3": "2024-Q4", "2024-Q4": "2024-Q4", "2025-Q1": "2024-Q4"}),
    ("A", "period_change_pct", {}, ["2023", "2024", "2025"], {"2024": "2023", "2025": "2024"}),
    ("A", "yoy_change", {}, ["2023", "2024", "2025"], {"2024": "2023", "2025": "2024"}),
]


def _rollover_setup(db, frequency, formula, params, periods):
    sync_registry(db, [spec("s9", frequency=frequency)])
    verified_values(db, "s9", {p: f"{100 + 7 * n}.{n}" for n, p in enumerate(periods)}, T1,
                    "k9")
    sync_derived(db, [derived_spec("derived.s9_x", "s9", formula, params=params)])
    dsid = db.derived_series_rows()[0]["id"]
    inputs = db.served_fetched_inputs("s9")
    vals, _ = derive.compute(formula, params, frequency, inputs)
    rows = [(dsid, v.period, v.value_text, v.scale,
             json.dumps(list(dict.fromkeys(v.input_ids)))) for v in vals]
    return dsid, inputs, rows


@pytest.mark.parametrize("frequency,formula,params,periods,refs", ROLLOVERS)
def test_verify_period_rollovers_match(db, frequency, formula, params, periods, refs):
    _, inputs, rows = _rollover_setup(db, frequency, formula, params, periods)
    by_id = {i: p for p, (i, _) in inputs.items()}
    got = {r[1]: by_id[json.loads(r[4])[-1]] for r in rows}
    assert got == refs  # derive's reference periods across the year boundary
    run = db.begin_derived_run(NOW, "cli", ["derived.s9_x"])
    db.write_derived_observations(run, NOW, rows)
    out = verify_run(db, run, NOW)
    assert (out.n_checked, out.n_mismatch) == (len(refs), 0)


@pytest.mark.parametrize("frequency,formula,periods,period,wrong_ref", [
    ("M", "yoy_change", ["2024-01", "2024-12", "2025-01"], "2025-01", "2024-12"),
    ("M", "period_change", ["2024-11", "2024-12", "2025-01"], "2025-01", "2024-11"),
    ("Q", "period_change", ["2024-Q3", "2024-Q4", "2025-Q1"], "2025-Q1", "2024-Q3"),
    ("Q", "yoy_change", ["2024-Q1", "2024-Q4", "2025-Q1"], "2025-Q1", "2024-Q4"),
    ("A", "yoy_change", ["2023", "2024", "2025"], "2025", "2023"),
])
def test_verify_wrong_rollover_reference_is_mismatch(db, frequency, formula, periods, period,
                                                    wrong_ref):
    dsid, inputs, _ = _rollover_setup(db, frequency, formula, {}, periods)
    run = db.begin_derived_run(NOW, "cli", ["derived.s9_x"])
    db.write_derived_observations(run, NOW, [(dsid, period, "1", 0, json.dumps(
        [inputs[period][0], inputs[wrong_ref][0]]))])
    [m] = verify_run(db, run, NOW).mismatches
    assert m["reason"] == "input_wrong_period"
