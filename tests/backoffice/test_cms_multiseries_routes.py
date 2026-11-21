"""Focused contracts for CMS-authored multiseries comparison charts.

The editor must expose six ordered series slots, optional explicit axes and the approved
analytical settings with ordinary native controls. The form parser is also the compatibility
boundary for older chart forms that only post the original five fields.
"""

import json

import pytest

from backoffice.cms_routes import FormError, _chart_body, _diff, _submitted_document
from tests.backoffice.test_cms_routes import ORIGIN, Env, chart_create


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def _fields(**overrides):
    data = {
        "title": "Comparação",
        "note_text": "Nota editorial.",
        "series_a": "",
        "series_b": "",
        "derived_key": "",
        "window": "max",
        "scale": "single",
        "day": "",
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
        "frequency": "",
        "transform": "",
        "base": "",
        "comparison_group": "",
    }
    data.update(overrides)
    return data


def test_new_form_maps_ordered_series_axes_and_approved_settings():
    body = _chart_body(_fields(
        series_a="s1",
        series_b="s2",
        series_extra_0="s3",
        series_extra_1="s4",
        axis_0="0",
        axis_1="1",
        axis_2="0",
        axis_3="1",
        frequency="annual",
        transform="base100",
        base="2019",
        comparison_group="portugal",
    ))

    assert body["series_a"] == "s1"
    assert body["series_b"] == "s2"
    assert body["series_extra"] == ["s3", "s4"]
    assert body["axes"] == [0, 1, 0, 1]
    assert body["frequency"] == "annual"
    assert body["transform"] == "base100"
    assert body["base"] == "2019"
    assert body["comparison_group"] == "portugal"


def test_empty_analytical_controls_are_none_not_invented_values():
    body = _chart_body(_fields(series_a="s1"))

    assert body["series_extra"] == []
    assert body["axes"] is None
    assert body["frequency"] is None
    assert body["transform"] is None
    assert body["base"] is None
    assert body["comparison_group"] is None


def test_automatic_axes_require_every_selected_axis_or_none():
    automatic = _chart_body(_fields(series_a="s1", series_b="s2"))
    assert automatic["axes"] is None

    with pytest.raises(FormError, match="eixo"):
        _chart_body(_fields(series_a="s1", series_b="s2", axis_0="0"))


def test_axis_values_on_unused_slots_are_ignored():
    body = _chart_body(_fields(series_a="s1", axis_0="1", axis_1="0"))
    assert body["axes"] == [1]


def test_duplicate_series_and_derived_multiseries_are_refused():
    with pytest.raises(FormError, match="repita"):
        _chart_body(_fields(series_a="s1", series_extra_0="s1"))

    with pytest.raises(FormError, match="calculada"):
        _chart_body(_fields(series_a="s1", series_b="s2", derived_key="derived.x"))


@pytest.mark.parametrize("field,value,fragment", [
    ("frequency", "weekly", "frequência"),
    ("transform", "index", "transformação"),
    ("base", "20x9", "ano base"),
    ("comparison_group", "europe", "categoria"),
])
def test_unknown_analytical_settings_are_refused(field, value, fragment):
    with pytest.raises(FormError, match=fragment):
        _chart_body(_fields(series_a="s1", **{field: value}))


def test_base_year_is_refused_without_a_transformation():
    with pytest.raises(FormError, match="transforma"):
        _chart_body(_fields(series_a="s1", base="2019", transform="original"))

    assert _chart_body(_fields(series_a="s1", base="2019",
                               transform="pp"))["base"] == "2019"


def test_legacy_chart_form_keeps_its_exact_body_shape():
    body = _chart_body({
        "title": "Antigo",
        "note_text": "Nota.",
        "series_a": "s1",
        "series_b": "s2",
        "derived_key": "",
        "window": "max",
        "scale": "dual",
        "day": "",
    })
    assert set(body) == {"title", "note", "series_a", "series_b", "derived_key",
                         "window", "scale", "day"}


def test_submitted_document_preserves_raw_multiseries_values_for_recovery():
    doc = _submitted_document("chart", _fields(
        series_a="s1", series_b="s2", series_extra_0="s3",
        axis_0="9", frequency="annual", transform="pp", base="2020",
        comparison_group="countries"))
    assert doc["series_extra"][0] == "s3"
    assert doc["axes"] == ["9", "", "", "", "", ""]
    assert doc["frequency"] == "annual"
    assert doc["transform"] == "pp"
    assert doc["base"] == "2020"
    assert doc["comparison_group"] == "countries"


def test_chart_diff_covers_every_new_analytical_field():
    live = {
        "title": "Antigo", "note": "Nota.", "series_a": "s1", "series_b": None,
        "derived_key": None, "window": "max", "scale": "single", "day": None,
    }
    draft = {
        "title": "Novo", "note": "Nota.", "series_a": "s1", "series_b": "s2",
        "series_extra": ["s3"], "derived_key": None, "window": "5y", "scale": "dual",
        "day": None, "axes": [1, 0, 1], "frequency": "annual",
        "transform": "base100", "base": "2019", "comparison_group": "countries",
    }
    rows = {row["field"]: row for row in _diff("chart", live, draft)}
    assert {"Título", "Série B", "Série C", "Janela", "Escala", "Eixos",
            "Frequência", "Transformação", "Ano base",
            "Categoria de comparação"} <= set(rows)
    assert rows["Eixos"]["draft"] == "série 1: eixo 1, série 2: eixo 0, série 3: eixo 1"


def test_editor_offers_six_series_axis_and_analytical_controls(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    html = c.get("/cms/chart/inflacao").text

    for name in ("series_a", "series_b", "series_extra_0", "series_extra_1",
                 "series_extra_2", "series_extra_3"):
        assert html.count(f'name="{name}"') == 1, name
    for index in range(6):
        assert html.count(f'name="axis_{index}"') == 1, index
    for name in ("frequency", "transform", "base", "comparison_group"):
        assert html.count(f'name="{name}"') == 1, name

    for text in ("Série A", "Série B", "Série C", "Série D", "Série E", "Série F",
                 "Eixo da Série A", "Automático", "Frequência", "Transformação",
                 "Ano base", "Categoria de comparação", "Comparações"):
        assert text in html
    assert "| Mensal |" in html and "| % |" in html
    assert 'name="body_json"' not in html
    assert "Identidade canónica:" in html


def test_dashboard_creation_form_offers_the_same_series_contract(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    html = c.get("/cms").text

    for name in ("series_a", "series_b", "series_extra_0", "series_extra_1",
                 "series_extra_2", "series_extra_3"):
        assert html.count(f'name="{name}"') == 1, name
    for index in range(6):
        assert html.count(f'name="axis_{index}"') == 1, index
    for name in ("frequency", "transform", "base", "comparison_group"):
        assert html.count(f'name="{name}"') == 1, name
    assert "Biblioteca de comparações" in html
    assert 'href="/cms#comparacoes"' in html
    assert "Sem categoria" in html or "sem categoria" in html


def test_invalid_axis_recovery_keeps_values_version_and_writes_nothing(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    before = env.meta("chart", "inflacao")
    history = env.revisions("chart", "inflacao")

    data = _fields(version="1", note="guardar", series_a="ine.hicp_yoy.PT",
                   series_b="ine.unemployment_rate.PT", axis_0="9")
    response = c.post("/cms/chart/inflacao/save", data=data, headers=ORIGIN)

    assert response.status_code == 422
    assert 'name="version" value="1"' in response.text
    assert "ine.unemployment_rate.PT" in response.text
    assert '<option value="9" selected>' in response.text
    assert env.meta("chart", "inflacao") == before
    assert env.revisions("chart", "inflacao") == history


def test_invalid_category_recovery_keeps_other_analytical_settings(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    before = env.meta("chart", "inflacao")
    history = env.revisions("chart", "inflacao")

    data = _fields(version="1", note="guardar", series_a="ine.hicp_yoy.PT",
                   series_b="ine.unemployment_rate.PT", frequency="annual",
                   transform="pp", comparison_group="europe")
    response = c.post("/cms/chart/inflacao/save", data=data, headers=ORIGIN)

    assert response.status_code == 422
    assert 'name="version" value="1"' in response.text
    assert '<option value="europe" selected>' in response.text
    assert '<option value="annual" selected>' in response.text
    assert '<option value="pp" selected>' in response.text
    assert 'name="comparison_group"' in response.text
    assert env.meta("chart", "inflacao") == before
    assert env.revisions("chart", "inflacao") == history


def test_legacy_chart_save_does_not_materialise_new_keys(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    assert c.post("/cms/chart/inflacao/save", data={
        "version": "1", "title": "Inflação em Portugal", "note_text": "Nota.",
        "series_a": "ine.hicp_yoy.PT", "series_b": "", "derived_key": "",
        "window": "max", "scale": "single", "day": "", "note": "guardar",
    }, headers=ORIGIN).status_code == 303
    body = json.loads(env.revisions("chart", "inflacao")[0]["body_json"])
    assert not {"series_extra", "axes", "frequency", "transform", "base",
                "comparison_group"} & set(body)


def test_new_multiseries_form_saves_publishes_and_enters_the_library(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    data = _fields(
        version="1", note="guardar", title="Inflação e desemprego",
        series_a="ine.hicp_yoy.PT", series_b="ine.unemployment_rate.PT",
        axis_0="0", axis_1="1", scale="dual", comparison_group="portugal")
    assert c.post("/cms/chart/inflacao/save", data=data,
                  headers=ORIGIN).status_code == 303

    body = json.loads(env.revisions("chart", "inflacao")[0]["body_json"])
    assert body["series_extra"] == []
    assert body["axes"] == [0, 1]
    assert body["comparison_group"] == "portugal"
    assert "frequency" not in body and "transform" not in body

    assert c.post("/cms/chart/inflacao/publish",
                  data={"version": "2", "note": "publicar"},
                  headers=ORIGIN).status_code == 303
    dashboard = c.get("/cms").text
    assert "Biblioteca de comparações" in dashboard
    assert "Portugal" in dashboard and "Inflação e desemprego" in dashboard

    changed = _fields(
        version="3", note="mudar categoria", title="Inflação e desemprego",
        series_a="ine.hicp_yoy.PT", series_b="ine.unemployment_rate.PT",
        axis_0="0", axis_1="1", scale="dual", comparison_group="general")
    assert c.post("/cms/chart/inflacao/save", data=changed,
                  headers=ORIGIN).status_code == 303
    dashboard = c.get("/cms").text
    assert "categoria por publicar" in dashboard
    assert "Portugal" in dashboard  # the published category is still live


def test_new_chart_creation_form_persists_ordered_series_and_category(env):
    c = env.client()
    data = _fields(
        kind="chart", slug="comparacao", note="criar",
        title="Comparação criada", series_a="ine.hicp_yoy.PT",
        series_b="ine.unemployment_rate.PT", axis_0="0", axis_1="1",
        scale="dual", comparison_group="general")
    response = c.post("/cms/new", data=data, headers=ORIGIN)
    assert response.status_code == 303
    assert response.headers["location"] == "/cms/chart/comparacao"
    editor = c.get("/cms/chart/comparacao").text
    assert 'value="ine.hicp_yoy.PT" selected' in editor
    assert 'value="ine.unemployment_rate.PT" selected' in editor
    assert '<option value="1" selected>Eixo 1' in editor
    assert '<option value="general" selected>Geral' in editor


def test_service_refusal_keeps_submitted_transformation_and_version(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    before = env.meta("chart", "inflacao")
    history = env.revisions("chart", "inflacao")
    data = _fields(version="1", note="guardar", series_a="ine.hicp_yoy.PT",
                   series_b="ine.unemployment_rate.PT", transform="pp")
    response = c.post("/cms/chart/inflacao/save", data=data, headers=ORIGIN)

    assert response.status_code == 422
    assert 'name="version" value="1"' in response.text
    assert '<option value="pp" selected>' in response.text
    assert "annual" in response.text  # the service explains the required frequency
    assert env.meta("chart", "inflacao") == before
    assert env.revisions("chart", "inflacao") == history


def test_annual_base100_settings_round_trip_through_the_editor(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    data = _fields(version="1", note="guardar", series_a="ine.hicp_yoy.PT",
                   frequency="annual", transform="base100", base="2019",
                   comparison_group="general")
    assert c.post("/cms/chart/inflacao/save", data=data,
                  headers=ORIGIN).status_code == 303
    body = json.loads(env.revisions("chart", "inflacao")[0]["body_json"])
    assert body["frequency"] == "annual"
    assert body["transform"] == "base100"
    assert body["base"] == "2019"
    assert body["comparison_group"] == "general"

    editor = c.get("/cms/chart/inflacao").text
    assert '<option value="annual" selected>' in editor
    assert '<option value="base100" selected>' in editor
    assert 'name="base" inputmode="numeric"' in editor and 'value="2019"' in editor
    assert '<option value="general" selected>' in editor


