"""Interactive chart enhancement: scope, same-snapshot values, escaping and fallback contracts.

The bundle's browser behaviour is exercised separately (see the smoke command in the handoff);
these tests pin the server side: only eligible detail responses carry the inert payload and the
local bundle, every displayed point comes from the same prepared model as the SVG and table, and
malformed or unsafe data simply leaves the SVG in place.
"""
import gzip
import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import reads
from app.main import SECURITY_HEADERS, create_app
from ingest.db import open_db
from presentation.catalog import pt
from tests.app.conftest import DERIVED, HICP, INE, T3, build, fetch
from tests.app.test_comparisons import _add_bp

ROOT = Path(__file__).parents[2]
MANIFEST = json.loads((ROOT / "static" / "js" / "prumo-charts.manifest.json").read_text())
DATA = re.compile(r'<script type="application/json" class="chart-data">(.*?)</script>', re.S)


@pytest.fixture
def pairs_path(tmp_path):
    path = tmp_path / "pairs.db"
    build(path)
    _add_bp(path)
    return path


@pytest.fixture
def pairs_client(pairs_path):
    with TestClient(create_app(str(pairs_path)), follow_redirects=False) as site:
        yield site


def payload_of(html: str) -> dict:
    match = DATA.search(html)
    assert match, "page carries no chart payload"
    return json.loads(match.group(1))


def test_series_payload_uses_the_same_periods_and_exact_tokens(client):
    html = client.get(f"/series/{HICP}").text
    payload = payload_of(html)
    assert payload["version"] == 1 and payload["kind"] == "line"
    assert payload["periods"] == ["agosto de 2026", "setembro de 2026", "outubro de 2026"]
    assert payload["display"] == [["2,1 %"], ["2,0 %"], ["1,8 %"]]
    assert payload["series"] == [{"title": "Taxa de variação homóloga do IHPC - Portugal",
                                  "unit": "%", "style": "ink", "badge": ""}]
    # The exact stored token is also what the table and the headline show.
    assert '<td class="num">2,0</td>' in html or '<td class="num">1,8</td>' in html
    assert "1,8" in html and payload["display"][-1][0].startswith("1,8")
    for forbidden in ("hicp_yoy", "redistribution_ok", "value_text"):
        assert forbidden not in json.dumps(payload, ensure_ascii=False)


def test_payload_axes_match_the_prepared_domain_and_ticks(client):
    from ingest.db import read_db_readonly

    page = None

    def read(db):
        nonlocal page
        page = reads.series_page(db, HICP)
        return page

    # Read the same page data through the read layer to compare model and payload directly.
    read_db_readonly(client.app.state.db_path, read)
    payload = payload_of(client.get(f"/series/{HICP}").text)
    axis = payload["axes"][0]
    assert axis["min"] <= min(p.number for p in page.chart.points)
    assert axis["max"] >= max(p.number for p in page.chart.points)
    assert payload["y"] == [[float(p.number)] for p in page.chart.points]
    assert [tick["text"] for tick in axis["ticks"]] == [t.text for t in page.chart.y_ticks]
    assert [tick["value"] for tick in axis["ticks"]] == [float(t.value)
                                                         for t in page.chart.y_ticks]
    gaps = [axis["ticks"][i]["value"] - axis["ticks"][i - 1]["value"]
            for i in range(1, len(axis["ticks"]))]
    assert gaps and all(abs(gap - axis["interval"]) < 1e-9 for gap in gaps)
    xs = payload["x"]
    assert xs == sorted(xs)
    assert all(isinstance(x, (int, float)) for x in xs)


def test_comparison_payload_carries_both_series_and_dual_axes(pairs_client):
    for slug, axes in (("inflacao-e-desemprego", 1), ("credito-e-taxa", 2)):
        html = pairs_client.get(f"/comparar/{slug}").text
        payload = payload_of(html)
        assert payload["kind"] == "comparison"
        assert len(payload["axes"]) == axes, slug
        assert len(payload["series"]) == 2, slug
        assert len(payload["periods"]) == len(payload["display"])
        assert all(len(row) == 2 for row in payload["display"]), slug
    html = pairs_client.get("/comparar/inflacao-e-desemprego").text
    payload = payload_of(html)
    assert payload["display"][-1] == ["1,8 %", "6,2 %"]
    assert payload["periods"][-1] == "outubro de 2026"
    for forbidden in ("ine.hicp_yoy.PT", "ine.unemployment_monthly.PT", "one_axis"):
        assert forbidden not in json.dumps(payload, ensure_ascii=False)
    dual = payload_of(pairs_client.get("/comparar/credito-e-taxa").text)
    assert dual["axes"][0]["unit"] == "%"
    assert dual["axes"][1]["unit"] == "milhões de euros"
    assert dual["axes"][0]["min"] != dual["axes"][1]["min"]


def test_derived_payload_is_marked_calculated_and_keeps_its_precision(client):
    html = client.get(f"/calculadas/{DERIVED}").text
    payload = payload_of(html)
    assert payload["kind"] == "line"
    assert len(payload["periods"]) == 1
    assert payload["display"] == [["0,3 p.p."]]
    assert payload["series"][0]["badge"] == "Calculado pelo Prumo"
    # One point: a visible SVG mark, a static readout target, no useless slider movement.
    assert 'class="chart-last"' in html
    assert 'max="0"' in html
    assert "0,3" in html and "p.p." in html


def test_single_point_chart_has_no_duplicate_unit(client):
    html = client.get(f"/calculadas/{DERIVED}").text
    labels = re.findall(r'<svg class="chart"[^>]*aria-label="([^"]*)"', html)
    heading = re.search(r"<h1>(.*?)</h1>", html, re.S).group(1)
    assert labels == [heading]
    assert "(p.p.) (p.p.)" not in html


def test_empty_chart_keeps_the_svg_state_and_no_script(site_path):
    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE observation SET value_text = 'n.d.' WHERE series_id = ?", (HICP,))
        db.conn.commit()
    finally:
        db.close()
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as client:
        response = client.get(f"/series/{HICP}")
        assert response.status_code == 200
        assert "chart-empty" in response.text
        assert "<script" not in response.text
        assert response.headers["content-security-policy"] == SECURITY_HEADERS[
            "Content-Security-Policy"]


def test_nonfinite_token_is_not_drawn_or_inspected(site_path):
    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE observation SET value_text = 'NaN' WHERE series_id = ? "
                        "AND period = '2026-09'", (HICP,))
        db.conn.commit()
    finally:
        db.close()
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as client:
        payload = payload_of(client.get(f"/series/{HICP}").text)
    assert payload["periods"] == ["agosto de 2026", "outubro de 2026"]
    assert payload["display"] == [["2,1 %"], ["1,8 %"]]


def test_hostile_catalogue_title_cannot_close_the_data_block(client, monkeypatch):
    hostile = '</script><img src=x onerror="alert(1)">'
    monkeypatch.setitem(pt.FAMILIES, "hicp_yoy", hostile)
    html = client.get(f"/series/{HICP}").text
    assert "<img src=x" not in html
    assert "</script><img" not in html
    payload = payload_of(html)
    assert payload["series"][0]["title"] == hostile + " - Portugal"
    assert "\u003c" in DATA.search(html).group(1) or "\\u003c" in DATA.search(html).group(1)


def test_detail_scripts_use_the_validated_prefix_and_stay_local(client):
    html = client.get(f"/series/{HICP}", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert '<script src="/dados/static/js/prumo-charts.min.js?v=' in html
    assert '<script src="/static/' not in html
    assert "cdn." not in html and "http://" not in html and "https://cdn" not in html
    assert DATA.search(html)


def test_controls_and_live_region_are_rendered_without_javascript(client):
    html = client.get(f"/series/{HICP}").text
    assert 'class="chart-range"' in html and "hidden" in re.search(
        r'<input class="chart-range"[^>]*>', html).group(0)
    assert 'aria-valuetext="outubro de 2026"' in html
    assert 'class="chart-readout"' in html
    assert 'class="sr-only chart-live" aria-live="polite"' in html
    assert "Período no gráfico" in html
    assert "Use as setas, Início e Fim" in html
    assert '<div class="chart-canvas" aria-hidden="true"></div>' in html
    # The SVG remains named and is not hidden from assistive technology.
    svg = re.search(r"<svg class=\"chart\".*?</svg>", html, re.S).group(0)
    assert 'role="img"' in svg and "aria-label=" in svg and "aria-hidden" not in svg


def test_fallback_and_print_css_keep_the_server_svg():
    css = (ROOT / "static" / "css" / "prumo.css").read_text(encoding="utf-8")
    assert ".chart-canvas" in css and "opacity: 0; pointer-events: none" in css
    assert ".chart-enhanced .chart { opacity: 0; pointer-events: none; }" in css
    assert "@media print" in css
    print_block = css.split("@media print", 1)[1]
    assert ".chart-enhanced .chart { opacity: 1 !important; }" in print_block
    assert ".chart-canvas, .chart-controls, .chart-hint { display: none !important; }" in print_block
    # Never remove the fallback from the document or the accessibility tree.
    assert ".chart { display: none" not in css
    assert ".chart-enhanced .chart { display: none" not in css


def test_comparison_colours_match_in_svg_canvas_and_legend():
    css = (ROOT / "static" / "css" / "prumo.css").read_text(encoding="utf-8")
    assert ".chart-line-a { stroke: var(--ink); }" in css
    assert ".chart-line-b { stroke: var(--red); stroke-dasharray: 6 3; }" in css
    assert ".chart-last-a { fill: var(--ink); }" in css
    assert ".chart-last-b { fill: var(--red); }" in css
    assert ".swatch-a { background: var(--ink); }" in css
    assert "repeating-linear-gradient(90deg, var(--red)" in css
    adapter = (ROOT / "tools" / "charts" / "src" / "adapter.js").read_text(encoding="utf-8")
    assert "color: index === 0 ? ink : red" in adapter
    assert "type: index === 0 ? 'solid' : 'dashed'" in adapter


def test_bundle_is_the_committed_fingerprinted_asset(client):
    body = (ROOT / "static" / "js" / "prumo-charts.min.js").read_bytes()
    assert hashlib.sha256(body).hexdigest() == MANIFEST["sha256"]
    assert len(body) == MANIFEST["bytes"] <= 650000
    assert MANIFEST["gzip_bytes"] <= 220000
    assert len(gzip.compress(body, 9, mtime=0)) <= 220000  # local Python cross-check
    served = client.get(f"/static/js/prumo-charts.min.js?v={MANIFEST['sha256'][:12]}")
    assert served.status_code == 200
    assert served.content == body
    assert served.headers["content-type"].startswith(("application/javascript", "text/javascript"))
    assert MANIFEST["echarts"] == "6.1.0"
    for version in ("echarts", "zrender", "tslib"):
        assert MANIFEST[version]
    for name in ("echarts-APACHE-2.0.txt", "zrender-APACHE-2.0.txt", "tslib-0BSD.txt"):
        assert (ROOT / "static" / "js" / "licenses" / name).is_file()
    source = (ROOT / "tools" / "charts" / "src" / "adapter.js").read_text(encoding="utf-8")
    for forbidden in ("innerHTML", "eval(", "new Function", "document.write"):
        assert forbidden not in source


# --- E-REDES: one explicit UTC day, hour labels, no silent substitution ----------------------

DAY_A = "2026-10-01"
DAY_B = "2026-10-02"
DAY_C = "2026-10-03"


def _interval_path(tmp_path):
    path = tmp_path / "interval.db"
    build(path)
    db = open_db(path)
    try:
        db.conn.execute(
            "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
            "frequency, unit, active) SELECT 'ine.hicp_yoy_15m.PT', id, 'hicp_yoy.PT.PT15M', "
            "'primary', 'economy', 'PT', 'PT15M', '%', 1 FROM source WHERE name = ?",
            (INE.name,))
        db.conn.commit()
    finally:
        db.close()
    db = open_db(path)
    try:
        fetch(db, "ine.hicp_yoy_15m.PT", {
            f"{DAY_A}T00:00:00+00:00": "2.0",
            f"{DAY_A}T00:15:00+00:00": "2.1",
            f"{DAY_A}T00:30:00+00:00": "2.2",
            f"{DAY_B}T00:00:00+00:00": "2.3",
        }, T3)
    finally:
        db.close()
    return path


def test_interval_chart_opens_the_newest_day_with_more_than_one_point(tmp_path):
    path = _interval_path(tmp_path)
    reads.clear_cache()
    with TestClient(create_app(str(path))) as client:
        html = client.get("/series/ine.hicp_yoy_15m.PT").text
    payload = payload_of(html)
    assert payload["periods"] == ["01/10/2026, 00:00 UTC", "01/10/2026, 00:15 UTC",
                                  "01/10/2026, 00:30 UTC"]
    assert [tick["text"] for tick in payload["x_ticks"]] == ["00:00", "00:15", "00:30"]
    assert len(payload["x"]) == 3


def test_explicit_utc_day_is_honoured_including_a_partial_newest_day(tmp_path):
    path = _interval_path(tmp_path)
    reads.clear_cache()
    with TestClient(create_app(str(path))) as client:
        html = client.get(f"/series/ine.hicp_yoy_15m.PT?dia={DAY_B}").text
    payload = payload_of(html)
    assert payload["periods"] == ["02/10/2026, 00:00 UTC"]
    assert "02/10/2026" in html


def test_invalid_explicit_day_is_404_not_another_day(tmp_path):
    path = _interval_path(tmp_path)
    reads.clear_cache()
    with TestClient(create_app(str(path))) as client:
        response = client.get("/series/ine.hicp_yoy_15m.PT?dia=2099-01-01")
        assert response.status_code == 404
        assert "Página não encontrada" in response.text
        assert SECURITY_HEADERS["Content-Security-Policy"] == response.headers[
            "content-security-policy"]


def test_newly_available_day_is_read_after_the_metadata_cache_was_warmed(tmp_path):
    path = _interval_path(tmp_path)
    reads.clear_cache()
    with TestClient(create_app(str(path))) as client:
        assert client.get("/series/ine.hicp_yoy_15m.PT").status_code == 200  # warms day cache
        db = open_db(path)
        try:
            fetch(db, "ine.hicp_yoy_15m.PT", {f"{DAY_C}T00:00:00+00:00": "2.4",
                                              f"{DAY_C}T00:15:00+00:00": "2.5"}, T3,
                  sha="9" * 64)
        finally:
            db.close()
        response = client.get(f"/series/ine.hicp_yoy_15m.PT?dia={DAY_C}")
    assert response.status_code == 200
    payload = payload_of(response.text)
    assert len(payload["periods"]) == 2 and payload["periods"][0].startswith("03/10/2026")


def test_interval_payload_x_is_proportional_in_utc_seconds(tmp_path):
    path = _interval_path(tmp_path)
    reads.clear_cache()
    with TestClient(create_app(str(path))) as client:
        payload = payload_of(client.get("/series/ine.hicp_yoy_15m.PT").text)
    xs = payload["x"]
    assert xs[1] - xs[0] == xs[2] - xs[1] == 900  # UTC seconds, not 15-minute index steps
