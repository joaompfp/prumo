"""Curated country pages: three groups, five countries, one shared scale.

The fixture builds the fifteen Eurostat identities through the real registry and run writes, so
the page is checked against the same eligibility, served-value and provenance paths production
uses. No browser and no network: the markup, the prepared chart and the read model are the
contract here.
"""
import hashlib
import re

import pytest
from fastapi.testclient import TestClient

from app import country_comparisons
from app.formatting import format_value
from app.main import create_app
from ingest.db import open_db, read_db_readonly
from ingest.models import SeriesSpec
from ingest.registry import sync_registry
from presentation.catalog import pt
from tests.app.cms_fixtures import publish_comparisons
from tests.app.conftest import EUROSTAT, T1, T2, T3, fetch

COUNTRIES = ("PT", "ES", "FR", "DE", "IT")
SLUGS = ("eletricidade-domestica", "pib-por-habitante", "divida-publica")
ELECTRICITY = "eurostat.electricity_price_household"
GDP = "eurostat.gdp_per_capita_eur"
DEBT = "eurostat.gov_debt_pct_gdp"

GROUPS = {
    "eletricidade-domestica": {
        "family": ELECTRICITY,
        "dataset": "nrg_pc_204",
        "frequency": "S",
        "unit": "EUR/kWh",
        "theme": "energy",
        "native": ("nrg_pc_204:freq=S,siec=E7000,nrg_cons=KWH2500-4999,unit=KWH,"
                   "tax=I_TAX,currency=EUR"),
        "periods": ("2024-S1", "2024-S2", "2025-S1", "2025-S2", "2026-S1"),
        "values": {
            "PT": ("0.2500", "0.2600", "0.2700", "0.2800", "0.2900"),
            "ES": ("0.2000", "0.2100", "0.2200", "0.2300", "0.2400"),
            "FR": ("0.2300", "0.2400", "0.2500", "0.2600", "0.2700"),
            "DE": ("0.4000", "0.4100", "0.4200", "0.4300", "0.4400"),
            "IT": ("0.3000", "0.3100", "0.3200", "0.3300", "0.3400"),
        },
    },
    "pib-por-habitante": {
        "family": GDP,
        "dataset": "nama_10_pc",
        "frequency": "A",
        "unit": "EUR per capita",
        "theme": "economy",
        "native": "nama_10_pc:freq=A,unit=CP_EUR_HAB,na_item=B1GQ",
        "periods": ("2023", "2024", "2025"),
        "values": {
            "PT": ("24000", "25000", "26000"),
            "ES": ("23000", "24000", "25000"),
            "FR": ("33000", "34000", "35000"),
            "DE": ("40000", "41000", "42000"),
            "IT": ("28000", "29000", "30000"),
        },
    },
    "divida-publica": {
        "family": DEBT,
        "dataset": "gov_10dd_edpt1",
        "frequency": "A",
        "unit": "% GDP",
        "theme": "economy",
        "native": "gov_10dd_edpt1:freq=A,unit=PC_GDP,sector=S13,na_item=GD",
        "periods": ("2023", "2024", "2025"),
        "values": {
            "PT": ("120.5", "121.0", "122.5"),
            "ES": ("105.0", "106.0", "107.0"),
            "FR": ("111.0", "112.0", "113.0"),
            "DE": ("63.0", "64.0", "65.0"),
            "IT": ("137.0", "138.0", "139.0"),
        },
    },
}


def _specs():
    specs = []
    for meta in GROUPS.values():
        for country in COUNTRIES:
            specs.append(SeriesSpec(
                id=f"{meta['family']}.{country}", source=EUROSTAT,
                indicator_key=f"{meta['family'].replace('.', '_')}.{country}."
                              f"{meta['frequency']}",
                role="primary", theme=meta["theme"], geography=country,
                frequency=meta["frequency"], unit=meta["unit"],
                native_code=f"{meta['native']},geo={country}"))
    return specs


def _seed(path):
    db = open_db(path)
    try:
        sync_registry(db, _specs())
    finally:
        db.close()
    db = open_db(path)
    try:
        for meta in GROUPS.values():
            for country in COUNTRIES:
                series_id = f"{meta['family']}.{country}"
                values = dict(zip(meta["periods"], meta["values"][country]))
                fetch(db, series_id, values, T1, source=EUROSTAT.name,
                      sha=hashlib.sha256(series_id.encode()).hexdigest())
        # A real provisional flag on the newest German GDP value, in its own later run.
        fetch(db, f"{GDP}.DE", {"2025": "42000"}, T2, source=EUROSTAT.name,
              flag="provisional", sha="f" * 64)
    finally:
        db.close()


@pytest.fixture
def countries_path(tmp_path):
    path = tmp_path / "countries.db"
    _seed(path)
    publish_comparisons(path, SLUGS)
    return path


@pytest.fixture
def countries_client(countries_path):
    with TestClient(create_app(str(countries_path)), follow_redirects=False) as client:
        yield client


def _page(path, slug):
    return read_db_readonly(path, lambda db: country_comparisons.page(db, slug))


def _index(path):
    return read_db_readonly(path, lambda db: country_comparisons.index(db))


def _mutate(path, sql, params=()):
    db = open_db(path)
    try:
        db.conn.execute(sql, params)
        db.conn.commit()
    finally:
        db.close()


def _run_of(db, series_id, period):
    return db.conn.execute(
        "SELECT dataset_run_id FROM served_observation WHERE series_id = ? AND period = ? "
        "AND kind = 'fetched'", (series_id, period)).fetchone()[0]


# --- discoverability and route -----------------------------------------------------------------

def test_index_lists_every_country_group_in_catalogue_order(countries_client):
    html = countries_client.get("/comparar").text
    positions = [html.index(f"/comparar/{slug}") for slug in SLUGS]
    assert len(set(positions)) == len(SLUGS)
    assert len(re.findall(r'class="compare-link"', html)) == len(SLUGS)
    assert "Entre países" in html
    assert "/caderno?" not in html
    assert "<script" not in html.lower()
    assert "prumo-charts" not in html


def test_index_does_not_prepare_a_chart(countries_path):
    index = _index(countries_path)
    assert tuple(row.slug for row in index.rows) == SLUGS
    # The bounded summary carries the common span and count, not a prepared chart.
    assert not hasattr(index.rows[0], "chart")


def test_unknown_country_slug_is_404_on_both_prefixes(countries_client):
    for headers in ({}, {"X-Forwarded-Prefix": "/dados"}):
        response = countries_client.get("/comparar/nao-existe", headers=headers)
        assert response.status_code == 404


def test_each_country_page_draws_five_distinct_lines_on_one_axis(countries_client):
    for slug in SLUGS:
        response = countries_client.get(f"/comparar/{slug}")
        assert response.status_code == 200, slug
        html = response.text
        styles = re.findall(r'class="chart-line chart-line-(g\d)"', html)
        assert styles == ["g0", "g1", "g2", "g3", "g4"], slug
        assert html.count("chart-axis-label") == 1, slug
        assert html.count("legend-swatch") == 5, slug
        assert "chart-line-g0" in html and "chart-line-g4" in html


def test_page_uses_short_country_labels_and_full_titles_elsewhere(countries_client):
    html = countries_client.get("/comparar/eletricidade-domestica").text
    for label in ("Portugal", "Espanha", "França", "Alemanha", "Itália"):
        assert label in html
    assert "Preço da eletricidade para uso doméstico - Portugal" in html
    assert "Eurostat" in html


def test_published_comparison_links_each_series_without_a_composition_form(countries_client):
    html = countries_client.get("/comparar/eletricidade-domestica").text
    assert "/caderno?" not in html
    assert 'name="series_a"' not in html
    assert 'name="escala"' not in html
    for country in COUNTRIES:
        assert f'href="/series/{ELECTRICITY}.{country}"' in html


def test_links_and_assets_carry_the_mount_prefix(countries_client):
    index = countries_client.get("/comparar", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert 'href="/dados/comparar/eletricidade-domestica"' in index
    assert 'href="/dados/static/css/prumo.css"' in index
    page = countries_client.get("/comparar/eletricidade-domestica",
                                headers={"X-Forwarded-Prefix": "/dados"}).text
    assert 'href="/dados/comparar"' in page
    assert 'src="/dados/static/js/prumo-charts.min.js?v=' in page


# --- exact values, flags and the complete table ------------------------------------------------

def test_summary_and_table_pin_the_exact_tokens(countries_path, countries_client):
    page = _page(countries_path, "eletricidade-domestica")
    assert page.latest_period_text == "1.º semestre de 2026"
    assert page.unit_text == "euros por kWh"
    assert tuple(side.latest_display for side in page.countries) == (
        format_value("0.2900"), format_value("0.2400"), format_value("0.2700"),
        format_value("0.4400"), format_value("0.3400"))
    html = countries_client.get("/comparar/eletricidade-domestica").text
    for token in ("0,29", "0,24", "0,27", "0,44", "0,34"):
        assert token in html
    # The exact four-decimal token survives; the axis may round, the summary and table do not.
    assert "0,29" in html


def test_provisional_flag_reaches_summary_and_table(countries_path, countries_client):
    page = _page(countries_path, "pib-por-habitante")
    de = page.countries[3]
    assert de.status_flag == "provisional" and de.status_text == "provisório"
    assert de.latest_display == format_value("42000")
    html = countries_client.get("/comparar/pib-por-habitante").text
    assert html.count("provisório") >= 2


def test_table_renders_every_plotted_period(countries_path, countries_client):
    for slug in SLUGS:
        page = _page(countries_path, slug)
        assert page.chart is not None, slug
        assert len(page.table_rows) == len(page.chart.points), slug
        assert len(page.table_rows) == len(GROUPS[slug]["periods"]), slug
        html = countries_client.get(f"/comparar/{slug}").text
        assert html.count('class="data-table"') == 1, slug
        # Newest first, as on the pair detail page, and every chart period is present.
        assert page.table_rows[0].period_text == page.chart.points[-1].period_text


def test_no_rounding_or_conversion_in_the_payload(countries_path):
    page = _page(countries_path, "eletricidade-domestica")
    assert page.chart_payload["kind"] == "group"
    assert len(page.chart_payload["series"]) == 5
    assert all(series["axis"] == 0 for series in page.chart_payload["series"])
    assert page.chart_payload["y"][-1] == [
        float(value.value_text) for value in page.chart.points[-1].values]


# --- alignment, missing values and gaps ---------------------------------------------------------

def test_alignment_counts_a_country_missing_from_the_common_periods(countries_path,
                                                                   countries_client):
    _mutate(countries_path,
            "DELETE FROM observation WHERE series_id = ? AND period = '2025-S1'",
            (f"{ELECTRICITY}.ES",))
    page = _page(countries_path, "eletricidade-domestica")
    assert len(page.table_rows) == 4
    assert page.alignment_text.startswith("4 períodos comuns,")
    assert "Espanha não publica 1 período que os outros países publicam." in page.alignment_text
    assert "Ficam de fora 1 período de Portugal" in page.alignment_text
    assert "Todos os países cobrem exactamente os mesmos períodos." not in page.alignment_text


def test_alignment_counts_each_country_that_has_an_unpaired_period(countries_path):
    for series_id in (f"{ELECTRICITY}.ES", f"{ELECTRICITY}.IT"):
        _mutate(countries_path,
                "DELETE FROM observation WHERE series_id = ? AND period = '2024-S1'",
                (series_id,))
    page = _page(countries_path, "eletricidade-domestica")
    assert len(page.table_rows) == 4
    assert "1 período de Portugal" in page.alignment_text
    assert "1 período de França" in page.alignment_text
    assert "1 período de Alemanha" in page.alignment_text
    # Spain and Italy share the same gap, so neither is behind the other three on its own.
    assert "Espanha nesta série" not in page.alignment_text
    assert "Itália nesta série" not in page.alignment_text


def test_full_coverage_is_stated_when_no_country_loses_a_period(countries_path):
    page = _page(countries_path, "divida-publica")
    assert "Todos os países cobrem exactamente os mesmos períodos." in page.alignment_text


def test_a_non_numeric_common_period_is_counted_separately(countries_path):
    _mutate(countries_path,
            "UPDATE observation SET value_text = 'n.d.' "
            "WHERE series_id = ? AND period = '2024-S2'", (f"{ELECTRICITY}.PT",))
    page = _page(countries_path, "eletricidade-domestica")
    assert len(page.table_rows) == 4
    assert "4 períodos comuns," in page.alignment_text
    assert ("1 período comum sem valor numérico na fonte fica fora do gráfico e da tabela."
            in page.alignment_text)
    assert "Ficam de fora" not in page.alignment_text


def test_a_country_with_a_gap_keeps_the_gap_in_the_line(countries_path):
    _mutate(countries_path,
            "DELETE FROM observation WHERE series_id = ? AND period = '2025-S1'",
            (f"{ELECTRICITY}.ES",))
    page = _page(countries_path, "eletricidade-domestica")
    assert page.chart is not None
    # 2024-S2 and 2025-S2 are two semesters apart in the shared intersection, so the line
    # restarts instead of crossing the absent 2025-S1.
    assert page.chart.breaks == (2,)


# --- eligibility, identity and dimensional refusal ---------------------------------------------

def test_withheld_source_hides_every_group(countries_path, countries_client):
    _mutate(countries_path, "UPDATE source SET redistribution_ok = 0 WHERE name = 'eurostat'")
    for slug in SLUGS:
        assert countries_client.get(f"/comparar/{slug}").status_code == 404, slug
    index = countries_client.get("/comparar").text
    assert "/comparar/" not in index


def test_inactive_country_hides_only_its_group(countries_path, countries_client):
    _mutate(countries_path, "UPDATE series SET active = 0 WHERE id = ?",
            (f"{ELECTRICITY}.IT",))
    assert countries_client.get("/comparar/eletricidade-domestica").status_code == 404
    assert countries_client.get("/comparar/pib-por-habitante").status_code == 200
    index = countries_client.get("/comparar").text
    assert "/comparar/eletricidade-domestica" not in index
    assert "/comparar/pib-por-habitante" in index


def test_withdrawn_run_hides_the_group(countries_path, countries_client):
    db = open_db(countries_path)
    try:
        run = _run_of(db, f"{ELECTRICITY}.IT", "2026-S1")
        db.withdraw_run(run, "teste de retirada", T3)
    finally:
        db.close()
    assert countries_client.get("/comparar/eletricidade-domestica").status_code == 404


def test_legacy_values_never_stand_in_for_a_fetched_side(countries_path, countries_client):
    _mutate(countries_path,
            "UPDATE observation SET kind = 'legacy-unverified' WHERE series_id = ?",
            (f"{ELECTRICITY}.ES",))
    _mutate(countries_path,
            "UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
    assert countries_client.get("/comparar/eletricidade-domestica").status_code == 404


def test_cross_check_side_hides_the_group(countries_path, countries_client):
    _mutate(countries_path, "UPDATE series SET role = 'cross_check' WHERE id = ?",
            (f"{ELECTRICITY}.FR",))
    assert countries_client.get("/comparar/eletricidade-domestica").status_code == 404


def test_a_different_native_dimension_hides_the_whole_group(countries_path, countries_client):
    _mutate(countries_path,
            "UPDATE series SET native_code = replace(native_code, "
            "'KWH2500-4999', 'KWH5000-14999') WHERE id = ?", (f"{ELECTRICITY}.FR",))
    assert countries_client.get("/comparar/eletricidade-domestica").status_code == 404
    index = countries_client.get("/comparar").text
    assert "/comparar/eletricidade-domestica" not in index


def test_a_different_stored_unit_hides_the_whole_group(countries_path, countries_client):
    _mutate(countries_path, "UPDATE series SET unit = 'EUR/MWh' WHERE id = ?",
            (f"{ELECTRICITY}.DE",))
    assert countries_client.get("/comparar/eletricidade-domestica").status_code == 404


def test_a_different_family_hides_the_whole_group(countries_path, countries_client):
    _mutate(countries_path,
            "UPDATE series SET indicator_key = 'eurostat_gdp_per_capita_eur.FR.A' "
            "WHERE id = ?", (f"{ELECTRICITY}.FR",))
    assert countries_client.get("/comparar/eletricidade-domestica").status_code == 404


# --- provenance is for the period drawn ---------------------------------------------------------

def test_provenance_uses_the_last_common_period_not_the_newest(countries_path):
    db = open_db(countries_path)
    try:
        run_2025 = _run_of(db, f"{GDP}.PT", "2025")
    finally:
        db.close()
    db = open_db(countries_path)
    try:
        run_2026 = fetch(db, f"{GDP}.PT", {"2026": "27000"}, T3,
                         source=EUROSTAT.name, sha="a" * 64)
    finally:
        db.close()
    page = _page(countries_path, "pib-por-habitante")
    assert page.latest_period_text == "2025"
    assert page.countries[0].latest_display == format_value("26000")
    assert page.countries[0].provenance is not None
    assert page.countries[0].provenance.run_id == run_2025
    assert run_2026 != run_2025
    with TestClient(create_app(str(countries_path))) as client:
        html = client.get("/comparar/pib-por-habitante").text
    assert f"#{run_2025}" in html
    assert f"#{run_2026}" not in html


# --- catalogue faults, headers, no writes -------------------------------------------------------

def test_old_curation_text_cannot_change_a_published_cms_comparison(countries_client, monkeypatch,
                                                                  caplog):
    broken = dict(pt.COUNTRY_COMPARISONS["pib-por-habitante"])
    del broken["subtitle"]
    monkeypatch.setitem(pt.COUNTRY_COMPARISONS, "pib-por-habitante", broken)
    cases = (("/comparar/pib-por-habitante", {}),
             ("/comparar/pib-por-habitante", {"X-Forwarded-Prefix": "/dados"}),
             ("/comparar", {}))
    for path, headers in cases:
        response = countries_client.get(path, headers=headers)
        assert response.status_code == 200, path
    assert "MissingText" not in caplog.text


def test_old_country_list_cannot_change_cms_series_membership(countries_client, monkeypatch):
    monkeypatch.setattr(pt, "COUNTRY_COMPARISONS_COUNTRIES", ("PT", "PT", "FR", "DE", "IT"))
    response = countries_client.get("/comparar/pib-por-habitante")
    assert response.status_code == 200
    assert 'href="/series/eurostat.gdp_per_capita_eur.ES"' in response.text
    assert countries_client.get("/comparar").status_code == 200


def test_index_is_script_free_and_pages_get_the_chart_policy(countries_client):
    index = countries_client.get("/comparar")
    assert "default-src 'none'" in index.headers["content-security-policy"]
    assert "script-src" not in index.headers["content-security-policy"]
    assert "<script" not in index.text.lower()
    page = countries_client.get("/comparar/eletricidade-domestica")
    assert page.status_code == 200
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert "script-src-attr 'none'" in page.headers["content-security-policy"]
    tags = re.findall(r"<script[^>]*>", page.text)
    assert len(tags) == 2
    assert '<script type="application/json"' in tags[0]
    assert '<script src="/static/js/prumo-charts.min.js?v=' in tags[1]
    assert " defer>" in tags[1]
    unknown = countries_client.get("/comparar/nao-existe")
    assert "script-src" not in unknown.headers["content-security-policy"]


def test_a_failed_chart_payload_keeps_the_server_svg(countries_path, countries_client,
                                                     monkeypatch):
    def decline(model, *, badge="", lang="pt"):
        return None
    monkeypatch.setattr("app.reads.interactive.build_payload", decline)
    response = countries_client.get("/comparar/eletricidade-domestica")
    assert response.status_code == 200
    assert "<svg" in response.text and "chart-line-g0" in response.text
    assert "prumo-charts" not in response.text
    assert "<script" not in response.text.lower()


def test_reads_do_not_write_the_database(countries_path, countries_client):
    before = hashlib.sha256(countries_path.read_bytes()).hexdigest()
    for path in ("/comparar", "/comparar/eletricidade-domestica",
                 "/comparar/nao-existe"):
        countries_client.get(path)
    after = hashlib.sha256(countries_path.read_bytes()).hexdigest()
    assert after == before
