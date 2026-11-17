"""Scoped contract for the indicator notebook: address, eligibility, cards and actions.

Every request goes through the real `create_app` registration, read-only handle, template
environment and security middleware. No test-only route registration substitutes for the
installed application contract.
"""
import hashlib
import re
import shutil
import sqlite3
from html import unescape
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import notebook
from app.main import create_app
from ingest.db import open_db
from ingest.models import Observation
from ingest.registry import sync_registry
from tests.app.conftest import (
    DERIVED,
    EUROSTAT,
    HICP,
    INACTIVE,
    INE,
    REN,
    T1,
    T2,
    T3,
    UNEMP,
    WITHHELD,
    WORLD,
    WORLDBANK,
    XCHECK,
    build,
    fetch,
    make_spec,
)

ROBOTS = "noindex, follow"


def _client(path):
    return TestClient(create_app(str(path)))


@pytest.fixture
def notebook_client(site_path):
    with _client(site_path) as client:
        yield client


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def card_count(html: str) -> int:
    return len(re.findall(r'<article class="card">', html))


def card_labels(html: str) -> list[str]:
    return [unescape(label) for label in re.findall(r'<p class="card-label">(.*?)</p>', html)]


def hidden_selection(html: str) -> list[str]:
    return re.findall(r'<input type="hidden" name="s" value="([^"]+)">', html)


def canonical_href(html: str) -> str:
    match = re.search(r'<a class="button-quiet" id="ligacao-limpa" href="([^"]+)"', html)
    assert match is not None
    return unescape(match.group(1))


def card_remove_href(html: str) -> str:
    match = re.search(r'class="card-remove" href="([^"]+)"', html)
    assert match is not None
    return unescape(match.group(1))


def clear_href(html: str) -> str | None:
    match = re.search(r'<a class="button-quiet" href="([^"]+)">Limpar seleção</a>', html)
    return unescape(match.group(1)) if match else None


# --- address parsing -------------------------------------------------------------------------

def test_selection_parser_accepts_domain_ids_and_rejects_bounds():
    assert notebook.parse_selection(["a.b-c_d", "S_2.0"]) == ("a.b-c_d", "S_2.0")
    assert notebook.parse_selection(["a", "a", "b"]) == ("a", "b")
    assert notebook.parse_selection(["x" * 255]) == ("x" * 255,)
    assert notebook.parse_selection(["x" * 256]) is None
    for malformed in ("", "a b", "a/b", "a#b", "../a", "a\nb"):
        assert notebook.parse_selection([malformed]) is None
    assert notebook.parse_selection([str(i) for i in range(13)]) is None
    # Over-limit is a bound on the address, not on its deduplicated result.
    assert notebook.parse_selection(["a"] * 13) is None


def test_query_parser_trims_and_bounds_the_transient_search():
    assert notebook.parse_query("  desemprego  ") == "desemprego"
    assert notebook.parse_query("") == ""
    assert notebook.parse_query("x" * 200) == "x" * 200
    assert notebook.parse_query("x" * 201) is None
    assert notebook.parse_query(" " * 201) is None
    assert notebook.parse_query("a\nb") is None
    assert notebook.parse_query("a\x7fb") is None


def test_selection_path_is_local_and_keeps_order():
    assert notebook.selection_path(("b", "a")) == "/caderno?s=b&s=a"
    assert notebook.selection_path(("b", "a"), None) == "/caderno?s=b&s=a"
    assert notebook.selection_path(("a.b",), "x y") == "/caderno?s=a.b&q=x+y"
    assert notebook.selection_path(()) == "/caderno"
    assert "://" not in notebook.selection_path(("a",), "https://evil.example")


# --- page ------------------------------------------------------------------------------------

def test_notebook_shows_exact_values_sources_flags_and_svg(notebook_client):
    response = notebook_client.get(f"/caderno?s={HICP}&s={UNEMP}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["x-robots-tag"] == ROBOTS
    html = response.text
    text = visible(html)

    assert "Caderno de indicadores" in text
    assert "2 de 12 séries." in text
    assert "Qualquer pessoa com esta ligação pode abrir a seleção." in text
    assert "não é um retrato histórico" in text
    assert "Cada abertura mostra os valores atuais" in text
    assert card_labels(html) == ["Taxa de variação homóloga do IHPC - Portugal",
                                 "Taxa de desemprego - Portugal"]
    assert text.index("Taxa de variação homóloga do IHPC") < text.index("Taxa de desemprego")
    assert "1,8" in text and "6,2" in text
    assert "outubro de 2026" in text
    assert "provisório" in text
    assert "INE - Instituto Nacional de Estatística" in text
    assert "recolhido a 03/11/2026" in text
    assert html.count('class="spark"') == 2
    assert "<script" not in html.lower()
    assert "localStorage" not in html and "sessionStorage" not in html
    assert "set-cookie" not in response.headers

    head = notebook_client.head(f"/caderno?s={HICP}")
    assert head.status_code == 200
    assert head.text == ""
    assert head.headers["x-robots-tag"] == ROBOTS


def test_search_echo_is_escaped_and_never_becomes_markup(notebook_client):
    response = notebook_client.get(
        "/caderno?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert "alert(1)" in visible(response.text)


def test_missing_built_in_catalogue_text_is_a_logged_503(notebook_client, monkeypatch):
    from presentation.catalog import pt

    monkeypatch.delitem(pt.FAMILIES, "hicp_yoy")
    response = notebook_client.get(f"/caderno?s={HICP}")
    assert response.status_code == 503
    assert "Serviço indisponível" in response.text
    assert HICP not in response.text


def test_selection_is_deduplicated_preserving_the_reader_order(notebook_client):
    response = notebook_client.get(
        f"/caderno?s={UNEMP}&s={HICP}&s={UNEMP}&s={HICP}")
    assert response.status_code == 200
    html = response.text
    assert "2 de 12 séries." in visible(html)
    assert card_count(html) == 2
    assert card_labels(html) == ["Taxa de desemprego - Portugal",
                                 "Taxa de variação homóloga do IHPC - Portugal"]
    assert canonical_href(html) == f"/caderno?s={UNEMP}&s={HICP}"
    assert card_remove_href(html) == f"/caderno?s={HICP}"


def test_limits_and_malformed_values_are_the_generic_404(notebook_client):
    over = "&".join(f"s=ine.series_{i}.PT" for i in range(13))
    duplicates = "&".join(f"s={HICP}" for _ in range(13))
    malformed = ("s=", "s=bad%20id", "s=..%2Fetc", f"s={'x' * 256}")
    for query in (over, duplicates, *malformed):
        response = notebook_client.get(f"/caderno?{query}")
        assert response.status_code == 404, query
        assert response.headers["x-robots-tag"] == ROBOTS
        assert "Página não encontrada" in response.text
        assert "ine.series_" not in response.text
        assert HICP not in response.text

    for query in ("q=" + "x" * 201, "q=ok%0Athen", f"s={HICP}&q=" + "x" * 201):
        response = notebook_client.get(f"/caderno?{query}")
        assert response.status_code == 404, query
        assert "Página não encontrada" in response.text


def test_unknown_and_ineligible_selections_are_omitted_with_one_count(notebook_client):
    response = notebook_client.get(
        f"/caderno?s={HICP}&s=ine.unknown.PT&s={INACTIVE}&s={WITHHELD}"
        f"&s={XCHECK}&s={DERIVED}")
    assert response.status_code == 200
    html = response.text
    text = visible(html)
    assert "1 de 12 séries." in text
    assert card_count(html) == 1
    assert "5 séries desta ligação já não podem ser mostradas e foram omitidas." in text
    for series_id in ("ine.unknown.PT", INACTIVE, WITHHELD, XCHECK, DERIVED):
        assert series_id not in html
    assert "REN" not in text and "Eurostat" not in text
    for reason in ("unknown_series", "inactive", "withheld", "cross_check",
                   "no_served_value", "legacy_only"):
        assert reason not in html


def test_legacy_only_and_withdrawn_series_are_skipped(tmp_path):
    path = tmp_path / "notebook-legacy.db"
    build(path)
    legacy_id = "ine.notebook_legacy.PT"
    db = open_db(path)
    try:
        sync_registry(db, [
            make_spec(HICP),
            make_spec(UNEMP, key="unemployment_rate.PT.M"),
            make_spec(XCHECK, source=EUROSTAT, role="cross_check"),
            make_spec(INACTIVE, active=False),
            make_spec(WITHHELD, source=REN, key="ren_electricity_biomass.PT.M", unit="GWh"),
            make_spec(WORLD, source=WORLDBANK, key="worldbank_gdp_growth.US.A",
                      geography="US", frequency="A"),
            make_spec(legacy_id, key="ine_live_births.PT.M"),
        ])
        legacy_run = db.legacy_run(INE.name, "legacy:ine", T2)
        db.write_legacy_observations(
            legacy_run, [(Observation.from_raw(legacy_id, "2026-10", "99.9"), T2)])
        db.conn.execute("UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
        db.conn.commit()
        # The view really does serve the legacy row; eligibility must still refuse it.
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation WHERE series_id = ?",
                               (legacy_id,)).fetchone()[0] == 1
        world_run = db.conn.execute(
            "SELECT r.id FROM dataset_run r JOIN source p ON p.id = r.source_id "
            "WHERE p.name = ? AND r.input_origin <> 'legacy' ORDER BY r.id",
            (WORLDBANK.name,)).fetchone()[0]
        db.withdraw_run(world_run, "test withdrawal", T3)
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation WHERE series_id = ?",
                               (WORLD,)).fetchone()[0] == 0
    finally:
        db.close()

    with _client(path) as client:
        response = client.get(f"/caderno?s={legacy_id}&s={WORLD}&s={HICP}")
    assert response.status_code == 200
    html = response.text
    text = visible(html)
    assert card_count(html) == 1
    assert "1 de 12 séries." in text
    assert "2 séries desta ligação já não podem ser mostradas e foram omitidas." in text
    assert "1,8" in text
    assert "99,9" not in text and "2,3" not in text
    assert legacy_id not in html and WORLD not in html
    assert "Nados-vivos" not in text and "Crescimento do PIB" not in text


def test_fresh_rights_and_activity_beat_the_warm_catalogue_cache(site_path):
    with _client(site_path) as client:
        home = client.get("/temas/economy")
        assert home.status_code == 200 and "Taxa de variação homóloga do IHPC" in home.text
        first_search = client.get("/caderno?q=desemprego")
        assert first_search.status_code == 200 and "Taxa de desemprego" in first_search.text

        db = open_db(site_path)
        try:
            db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = ?",
                            (INE.name,))
            db.conn.commit()
        finally:
            db.close()

        response = client.get(f"/caderno?s={HICP}&q=desemprego")
        assert response.status_code == 200
        html = response.text
        text = visible(html)
        assert "0 de 12 séries." in text
        assert "1 série desta ligação já não pode ser mostrada e foi omitida." in text
        assert "1,8" not in text
        assert "Taxa de desemprego" not in text
        assert "Sem resultados para «desemprego»." in text
        assert "/caderno?s=" not in html


def test_search_keeps_selection_and_offers_add_remove_clear_and_canonical(notebook_client):
    response = notebook_client.get(f"/caderno?s={HICP}&q=desemprego")
    assert response.status_code == 200
    html = response.text
    text = visible(html)
    assert hidden_selection(html) == [HICP]
    assert 'action="/caderno"' in html
    assert "Taxa de desemprego" in text
    assert "1 resultado." in text
    assert "Só aparecem séries que podem ser publicadas neste momento." in text
    assert f'href="/caderno?s={HICP}&amp;s={UNEMP}&amp;q=desemprego"' in html
    assert canonical_href(html) == f"/caderno?s={HICP}"
    assert clear_href(html) == "/caderno?q=desemprego"
    assert card_remove_href(html) == "/caderno?q=desemprego"

    selected = notebook_client.get(f"/caderno?s={HICP}&s={UNEMP}&q=desemprego")
    assert selected.status_code == 200
    selected_html = selected.text
    assert hidden_selection(selected_html) == [HICP, UNEMP]
    assert "Já no caderno" in visible(selected_html)
    assert f'href="/caderno?s={HICP}&amp;q=desemprego"' in selected_html
    assert f"/caderno?s={HICP}&amp;s={UNEMP}&amp;q=desemprego" not in selected_html


def test_full_notebook_still_shows_selection_and_refuses_a_thirteenth(tmp_path):
    path = tmp_path / "notebook-full.db"
    rows = (
        ("ine.notebook_01.PT", "hicp_yoy.PT.M"),
        ("ine.notebook_02.PT", "unemployment_rate.PT.M"),
        ("ine.notebook_03.PT", "consumer_confidence.PT.M"),
        ("ine.notebook_04.PT", "ine_deaths.PT.M"),
        ("ine.notebook_05.PT", "ine_live_births.PT.M"),
        ("ine.notebook_06.PT", "ine_population.PT.M"),
        ("ine.notebook_07.PT", "pt_10y.PT.M"),
        ("ine.notebook_08.PT", "euribor_3m.PT.M"),
        ("ine.notebook_09.PT", "worldbank_life_expectancy.PT.M"),
        ("ine.notebook_10.PT", "ipi_total.PT.M"),
        ("ine.notebook_11.PT", "worldbank_gdp_growth.PT.M"),
        ("ine.notebook_12.PT", "eurostat_gdp_quarterly.PT.M"),
        ("ine.notebook_13.PT", "worldbank_gini.PT.M"),
    )
    db = open_db(path)
    try:
        specs = [make_spec(series_id, key=key) for series_id, key in rows]
        sync_registry(db, specs)
        for position, spec in enumerate(specs):
            fetch(db, spec.id, {"2026-10": f"{position + 1}.90"}, T1)
    finally:
        db.close()

    selection = [series_id for series_id, _ in rows[:12]]
    query = "&".join(f"s={series_id}" for series_id in selection)
    with _client(path) as client:
        response = client.get(f"/caderno?{query}&q=Gini")
        assert response.status_code == 200
        html = response.text
        text = visible(html)
        assert "12 de 12 séries." in text
        assert "1,90" in text  # the publisher token 1.90 keeps its trailing zero
        assert card_count(html) == 12
        assert hidden_selection(html) == selection
        assert "Coeficiente de Gini" in text
        assert "O caderno tem 12 séries, o máximo. Remova uma para acrescentar outra." in text
        assert "ine.notebook_13.PT" not in html
        canonical = canonical_href(html)
        assert canonical.startswith("/caderno?")
        assert canonical.count("s=") == 12 and "q=" not in canonical
        clear = clear_href(html)
        assert clear == "/caderno?q=Gini"

        cleared = client.get(clear)
        assert cleared.status_code == 200
        assert card_count(cleared.text) == 0
        assert "O caderno está vazio." in visible(cleared.text)
        assert "omitidas" not in visible(cleared.text)


def test_same_selection_reopens_under_both_public_prefixes(site_path):
    url = f"/caderno?s={HICP}&s={UNEMP}&q=desemprego"
    with _client(site_path) as client:
        plain = client.get(url)
        prefixed = client.get(url, headers={"X-Forwarded-Prefix": "/dados"})
        hostile = client.get(f"/caderno?s={HICP}",
                             headers={"X-Forwarded-Prefix": "//evil.example"})
    assert plain.status_code == prefixed.status_code == 200
    assert card_labels(plain.text) == card_labels(prefixed.text)
    assert "1,8" in visible(plain.text) and "1,8" in visible(prefixed.text)
    assert "x-forwarded-prefix" in prefixed.headers["vary"].lower()

    prefixed_html = prefixed.text
    assert 'action="/dados/caderno"' in prefixed_html
    assert f'href="/dados/caderno?s={HICP}&amp;q=desemprego"' in prefixed_html
    assert canonical_href(prefixed_html) == f"/dados/caderno?s={HICP}&s={UNEMP}"
    assert clear_href(prefixed_html) == "/dados/caderno?q=desemprego"
    assert 'href="/dados/series/' in prefixed_html
    assert 'href="/caderno' not in prefixed_html
    assert 'action="/caderno' not in prefixed_html

    assert hostile.status_code == 200
    assert "evil.example" not in hostile.text
    assert canonical_href(hostile.text) == f"/caderno?s={HICP}"


def test_head_only_serves_no_script_cookie_or_write(site_path):
    def digest():
        return hashlib.sha256(site_path.read_bytes()).hexdigest()

    before = digest()
    urls = ("/caderno", f"/caderno?s={HICP}", f"/caderno?s={HICP}&s={UNEMP}&q=desemprego",
            f"/caderno?s={HICP}&s=ine.unknown.PT", "/caderno?s=bad%20id")
    with _client(site_path) as client:
        responses = [client.get(url) for url in urls]
        head = client.head(f"/caderno?s={HICP}")
        assert all(response.status_code in (200, 404) for response in responses)
        assert head.status_code == 200 and head.text == ""
        assert head.headers["x-robots-tag"] == ROBOTS
        for response in [*responses, head]:
            assert "set-cookie" not in response.headers
            assert "localStorage" not in response.text
            assert "sessionStorage" not in response.text
            assert "document.cookie" not in response.text
            assert not re.search(r"<[a-zA-Z][^>]*\son[a-z]+=", response.text)
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(f"/caderno?s={HICP}").status_code == 405
    assert digest() == before


def test_unavailable_database_is_the_generic_503(tmp_path, site_path):
    missing_view = tmp_path / "notebook-no-view.db"
    shutil.copy(site_path, missing_view)
    connection = sqlite3.connect(missing_view)
    connection.execute("DROP VIEW served_observation")
    connection.commit()
    connection.close()

    missing_schema = tmp_path / "notebook-no-schema.db"
    shutil.copy(site_path, missing_schema)
    connection = sqlite3.connect(missing_schema)
    connection.execute("DELETE FROM schema_migration WHERE version = "
                       "(SELECT version FROM schema_migration LIMIT 1)")
    connection.commit()
    connection.close()

    for path in (missing_view, missing_schema):
        with _client(path) as client:
            response = client.get(f"/caderno?s={HICP}")
            head = client.head(f"/caderno?s={HICP}")
        assert response.status_code == 503
        assert head.status_code == 503
        assert "Serviço indisponível" in response.text
        assert "served_observation" not in response.text
        assert HICP not in response.text


def test_template_asks_the_base_shell_for_the_noindex_meta():
    source = (Path(__file__).parents[2] / "app" / "templates" / "notebook.html").read_text()
    assert '{% block robots %}<meta name="robots" content="noindex, follow">{% endblock %}' in source
    assert "<script" not in source.lower()
    assert "localStorage" not in source
