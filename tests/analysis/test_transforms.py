"""Annual harmonisation, base100 and percentage-point tests."""
from collections import defaultdict
from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from analysis import transforms
from analysis.transforms import (
    AnalysisUnavailable,
    AnalyticalValue,
    InputValue,
    annualise,
    normalise,
    verify_result,
)


def year_values(year: int, values) -> tuple[InputValue, ...]:
    return tuple(InputValue(f"{year}.series", f"{year:04d}-{month:02d}", str(value))
                 for month, value in enumerate(values, 1))


def native_values(*pairs: tuple[str, str]) -> tuple[AnalyticalValue, ...]:
    return tuple(
        AnalyticalValue(year, token, (InputValue("native.series", year, token),), "native")
        for year, token in pairs
    )


def test_mean_of_a_complete_year_is_exact_and_quantised():
    values = year_values(2024, range(1, 13))
    series = annualise("hicp_yoy.PT.M", "M", "%", values)
    assert series.method == "mean" and series.dropped_years == ()
    [value] = series.values
    assert (value.period, value.value_text, value.method) == ("2024", "6.500000", "mean")
    assert value.inputs == values
    assert all(left is right for left, right in zip(value.inputs, values))
    assert value.transformation == "original" and value.base_inputs == ()


def test_computed_output_uses_four_digit_year_tokens():
    series = annualise("hicp_yoy.PT.M", "M", "%", year_values(1, range(1, 13)))
    assert series.values[0].period == "0001"
    incomplete = annualise("hicp_yoy.PT.M", "M", "%", year_values(1, range(1, 12)))
    assert incomplete.dropped_years == ("0001",)


def test_noncanonical_period_poisons_only_its_own_year():
    good = year_values(2023, range(1, 13))
    bad = list(year_values(2024, range(1, 13)))
    bad[0] = InputValue("bad", "2024-1", "1")
    series = annualise("hicp_yoy.PT.M", "M", "%", good + tuple(bad))
    assert [value.period for value in series.values] == ["2023"]
    assert series.dropped_years == ("2024",)

    native = annualise("anything", "A", "-", (
        InputValue("s", "2023", "1"),
        InputValue("s", "2024-02", "2"),
    ))
    assert [value.period for value in native.values] == ["2023"]
    assert native.dropped_years == ("2024",)


@pytest.mark.parametrize("period", ["not-a-period", "0000-01", "junk"])
def test_unattributable_period_raises_invalid_period(period):
    with pytest.raises(AnalysisUnavailable) as info:
        annualise("hicp_yoy.PT.M", "M", "%", (InputValue("s", period, "1"),))
    assert info.value.code == "invalid_period"


def test_incomplete_year_is_omitted_and_reported():
    series = annualise("hicp_yoy.PT.M", "M", "%", year_values(2024, range(1, 12)))
    assert series.values == ()
    assert series.dropped_years == ("2024",)
    assert series.method == "mean"


def test_duplicate_month_poisons_a_complete_year():
    values = list(year_values(2024, range(1, 13)))
    values[11] = InputValue("dup", "2024-01", "12")
    series = annualise("hicp_yoy.PT.M", "M", "%", tuple(values))
    assert series.values == () and series.dropped_years == ("2024",)


def test_break_status_drops_the_year_but_other_flags_are_kept():
    broken = list(year_values(2024, range(1, 13)))
    broken[5] = InputValue("break", "2024-06", "6", "break")
    series = annualise("hicp_yoy.PT.M", "M", "%", tuple(broken))
    assert series.values == () and series.dropped_years == ("2024",)

    provisional = list(year_values(2025, range(1, 13)))
    provisional[5] = InputValue("prov", "2025-06", "6", "provisional")
    series = annualise("hicp_yoy.PT.M", "M", "%", tuple(provisional))
    assert series.values[0].value_text == "6.500000"
    assert series.values[0].inputs[5].status_flag == "provisional"


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity", "n.d.", "1,5",
                                 "1e309", "1e99999"])
def test_nonfinite_malformed_or_huge_monthly_value_drops_the_year(bad):
    values = list(year_values(2024, range(1, 13)))
    values[4] = InputValue("bad", "2024-05", bad)
    series = annualise("hicp_yoy.PT.M", "M", "%", tuple(values))
    assert series.values == () and series.dropped_years == ("2024",)


def test_unknown_family_unit_or_subannual_frequency_is_refused():
    values = year_values(2024, range(1, 13))
    for key, unit in [
        ("consumer_confidence.PT.M", "balance"),
        ("ine_ipi_seasonal_cae.PT.M", "%"),
        ("ine_ipi_seasonal_cae_99.PT.M", "index_2021=100"),
        ("hicp_yoy.PT.M", "MEUR"),
    ]:
        with pytest.raises(AnalysisUnavailable) as info:
            annualise(key, "M", unit, values)
        assert info.value.code == "unsupported_annual"
    for frequency in ("Q", "S", "D", "PT15M", "W"):
        with pytest.raises(AnalysisUnavailable) as info:
            annualise("hicp_yoy.PT.M", frequency, "%", values)
        assert info.value.code == "unsupported_annual"


def test_native_annual_passes_exact_tokens_oldest_first_and_drops_duplicates():
    raw = (
        InputValue("s", "2024", "2.500"),
        InputValue("s", "2022", "-0.50"),
        InputValue("s", "2022", "9"),
        InputValue("s", "2023", "0"),
    )
    series = annualise("anything_at_all", "A", "unknown unit", raw)
    assert series.method == "native" and series.dropped_years == ("2022",)
    assert [(value.period, value.value_text) for value in series.values] == [
        ("2023", "0"), ("2024", "2.500")]
    assert series.values[0].inputs[0] is raw[3]


def test_native_annual_nonfinite_or_huge_value_drops_year():
    raw = (
        InputValue("s", "2022", "n.d."),
        InputValue("s", "2023", "1e99999"),
        InputValue("s", "2024", "4"),
    )
    series = annualise("anything", "A", "-", raw)
    assert series.dropped_years == ("2022", "2023")
    assert [value.period for value in series.values] == ["2024"]


def test_year_end_keeps_december_token_and_requires_twelve_months():
    values = year_values(2024, range(1, 12)) + (
        InputValue("credit", "2024-12", "-12.3450"),)
    series = annualise("credit_housing.PT.M", "M", "MEUR", values)
    [value] = series.values
    assert (value.value_text, value.method) == ("-12.3450", "year_end")
    assert value.inputs == values
    assert annualise(
        "credit_housing.PT.M", "M", "MEUR", values[:-1]).dropped_years == ("2024",)


def test_mean_is_recomputed_from_inputs_not_from_its_rounded_token():
    base = year_values(2023, [10] * 12)
    target = year_values(2024, [10] * 11 + ["10.000006"])
    series = annualise("ipi_total.PT.M", "M", "index_2021=100", base + target)
    assert [value.value_text for value in series.values] == ["10.000000", "10.000000"]
    output = normalise(
        series.values, indicator_key="ipi_total.PT.M", unit="index_2021=100",
        mode="base100", base_year="2023")
    assert [value.value_text for value in output] == ["100.000000", "100.000005"]
    base_value = series.values[0]
    assert all(left is right for left, right in zip(
        output[1].base_inputs, base_value.inputs))


def test_base_is_recomputed_from_inputs_not_from_its_rounded_token():
    base = year_values(2023, [10] * 11 + ["10.000006"])
    target = year_values(2024, [10] * 11 + ["10.000006"])
    series = annualise("ipi_total.PT.M", "M", "index_2021=100", base + target)
    assert series.values[0].value_text == "10.000000"
    output = normalise(
        series.values, indicator_key="ipi_total.PT.M", unit="index_2021=100",
        mode="base100", base_year="2023")
    assert [value.value_text for value in output] == ["100.000000", "100.000000"]


def test_base100_positive_base_and_negative_levels_are_kept():
    values = native_values(("2022", "100"), ("2023", "-50"))
    output = normalise(values, indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                       mode="base100", base_year="2022")
    assert [value.value_text for value in output] == ["100.000000", "-50.000000"]
    assert output[0].transformation == "base100" and output[0].method == "native"


def test_base100_refuses_zero_and_negative_base():
    for base in ("0", "-5"):
        with pytest.raises(AnalysisUnavailable) as info:
            normalise(native_values(("2022", base), ("2023", "1")),
                      indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                      mode="base100", base_year="2022")
        assert info.value.code == "base_not_positive"


def test_pp_accepts_zero_and_negative_base():
    zero = normalise(native_values(("2020", "0"), ("2021", "1.5")),
                     indicator_key="unemployment_rate.PT.A", unit="%",
                     mode="pp", base_year="2020")
    assert [value.value_text for value in zero] == ["0.000000", "1.500000"]

    negative = normalise(native_values(("2020", "-2"), ("2021", "1.5")),
                          indicator_key="unemployment_rate.PT.A", unit="%",
                          mode="pp", base_year="2020")
    assert [value.value_text for value in negative] == ["0.000000", "3.500000"]


def test_explicit_base_must_be_canonical_and_present():
    values = native_values(("2023", "1"))
    with pytest.raises(AnalysisUnavailable) as info:
        normalise(values, indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                  mode="base100", base_year="2022")
    assert info.value.code == "missing_base"
    for base in ("2022-01", "0000", "22", "2022 "):
        with pytest.raises(AnalysisUnavailable) as info:
            normalise(values, indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                      mode="base100", base_year=base)
        assert info.value.code == "invalid_base"


def test_unsupported_transform_mode_and_period_contracts():
    with pytest.raises(AnalysisUnavailable) as info:
        normalise(native_values(("2022", "1")), indicator_key="hicp_yoy.PT.M",
                  unit="%", mode="base100", base_year="2022")
    assert info.value.code == "unsupported_base100"
    with pytest.raises(AnalysisUnavailable) as info:
        normalise(native_values(("2022", "1")), indicator_key="worldbank_gdp_usd.US.A",
                  unit="USD", mode="pp", base_year="2022")
    assert info.value.code == "unsupported_pp"
    with pytest.raises(AnalysisUnavailable) as info:
        normalise(native_values(("2022", "1")), indicator_key="worldbank_gdp_usd.US.A",
                  unit="USD", mode="ratio", base_year="2022")
    assert info.value.code == "unknown_mode"
    monthly = (AnalyticalValue("2022-01", "1", (), "native"),)
    with pytest.raises(AnalysisUnavailable) as info:
        normalise(monthly, indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                  mode="base100", base_year="2022")
    assert info.value.code == "annual_required"
    duplicate = native_values(("2022", "1")) + native_values(("2022", "2"))
    with pytest.raises(AnalysisUnavailable) as info:
        normalise(duplicate, indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                  mode="base100", base_year="2022")
    assert info.value.code == "duplicate_period"


def test_half_even_ties_in_both_signs_and_exact_zero():
    output = normalise(
        native_values(("2020", "200000000"), ("2021", "3"),
                      ("2022", "-3"), ("2023", "1")),
        indicator_key="worldbank_population.PT.A", unit="hab.",
        mode="base100", base_year="2020")
    assert [value.value_text for value in output] == [
        "100.000000", "0.000002", "-0.000002", "0.000000"]


@pytest.mark.parametrize(("calculated", "exact", "token"), [
    (Decimal("0.0000005"), Fraction(1, 2_000_000), "0.000000"),
    (Decimal("-0.0000005"), Fraction(-1, 2_000_000), "0.000000"),
    (Decimal("0.0000015"), Fraction(3, 2_000_000), "0.000002"),
    (Decimal("-0.0000015"), Fraction(-3, 2_000_000), "-0.000002"),
    (Decimal("0.0000025"), Fraction(1, 400_000), "0.000002"),
    (Decimal("1.2345675"), Fraction(2469135, 2_000_000), "1.234568"),
])
def test_independent_rational_half_even_rounding(calculated, exact, token):
    assert verify_result(calculated, exact) == token


def test_verification_rejects_decimal_rational_disagreement_and_can_be_probed(monkeypatch):
    with pytest.raises(AnalysisUnavailable) as info:
        verify_result(Decimal("1.0"), Fraction(1, 3))
    assert info.value.code == "verification_failed"

    monkeypatch.setattr(transforms, "_decimal_token", lambda *args, **kwargs: "999.000000")
    with pytest.raises(AnalysisUnavailable) as info:
        normalise(native_values(("2022", "1")),
                  indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                  mode="base100", base_year="2022")
    assert info.value.code == "verification_failed"


def test_dataclasses_are_frozen_and_inputs_are_never_mutated():
    raw = native_values(("2022", "1"), ("2023", "2"))
    before = tuple(raw)
    output = normalise(raw, indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                       mode="base100", base_year="2022")
    with pytest.raises(FrozenInstanceError):
        raw[0].value_text = "9"
    with pytest.raises(FrozenInstanceError):
        output[0].base_inputs = ()
    assert raw == before
    assert output[1].inputs[0] is raw[1].inputs[0]


def test_normalise_rejects_malformed_native_token():
    for token in ("n.d.", "NaN", "1,5", "1e99999"):
        with pytest.raises(AnalysisUnavailable) as info:
            normalise(native_values(("2022", "1"), ("2023", token)),
                      indicator_key="worldbank_gdp_usd.US.A", unit="USD",
                      mode="base100", base_year="2022")
        assert info.value.code == "invalid_value"


@pytest.mark.parametrize(("family", "unit"), sorted(
    (family, unit) for family, units in transforms._MEAN_MONTHLY.items() for unit in units))
def test_every_reviewed_monthly_mean_family_annualises(family, unit):
    series = annualise(f"{family}.PT.M", "M", unit, year_values(2024, range(1, 13)))
    assert series.method == "mean" and series.values[0].value_text == "6.500000"


@pytest.mark.parametrize(("family", "unit"), sorted(
    (family, unit) for family, units in transforms._YEAR_END_MONTHLY.items() for unit in units))
def test_every_reviewed_year_end_family_annualises(family, unit):
    series = annualise(f"{family}.PT.M", "M", unit, year_values(2024, range(1, 13)))
    assert series.method == "year_end" and series.values[0].value_text == "12"


@pytest.mark.parametrize("suffix", sorted(transforms._INE_IPI_SUFFIXES))
def test_every_actual_ine_ipi_suffix_annualises(suffix):
    series = annualise(f"ine_ipi_seasonal_cae_{suffix}.PT.M", "M", "index_2021=100",
                       year_values(2024, range(1, 13)))
    assert series.method == "mean" and series.values[0].value_text == "6.500000"


@pytest.mark.parametrize(("family", "unit"), sorted(
    (family, unit) for family, units in transforms._LEVEL_UNITS.items() for unit in units))
def test_every_reviewed_base100_family_transforms(family, unit):
    output = normalise(native_values(("2022", "10"), ("2023", "20")),
                       indicator_key=f"{family}.PT.A", unit=unit,
                       mode="base100", base_year="2022")
    assert [value.value_text for value in output] == ["100.000000", "200.000000"]


@pytest.mark.parametrize(("family", "unit"), sorted(
    (family, unit) for family, units in transforms._RATE_UNITS.items() for unit in units))
def test_every_reviewed_rate_family_transforms_in_pp(family, unit):
    output = normalise(native_values(("2022", "2"), ("2023", "3")),
                       indicator_key=f"{family}.PT.A", unit=unit,
                       mode="pp", base_year="2022")
    assert [value.value_text for value in output] == ["0.000000", "1.000000"]


def test_reviewed_policy_families_exist_in_the_validated_registry():
    from ingest.registry import load_registry

    path = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
    specs = load_registry(path)
    by_family = defaultdict(list)
    for spec in specs:
        by_family[spec.indicator_key.split(".", 1)[0]].append(
            (spec.frequency, spec.unit))
    for family, units in transforms._MEAN_MONTHLY.items():
        assert any(frequency == "M" and unit in units
                   for frequency, unit in by_family[family]), family
    for family, units in transforms._YEAR_END_MONTHLY.items():
        assert any(frequency == "M" and unit in units
                   for frequency, unit in by_family[family]), family
    for suffix in transforms._INE_IPI_SUFFIXES:
        family = f"{transforms._INE_IPI_PREFIX}{suffix}"
        assert any(frequency == "M" and unit == "index_2021=100"
                   for frequency, unit in by_family[family]), family
    for family, units in transforms._LEVEL_UNITS.items():
        assert any(unit in units for _, unit in by_family[family]), family
    for family, units in transforms._RATE_UNITS.items():
        assert any(frequency in ("A", "M") and unit in units
                   for frequency, unit in by_family[family]), family
