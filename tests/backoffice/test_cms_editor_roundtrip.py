"""Editor round-trip contracts for persisted and refused multiseries charts.

A stored ChartDocument keeps axes in selected-series order, while the editor renders six
fixed series slots. These tests pin the slot mapping for a gap in the B slot, the raw field
recovery after a refused creation, and the raw slot axes kept after a refused save.
"""

import json
import re

import pytest

from backoffice.cms import Cms
from tests.backoffice.test_cms_routes import ORIGIN, Env, chart_create

A = "ine.hicp_yoy.PT"
B = "ine.unemployment_rate.PT"
C = "eurostat.gdp.PT"


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def _select(html: str, element_id: str) -> str:
    match = re.search(rf'<select[^>]*id="{re.escape(element_id)}"[^>]*>(.*?)</select>',
                      html, re.S)
    assert match is not None, element_id
    return match.group(1)


def _selected(html: str, element_id: str) -> str | None:
    match = re.search(r'<option value="([^"]*)" selected>', _select(html, element_id))
    return match.group(1) if match else None


def chart_form(**overrides) -> dict[str, str]:
    data = {
        "version": "1",
        "title": "Comparação",
        "note_text": "Nota editorial.",
        "series_a": A,
        "series_b": "",
        "series_extra_0": "",
        "series_extra_1": "",
        "series_extra_2": "",
        "series_extra_3": "",
        "axis_0": "",
        "axis_1": "",
        "axis_2": "",
        "axis_3": "",
        "axis_4": "",
        "axis_5": "",
        "derived_key": "",
        "window": "max",
        "scale": "single",
        "day": "",
        "frequency": "",
        "transform": "",
        "base": "",
        "comparison_group": "",
        "note": "guardar",
    }
    data.update(overrides)
    return data


def test_gap_selection_with_explicit_axes_round_trips_unchanged(env):
    Cms(env.db_path, env.db_path).create(
        "chart", "gap",
        {"title": "Comparação com intervalo", "note": "", "series_a": A,
         "series_b": None, "series_extra": [C], "derived_key": None,
         "window": "max", "scale": "dual", "day": None, "axes": [0, 1]},
        actor="test", note="criar gráfico")

    c = env.client()
    html = c.get("/cms/chart/gap").text
    assert _selected(html, "chart-series-0") == A
    assert _selected(html, "chart-series-1") is None
    assert _selected(html, "chart-series-2") == C
    assert _selected(html, "chart-axis-0") == "0"
    assert _selected(html, "chart-axis-1") is None
    assert _selected(html, "chart-axis-2") == "1"

    response = c.post("/cms/chart/gap/save", data=chart_form(
        title="Comparação com intervalo", series_a=A, series_b="",
        series_extra_0=C, axis_0="0", axis_2="1", scale="dual"),
        headers=ORIGIN)

    assert response.status_code == 303
    stored = json.loads(env.revisions("chart", "gap")[0]["body_json"])
    assert stored["series_a"] == A
    assert stored["series_b"] is None
    assert stored["series_extra"] == [C]
    assert stored["axes"] == [0, 1]


def test_creation_refusal_preserves_extra_slot_and_explicit_axes(env):
    c = env.client()
    data = chart_form(series_a=A, series_b=B, series_extra_0=A,
                      axis_0="0", axis_1="1", axis_2="1", scale="dual")
    data.update(kind="chart", slug="duplicado", note="criar gráfico")

    response = c.post("/cms/new", data=data, headers=ORIGIN)

    assert response.status_code == 422
    assert env.meta("chart", "duplicado") is None
    html = response.text
    assert 'value="duplicado"' in html
    assert _selected(html, "new-chart-series-0") == A
    assert _selected(html, "new-chart-series-1") == B
    assert _selected(html, "new-chart-series-2") == A
    assert _selected(html, "new-chart-axis-0") == "0"
    assert _selected(html, "new-chart-axis-1") == "1"
    assert _selected(html, "new-chart-axis-2") == "1"
    assert _selected(html, "new-chart-axis-3") is None


def test_service_refusal_recovery_preserves_raw_slot_axes(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    before = env.meta("chart", "inflacao")
    history = env.revisions("chart", "inflacao")

    response = c.post("/cms/chart/inflacao/save", data=chart_form(
        series_a=A, series_b="", series_extra_0=C, axis_0="0", axis_2="1",
        scale="dual", frequency="annual", transform="pp"), headers=ORIGIN)

    assert response.status_code == 422
    html = response.text
    assert 'name="version" value="1"' in html
    assert _selected(html, "chart-axis-0") == "0"
    assert _selected(html, "chart-axis-1") is None
    assert _selected(html, "chart-axis-2") == "1"
    assert _selected(html, "chart-scale") == "dual"
    assert _selected(html, "chart-frequency") == "annual"
    assert _selected(html, "chart-transform") == "pp"
    assert env.meta("chart", "inflacao") == before
    assert env.revisions("chart", "inflacao") == history


def test_transformed_dual_with_automatic_axes_is_refused_before_any_save(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    before = env.meta("chart", "inflacao")
    history = env.revisions("chart", "inflacao")

    response = c.post("/cms/chart/inflacao/save", data=chart_form(
        series_a=A, series_b=B, scale="dual", frequency="annual",
        transform="pp"), headers=ORIGIN)

    assert response.status_code == 422
    html = response.text
    assert 'name="version" value="1"' in html
    assert _selected(html, "chart-scale") == "dual"
    assert _selected(html, "chart-frequency") == "annual"
    assert _selected(html, "chart-transform") == "pp"
    assert env.meta("chart", "inflacao") == before
    assert env.revisions("chart", "inflacao") == history
