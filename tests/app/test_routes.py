"""HTTP contract of the public site: routes, headers, every page and the CSV export.

The pages are checked against the markup readers see, not against raw codes: a value rendered
without its source line, a withheld source named on a public list, or a code leaking into text
is a defect here too.
"""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import SECURITY_HEADERS, create_app
from tests.app.conftest import DERIVED, HICP, INACTIVE, UNEMP, WITHHELD, XCHECK

PAGES = ("/", "/temas/economy", f"/series/{HICP}", f"/calculadas/{DERIVED}", "/fontes",
         "/metodologia", "/pesquisa?q=desemprego")


def visible(html: str) -> str:
    """Text nodes only: tags (and the attributes inside them) are dropped."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# --- shell ------------------------------------------------------------------------------------

def test_healthz_answers_get_and_head(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.head("/healthz").status_code == 200


def test_home_answers_200_with_the_site_title(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Estatísticas oficiais, com a proveniência à vista" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_static_css_and_favicon_are_served(client):
    css = client.get("/static/css/prumo.css")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    icon = client.get("/static/images/prumo/favicon.svg")
    assert icon.status_code == 200 and icon.headers["content-type"].startswith("image/svg")


def test_unknown_route_renders_the_404_page(client):
    response = client.get("/nao-existe")
    assert response.status_code == 404
    assert "Página não encontrada" in response.text


def test_security_headers_are_exact_on_every_page(client):
    for path in PAGES + ("/nao-existe",):
        headers = client.get(path).headers
        assert headers["content-security-policy"] == SECURITY_HEADERS["Content-Security-Policy"]
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"


def test_only_get_and_head_are_routed(client):
    for path in PAGES:
        assert client.post(path).status_code == 405
        assert client.delete(path).status_code == 405


def test_no_page_ships_javascript_or_remote_asset(client):
    for path in PAGES:
        html = client.get(path).text
        assert "<script" not in html.lower()
        assert not re.search(r"<[a-zA-Z][^>]*\son[a-z]+=", html)  # no inline event handlers
        assert 'href="http://' not in html and 'src="http://' not in html
        assert "cdn." not in html and "googleapis" not in html


def test_forwarded_prefix_prefixes_every_internal_link(client):
    html = client.get("/", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert 'href="/dados/"' in html
    assert 'href="/dados/temas/economy"' in html
    assert 'href="/dados/static/css/prumo.css"' in html
    assert 'href="/series/' not in html  # nothing left un-prefixed


def test_prefix_is_normalised_when_it_arrives_unclean(client):
    for prefix in ("/dados/", "dados", "  /dados  "):
        html = client.get("/fontes", headers={"X-Forwarded-Prefix": prefix}).text
        assert 'href="/dados/fontes"' in html
        assert 'href="//dados' not in html


def test_hostile_prefix_is_ignored_not_echoed(client):
    # `//evil.example` would turn every href into a link to another host.
    for prefix in ("//evil.example", "/dados//x", "https://evil.example", "/dados?x=1",
                   "/../x", "\\evil.example"):
        html = client.get("/fontes", headers={"X-Forwarded-Prefix": prefix}).text
        assert "evil.example" not in html
        assert 'href="/fontes"' in html


def test_responses_vary_on_the_forwarded_prefix(client):
    assert client.get("/").headers["vary"] == "X-Forwarded-Prefix"


def test_a_catalogue_gap_is_a_503_not_a_500(client, monkeypatch):
    from presentation.catalog import pt

    monkeypatch.delitem(pt.FAMILIES, "hicp_yoy")
    response = client.get(f"/series/{HICP}")
    assert response.status_code == 503
    assert "Serviço indisponível" in response.text


def test_a_missing_view_is_a_503_not_a_500(site_path, tmp_path):
    import shutil
    import sqlite3

    path = tmp_path / "noview.db"
    shutil.copy(site_path, path)
    connection = sqlite3.connect(path)
    connection.execute("DROP VIEW served_observation")
    connection.commit()
    connection.close()
    with TestClient(create_app(str(path))) as broken:
        response = broken.get("/")
    assert response.status_code == 503
    assert "Serviço indisponível" in response.text


def test_unusable_database_renders_the_503_page(tmp_path):
    app = create_app(str(tmp_path / "missing.db"))
    with TestClient(app) as failing:
        response = failing.get("/")
    assert response.status_code == 503
    assert "Serviço indisponível" in response.text


# --- series page ------------------------------------------------------------------------------

def test_series_page_shows_the_stored_token_and_period(client):
    html = client.get(f"/series/{HICP}").text
    assert "1,8" in html and "outubro de 2026" in html
    assert "Taxa de variação homóloga do IHPC" in html
    assert "INE — Instituto Nacional de Estatística" in html


def test_series_page_hides_unknown_inactive_cross_check_and_withheld(client):
    for series_id in ("ine.nope.PT", INACTIVE, XCHECK, WITHHELD):
        response = client.get(f"/series/{series_id}")
        assert response.status_code == 404, series_id


def test_provenance_block_carries_receipt_run_and_sha(client):
    html = client.get(f"/series/{HICP}").text
    text = visible(html)
    assert "Execução" in text and "#" in text
    assert "b" * 12 in text and "bbbbbbbbbb" in text
    assert "HTTP 200" in text
    assert "amostra de 3 valores do conjunto" in text and "100% coincidentes" in text
    assert "Este valor foi um dos comparados." in text
    assert "CC BY 4.0" in text and 'href="https://www.ine.pt/x/terms"' in html


def test_revision_table_marks_the_served_version(client):
    text = visible(client.get(f"/series/{HICP}").text)
    assert "1,9" in text and "1,8" in text
    assert "em vigor" in text and "substituído" in text
    assert "1 períodos com revisões" in text


def test_series_page_shows_derived_and_cross_check_blocks(client):
    html = client.get(f"/series/{HICP}").text
    text = visible(html)
    assert "Verificação cruzada" in text and "Eurostat" in text
    assert "Calculado" not in text or "calculado" in text.lower()
    unemployment = visible(client.get(f"/series/{UNEMP}").text)
    assert "variação homóloga" in unemployment and "Calculado" in unemployment


def test_series_page_has_no_raw_codes_in_visible_text(client):
    text = visible(client.get(f"/series/{HICP}").text)
    for code in ("hicp_yoy", "unemployment_monthly", "sa_base", "period_change",
                 "yoy_change", "% M", "redistribution_ok"):
        assert code not in text, code


def test_series_csv_shares_the_value_tokens_byte_for_byte(client):
    response = client.get(f"/series/{HICP}.csv")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == f'attachment; filename="{HICP}.csv"'
    body = response.text
    assert body.startswith("\ufeff")
    lines = body.lstrip("\ufeff").splitlines()
    assert lines[0] == "periodo;valor;estado;recolhido_em"
    assert "2026-10;1.8;;2026-11-03T09:00:00+00:00" in lines
    assert "2026-08;2.1;;2026-11-01T09:00:00+00:00" in lines
    assert sum(1 for line in lines if re.match(r"^\d{4}-\d{2};", line)) == 3
    assert any(line.startswith("Licença: CC BY 4.0") for line in lines)


def test_series_csv_refuses_a_withheld_series(client):
    assert client.get(f"/series/{WITHHELD}.csv").status_code == 404
    assert client.get("/series/ine.nope.PT.csv").status_code == 404


def test_csv_exports_ship_reader_text_not_internal_codes(client):
    body = client.get(f"/series/{UNEMP}.csv").text
    lines = body.lstrip("\ufeff").splitlines()
    assert "2026-10;6.2;provisório;2026-11-03T09:00:00+00:00" in lines
    for code in ("normal", "provisional", "estimated", "revised", "break",
                 "UNVERIFIED", "pending", UNEMP, "unemployment_rate"):
        assert code not in body, code
    derived = client.get(f"/calculadas/{DERIVED}.csv").text
    rows = [line.split(";") for line in derived.lstrip("\ufeff").splitlines()
            if re.match(r"^\d{4}-\d{2};", line)]
    assert rows and all(row[2] == "p.p." for row in rows)
    for code in ("pct", "pp;", "balance", "index_2015_100", DERIVED):
        assert code not in derived, code


def test_derived_page_shows_the_badge_formula_and_inputs(client):
    html = client.get(f"/calculadas/{DERIVED}").text
    text = visible(html)
    assert "Calculado pelo Prumo" in text
    assert "Como é calculado" in text
    assert "Variação homóloga" in text
    assert "0,3" in text and "p.p." in text or "pontos percentuais" in text
    assert "Este valor não é publicado pelo editor" in text or "não publicado pelo editor" in text
    assert client.get("/calculadas/derived.nope").status_code == 404


def test_derived_page_names_the_base_by_title_never_by_id(client):
    text = visible(client.get(f"/calculadas/{DERIVED}").text)
    assert "a partir de Taxa de desemprego" in text
    assert DERIVED not in text and UNEMP not in text


def test_search_finds_by_id_but_never_renders_it(client):
    html = client.get(f"/pesquisa?q={UNEMP}").text
    assert "Taxa de desemprego" in html
    # the query itself is echoed in the heading; the result row must not carry the id
    meta = re.findall(r'<span class="row-meta">(.*?)</span>', html)
    assert meta and all(UNEMP not in line for line in meta)


def test_a_withdrawn_execution_never_publishes_legacy_rows(tmp_path):
    from ingest.db import open_db
    from ingest.models import Observation
    from tests.app.conftest import T2, T3, WORLD, build

    path = tmp_path / "legacy.db"
    build(path)
    db = open_db(path)
    legacy = db.legacy_run("worldbank", "legacy:worldbank", T2)
    db.write_legacy_observations(legacy,
                                 [(Observation.from_raw(WORLD, "2023", "9.99"), T2)])
    fetched = db.conn.execute(
        "SELECT r.id FROM dataset_run r JOIN source p ON p.id = r.source_id "
        "WHERE p.name = 'worldbank' AND r.state = 'verified' "
        "AND r.input_origin <> 'legacy' ORDER BY r.id").fetchone()[0]
    db.withdraw_run(fetched, "test withdrawal", T3)
    db.close()

    with TestClient(create_app(str(path))) as site:
        assert site.get(f"/series/{WORLD}").status_code == 404
        assert site.get(f"/series/{WORLD}.csv").status_code == 404
        for page in ("/", "/temas/economy", f"/pesquisa?q={WORLD}"):
            body = site.get(page).text
            assert "9.99" not in body and "9,99" not in body, page


def test_derived_csv_carries_the_formula_and_inherited_licence(client):
    response = client.get(f"/calculadas/{DERIVED}.csv")
    assert response.status_code == 200
    lines = response.text.lstrip("\ufeff").splitlines()
    assert lines[0] == "periodo;valor;unidade"
    assert any(line.startswith("Série calculada: ") for line in lines)
    assert any("Calculado pelo Prumo" in line for line in lines)
    assert any(line.startswith("Licença: CC BY 4.0") for line in lines)


# --- home, themes and search ------------------------------------------------------------------

def test_home_counts_cards_and_published_sources(client):
    text = visible(client.get("/").text)
    assert "3 séries de 2 instituições" in text
    assert "Inflação (IHPC)" in text and "Desemprego" in text
    assert "INE — Instituto Nacional de Estatística" in text
    assert "Banco Mundial" in text
    assert "Última recolha verificada" in text


def test_home_never_names_a_withheld_source(client):
    html = client.get("/").text
    assert "Redes Energéticas" not in html
    assert "Uso restrito" not in html


def test_theme_page_lists_the_series_of_that_theme(client):
    text = visible(client.get("/temas/economy").text)
    assert "Taxa de variação homóloga do IHPC" in text
    assert "Taxa de desemprego" in text
    assert "Crescimento do PIB" in text
    assert "3 séries publicadas nesta secção" in text


def test_theme_page_filters_by_geography_group(client):
    text = visible(client.get("/temas/economy?grupo=world").text)
    assert "Crescimento do PIB" in text
    assert "Taxa de desemprego" not in text
    assert "1 séries publicadas nesta secção" in text


def test_theme_unknown_or_cross_check_series_stay_out(client):
    assert client.get("/temas/nope").status_code == 404
    text = visible(client.get("/temas/economy").text)
    assert "eurostat.hicp_yoy.PT" not in text


def test_search_is_accent_insensitive_and_finds_by_geography(client):
    assert "Taxa de variação homóloga do IHPC" in visible(client.get("/pesquisa?q=inflacao").text)
    assert "Crescimento do PIB" in visible(client.get("/pesquisa?q=estados unidos").text)
    assert "Taxa de desemprego" in visible(client.get(f"/pesquisa?q={UNEMP}").text)


def test_search_without_results_and_without_query(client):
    empty = visible(client.get("/pesquisa?q=zzzz").text)
    assert "Sem resultados" in empty
    assert "Escreva um termo" in visible(client.get("/pesquisa").text)


def test_search_escapes_the_query_in_input_and_heading(client):
    html = client.get('/pesquisa?q="><script>alert(1)</script>').text
    assert "<script>" not in html
    assert "&lt;script&gt;" in html or "&#34;&gt;&lt;script&gt;" in html


# --- sources and methodology ------------------------------------------------------------------

def test_sources_page_separates_published_and_withheld(client):
    text = visible(client.get("/fontes").text)
    assert "Fontes e licenças" in text
    assert "INE — Instituto Nacional de Estatística" in text
    assert "Redes Energéticas Nacionais" in text
    assert "Fontes em avaliação" in text
    # the stored licence string is an operator note; readers get the catalogue's sentence
    assert "Preços e produção de eletricidade em Portugal" in text
    assert "Uso restrito" not in text
    assert "UNVERIFIED" not in text and "pending" not in text
    assert "99.9" not in text and "99,9" not in text  # no value of a withheld source


def test_source_licence_links_are_https_only(client):
    html = client.get("/fontes").text
    assert 'href="https://www.ine.pt/x/terms"' in html
    assert 'href="http://' not in html


def test_methodology_has_no_raw_codes_in_visible_text(client):
    text = visible(client.get("/metodologia").text)
    for code in ("period_change", "sa_base", "redistribution_ok", "raw_sha", "value_text"):
        assert code not in text, code
    assert "verificação" in text.lower()


@pytest.mark.parametrize("path", PAGES)
def test_every_page_declares_the_language_and_a_title(client, path):
    html = client.get(path).text
    assert '<html lang="pt-PT">' in html
    assert "<title>" in html and "Prumo" in html
