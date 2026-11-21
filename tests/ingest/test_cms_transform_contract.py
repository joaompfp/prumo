"""A transformed chart is always single-scale.

The shared preparation refuses a transformed dual chart, so the typed contract must refuse it
too. Otherwise the editor can save a draft that can never be published.
"""

import pytest
from pydantic import ValidationError

from ingest import cms

A = "ine.hicp_yoy.PT"
B = "ine.unemployment.PT"


def chart_body(**overrides):
    data = {
        "title": "Comparação transformada",
        "note": "",
        "series_a": A,
        "series_b": None,
        "derived_key": None,
        "window": "max",
        "scale": "single",
        "day": None,
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("transform", ["pp", "base100"])
def test_transformed_dual_chart_with_automatic_axes_is_refused(transform):
    with pytest.raises(ValidationError, match="single"):
        cms.parse_body("chart", chart_body(
            series_b=B, scale="dual", frequency="annual", transform=transform))


def test_transformed_single_scale_with_automatic_axes_stays_valid():
    document = cms.parse_body("chart", chart_body(
        series_b=B, scale="single", frequency="annual", transform="pp"))

    assert document.scale == "single"
    assert document.axes is None


def test_dual_chart_without_a_transformation_stays_valid():
    document = cms.parse_body("chart", chart_body(
        series_b=B, scale="dual", axes=None))

    assert document.scale == "dual"
    assert document.axes is None
