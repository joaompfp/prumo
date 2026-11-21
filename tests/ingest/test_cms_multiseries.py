"""Typed CMS chart contract: ordered extra series, axes, frequency, transform and base.

The stored JSON is immutable editorial configuration. These tests keep the older single/pair
bodies canonical while extending the contract to at most six ordered series and one reviewed
analytical view.
"""

import json

import pytest
from pydantic import ValidationError

from ingest import cms

A = "ine.hicp_yoy.PT"
B = "ine.unemployment.PT"
C = "eurostat.gdp.PT"
D = "worldbank.population.PT"
E = "eurostat.debt.PT"


def chart_body(**overrides):
    data = {
        "title": "Comparação revista",
        "note": "Uma leitura comparada.",
        "series_a": A,
        "series_b": None,
        "derived_key": None,
        "window": "max",
        "scale": "single",
        "day": None,
    }
    data.update(overrides)
    return data


def parse(**overrides):
    return cms.parse_body("chart", chart_body(**overrides))


def test_series_ids_keep_the_authored_order_of_b_extra_and_no_derived_key():
    document = parse(series_b=B, series_extra=[C, D])
    assert document.series_ids == (A, B, C, D)
    assert parse(series_b=B).series_ids == (A, B)
    assert parse().series_ids == (A,)


def test_six_distinct_references_are_allowed_and_a_seventh_is_refused():
    six = parse(series_b=B, series_extra=[C, D, E, "eurostat.deficit.PT"])
    assert len(six.series_ids) == 6
    with pytest.raises(ValidationError):
        parse(series_b=B, series_extra=[C, D, E, "eurostat.deficit.PT", "eurostat.gdp_growth.PT"])


def test_a_reference_cannot_repeat_across_a_b_extra_or_within_extra():
    for overrides in (
            {"series_b": A},
            {"series_extra": [A]},
            {"series_b": B, "series_extra": [B]},
            {"series_extra": [C, C]}):
        with pytest.raises(ValidationError):
            parse(**overrides)


def test_axes_must_assign_one_of_two_axes_to_every_selected_series():
    document = parse(series_b=B, series_extra=[C], scale="dual", axes=[1, 0, 1])
    assert document.axes == [1, 0, 1]
    for axes in ([0], [0, 1], [0, 1, 2], [0, 1, -1], [True, False, 0]):
        with pytest.raises(ValidationError):
            parse(series_b=B, series_extra=[C], scale="dual", axes=axes)


def test_explicit_axes_agree_with_the_declared_scale():
    # First series on the right, second on the left: membership is authored, not first-seen.
    assert parse(series_b=B, scale="dual", axes=[1, 0]).axes == [1, 0]
    with pytest.raises(ValidationError):
        parse(series_b=B, scale="single", axes=[1, 0])
    with pytest.raises(ValidationError):
        parse(series_b=B, scale="dual", axes=[0, 0])


def test_a_single_series_chart_cannot_use_the_right_axis_alone():
    with pytest.raises(ValidationError):
        parse(scale="dual", axes=[1])
    assert parse(axes=[0]).axes == [0]


def test_transform_requires_an_annual_view_and_a_base_only_accompanies_it():
    document = parse(frequency="annual", transform="pp", base="2025")
    assert (document.frequency, document.transform, document.base) == ("annual", "pp", "2025")
    for overrides in (
            {"transform": "pp"},
            {"frequency": "annual", "transform": "pp", "base": "26"},
            {"frequency": "annual", "transform": "pp", "base": "20255"},
            {"frequency": "annual", "transform": "pp", "base": "abcd"},
            {"frequency": "annual", "base": "2025"},
            {"frequency": "annual", "transform": "base100", "base": "0000"}):
        with pytest.raises(ValidationError):
            parse(**overrides)


def test_transformed_views_share_one_axis_and_never_claim_a_right_axis():
    parse(frequency="annual", transform="pp", axes=[0, 0], series_b=B)
    with pytest.raises(ValidationError):
        parse(frequency="annual", transform="pp", axes=[1, 0], series_b=B)


def test_a_day_is_refused_for_annual_or_transformed_views():
    assert parse(day="2026-10-01").day == "2026-10-01"
    for overrides in (
            {"frequency": "annual", "day": "2026-10-01"},
            {"frequency": "annual", "transform": "pp", "day": "2026-10-01"}):
        with pytest.raises(ValidationError):
            parse(**overrides)


def test_unknown_frequency_transform_or_comparison_group_is_refused():
    assert parse(comparison_group="portugal").comparison_group == "portugal"
    assert parse(comparison_group="countries").comparison_group == "countries"
    assert parse(comparison_group="general").comparison_group == "general"
    for overrides in (
            {"frequency": "quarterly"},
            {"transform": "index"},
            {"comparison_group": "europe"}):
        with pytest.raises(ValidationError):
            parse(**overrides)


def test_derived_charts_stay_single_series_and_library_only():
    assert parse(derived_key="unemployment_yoy").series_ids == (A,)
    for overrides in (
            {"derived_key": "unemployment_yoy", "series_b": B},
            {"derived_key": "unemployment_yoy", "series_extra": [C]},
            {"derived_key": "unemployment_yoy", "axes": [0]},
            {"derived_key": "unemployment_yoy", "frequency": "annual"},
            {"derived_key": "unemployment_yoy", "transform": "pp", "frequency": "annual"},
            {"derived_key": "unemployment_yoy", "comparison_group": "general"}):
        with pytest.raises(ValidationError):
            parse(**overrides)


def test_older_canonical_bodies_are_retained_without_materializing_new_defaults():
    old = cms.canonical_for("chart", chart_body())
    document = cms.parse_body("chart", old)
    assert cms.canonical_body(document) == old
    payload = json.loads(old)
    for field in ("series_extra", "axes", "frequency", "transform", "base", "comparison_group"):
        assert field not in payload


def test_explicit_new_fields_survive_the_canonical_round_trip():
    raw = cms.canonical_for("chart", chart_body(
        series_b=B, series_extra=[C], scale="dual", axes=[1, 0, 0],
        frequency="annual", transform="original", comparison_group="general"))
    payload = json.loads(raw)
    assert payload["series_extra"] == [C]
    assert payload["axes"] == [1, 0, 0]
    assert payload["frequency"] == "annual"
    assert payload["comparison_group"] == "general"
    assert cms.canonical_body(cms.parse_body("chart", raw)) == raw
