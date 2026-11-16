"""Pure CMS document contracts: strict shapes, bounds, references and canonical text."""

import json

import pytest
from pydantic import ValidationError

from ingest import cms

EM = chr(0x2014)
BS = chr(92)


def page_body(**overrides):
    data = {
        "title": "Precos e rendimento",
        "introduction": "Uma leitura da economia portuguesa.",
        "section": "economy",
        "blocks": [
            {"type": "text", "text": "O texto editorial fica em paragrafos simples."},
            {"type": "card", "series_id": "ine.hicp_yoy.PT", "derived_key": None},
            {"type": "chart", "chart_slug": "inflacao-em-portugal"},
        ],
    }
    data.update(overrides)
    return data


def chart_body(**overrides):
    data = {
        "title": "Inflacao em Portugal",
        "note": "Variacao homóloga do indice de precos.",
        "series_a": "ine.hicp_yoy.PT",
        "series_b": None,
        "derived_key": None,
        "window": "max",
        "scale": "single",
        "day": None,
    }
    data.update(overrides)
    return data


def canonical_page(**overrides):
    return cms.canonical_for("page", page_body(**overrides))


def canonical_chart(**overrides):
    return cms.canonical_for("chart", chart_body(**overrides))


def test_page_parses_to_the_typed_model_and_round_trips():
    raw = canonical_page()
    document = cms.parse_body("page", raw)
    assert isinstance(document, cms.PageDocument)
    assert cms.canonical_body(document) == raw
    payload = json.loads(raw)
    assert payload["title"] == "Precos e rendimento"
    assert payload["introduction"] == "Uma leitura da economia portuguesa."
    assert payload["blocks"][1] == {
        "type": "card", "series_id": "ine.hicp_yoy.PT", "derived_key": None}


def test_chart_parses_to_the_typed_model_and_round_trips():
    raw = canonical_chart()
    document = cms.parse_body("chart", raw)
    assert isinstance(document, cms.ChartDocument)
    assert cms.canonical_body(document) == raw
    payload = json.loads(raw)
    assert payload["window"] == "max" and payload["scale"] == "single"
    assert payload["series_b"] is None and payload["derived_key"] is None


def test_canonical_text_keeps_unicode_and_is_compact_and_sorted():
    raw = canonical_chart(title="Inflação", note="Prumo - dados")
    assert "Inflação" in raw and '"day":null' in raw
    assert json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")) == raw


def test_storage_gate_accepts_only_exact_canonical_text():
    raw = canonical_page()
    assert cms.require_canonical_body("page", raw) == raw
    for noncanonical in (
            json.dumps(json.loads(raw), ensure_ascii=False, indent=2),
            raw + "\n",
            raw.replace(",", ", ")):
        with pytest.raises(cms.CmsDocumentError):
            cms.require_canonical_body("page", noncanonical)
    with pytest.raises(cms.CmsDocumentError):
        cms.require_canonical_body("page", page_body())


def test_unknown_kind_and_non_object_bodies_are_refused():
    with pytest.raises(cms.CmsDocumentError):
        cms.parse_body("article", "{}")
    with pytest.raises(cms.CmsDocumentError):
        cms.parse_body("page", "[]")
    with pytest.raises(cms.CmsDocumentError):
        cms.parse_body("page", "not json")
    with pytest.raises(cms.CmsDocumentError):
        cms.parse_body("page", 123)


def test_kind_selects_the_model_and_cross_kind_fields_are_refused():
    with pytest.raises(ValidationError):
        cms.parse_body("page", chart_body())
    with pytest.raises(ValidationError):
        cms.parse_body("chart", page_body())


def test_extra_fields_are_refused_at_every_level():
    with pytest.raises(ValidationError):
        cms.parse_body("page", page_body(html="<b>texto</b>"))
    with pytest.raises(ValidationError):
        cms.parse_body("page", page_body(blocks=[
            {"type": "card", "series_id": "ine.hicp_yoy.PT", "unit": "pct"}]))
    with pytest.raises(ValidationError):
        cms.parse_body("chart", chart_body(raw_values=[1, 2, 3]))
    with pytest.raises(ValidationError):
        cms.parse_body("chart", chart_body(series_b="ine.gdp.PT", unit="pct"))


@pytest.mark.parametrize("slug", [
    "", "Precos", "precos--pt", "-precos", "precos-", "precos_pt", "precos pt",
    "a" * 61,
])
def test_slug_is_lower_kebab_and_at_most_sixty(slug):
    with pytest.raises(cms.CmsDocumentError):
        cms.validate_slug(slug)
    assert cms.validate_slug("a" * 60) == "a" * 60


def test_bad_chart_slug_reference_is_refused():
    with pytest.raises(ValidationError):
        cms.parse_body("page", page_body(blocks=[
            {"type": "chart", "chart_slug": "Inflacao"}]))


@pytest.mark.parametrize("bad", [
    EM,
    "texto " + EM,
    "&" + "mdash;",
    "&" + "mdash",
    "&" + "#8212;",
    "&" + "#x2014;",
    "&" + "#X02014;",
    "&" + "amp;" + "mdash;",
    "&" + "amp;" + "#8212;",
    "%" + "e2" + "%" + "80" + "%" + "94",
    BS + "u2014",
    BS + "U00002014",
    BS + "u{2014}",
    BS + "N{EM DASH}",
    BS + "002014",
])
def test_literal_and_encoded_em_dashes_are_refused(bad):
    with pytest.raises(ValidationError):
        cms.canonical_for("page", page_body(title=bad))
    with pytest.raises(ValidationError):
        cms.canonical_for("page", page_body(blocks=[{"type": "text", "text": bad}]))
    with pytest.raises(ValidationError):
        cms.canonical_for("chart", chart_body(note=bad))


@pytest.mark.parametrize("safe", ["Prumo - dados", "0x2014", "U+2014", "1998-2026"])
def test_plain_hyphens_and_code_point_names_survive(safe):
    raw = canonical_page(title=safe)
    assert json.loads(raw)["title"] == safe


def test_title_introduction_text_and_note_bounds():
    assert json.loads(canonical_page(title="t" * 160))["title"] == "t" * 160
    with pytest.raises(ValidationError):
        canonical_page(title="t" * 161)
    assert json.loads(canonical_page(introduction="i" * 4000))["introduction"]
    with pytest.raises(ValidationError):
        canonical_page(introduction="i" * 4001)
    assert json.loads(canonical_page(blocks=[
        {"type": "text", "text": "x" * 4000}]))["blocks"]
    with pytest.raises(ValidationError):
        canonical_page(blocks=[{"type": "text", "text": "x" * 4001}])
    with pytest.raises(ValidationError):
        canonical_page(blocks=[{"type": "text", "text": "   "}])
    assert json.loads(canonical_chart(note="n" * 4000))["note"] == "n" * 4000
    with pytest.raises(ValidationError):
        canonical_chart(note="n" * 4001)


def test_block_list_holds_at_most_twelve_typed_blocks():
    blocks = [{"type": "text", "text": f"paragrafo {i}"} for i in range(12)]
    assert len(json.loads(canonical_page(blocks=blocks))["blocks"]) == 12
    with pytest.raises(ValidationError):
        canonical_page(blocks=blocks + [{"type": "text", "text": "a mais"}])
    with pytest.raises(ValidationError):
        canonical_page(blocks=[{"type": "unknown"}])
    missing = page_body()
    del missing["blocks"]
    with pytest.raises(ValidationError):
        cms.parse_body("page", missing)


def test_registry_references_are_ids_not_free_text_or_html():
    with pytest.raises(ValidationError):
        cms.parse_body("page", page_body(blocks=[
            {"type": "card", "series_id": "<script>alert(1)</script>"}]))
    with pytest.raises(ValidationError):
        cms.parse_body("page", page_body(blocks=[
            {"type": "card", "series_id": "ine.hicp_yoy.PT", "derived_key": "<b>"}]))
    with pytest.raises(ValidationError):
        cms.parse_body("chart", chart_body(series_a="ine.hicp_yoy.PT; DROP TABLE"))


def test_two_series_must_differ_and_can_use_dual_scale():
    document = cms.parse_body("chart", canonical_chart(
        series_b="ine.gdp_yoy.PT", scale="dual"))
    assert document.series_b == "ine.gdp_yoy.PT" and document.scale == "dual"
    with pytest.raises(ValidationError):
        canonical_chart(series_b="ine.hicp_yoy.PT", scale="dual")


def test_derived_key_is_only_for_a_single_series_chart():
    document = cms.parse_body("chart", canonical_chart(
        derived_key="derived.hicp_yoy.PT.period_change"))
    assert document.derived_key == "derived.hicp_yoy.PT.period_change"
    with pytest.raises(ValidationError):
        canonical_chart(series_b="ine.gdp_yoy.PT", scale="dual",
                        derived_key="derived.hicp_yoy.PT.period_change")


def test_one_series_cannot_use_the_dual_scale():
    with pytest.raises(ValidationError):
        canonical_chart(scale="dual")


def test_day_is_an_optional_real_iso_date():
    assert json.loads(canonical_chart(day="2026-11-10"))["day"] == "2026-11-10"
    for bad in ("2026-02-30", "10-11-2026", "2026-1-01", "2026-11-10T00:00:00Z"):
        with pytest.raises(ValidationError):
            canonical_chart(day=bad)


def test_window_and_scale_vocabularies_are_closed():
    for window in ("max", "1y", "5y", "10y"):
        assert json.loads(canonical_chart(window=window))["window"] == window
    with pytest.raises(ValidationError):
        canonical_chart(window="10")
    with pytest.raises(ValidationError):
        canonical_chart(scale="log")
