"""Authored multiseries CMS charts through the shared Caderno preparation.

The same read-only snapshot prepares the authored document and its cards. These tests check the
authoritative axis membership at every reader surface, the annual/transformed views, the 1y
window and the refusal to publish a document with one selected side missing.
"""

import pytest

from app import cms_reads
from app.charts import chart_svg
from app.main import _templates
from backoffice.cms import Cms, CmsRefused
from ingest import cms as documents
from ingest.db import open_db
from tests.app.test_notebook_chart import build_site

A = "ine.hicp.PT"
B = "ine.unemp.PT"
C = "ine.credit.PT"
D = "ine.housing.PT"
SLUG = "comparacao-revista"


def months(start_year, end_year, value):
    return {f"{year:04d}-{month:02d}": value
            for year in range(start_year, end_year + 1) for month in range(1, 13)}


def site(tmp_path):
    path = build_site(tmp_path, [
        {"id": A, "key": "hicp_yoy.PT.M", "unit": "%", "periods": months(2022, 2026, "2.0")},
        {"id": B, "key": "unemployment_rate.PT.M", "unit": "%",
         "periods": months(2022, 2026, "6.0")},
        {"id": C, "key": "credit_consumer.PT.M", "unit": "MEUR",
         "periods": months(2022, 2026, "100.00")},
        {"id": D, "key": "credit_housing.PT.M", "unit": "MEUR",
         "periods": months(2022, 2026, "200.00")},
    ], name="cms-multiseries.db")
    return path, Cms(path, path)


def chart_body(**overrides):
    data = {
        "title": "Comparação revista",
        "note": "Uma leitura comparada.",
        "series_a": A,
        "series_b": B,
        "derived_key": None,
        "window": "max",
        "scale": "single",
        "day": None,
    }
    data.update(overrides)
    return data


def publish(cms, slug, body):
    meta = cms.create("chart", slug, body, actor="owner", note="criar")
    return cms.publish("chart", slug, meta["version"], actor="owner", note="publicar")


def read_view(path, slug=SLUG):
    db = open_db(path)
    try:
        return cms_reads.public_chart(db, slug)
    finally:
        db.close()


def test_four_series_keep_the_authored_axis_membership_at_every_surface(tmp_path):
    path, cms = site(tmp_path)
    publish(cms, SLUG, chart_body(
        series_b=B, series_extra=[C, D], scale="dual", axes=[1, 1, 0, 0],
        comparison_group="general", window="5y"))
    view = read_view(path)
    assert view is not None and view.analysis is not None
    panel = view.analysis
    assert panel.state == "ready"
    assert panel.chart.kind == "group" and panel.chart.axes == (1, 1, 0, 0)
    assert panel.chart.dual is True
    assert panel.chart.axis_labels == ("Eixo direito", "Eixo direito",
                                       "Eixo esquerdo", "Eixo esquerdo")
    assert [entry["axis"] for entry in panel.chart_payload["series"]] == [1, 1, 0, 0]
    assert [axis["unit"] for axis in panel.chart_payload["axes"]] == [
        "milhões de euros", "%"]
    assert len(panel.table_rows[0].cells) == len(panel.sides) == 4
    assert len(view.provenance) == 4
    assert [line.unit_text for line in view.provenance] == [
        "%", "%", "milhões de euros", "milhões de euros"]
    assert view.comparison_group == "general"
    assert view.is_pair is False
    assert view.chart is panel.chart and view.chart_payload is panel.chart_payload


def test_annual_original_view_validates_the_output_signature_after_harmonisation(tmp_path):
    path, cms = site(tmp_path)
    publish(cms, SLUG, chart_body(
        scale="dual", axes=[0, 1], frequency="annual", window="max"))
    view = read_view(path)
    assert view is not None and view.analysis is not None
    panel = view.analysis
    assert view.frequency == "A"
    assert panel.chart.frequency == "A" and panel.chart.axes == (0, 1)
    assert panel.period_label == "Último período anual"
    assert len(panel.evidence) == 2
    for evidence in panel.evidence:
        assert evidence.calculated is True
        assert evidence.latest.method_text
        assert len(evidence.latest.inputs) == 12
        assert len(evidence.outputs) == 5          # 2022..2026 complete years
    assert len(panel.table_rows) == 5
    assert panel.table_rows[-1].period_text == "2022"


def test_percentage_point_view_uses_one_common_axis_and_keeps_the_base_evidence(tmp_path):
    path, cms = site(tmp_path)
    publish(cms, SLUG, chart_body(
        frequency="annual", transform="pp", base="2025", window="5y"))
    view = read_view(path)
    assert view is not None and view.analysis is not None
    panel = view.analysis
    assert panel.chart.axes == (0, 0) and panel.chart.dual is False
    assert panel.chart.units == ("p.p.", "p.p.")
    assert [entry["badge"] for entry in panel.chart_payload["series"]] == [
        "calculado", "calculado"]
    assert [line.unit_text for line in view.provenance] == ["p.p.", "p.p."]
    assert panel.evidence and "2025" in panel.evidence[0].base_text
    assert all(cell.calculated for row in panel.table_rows for cell in row.cells)
    assert panel.evidence[0].chart_unit_text == "p.p."


def test_cms_one_year_window_is_honoured_and_not_silently_mapped_to_five(tmp_path):
    path, cms = site(tmp_path)
    publish(cms, SLUG, chart_body(
        comparison_group="general", window="1y"))
    view = read_view(path)
    assert view is not None and view.analysis is not None
    panel = view.analysis
    assert panel.settings.window == "1a"
    assert "1 ano" in panel.window_text
    assert len(panel.table_rows) == 13
    assert panel.table_rows[-1].period_text == "dezembro de 2025"
    assert panel.table_rows[0].period_text == "dezembro de 2026"


def test_pair_can_put_its_first_series_on_the_right_axis(tmp_path):
    path, cms = site(tmp_path)
    publish(cms, SLUG, chart_body(
        series_b=C, scale="dual", axes=[1, 0], comparison_group="general"))
    view = read_view(path)
    assert view is not None and view.analysis is not None
    panel = view.analysis
    assert panel.chart.kind == "group"
    assert panel.chart.axes == (1, 0)
    assert panel.chart.axis_labels == ("Eixo direito", "Eixo esquerdo")
    assert panel.chart.unit_a == "milhões de euros" and panel.chart.unit_b == "%"
    assert [entry["axis"] for entry in panel.chart_payload["series"]] == [1, 0]
    assert [axis["unit"] for axis in panel.chart_payload["axes"]] == [
        "milhões de euros", "%"]
    assert [side.unit_text for side in panel.sides] == ["%", "milhões de euros"]
    assert [line.period_text for line in view.provenance] == [
        side.period_text for side in panel.sides]


def test_explicit_axes_are_refused_when_one_axis_mixes_scale_signatures(tmp_path):
    _path, cms = site(tmp_path)
    body = chart_body(series_b=B, series_extra=[C], scale="dual", axes=[0, 1, 0],
                      comparison_group="general")
    meta = cms.create("chart", SLUG, body, actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        cms.publish("chart", SLUG, meta["version"], actor="owner", note="publicar")


def test_a_missing_selected_side_refuses_publication_instead_of_dropping_it(tmp_path):
    path, cms = site(tmp_path)
    body = chart_body(series_b=B, series_extra=["ine.missing.PT"], scale="dual",
                      axes=[0, 0, 1], comparison_group="general")
    meta = cms.create("chart", SLUG, body, actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        cms.publish("chart", SLUG, meta["version"], actor="owner", note="publicar")
    db = open_db(path)
    try:
        doc = cms_reads._document(db, "chart", SLUG, meta["draft_revision_id"])
        assert isinstance(doc, documents.ChartDocument)
        assert cms_reads.chart_problem(db, doc) is not None
    finally:
        db.close()
    assert read_view(path) is None


def test_a_day_is_refused_for_monthly_authored_series(tmp_path):
    _path, cms = site(tmp_path)
    body = chart_body(comparison_group="general", day="2026-10-01")
    meta = cms.create("chart", SLUG, body, actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        cms.publish("chart", SLUG, meta["version"], actor="owner", note="publicar")


def test_draft_preview_and_public_share_the_same_prepared_svg(tmp_path):
    path, cms = site(tmp_path)
    body = chart_body(series_b=B, series_extra=[C, D], scale="dual",
                      axes=[1, 1, 0, 0], comparison_group="general", window="5y")
    cms.create("chart", SLUG, body, actor="owner", note="criar")
    preview_name, preview = cms.preview("chart", SLUG)
    assert preview is not None
    assert preview_name == "cms_chart.html"
    assert preview.analysis is not None and preview.chart is not None
    preview_svg = str(chart_svg(preview.chart))
    assert "<script" not in preview_svg.lower()

    meta = cms.get("chart", SLUG)
    assert meta is not None
    cms.publish("chart", SLUG, meta["meta"]["version"], actor="owner", note="publicar")
    public = read_view(path)
    assert public is not None and public.chart is not None
    assert str(chart_svg(public.chart)) == preview_svg


def test_reader_address_contract_keeps_three_windows_and_no_axis_parameter():
    from app.notebook_chart import PARAM_NAMES, ChartSettings, parse_settings

    assert "axes" not in PARAM_NAMES
    values = {name: [] for name in PARAM_NAMES}
    values["janela"] = ["1a"]
    assert parse_settings(values, ("a", "b")) is None
    assert ChartSettings().axes == () and ChartSettings().params() == []


def test_authored_preview_renders_the_same_svg_without_the_chart_bundle(tmp_path):
    _path, cms = site(tmp_path)
    cms.create("chart", SLUG, chart_body(
        series_b=B, series_extra=[C, D], scale="dual", axes=[1, 1, 0, 0],
        comparison_group="general", window="5y"), actor="owner", note="criar")
    name, view = cms.preview("chart", SLUG)
    assert view is not None and view.analysis is not None
    html = _templates().env.get_template(name).render(
        page=view, preview=True, admin_base="/dados/admin/cms/graficos/comparacao-revista",
        base="/dados", nav=[], path="/dados/admin/cms/graficos/comparacao-revista/preview")
    assert "Pré-visualização" in html
    assert "/static/js/prumo-charts" not in html
    assert '<svg class="chart' in html
    assert "Eixo direito" in html and "Eixo esquerdo" in html


def test_axis_membership_is_ordered_and_rejects_a_mixed_axis_group():
    from app.notebook_chart import axes_shape_problem, axis_membership_problem

    signatures = (("%", None, None), ("MEUR", None, None), ("MEUR", None, None))
    # First authored series on the right, the two compatible sides on the left.
    assert axis_membership_problem(signatures, (1, 0, 0), "dupla") == ""
    assert axis_membership_problem(signatures, (0, 0, 1), "dupla") == "mixed_scale"
    assert axis_membership_problem(signatures, (1, 1, 1), "dupla") == "one_group"
    assert axis_membership_problem(signatures, (0, 0, 0), "comum") == "mixed_scale"
    assert axis_membership_problem((("%", None, None),) * 3, (0, 0, 0), "comum") == ""
    assert axes_shape_problem((0,), 2) == "invalid_axes"
    assert axes_shape_problem((0, 2), 2) == "invalid_axes"


def test_legacy_pair_keeps_the_old_preparation_and_carries_no_analysis(tmp_path):
    path, cms = site(tmp_path)
    publish(cms, SLUG, chart_body(scale="dual", axes=None))
    view = read_view(path)
    assert view is not None and view.analysis is None
    assert view.chart is not None
    assert view.chart.kind == "comparison" and view.chart.axes == (0, 1)
    assert len(view.provenance) == 2 and len(view.table) > 0
    assert view.table[0].a_display and view.table[0].b_display
    assert view.comparison_group is None
