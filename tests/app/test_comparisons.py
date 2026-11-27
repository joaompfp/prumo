"""Two-series comparisons: curated pairs, aligned periods, one or two axes.

The pair fixture adds three Banco de Portugal series to the shared site database so all three
catalogue pairs render; the shared fixture is left untouched because other tests assert its counts.
"""
import re

import pytest
from fastapi.testclient import TestClient

from app import reads
from app.charts import two_series_chart
from app.formatting import format_value
from app.main import create_app
from ingest.db import open_db, read_db_readonly
from presentation.catalog import pt
from tests.app.cms_fixtures import publish_comparisons
from tests.app.conftest import T2, T3, build, fetch

BP = "bportugal"
EUR3 = "bportugal.euribor_3m.EA"
EUR12 = "bportugal.euribor_12m.EA"
CREDIT = "bportugal.credit_housing.PT"
UNEMP = "ine.unemployment_monthly.PT"
SLUGS = ("inflacao-e-desemprego", "euribor-e-inflacao", "credito-e-taxa")


def _add_bp(path):
    db = open_db(path)
    try:
        db.conn.execute(
            "INSERT INTO source(id, name, licence, licence_url, attribution, redistribution_ok) "
            "VALUES (6, ?, 'CC BY 4.0', 'https://www.bportugal.pt/terms', "
            "'Banco de Portugal', 1)", (BP,))
        for sid, key, geography, unit in (
                (EUR3, "euribor_3m.EA.M", "EA", "%"),
                (EUR12, "euribor_12m.EA.M", "EA", "%"),
                (CREDIT, "credit_housing.PT.M", "PT", "MEUR")):
            db.conn.execute(
                "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
                "frequency, unit, active) VALUES (?, 6, ?, 'primary', 'economy', ?, 'M', ?, 1)",
                (sid, key, geography, unit))
        db.conn.commit()
    finally:
        db.close()
    db = open_db(path)
    try:
        fetch(db, EUR3, {"2026-08": "2.1", "2026-09": "2.0", "2026-10": "1.9"}, T2,
              source=BP, sha="1" * 64)
        fetch(db, EUR12, {"2026-08": "2.6", "2026-09": "2.5"}, T2, source=BP, sha="2" * 64)
        # A newer period, in its own later run, so the pair's last COMMON period sits in the
        # earlier run: the page must cite the run behind the value it shows.
        fetch(db, EUR12, {"2026-10": "2.4"}, T3, source=BP, sha="4" * 64)
        fetch(db, CREDIT, {"2026-07": "100000", "2026-08": "101000", "2026-09": "102000"},
              T2, source=BP, sha="3" * 64)
    finally:
        db.close()


@pytest.fixture
def pairs_path(tmp_path):
    path = tmp_path / "pairs.db"
    build(path)
    _add_bp(path)
    publish_comparisons(path, SLUGS)
    return path


@pytest.fixture
def pairs_client(pairs_path):
    with TestClient(create_app(str(pairs_path)), follow_redirects=False) as client:
        yield client


def _page(path, slug):
    return read_db_readonly(path, lambda db: reads.comparison_page(db, slug))


def _chart_paths(html):
    return re.findall(r'<path class="chart-line chart-line-[ab]" d="([^"]+)"', html)


def test_index_lists_every_pair_in_catalogue_order(pairs_client):
    html = pairs_client.get("/comparar").text
    positions = [html.index(f"/comparar/{slug}") for slug in SLUGS]
    assert len(set(positions)) == len(SLUGS)
    assert len(re.findall(r'class="compare-link"', html)) == len(SLUGS)
    assert "Indicadores relacionados" in html
    assert "/caderno?" not in html


def test_each_pair_draws_two_distinct_lines(pairs_client):
    for slug in SLUGS:
        response = pairs_client.get(f"/comparar/{slug}")
        assert response.status_code == 200, slug
        html = response.text
        paths = _chart_paths(html)
        assert len(paths) == 2, slug
        assert paths[0] != paths[1], slug
        assert "legend-swatch" in html
        assert "style=" not in html
        # The approved enhancement adds one inert JSON block and one local deferred bundle.
        assert len(re.findall(r"<script[^>]*>", html)) == 2, slug


def test_each_pair_names_both_publishers(pairs_client):
    assert "INE - Instituto Nacional de Estatística" in pairs_client.get(
        "/comparar/inflacao-e-desemprego").text
    credit = pairs_client.get("/comparar/credito-e-taxa").text
    assert "Banco de Portugal" in credit
    # The mixed pair: one series from each institution, both named on the same page.
    mixed = pairs_client.get("/comparar/euribor-e-inflacao").text
    assert "Banco de Portugal" in mixed and "INE - Instituto Nacional de Estatística" in mixed
    # Both sides of a pair carry their own provenance block.
    assert credit.count('class="provenance-list"') == 2


def test_pair_one_pins_the_exact_stored_tokens_in_the_table(pairs_client):
    html = pairs_client.get("/comparar/inflacao-e-desemprego").text
    # Last common period 2026-10: HICP 1.8 (the revised token), unemployment 6.2.
    assert f'<td class="num">{format_value("1.8")}</td>' in html
    assert re.search(r'<td class="num">6,2(?:<| )', html)
    # The chart's own point titles carry the same tokens, not a rounded copy.
    assert "- outubro de 2026: 1,8 %" in html
    assert "- outubro de 2026: 6,2 %" in html


def test_table_renders_every_period_the_chart_draws(pairs_path):
    for slug in SLUGS:
        page = _page(pairs_path, slug)
        assert len(page.table_rows) == len(page.chart_points), slug


def test_alignment_states_what_each_side_loses(pairs_client):
    html = pairs_client.get("/comparar/inflacao-e-desemprego").text
    assert "2 períodos comuns, de setembro de 2026 a outubro de 2026." in html
    assert "Ficam de fora 1 período de Taxa de variação homóloga do IHPC" in html
    assert "Ficam de fora" in html


def test_alignment_counts_the_periods_lost_by_the_second_series(pairs_client):
    # EUR12 has 2026-10 that the credit stock lacks; the stock has 2026-07 that EUR12 lacks.
    html = pairs_client.get("/comparar/credito-e-taxa").text
    assert "2 períodos comuns, de agosto de 2026 a setembro de 2026." in html
    assert ("Ficam de fora 1 período de Taxa Euribor a 12 meses - Área do euro e "
            "1 período de Crédito à habitação - Portugal") in html


def test_dual_axis_pair_labels_both_sides(pairs_client):
    html = pairs_client.get("/comparar/credito-e-taxa").text
    assert html.count("chart-axis-label") == 2
    assert "Percentagem à esquerda, milhões de euros à direita" in html


def test_provenance_names_the_run_behind_the_period_shown(pairs_path, pairs_client):
    db = open_db(pairs_path)
    try:
        def run_of(period):
            return db.conn.execute(
                "SELECT dataset_run_id FROM served_observation WHERE series_id = ? "
                "AND period = ? AND kind = 'fetched'", (EUR12, period)).fetchone()[0]
        run_september = run_of("2026-09")
        run_october = run_of("2026-10")
    finally:
        db.close()
    assert run_september != run_october
    html = pairs_client.get("/comparar/credito-e-taxa").text
    assert f"#{run_september}" in html           # the value the page shows
    assert f"#{run_october}" not in html         # the series' newer, unpaired period


def test_unknown_slug_is_404(pairs_client):
    assert pairs_client.get("/comparar/nao-existe").status_code == 404


def test_published_comparison_is_independent_of_old_curation_copy(pairs_client, monkeypatch):
    broken = dict(pt.COMPARISONS["inflacao-e-desemprego"])
    del broken["subtitle"]
    monkeypatch.setitem(pt.COMPARISONS, "inflacao-e-desemprego", broken)
    assert pairs_client.get("/comparar/inflacao-e-desemprego").status_code == 200
    assert pairs_client.get("/comparar").status_code == 200


def test_a_non_numeric_token_leaves_the_chart_and_is_declared(tmp_path):
    path = tmp_path / "na.db"
    build(path)
    publish_comparisons(path, ("inflacao-e-desemprego",))
    db = open_db(path)
    try:
        db.conn.execute("UPDATE observation SET value_text = 'n.d.' "
                        "WHERE series_id = ? AND period = '2026-10'", (UNEMP,))
        db.conn.commit()
    finally:
        db.close()
    with TestClient(create_app(str(path))) as client:
        html = client.get("/comparar/inflacao-e-desemprego").text
        index = client.get("/comparar").text
    # 2026-10 is common but undrawable, so the page must not call it the last period shown.
    assert "1 período comum, em setembro de 2026." in html
    assert "setembro de 2026" in html
    assert "1 período comum sem valor numérico ou data reconhecida fica fora do gráfico e da tabela." in html
    # The CMS directory advertises the published composition rather than duplicating its table.
    assert "/comparar/inflacao-e-desemprego" in index
    assert "período comuns" not in index


def test_withheld_source_hides_the_pair_whole(tmp_path):
    path = tmp_path / "withdrawn.db"
    build(path)
    _add_bp(path)
    publish_comparisons(path, SLUGS)
    db = open_db(path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = ?", (BP,))
        db.conn.commit()
    finally:
        db.close()
    with TestClient(create_app(str(path))) as client:
        assert client.get("/comparar/credito-e-taxa").status_code == 404
        assert client.get("/comparar/euribor-e-inflacao").status_code == 404
        index = client.get("/comparar").text
        assert "/comparar/credito-e-taxa" not in index
        assert "/comparar/inflacao-e-desemprego" in index


def test_links_carry_the_mount_prefix(pairs_client):
    html = pairs_client.get("/comparar", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert 'href="/dados/comparar/inflacao-e-desemprego"' in html
    assert 'href="/dados/static/css/prumo.css"' in html


def test_headers_and_no_javascript_on_index_and_pair(pairs_client):
    index = pairs_client.get("/comparar")
    assert "default-src 'none'" in index.headers["content-security-policy"]
    assert "script-src" not in index.headers["content-security-policy"]
    assert "<script" not in index.text
    pair = pairs_client.get("/comparar/credito-e-taxa")
    assert "script-src 'self'" in pair.headers["content-security-policy"]
    assert "script-src-attr 'none'" in pair.headers["content-security-policy"]
    assert "default-src 'none'" in pair.headers["content-security-policy"]
    for response in (index, pair):
        assert "x-forwarded-prefix" in response.headers["vary"].lower()
        assert "style=" not in response.text


def test_unusable_database_is_503(tmp_path):
    with TestClient(create_app(str(tmp_path / "missing.db"))) as client:
        assert client.get("/comparar").status_code == 503
        assert client.get("/comparar/inflacao-e-desemprego").status_code == 503


def test_nav_carries_the_section_once_per_page(pairs_client):
    for path in ("/", "/comparar", "/comparar/credito-e-taxa"):
        html = pairs_client.get(path).text
        nav = re.search(r'<nav class="site-nav nav".*?</nav>', html, re.S)
        assert nav is not None, path
        assert nav.group(0).count('href="/comparar"') == 1, path
        assert ">Comparações<" in nav.group(0), path


# --- catalogue and chart, without a database -------------------------------------------------

def test_catalogue_pairs_are_internally_consistent():
    for slug, pair in pt.COMPARISONS.items():
        for key in ("series_a", "series_b", "title", "subtitle", "mechanism", "caption_note",
                    "scale"):
            assert pair.get(key, "").strip(), (slug, key)
        assert pair["series_a"] != pair["series_b"], slug
        assert pair["scale"] in ("one_axis", "dual_axis"), slug
    titles = [pair["title"] for pair in pt.COMPARISONS.values()]
    assert len(titles) == len(set(titles))


def test_scale_mode_is_declared_per_pair():
    assert pt.COMPARISONS["inflacao-e-desemprego"]["scale"] == "one_axis"
    assert pt.COMPARISONS["euribor-e-inflacao"]["scale"] == "one_axis"
    assert pt.COMPARISONS["credito-e-taxa"]["scale"] == "dual_axis"


def test_unit_rule_holds_against_the_served_series(pairs_path):
    """Every pair's two series are publishable and the declared scale matches the units."""
    db = open_db(pairs_path)
    try:
        for slug, pair in pt.COMPARISONS.items():
            a = db.public_series(pair["series_a"])
            b = db.public_series(pair["series_b"])
            assert a is not None and b is not None, slug
            assert a["role"] == "primary" and b["role"] == "primary", slug
            same = a["unit"] == b["unit"]
            assert same == (pair["scale"] == "one_axis"), slug
    finally:
        db.close()


def test_no_pair_names_a_withheld_source(pairs_path):
    db = open_db(pairs_path)
    try:
        for slug, pair in pt.COMPARISONS.items():
            for series_id in (pair["series_a"], pair["series_b"]):
                row = db.public_series(series_id)
                assert row is not None, (slug, series_id)
                assert row["licence"], (slug, series_id)
    finally:
        db.close()


def _points(rows):
    return [{"period": period, "a": a, "b": b} for period, a, b in rows]


def test_chart_one_axis_draws_two_lines_and_one_axis_label():
    svg = str(two_series_chart(_points([("2026-01", "1.0", "2.0"), ("2026-02", "1.5", "2.5")]),
                               frequency="M", title="Par", labels=("A", "B"), unit_a="%",
                               unit_b="%"))
    assert len(re.findall(r'class="chart-line chart-line-a"', svg)) == 1
    assert len(re.findall(r'class="chart-line chart-line-b"', svg)) == 1
    assert svg.count("chart-axis-label") == 1
    assert "Par: A (%) e B (%)" in svg


def test_chart_dual_flag_wins_over_equal_units():
    svg = str(two_series_chart(_points([("2026-01", "1.0", "2.0"), ("2026-02", "1.5", "2.5")]),
                               frequency="M", title="Par", labels=("A", "B"), unit_a="%",
                               unit_b="%", dual=True))
    assert svg.count("chart-axis-label") == 2


def test_chart_dual_axis_draws_two_axis_labels():
    svg = str(two_series_chart(
        _points([("2026-01", "1.0", "100000"), ("2026-02", "1.5", "101000")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="milhões de euros"))
    assert svg.count("chart-axis-label") == 2
    assert "milhões de euros" in svg


def test_chart_drops_a_period_whose_token_is_not_numeric():
    svg = str(two_series_chart(_points([("2026-01", "1.0", "n.d."), ("2026-02", "1.5", "2.5")]),
                               frequency="M", title="Par", labels=("A", "B"), unit_a="%",
                               unit_b="%"))
    # Two series at the one drawable period, and the undrawable period named in neither line.
    assert svg.count('class="chart-point"') == 2
    assert 'title="A - janeiro de 2026' not in svg


def test_chart_single_period_leaves_a_visible_mark():
    svg = str(two_series_chart(_points([("2026-01", "1.0", "2.0")]), frequency="M",
                               title="Par", labels=("A", "B"), unit_a="%", unit_b="%"))
    assert svg.count('class="chart-last chart-last-a"') == 1
    assert svg.count('class="chart-last chart-last-b"') == 1


def test_chart_breaks_the_line_across_a_missing_period():
    svg = str(two_series_chart(
        _points([("2026-01", "1.0", "2.0"), ("2026-02", "1.5", "2.5"), ("2026-06", "1.2", "2.2")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="%"))
    paths = re.findall(r'class="chart-line chart-line-a" d="([^"]+)"', svg)
    assert len(paths) == 1
    assert paths[0].count("M") == 2      # the line restarts after the gap instead of crossing it


def test_chart_survives_an_annual_gap_at_a_boundary_year():
    # 2005 is missing, so the decade tick cannot be placed by list index; the chart must still draw.
    svg = str(two_series_chart(_points([("2000", "1.0", "2.0"), ("2006", "1.5", "2.5"),
                                        ("2010", "1.2", "2.2")]),
                               frequency="A", title="Par", labels=("A", "B"), unit_a="%",
                               unit_b="%"))
    assert "<svg" in svg
    assert len(re.findall(r'class="chart-line chart-line-a"', svg)) == 1


def test_chart_emphasises_zero_on_one_axis_only():
    single = str(two_series_chart(
        _points([("2026-01", "-1.0", "2.0"), ("2026-02", "1.5", "2.5")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%", unit_b="%"))
    assert "chart-zero" in single
    dual = str(two_series_chart(
        _points([("2026-01", "-1.0", "200000"), ("2026-02", "1.5", "250000")]),
        frequency="M", title="Par", labels=("A", "B"), unit_a="%",
        unit_b="milhões de euros", dual=True))
    assert "chart-zero" not in dual


def test_chart_empty_state():
    svg = str(two_series_chart(_points([("2026-01", "x", "y")]), frequency="M", title="Par",
                               labels=("A", "B"), unit_a="%"))
    assert "chart-empty" in svg and "<svg" not in svg
