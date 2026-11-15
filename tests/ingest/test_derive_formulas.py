import random
from decimal import Decimal
from pathlib import Path

import pytest

from ingest import derive
from ingest.derive import DerivedValue, Skip, compute, format_fixed, previous_period, year_ago


def test_previous_period_and_year_ago_m_q_a():
    assert previous_period("2025-01", "M") == "2024-12"
    assert previous_period("2025-03", "M") == "2025-02"
    assert previous_period("2025-Q1", "Q") == "2024-Q4"
    assert previous_period("2025-Q3", "Q") == "2025-Q2"
    assert previous_period("2025", "A") == "2024"
    assert year_ago("2025-03", "M") == "2024-03"
    assert year_ago("2025-Q2", "Q") == "2024-Q2"
    assert year_ago("2025", "A") == "2024"


@pytest.mark.parametrize("freq", ["D", "S", "PT15M"])
def test_period_helpers_refuse_d_s_pt15m(freq):
    with pytest.raises(ValueError):
        previous_period("2025-01", freq)
    with pytest.raises(ValueError):
        year_ago("2025-01", freq)


def _one(formula, cur, ref, freq="M", params=None, cp="2025-02", rp="2025-01"):
    vals, skips = compute(formula, params or {}, freq, {rp: (1, ref), cp: (2, cur)})
    return [v for v in vals if v.period == cp], skips


def test_period_change_scale_is_max_input_decimals():
    (v,), _ = _one("period_change", "1.50", "1.2")
    assert (v.value_text, v.scale) == ("0.30", 2)


def test_yoy_change_pct_value():
    (v,), _ = _one("yoy_change_pct", "103.5", "100", cp="2025-01", rp="2024-01")
    assert (v.value_text, v.scale) == ("3.5000", 4)


def test_half_even_ties():
    (a,), _ = _one("period_change_pct", "100.00005", "100")
    (b,), _ = _one("period_change_pct", "100.00015", "100")
    assert a.value_text == "0.0000"
    assert b.value_text == "0.0002"


def test_negative_zero_is_written_as_zero():
    (a,), _ = _one("period_change_pct", "99.99999", "100")
    assert a.value_text == "0.0000"
    (b,), _ = _one("period_change", "5", "5")
    assert (b.value_text, b.scale) == ("0", 0)
    assert format_fixed(Decimal("-0.00001"), 4) == "0.0000"
    assert format_fixed(Decimal("-0.5"), 4) == "-0.5000"
    assert format_fixed(Decimal("1E+3"), 0) == "1000"


def test_missing_reference_period_yields_nothing_and_no_skip():
    vals, skips = compute("period_change", {}, "M", {"2025-03": (1, "5")})
    assert vals == [] and skips == []


def test_zero_denominator_skipped_with_reason():
    vals, skips = _one("period_change_pct", "5", "0")
    assert vals == [] and skips == [Skip("2025-02", "zero_denominator", (2, 1))]


def test_negative_denominator_keeps_sign_as_published():
    (v,), _ = _one("period_change_pct", "-50", "-100")
    assert v.value_text == "-50.0000"  # (-50 - -100) / -100: denominator sign kept


def test_rebase_100_base_period_is_100():
    vals, skips = compute("rebase_100", {"base_period": "2025-01"}, "M",
                          {"2025-01": (7, "50"), "2025-02": (8, "55")})
    assert skips == []
    assert vals == [DerivedValue("2025-01", "100.0000", 4, (7, 7)),
                    DerivedValue("2025-02", "110.0000", 4, (8, 7))]


def test_rebase_missing_base_period_skips_whole_series():
    vals, skips = compute("rebase_100", {"base_period": "2020-01"}, "M", {"2025-01": (1, "5")})
    assert vals == [] and skips == [Skip(None, "missing_base_period")]


def test_rebase_zero_base_is_zero_denominator():
    vals, skips = compute("rebase_100", {"base_period": "2025-01"}, "M",
                          {"2025-01": (1, "0"), "2025-02": (2, "5")})
    assert vals == []
    assert skips == [Skip("2025-01", "zero_denominator", (1,)),  # base period: one id
                     Skip("2025-02", "zero_denominator", (2, 1))]


def test_input_ids_are_current_then_reference_and_ordered():
    vals, _ = compute("period_change", {}, "M",
                      {"2025-03": (30, "3"), "2025-01": (10, "1"), "2025-02": (20, "2")})
    assert [(v.period, v.input_ids) for v in vals] == [("2025-02", (20, 10)),
                                                       ("2025-03", (30, 20))]
    assert all(len(set(v.input_ids)) == 2 for v in vals)


def test_property_exact_on_random_grid():
    rng = random.Random(7)
    for _ in range(300):
        a = Decimal(rng.randint(-10**6, 10**6)).scaleb(-rng.randint(0, 5))
        b = Decimal(rng.randint(1, 10**6)).scaleb(-rng.randint(0, 5))
        (v,), _ = _one("period_change_pct", str(a), str(b))
        from fractions import Fraction
        exp = (Fraction(a) - Fraction(b)) / Fraction(b) * 100
        n = round(exp * 10**4)
        assert Decimal(v.value_text) == Decimal(n).scaleb(-4)
        assert not v.value_text.startswith("-0") or Decimal(v.value_text) != 0


def test_no_float_in_module():
    assert "float(" not in Path(derive.__file__).read_text()
