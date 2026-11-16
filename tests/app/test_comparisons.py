"""Two-series comparisons: curated pairs, aligned periods, one or two axes.

The pair fixture adds three Banco de Portugal series to the shared site database so all three
catalogue pairs render; the shared fixture is left untouched because other tests assert its counts.
"""
import pytest
from fastapi.testclient import TestClient

from app.charts import two_series_chart
from app.formatting import format_value
from app.main import create_app
from ingest.db import open_db
from presentation.catalog import pt
from tests.app.conftest import T2, build, fetch

BP = "bportugal"
EUR3 = "bportugal.euribor_3m.EA"
EUR12 = "bportugal.euribor_12m.EA"
CREDIT = "bportugal.credit_housing.PT"
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
        fetch(db, CREDIT, {"2026-07": "100000", "2026-08": "101000", "2026-09": "102000"},
              T2, source=BP, sha="3" * 64)
    finally:
        db.close()


@pytest.fixture
def pairs_path(tmp_path):
    path = tmp_path / "pairs.db"
    build(path)
    _add_bp(path)
    return path


@pytest.fixture
def pairs_client(pairs_path):
    with TestClient(create_app(str(pairs_path)), follow_redirects=False) as client:
        yield client


def test_index_lists_every_pair_in_catalogue_order(pairs_client):
    html = pairs_client.get("/comparar").text
    positions = [html.index(f"/comparar/{slug}") for slug in SLUGS]
    assert positions == sorted(positions)
    assert "Não há escolha livre" in html


def test_each_pair_renders_both_series_and_both_publishers(pairs_client):
    for slug in SLUGS:
        response = pairs_client.get(f"/comparar/{slug}")
        assert response.status_code == 200, slug
        html = response.text
        assert html.count("chart-line-a") == 1 and html.count("chart-line-b") == 1
        assert "legend-swatch" in html
        assert "Proveniência" in html
        assert "<script" not in html and "style=" not in html


def test_pair_one_pins_the_exact_stored_tokens(pairs_client):
    html = pairs_client.get("/comparar/inflacao-e-desemprego").text
    # HICP 2026-10 is 1.8 (revised), unemployment 2026-10 is 6.2; both are the last common period.
    assert format_value("1.8") in html
    assert format_value("6.2") in html
    assert "INE — Instituto Nacional de Estatística" in html


def test_alignment_states_what_each_side_loses(pairs_client):
    html = pairs_client.get("/comparar/inflacao-e-desemprego").text
    assert "2 períodos comuns, de setembro de 2026 a outubro de 2026." in html
    assert "Ficam de fora 1 período de Taxa de variação homóloga do IHPC" in html
    assert "sem par na outra série" in html


def test_dual_axis_pair_labels_both_sides(pairs_client):
    html = pairs_client.get("/comparar/credito-e-taxa").text
    assert html.count("chart-axis-label") == 2
    assert "Percentagem à esquerda, milhões de euros à direita" in html


def test_unknown_slug_is_404(pairs_client):
    assert pairs_client.get("/comparar/nao-existe").status_code == 404


def test_withheld_source_hides_the_pair_whole(tmp_path):
    path = tmp_path / "withdrawn.db"
    build(path)
    _add_bp(path)
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


def test_headers_and_no_javascript(pairs_client):
    response = pairs_client.get("/comparar")
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "x-forwarded-prefix" in response.headers["vary"].lower()
    assert "<script" not in response.text


def test_unusable_database_is_503(tmp_path):
    with TestClient(create_app(str(tmp_path / "missing.db"))) as client:
        assert client.get("/comparar").status_code == 503
        assert client.get("/comparar/inflacao-e-desemprego").status_code == 503


def test_nav_carries_the_section_once(pairs_client):
    html = pairs_client.get("/").text
    assert html.count('href="/comparar"') == 1
    assert ">Comparações<" in html


# --- catalogue and chart, without a database -------------------------------------------------

def test_catalogue_pairs_are_internally_consistent():
    for slug, pair in pt.COMPARISONS.items():
        assert pair["series_a"] != pair["series_b"], slug
        assert pair["scale"] in ("one_axis", "dual_axis"), slug
        assert pair["mechanism"].strip() and pair["caption_note"].strip(), slug
        if pair["scale"] == "dual_axis":
            assert pair["caption_note"], slug
    titles = [pair["title"] for pair in pt.COMPARISONS.values()]
    assert len(titles) == len(set(titles))


def test_scale_mode_is_declared_per_pair():
    assert pt.COMPARISONS["inflacao-e-desemprego"]["scale"] == "one_axis"
    assert pt.COMPARISONS["euribor-e-inflacao"]["scale"] == "one_axis"
    assert pt.COMPARISONS["credito-e-taxa"]["scale"] == "dual_axis"


def test_unit_rule_holds_against_the_served_series(pairs_path):
    db = open_db(pairs_path)
    try:
        for slug, pair in pt.COMPARISONS.items():
            a = db.public_series(pair["series_a"])
            b = db.public_series(pair["series_b"])
            if a is None or b is None:
                continue
            same = a["unit"] == b["unit"]
            assert same == (pair["scale"] == "one_axis"), slug
    finally:
        db.close()


def _points(rows):
    return [{"period": period, "a": a, "b": b} for period, a, b in rows]


def test_chart_one_axis_draws_two_lines_and_one_axis_label():
    svg = str(two_series_chart(_points([("2026-01", "1.0", "2.0"), ("2026-02", "1.5", "2.5")]),
                               frequency="M", title="Par", labels=("A", "B"), unit_a="%",
                               unit_b="%"))
    assert svg.count("chart-line-a") == 1 and svg.count("chart-line-b") == 1
    assert svg.count("chart-axis-label") == 1
    assert "Par: A (%) e B (%)" in svg


def test_chart_dual_axis_draws_two_axis_labels():
    svg = str(two_series_chart(_points([("2026-01", "1.0", "100000"), ("2026-02", "1.5", "101000")]),
                               frequency="M", title="Par", labels=("A", "B"), unit_a="%",
                               unit_b="milhões de euros"))
    assert svg.count("chart-axis-label") == 2
    assert "milhões de euros" in svg


def test_chart_drops_a_period_whose_token_is_not_numeric():
    svg = str(two_series_chart(_points([("2026-01", "1.0", "x"), ("2026-02", "1.5", "2.5")]),
                               frequency="M", title="Par", labels=("A", "B"), unit_a="%",
                               unit_b="%"))
    assert svg.count("<circle") == 2          # one point per series, one period only


def test_chart_empty_state():
    svg = str(two_series_chart(_points([("2026-01", "x", "y")]), frequency="M", title="Par",
                               labels=("A", "B"), unit_a="%"))
    assert "chart-empty" in svg and "<svg" not in svg
