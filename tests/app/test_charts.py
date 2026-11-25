"""Inline SVG charts: no script, no inline style, safe text, finite geometry."""
import re

from app.charts import line_chart, sparkline


def _points(values):
    return [{"period": f"2026-{m:02d}", "value_text": v} for m, v in enumerate(values, 1)]


def test_chart_is_svg_with_finite_geometry_and_no_script():
    svg = str(line_chart(_points(["1.0", "2.0", "3.0"]), frequency="M",
                         title="Taxa de desemprego", unit="%"))
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "NaN" not in svg and "None" not in svg
    assert "<script" not in svg and "style=" not in svg
    coords = re.findall(r'd="([^"]+)"', svg)
    assert coords and all("L" in c for c in coords)
    assert 'class="chart-last"' in svg


def test_chart_shows_periods_and_values_in_titles():
    svg = str(line_chart(_points(["1.0", "2.0"]), frequency="M", title="T", unit="%"))
    assert "janeiro de 2026: 1 %" in svg
    assert "fevereiro de 2026: 2 %" in svg


def test_chart_escapes_untrusted_title():
    svg = str(line_chart(_points(["1"]), frequency="M",
                         title='<img src=x onerror="alert(1)">'))
    assert "<img" not in svg and "&lt;img" in svg


def test_single_point_draws_without_dividing_by_zero():
    svg = str(line_chart(_points(["3.9"]), frequency="M", title="Um valor"))
    assert "<svg" in svg and 'class="chart-last"' in svg


def test_negative_domain_includes_zero():
    svg = str(line_chart(_points(["-30.5", "-20.0", "-25.0"]), frequency="M", title="Saldo"))
    assert ">0</text>" in svg


def test_empty_chart_is_a_sentence_not_a_broken_svg():
    assert str(line_chart([], frequency="M", title="x")) == \
        '<p class="chart-empty">Sem valores para representar.</p>'
    assert str(line_chart([{"period": "2026", "value_text": "n/d"}], frequency="A",
                          title="x")).startswith("<p")


def test_month_labels_differ_within_one_year():
    svg = str(line_chart(_points(["1", "2", "3"]), frequency="M", title="x"))
    assert "jan 2026" in svg and "fev 2026" in svg


def test_sparkline_is_optional_and_bare():
    assert str(sparkline([])) == ""
    assert str(sparkline([{"period": "2026", "value_text": "n/d"}])) == ""
    svg = str(sparkline(_points(["1", "2", "3"])))
    assert svg.startswith("<svg") and "chart-line" not in svg and "spark-line" in svg
    assert "<text" not in svg
