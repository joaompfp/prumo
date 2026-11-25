"""Exact source tokens survive the rounded reader display, in a closed disclosure."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader, select_autoescape

from analysis.transforms import AnalyticalValue, InputValue
from app import calendar_notebook, notebook_chart, reads
from app.main import create_app
from ingest.db import open_db
from presentation.notebook import text
from tests.app.conftest import DERIVED, HICP, T3, T4, XCHECK, build, fetch

T5 = "2026-11-05T09:00:00+00:00"
TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"
_DISCLOSURE = re.compile(
    r'<details class="original-value"><summary>Valor original</summary>'
    r'<span class="num">([^<]+)</span></details>')


@pytest.fixture
def evidence_db(tmp_path):
    """The shared served fixture plus two close vintages of one period (2.3451, 2.3452)."""
    path = tmp_path / "evidence.db"
    build(path)
    db = open_db(path)
    fetch(db, HICP, {"2026-11": "2.3451"}, T4)
    fetch(db, HICP, {"2026-11": "2.3452"}, T5)
    fetch(db, XCHECK, {"2026-11": "2.3451"}, T4, source="eurostat")
    db.close()
    reads.clear_cache()
    return path


def test_small_revisions_share_the_display_and_keep_both_exact_tokens(evidence_db):
    db = open_db(evidence_db)
    try:
        page = reads.series_page(db, HICP)
    finally:
        db.close()
    assert page is not None
    latest = page.revisions[0]
    assert latest.period == "2026-11"
    assert [version.value_display for version in latest.versions] == ["2,345", "2,345"]
    assert [version.raw_value for version in latest.versions] == ["2.3451", "2.3452"]
    assert page.cross_checks[0].value_display == "2,345"
    assert page.cross_checks[0].raw_value == "2.3451"

    with TestClient(create_app(str(evidence_db))) as client:
        html = client.get(f"/series/{HICP}").text
    disclosed = _DISCLOSURE.findall(html)
    assert disclosed.count("2.3451") == 2  # both revisions and the cross-check
    assert disclosed.count("2.3452") == 1
    # The long tokens occur only inside the closed disclosure, never in visible text.
    visible = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)
    assert visible.count("2.3451") == 2 and visible.count("2.3452") == 1


def test_derived_inputs_keep_the_exact_source_token(evidence_db):
    db = open_db(evidence_db)
    try:
        page = reads.derived_page(db, DERIVED)
    finally:
        db.close()
    assert page is not None and page.inputs
    assert page.inputs[0].value_display == "6,4"
    assert page.inputs[0].raw_value == "6.4"

    with TestClient(create_app(str(evidence_db))) as client:
        html = client.get(f"/calculadas/{DERIVED}").text
    assert "6.4" in _DISCLOSURE.findall(html)


def test_notebook_evidence_preserves_exact_input_and_output_tokens():
    copy = text("pt")
    raw = {"fetched_at": T3, "run_id": 7, "raw_sha": "a" * 64, "status_flag": None}
    item = InputValue(series_id=HICP, period="2026-09", value_text="6.400123")
    source = calendar_notebook._evidence_input(item, raw, "M", "pt")
    value = AnalyticalValue(period="2026", value_text="1.234568", inputs=(item,), method="mean")
    output = calendar_notebook._evidence_output(copy, value, raw, "M", "pt")
    assert source.value_display == "6,4" and source.raw_value == "6.400123"
    assert output.value_display == "1,235" and output.raw_value == "1.234568"
    assert output.inputs[0].raw_value == "6.400123"

    side = notebook_chart.SideEvidence(
        label="Taxa", series_path=f"/series/{HICP}", method_text="Média",
        formula_text="", base_text="", rounding_text=copy.chart_analysis_rounding,
        source_unit_text="%", chart_unit_text="%", calculated=True, latest=output,
        base=None, outputs=(), note="")
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)),
                      autoescape=select_autoescape(["html"]))
    macro = env.from_string(
        '{% from "_notebook_analysis.html" import analysis_evidence with context %}'
        "{{ analysis_evidence(panel, page) }}")
    html = macro.render(base="", panel={"evidence": [side]}, page={"copy": copy})
    disclosed = _DISCLOSURE.findall(html)
    assert "6.400123" in disclosed and "1.234568" in disclosed


def test_original_value_macro_escapes_tokens_and_stays_optional():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)),
                      autoescape=select_autoescape(["html"]))
    macro = env.from_string(
        '{% from "_original_value.html" import original_value %}{{ original_value(raw, display) }}')
    rendered = macro.render(raw="<script>alert(1)</script>", display=None)
    assert '<details class="original-value"><summary>Valor original</summary>' in rendered
    assert "&lt;script&gt;" in rendered and "<script>" not in rendered
    assert macro.render(raw="", display=None).strip() == ""
    assert macro.render(raw="2", display="2").strip() == ""
