"""The reserved CMS page `inicio` as the public homepage.

The fixture database is the deterministic public one. Documents are authored through the
real service, so these tests exercise the same typed bodies, eligibility rule and renderer as
the backoffice and the public app. The legacy home must stay byte-for-byte in charge until the
first CMS publication; after that the CMS owns `/` and no draft, unpublish or invalid block may
resurrect the old list.
"""
import re

import pytest
from fastapi.testclient import TestClient

from app import reads
from app.cms_reads import HOME_SLUG
from app.main import CHART_CSP, SECURITY_HEADERS, _templates, create_app
from backoffice.cms import Cms, CmsConflict
from ingest.db import open_db
from tests.app.conftest import DERIVED, HICP, UNEMP, WORLD

PAGE_TITLE = "A nossa página inicial"
INTRODUCTION = "Uma introdução escrita no CMS.\n\nSegundo parágrafo."
CHART = "inflacao"
LEGACY_TITLE = "Estatísticas oficiais, com a proveniência à vista."
LEGACY_CARD = "Inflação (IHPC)"


@pytest.fixture
def cms(site_path):
    return Cms(site_path, site_path)


def _chart(**overrides):
    data = {"title": "Inflação", "note": "Série publicada.", "series_a": HICP,
            "series_b": None, "derived_key": None, "window": "max", "scale": "single",
            "day": None}
    data.update(overrides)
    return data


def _page(blocks, *, title=PAGE_TITLE, introduction=INTRODUCTION):
    return {"title": title, "introduction": introduction, "section": "general",
            "blocks": blocks}


def _publish_page(cms, blocks, *, title=PAGE_TITLE, introduction=INTRODUCTION):
    data = cms.get("page", HOME_SLUG)
    meta = data["meta"] if data is not None else cms.prepare_home(
        actor="owner", note="preparar a página inicial")
    saved = cms.save("page", HOME_SLUG, meta["version"], _page(
        blocks, title=title, introduction=introduction), actor="owner", note="editar")
    return cms.publish("page", HOME_SLUG, saved["version"], actor="owner", note="publicar")


def _publish_chart(cms):
    meta = cms.create("chart", CHART, _chart(), actor="owner", note="criar gráfico")
    return cms.publish("chart", CHART, meta["version"], actor="owner", note="publicar")


def _home(site_path):
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as client:
        return client.get("/")


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# --- preparation -----------------------------------------------------------------------------

def test_prepare_imports_effective_home_cards_title_and_introduction(cms, site_path):
    meta = cms.prepare_home(actor="owner", note="preparar a página inicial")
    assert meta["version"] == 1
    assert meta["published_revision_id"] is None

    data = cms.get("page", HOME_SLUG)
    draft = data["draft"]
    assert draft.title == "Início"
    assert draft.introduction == "Portugal. Valores publicados tal como a fonte os publica."
    cards = [(block.series_id, block.derived_key) for block in draft.blocks
             if block.type == "card"]
    assert cards == [(HICP, None), (UNEMP, DERIVED)]
    assert data["events"][0]["action"] == "created"
    assert data["events"][0]["actor"] == "owner"
    assert data["events"][0]["note"] == "preparar a página inicial"

    # The preparation is a private draft: the public home is still the legacy one.
    response = _home(site_path)
    assert response.status_code == 200
    assert LEGACY_TITLE in response.text
    assert LEGACY_CARD in response.text
    assert PAGE_TITLE not in response.text


def test_prepare_does_not_overwrite_and_leaves_source_rows_untouched(cms, site_path):
    db = open_db(site_path)
    try:
        before = {
            table: db.conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("source", "series", "observation")
        }
        editorial_before = db.conn.execute("SELECT COUNT(*) FROM editorial_slot").fetchone()
    finally:
        db.close()

    first = cms.prepare_home(actor="owner", note="primeira preparação")
    history = cms.get("page", HOME_SLUG)["history"]

    with pytest.raises(CmsConflict) as raised:
        cms.prepare_home(actor="intruso", note="segunda preparação")
    assert raised.value.actual == first["version"]

    after = cms.get("page", HOME_SLUG)
    assert after["meta"]["version"] == first["version"]
    assert after["history"] == history
    assert [event["actor"] for event in after["events"]] == ["owner"]

    db = open_db(site_path)
    try:
        for table, rows in before.items():
            assert db.conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() == rows
        assert db.conn.execute(
            "SELECT COUNT(*) FROM editorial_slot").fetchone() == editorial_before
    finally:
        db.close()


# --- publication ownership ------------------------------------------------------------------

def test_first_publication_switches_root_to_the_cms_and_drafts_stay_private(cms, site_path):
    _publish_page(cms, [{"type": "text", "text": "Texto publicado."}])

    response = _home(site_path)
    assert response.status_code == 200
    assert PAGE_TITLE in response.text
    assert "Texto publicado." in response.text
    assert LEGACY_TITLE not in response.text
    assert LEGACY_CARD not in response.text
    assert response.headers["content-security-policy"] == SECURITY_HEADERS["Content-Security-Policy"]

    meta = cms.get("page", HOME_SLUG)["meta"]
    cms.save("page", HOME_SLUG, meta["version"], _page(
        [{"type": "text", "text": "Texto privado."}]), actor="owner", note="novo rascunho")
    private = _home(site_path)
    assert "Texto publicado." in private.text
    assert "Texto privado." not in private.text

    name, view = cms.preview("page", HOME_SLUG)
    assert name == "cms_home.html"
    html = _templates().env.get_template(name).render(
        page=view, preview=True, admin_base="/dados/admin/cms/page/inicio",
        base="/dados", nav=[], path="/dados/admin/cms/page/inicio/preview")
    assert "Pré-visualização" in html
    assert "Texto privado." in html
    assert 'class="hero"' in html
    assert "/static/js/prumo-charts" not in html


def test_restore_creates_a_private_draft_and_unpublish_is_a_neutral_home(cms, site_path):
    _publish_page(cms, [{"type": "text", "text": "Versão em direto."}])
    db = open_db(site_path)
    try:
        published_id = db.cms_get("page", HOME_SLUG)["published_revision_id"]
    finally:
        db.close()

    meta = cms.get("page", HOME_SLUG)["meta"]
    cms.restore("page", HOME_SLUG, meta["version"], published_id, actor="owner",
                note="restaurar histórico")
    assert "Versão em direto." in _home(site_path).text

    meta = cms.get("page", HOME_SLUG)["meta"]
    cms.unpublish("page", HOME_SLUG, meta["version"], actor="owner", note="retirar")
    unpublished = _home(site_path)
    assert unpublished.status_code == 200
    assert "A página inicial está por publicar." in unpublished.text
    assert "Versão em direto." not in unpublished.text
    assert LEGACY_TITLE not in unpublished.text
    assert LEGACY_CARD not in unpublished.text
    assert "Inflação (IHPC)" not in unpublished.text


def test_unusable_published_revision_fails_closed_without_the_old_home(cms, site_path):
    meta = _publish_page(cms, [{"type": "text", "text": "Texto válido."}])
    db = open_db(site_path)
    try:
        # Revisions are append-only: add an intentionally unusable revision and point the
        # published head at it, which is the state a corrupted or unreadable revision leaves.
        cursor = db.conn.execute(
            "INSERT INTO cms_revision(kind, slug, body_json, created_at, actor) "
            "VALUES ('page', ?, '{}', '2026-11-17T00:00:00+00:00', 'test')", (HOME_SLUG,))
        db.conn.execute(
            "UPDATE cms_document SET published_revision_id = ? WHERE kind = 'page' AND slug = ?",
            (cursor.lastrowid, HOME_SLUG))
        db.conn.commit()
    finally:
        db.close()

    failed = _home(site_path)
    assert failed.status_code == 503
    assert "Início indisponível" in failed.text
    assert "Texto válido." not in failed.text
    assert LEGACY_TITLE not in failed.text
    assert LEGACY_CARD not in failed.text


def test_all_cards_losing_eligibility_render_empty_not_the_legacy_list(cms, site_path):
    _publish_page(cms, [
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "card", "series_id": UNEMP, "derived_key": None},
    ])
    assert LEGACY_TITLE.encode() not in _home(site_path).content

    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'ine'")
        db.conn.commit()
    finally:
        db.close()
    reads.clear_cache()

    empty = _home(site_path)
    assert empty.status_code == 200
    assert "Parte desta página não está disponível neste momento." in empty.text
    assert LEGACY_CARD not in empty.text
    assert "Taxa de desemprego - Portugal" not in empty.text
    assert "Inflação (IHPC)" not in empty.text


# --- canonical address and listings ----------------------------------------------------------

def test_published_home_is_canonical_excluded_from_pages_and_redirects_the_old_slug(
        cms, site_path):
    meta = cms.prepare_home(actor="owner", note="preparar")
    with TestClient(create_app(str(site_path))) as client:
        assert client.get("/paginas/inicio").status_code == 404  # a draft is not a page
        assert "inicio" not in client.get("/paginas").text

    _publish_page(cms, [{"type": "text", "text": "Página inicial pública."}])
    reads.clear_cache()
    with TestClient(create_app(str(site_path))) as client:
        listing = client.get("/paginas")
        assert listing.status_code == 200
        assert "inicio" not in listing.text
        redirect = client.get("/paginas/inicio", follow_redirects=False)
        assert redirect.status_code == 301
        assert redirect.headers["location"] == "/"
        prefixed = client.get("/paginas/inicio", headers={"X-Forwarded-Prefix": "/dados"},
                              follow_redirects=False)
        assert prefixed.status_code == 301
        assert prefixed.headers["location"] == "/dados/"

        meta = cms.get("page", HOME_SLUG)["meta"]
        cms.unpublish("page", HOME_SLUG, meta["version"], actor="owner", note="retirar")
        reads.clear_cache()
        assert client.get("/paginas/inicio").status_code == 404


# --- shared block rendering ------------------------------------------------------------------

def test_contiguous_cards_share_one_grid_and_keep_their_order(cms, site_path):
    _publish_page(cms, [
        {"type": "text", "text": "Antes dos cartões."},
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "card", "series_id": UNEMP, "derived_key": None},
        {"type": "text", "text": "Entre os cartões."},
        {"type": "card", "series_id": WORLD, "derived_key": None},
    ])
    html = _home(site_path).text
    assert html.count('<div class="cards">') == 2
    assert html.index("1,8") < html.index("6,2") < html.index("2,3")
    assert html.index("Antes dos cartões.") < html.index("1,8")
    assert html.index("6,2") < html.index("Entre os cartões.") < html.index("2,3")


def test_only_a_published_eligible_chart_payload_enables_scripts_on_the_home(cms, site_path):
    _publish_chart(cms)
    _publish_page(cms, [{"type": "chart", "chart_slug": CHART}])
    response = _home(site_path)
    assert response.status_code == 200
    assert response.headers["content-security-policy"] == CHART_CSP
    assert "/static/js/prumo-charts" in response.text
    assert '<svg class="chart' in response.text

    meta = cms.get("chart", CHART)["meta"]
    cms.unpublish("chart", CHART, meta["version"], actor="owner", note="retirar gráfico")
    dropped = _home(site_path)
    assert dropped.status_code == 200
    assert dropped.headers["content-security-policy"] == SECURITY_HEADERS["Content-Security-Policy"]
    assert "/static/js/prumo-charts" not in dropped.text
    assert "Parte desta página não está disponível neste momento." in dropped.text
    assert LEGACY_TITLE not in dropped.text
