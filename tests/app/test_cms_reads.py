"""Public CMS rendering: published-only routes, read-time eligibility and one chart preparation.

The database is the deterministic public fixture; documents are authored through the real
service. Every assertion is about what a reader receives, not about internal codes.
"""
import re

import pytest

from app import reads
from app.main import CHART_CSP, SECURITY_HEADERS, _templates
from backoffice.cms import Cms, CmsRefused
from ingest.db import open_db
from presentation.catalog import pt
from tests.app.conftest import (
    DERIVED,
    HICP,
    T1,
    T2,
    T3,
    UNEMP,
    WORLD,
    fetch,
)
from tests.app.test_interactive import payload_of

PAGE = "precos-e-desemprego"
CHART = "inflacao-desemprego"


def _chart(**overrides):
    data = {"title": "Inflação e desemprego", "note": "Dois indicadores no mesmo gráfico.",
            "series_a": HICP, "series_b": UNEMP, "derived_key": None, "window": "max",
            "scale": "single", "day": None}
    data.update(overrides)
    return data


def _page(blocks, *, title="Preços e desemprego", section="economy",
          introduction="Primeiro parágrafo.\n\nSegundo parágrafo."):
    return {"title": title, "introduction": introduction, "section": section,
            "blocks": blocks}


def publish(cms, kind, slug, body):
    meta = cms.create(kind, slug, body, actor="owner", note="criar")
    return cms.publish(kind, slug, meta["version"], actor="owner", note="publicar")


def add_series(path, series_id, *, key, frequency="M", unit="%", theme="economy",
               geography="PT", source="ine"):
    db = open_db(path)
    try:
        db.conn.execute(
            "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
            "frequency, unit, active) SELECT ?, id, ?, 'primary', ?, ?, ?, ?, 1 "
            "FROM source WHERE name = ?",
            (series_id, key, theme, geography, frequency, unit, source))
    finally:
        db.close()


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.fixture
def cms(site_path):
    return Cms(site_path, site_path)


def test_page_renders_escaped_text_cards_and_a_chart(client, cms):
    publish(cms, "chart", CHART, _chart())
    publish(cms, "page", PAGE, _page([
        {"type": "text", "text": "Uma leitura <b>editorial</b>.\n\nOutro parágrafo."},
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "chart", "chart_slug": CHART},
    ]))
    response = client.get(f"/paginas/{PAGE}")
    assert response.status_code == 200
    assert response.headers["content-security-policy"] == CHART_CSP
    html = response.text
    assert "&lt;b&gt;editorial&lt;/b&gt;" in html
    assert "<b>editorial</b>" not in html
    assert html.count('class="lede"') == 2          # introduction paragraphs
    assert "1,8" in html                             # HICP latest stored token
    assert '<svg class="chart' in html
    assert f'href="/graficos/{CHART}"' in html
    assert "/static/js/prumo-charts" in html
    assert client.head(f"/paginas/{PAGE}").status_code == 200


def test_page_with_a_hero_renders_exactly_one_h1_and_keeps_section_metadata(client, cms):
    publish(cms, "page", "abertura", _page([
        {"type": "hero", "eyebrow": "Dados", "title": "Título de abertura"},
        {"type": "text", "text": "Corpo depois do herói."},
    ], introduction="Introdução da página."))
    response = client.get("/paginas/abertura")
    assert response.status_code == 200
    html = response.text
    headings = re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, re.S)
    assert len(headings) == 1
    assert "Título de abertura" in headings[0]
    assert 'aria-label="Caminho"' in html       # the breadcrumb stays
    assert "Economia" in html                   # the section metadata stays


def test_page_without_a_hero_keeps_the_page_title_as_its_single_h1(client, cms):
    publish(cms, "page", "sem-abertura", _page([{"type": "text", "text": "Corpo."}]))
    html = client.get("/paginas/sem-abertura").text
    headings = re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, re.S)
    assert len(headings) == 1
    assert "Preços e desemprego" in headings[0]


def test_drafts_unknown_slugs_and_unpublished_documents_are_404(client, cms):
    cms.create("page", "rascunho", _page([{"type": "text", "text": "Por publicar."}]),
               actor="owner", note="criar")
    cms.create("chart", "por-publicar", _chart(), actor="owner", note="criar")
    assert client.get("/paginas/rascunho").status_code == 404
    assert client.get("/graficos/por-publicar").status_code == 404
    assert client.get("/paginas/Nao-Existe").status_code == 404
    assert client.get("/graficos/slug_invalido").status_code == 404

    publish(cms, "page", PAGE, _page([{"type": "text", "text": "Publicado."}]))
    assert client.get(f"/paginas/{PAGE}").status_code == 200
    meta = cms.get("page", PAGE)["meta"]
    cms.unpublish("page", PAGE, meta["version"], actor="owner", note="despublicar")
    assert client.get(f"/paginas/{PAGE}").status_code == 404
    assert client.post(f"/paginas/{PAGE}").status_code == 405


def test_licence_revocation_drops_only_the_affected_card_with_a_generic_note(
        client, cms, site_path, caplog):
    publish(cms, "page", PAGE, _page([
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "card", "series_id": WORLD, "derived_key": None},
    ]))
    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'worldbank'")
    finally:
        db.close()
    with caplog.at_level("WARNING", logger="prumo.app"):
        response = client.get(f"/paginas/{PAGE}")
    assert response.status_code == 200
    html = response.text
    assert "Taxa de variação homóloga do IHPC - Portugal" in html
    assert "Crescimento do PIB" not in html
    assert "Parte desta página não está disponível neste momento." in html
    assert "worldbank" not in visible(html)
    assert WORLD not in html
    assert any("cms page block dropped" in message and WORLD in message
               and "withheld" in message for message in caplog.messages)


def test_missing_reader_text_drops_the_card_and_keeps_the_page(client, cms, monkeypatch):
    publish(cms, "page", PAGE, _page([
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "card", "series_id": UNEMP, "derived_key": None},
    ]))
    monkeypatch.delitem(pt.FAMILIES, "hicp_yoy")
    response = client.get(f"/paginas/{PAGE}")
    assert response.status_code == 200
    assert "Taxa de desemprego - Portugal" in response.text
    assert "IHPC" not in response.text
    assert "Parte desta página não está disponível neste momento." in response.text


def test_chart_block_is_dropped_when_its_chart_is_unpublished(client, cms):
    publish(cms, "chart", CHART, _chart())
    publish(cms, "page", PAGE, _page([
        {"type": "text", "text": "Texto que fica."},
        {"type": "chart", "chart_slug": CHART},
    ]))
    assert f'href="/graficos/{CHART}"' in client.get(f"/paginas/{PAGE}").text
    meta = cms.get("chart", CHART)["meta"]
    cms.unpublish("chart", CHART, meta["version"], actor="owner", note="retirar")
    response = client.get(f"/paginas/{PAGE}")
    assert response.status_code == 200
    assert "Texto que fica." in response.text
    assert f'href="/graficos/{CHART}"' not in response.text
    assert "Parte desta página não está disponível neste momento." in response.text
    assert client.get(f"/graficos/{CHART}").status_code == 404


def test_chart_block_is_dropped_when_its_series_licence_is_revoked(
        client, cms, site_path, caplog):
    publish(cms, "chart", CHART, _chart())
    publish(cms, "page", PAGE, _page([
        {"type": "text", "text": "Texto que fica."},
        {"type": "chart", "chart_slug": CHART},
    ]))
    assert f'href="/graficos/{CHART}"' in client.get(f"/paginas/{PAGE}").text
    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'ine'")
    finally:
        db.close()
    with caplog.at_level("WARNING", logger="prumo.app"):
        response = client.get(f"/paginas/{PAGE}")
    assert response.status_code == 200
    assert "Texto que fica." in response.text
    assert f'href="/graficos/{CHART}"' not in response.text
    assert "Parte desta página não está disponível neste momento." in response.text
    assert client.get(f"/graficos/{CHART}").status_code == 404
    assert any("cms page block dropped" in message and CHART in message
               for message in caplog.messages)


def test_calculated_chart_shows_badge_formula_base_and_caveats_without_raw_keys(
        client, cms):
    publish(cms, "chart", "desemprego-calculado", _chart(
        title="Variação do desemprego", series_a=UNEMP, series_b=None,
        derived_key=DERIVED, note="Calculado a partir da taxa publicada."))
    response = client.get("/graficos/desemprego-calculado")
    assert response.status_code == 200
    html = response.text
    assert "Calculado pelo Prumo" in html
    assert "Variação homóloga (diferença), calculada pelo Prumo a partir de" in html
    assert "Taxa de desemprego - Portugal" in html
    assert "0,3" in html
    assert f'href="/calculadas/{DERIVED}"' in html
    assert f'href="/series/{UNEMP}"' in html
    assert DERIVED not in visible(html) and UNEMP not in visible(html)
    assert "Base" in html and "p.p." in html
    assert "6,2 %" in html
    assert "6,2 p.p." not in html


def test_day_is_refused_outside_fifteen_minutes_and_an_old_bad_chart_is_dropped(
        client, cms, site_path):
    meta = cms.create("chart", "dia-mensal", _chart(
        series_b=None, scale="single", day="2026-11-10"), actor="owner", note="criar")
    with pytest.raises(CmsRefused, match="15 minutos"):
        cms.publish("chart", "dia-mensal", meta["version"], actor="owner", note="publicar")
    assert cms.get("chart", "dia-mensal")["meta"]["published_revision_id"] is None

    publish(cms, "chart", CHART, _chart())
    publish(cms, "page", PAGE, _page([{"type": "chart", "chart_slug": CHART}]))
    current = cms.get("chart", CHART)["meta"]
    cms.save("chart", CHART, current["version"], _chart(day="2026-11-10"),
             actor="owner", note="rascunho inválido")
    db = open_db(site_path)
    try:
        legacy = db.cms_get("chart", CHART)
        db.cms_publish("chart", CHART, legacy["version"], actor="owner", note="legado")
    finally:
        db.close()
    assert client.get(f"/graficos/{CHART}").status_code == 404
    html = client.get(f"/paginas/{PAGE}").text
    assert "Parte desta página não está disponível neste momento." in html
    assert f'href="/graficos/{CHART}"' not in html


def test_chart_provenance_links_each_line_to_its_own_data_page(client, cms):
    publish(cms, "chart", CHART, _chart())
    html = client.get(f"/graficos/{CHART}").text
    assert f'href="/series/{HICP}"' in html
    assert f'href="/series/{UNEMP}"' in html
    assert HICP not in visible(html) and UNEMP not in visible(html)


def test_page_index_is_reachable_when_empty_and_the_footer_links_both_hosts(client):
    empty = client.get("/paginas")
    assert empty.status_code == 200
    assert "Ainda não há páginas publicadas." in empty.text
    for headers, prefix in (({}, ""), ({"X-Forwarded-Prefix": "/dados"}, "/dados")):
        home = client.get("/", headers=headers).text
        assert f'href="{prefix}/paginas">Páginas</a>' in home
        # The destination is intentional shared chrome: once in the desktop rail,
        # once in the compact menu, and once in the footer.
        header = home[:home.index('<main id="conteudo"')]
        footer = home[home.index('<footer class="site-footer">'):]
        assert header.count(f'href="{prefix}/paginas"') == 2
        assert footer.count(f'href="{prefix}/paginas"') == 1
        assert client.get("/paginas", headers=headers).status_code == 200


def test_page_with_two_charts_uses_distinct_dom_ids_and_one_bundle(client, cms, site_path):
    add_series(site_path, "ine.credit_consumer_test.PT", key="credit_consumer.PT.M",
               unit="MEUR")
    add_series(site_path, "ine.credit_housing_test.PT", key="credit_housing.PT.M",
               unit="MEUR")
    db = open_db(site_path)
    try:
        fetch(db, "ine.credit_consumer_test.PT", {"2026-10": "10.0"}, T1)
        fetch(db, "ine.credit_housing_test.PT", {"2026-10": "20.0"}, T2)
    finally:
        db.close()
    publish(cms, "chart", "credito-consumo", _chart(
        title="Crédito ao consumo", series_a="ine.credit_consumer_test.PT",
        series_b=None, derived_key=None))
    publish(cms, "chart", "credito-habitacao", _chart(
        title="Crédito à habitação", series_a="ine.credit_housing_test.PT",
        series_b=None, derived_key=None))
    publish(cms, "page", PAGE, _page([
        {"type": "chart", "chart_slug": "credito-consumo"},
        {"type": "chart", "chart_slug": "credito-habitacao"},
    ]))
    html = client.get(f"/paginas/{PAGE}").text
    ids = re.findall(r'id="chart-range-([^"]+)"', html)
    assert len(ids) == 2 and len(set(ids)) == 2
    assert html.count('class="chart-data"') == 2
    assert html.count("/static/js/prumo-charts") == 1


def test_chart_provenance_is_the_last_common_period_not_the_newest_value(
        client, cms, site_path):
    add_series(site_path, "ine.test_pair_a.PT", key="credit_consumer.PT.M", unit="MEUR")
    add_series(site_path, "ine.test_pair_b.PT", key="credit_housing.PT.M", unit="MEUR")
    db = open_db(site_path)
    try:
        fetch(db, "ine.test_pair_a.PT", {"2026-08": "10.0", "2026-09": "11.0"}, T1)
        fetch(db, "ine.test_pair_a.PT", {"2026-10": "12.0"}, T3)
        fetch(db, "ine.test_pair_b.PT", {"2026-08": "20.0", "2026-09": "21.0"}, T2)
    finally:
        db.close()
    publish(cms, "chart", "credito", _chart(
        title="Crédito", series_a="ine.test_pair_a.PT", series_b="ine.test_pair_b.PT"))
    response = client.get("/graficos/credito")
    assert response.status_code == 200
    html = visible(response.text)
    assert "setembro de 2026" in html
    assert "outubro de 2026" not in html
    assert payload_of(response.text)["display"][-1] == ["11 milhões de euros",
                                                        "21 milhões de euros"]
    assert "01/11/2026, 09:00 UTC" in html     # A's provenance at the common period
    assert "02/11/2026, 09:00 UTC" in html     # B's provenance at the common period
    assert "03/11/2026, 09:00 UTC" not in html  # A's newer period is not drawn


def test_interval_chart_reads_only_the_explicit_utc_day(client, cms, site_path):
    add_series(site_path, "eredes.test_15m.PT", key="eredes_production_total.PT.PT15M",
               frequency="PT15M", unit="GWh", theme="energy")
    db = open_db(site_path)
    try:
        fetch(db, "eredes.test_15m.PT", {
            "2026-11-01T00:00:00+00:00": "10.0",
            "2026-11-01T00:15:00+00:00": "11.0",
            "2026-11-02T00:00:00+00:00": "99.0",
        }, T1)
    finally:
        db.close()
    publish(cms, "chart", "dia-eredes", _chart(
        title="Produção num dia", series_a="eredes.test_15m.PT", series_b=None,
        derived_key=None, day="2026-11-01"))
    response = client.get("/graficos/dia-eredes")
    assert response.status_code == 200
    html = visible(response.text)
    assert "01/11/2026" in html
    assert payload_of(response.text)["display"] == [["10 GWh"], ["11 GWh"]]
    assert "2 intervalos no dia UTC escolhido." in html


def test_window_is_measured_from_the_latest_data_time(client, cms, site_path):
    add_series(site_path, "ine.test_long.PT", key="consumer_confidence.PT.M", unit="0-100")
    db = open_db(site_path)
    try:
        fetch(db, "ine.test_long.PT",
              {"2014-01": "1.0", "2020-01": "2.0", "2026-10": "3.0"}, T1)
    finally:
        db.close()
    publish(cms, "chart", "longa", _chart(
        title="Série longa", series_a="ine.test_long.PT", series_b=None,
        derived_key=None, window="10y"))
    html = visible(client.get("/graficos/longa").text)
    assert "janeiro de 2020" in html
    assert "outubro de 2026" in html
    assert "janeiro de 2014" not in html


def test_window_start_maps_both_vocabularies_from_the_data_point():
    assert reads.window_start("2026-10", "M", "1y") == "2025-10"
    assert reads.window_start("2026-10", "M", "5y") == "2021-10"
    assert reads.window_start("2026-10", "M", "10y") == "2016-10"
    assert reads.window_start("2026-10", "M", "10") == "2017-10"
    assert reads.window_start("2026-Q3", "Q", "5y") == "2021-Q3"
    assert reads.window_start("2026", "A", "1y") == "2025"
    assert reads.window_start("2026-10", "M", "max") is None
    assert reads.window_start("2026-11-01T00:00:00+00:00", "PT15M", "1y") is None


def test_index_and_theme_links_list_only_published_pages_of_that_section(client, cms):
    publish(cms, "page", "economia", _page(
        [{"type": "text", "text": "Economia."}], title="Leitura económica",
        section="economy"))
    publish(cms, "page", "geral", _page(
        [{"type": "text", "text": "Geral."}], title="Leitura geral", section="general"))
    cms.create("page", "rascunho-economia", _page(
        [{"type": "text", "text": "Rascunho."}], title="Rascunho", section="economy"),
        actor="owner", note="criar")

    index = client.get("/paginas")
    assert index.status_code == 200
    assert "Leitura económica" in index.text and "Leitura geral" in index.text
    assert "Rascunho" not in index.text
    assert "Economia" in index.text and "Geral" in index.text

    economy = client.get("/temas/economy").text
    assert 'href="/paginas/economia"' in economy
    assert 'href="/paginas/geral"' not in economy
    assert 'href="/paginas/rascunho-economia"' not in economy
    assert "/paginas/geral" not in client.get("/temas/energy").text


def test_summary_pages_ship_no_chart_bundle(client, cms):
    publish(cms, "page", PAGE, _page([{"type": "text", "text": "Só texto."}]))
    response = client.get(f"/paginas/{PAGE}")
    assert response.status_code == 200
    assert response.headers["content-security-policy"] == SECURITY_HEADERS["Content-Security-Policy"]
    assert "/static/js/prumo-charts" not in response.text


def test_preview_templates_show_the_banner_and_suppress_the_bundle(client, cms):
    publish(cms, "chart", CHART, _chart())
    publish(cms, "page", PAGE, _page([
        {"type": "text", "text": "Rascunho."},
        {"type": "chart", "chart_slug": CHART},
    ]))
    env = _templates().env
    name, view = cms.preview("page", PAGE)
    html = env.get_template(name).render(
        page=view, preview=True, admin_base="/dados/admin/cms/paginas/precos",
        base="/dados", nav=[], path="/dados/admin/cms/paginas/precos/preview")
    assert "Pré-visualização" in html
    assert 'href="/dados/admin/cms/paginas/precos"' in html
    assert "/static/js/prumo-charts" not in html
    assert '<svg class="chart' in html

    name, view = cms.preview("chart", CHART)
    html = env.get_template(name).render(
        page=view, preview=True, admin_base="/dados/admin/cms/graficos/inflacao-desemprego",
        base="/dados", nav=[], path="/dados/admin/cms/graficos/inflacao-desemprego/preview")
    assert "Pré-visualização" in html
    assert "/static/js/prumo-charts" not in html
    assert '<svg class="chart' in html


def test_public_routes_are_get_and_head_only(client):
    for path in ("/paginas", "/paginas/desconhecida", "/graficos/desconhecido"):
        assert client.head(path).status_code in (200, 404)
        assert client.post(path).status_code == 405
