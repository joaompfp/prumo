"""The CMS home integration boundary: dashboard context, prepare route and legacy gating.

The route is a thin form layer over `backoffice.cms`, guarded by the same origin check and
authenticated actor as every other CMS mutation. These tests use the real migrated fixture,
the real service and both Admin mount prefixes.
"""
import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app import reads
from app.main import create_app
from backoffice.cms import HOME_SLUG, Cms, CmsConflict, CmsRefused
from ingest.db import open_db
from ingest.models import Observation
from ingest.registry import load_registry, sync_registry
from presentation.catalog import pt
from tests.backoffice.test_cms_routes import (
    FETCHED,
    ORIGIN,
    PREFIX,
    Env,
    chart_create,
    page_create,
    page_form,
)


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def _prepare(client, **headers):
    return client.post("/cms/home/prepare", data={"note": "preparar a página inicial"},
                       headers={**ORIGIN, **headers}, follow_redirects=False)


def _capture_render(client):
    """Record the context each Admin template receives, then render normally."""
    seen = {}
    admin = client.app.state.admin
    original = admin.render

    def render(request, name, status_code=200, **context):
        seen[name] = context
        return original(request, name, status_code, **context)

    admin.render = render
    return seen


def test_get_home_is_an_explicit_preparation_page_and_dashboard_gets_the_head(env):
    c = env.client()
    seen = _capture_render(c)
    assert c.get("/cms").status_code == 200
    assert seen["cms_list.html"]["home"] is None

    page = c.get("/cms/home")
    assert page.status_code == 200
    assert 'action="/cms/home/prepare"' in page.text
    assert "página inicial" in page.text.lower()
    assert 'href="/cms"' in page.text
    assert env.meta("page", HOME_SLUG) is None  # a GET never prepares


def test_prepare_is_authenticated_same_origin_audited_and_redirects_to_the_editor(env):
    c = env.client()

    no_origin = c.post("/cms/home/prepare", data={"note": "sem origem"},
                       follow_redirects=False)
    assert no_origin.status_code == 403
    assert env.meta("page", HOME_SLUG) is None

    cross = c.post("/cms/home/prepare", data={"note": "origem errada"},
                   headers={"Origin": "https://evil.example"}, follow_redirects=False)
    assert cross.status_code == 403
    assert env.meta("page", HOME_SLUG) is None
    assert c.post("/cms/home/prepare", data={"note": "sem origem"},
                  headers={"X-Forwarded-Prefix": PREFIX},
                  follow_redirects=False).status_code == 403
    assert c.post("/cms/home/prepare", data={"note": "origem errada"},
                  headers={"Origin": "https://evil.example",
                           "X-Forwarded-Prefix": PREFIX},
                  follow_redirects=False).status_code == 403
    assert env.meta("page", HOME_SLUG) is None

    missing_note = c.post("/cms/home/prepare", data={"note": ""}, headers=ORIGIN,
                          follow_redirects=False)
    assert missing_note.status_code == 422
    assert env.meta("page", HOME_SLUG) is None

    prepared = _prepare(c)
    assert prepared.status_code == 303
    assert prepared.headers["location"] == "/cms/page/inicio"
    meta = env.meta("page", HOME_SLUG)
    assert meta["version"] == 1 and meta["published_revision_id"] is None
    events = env.events("page", HOME_SLUG)
    assert events[0]["action"] == "created"
    assert events[0]["actor"] == "local-developer"
    assert events[0]["note"] == "preparar a página inicial"
    body = json.loads(env.revisions("page", HOME_SLUG)[0]["body_json"])
    assert body["title"] == "Início"
    assert [block["type"] for block in body["blocks"]] == [
        "hero", "heading", "card", "themes", "verification", "sources"]
    cards = [block for block in body["blocks"] if block["type"] == "card"]
    assert [(card["series_id"], card["label"]) for card in cards] == [
        ("ine.hicp_yoy.PT", "Inflação (IHPC)")]


def test_a_second_prepare_is_409_and_overwrites_nothing(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    before_meta = env.meta("page", HOME_SLUG)
    before_history = env.revisions("page", HOME_SLUG)
    before_events = env.events("page", HOME_SLUG)

    again = _prepare(c)
    assert again.status_code == 409
    assert "nothing was written" in again.text
    assert env.meta("page", HOME_SLUG) == before_meta
    assert env.revisions("page", HOME_SLUG) == before_history
    assert env.events("page", HOME_SLUG) == before_events


def test_home_entry_and_redirects_use_the_admin_prefix(env):
    c = env.client()
    page = c.get("/cms/home", headers={"X-Forwarded-Prefix": PREFIX})
    assert page.status_code == 200
    assert 'action="/dados/admin/cms/home/prepare"' in page.text
    assert 'href="/dados/admin/cms"' in page.text

    prepared = _prepare(c, **{"X-Forwarded-Prefix": PREFIX})
    assert prepared.status_code == 303
    assert prepared.headers["location"] == "/dados/admin/cms/page/inicio"

    again = c.get("/cms/home", headers={"X-Forwarded-Prefix": PREFIX},
                  follow_redirects=False)
    assert again.status_code in (302, 303)
    assert again.headers["location"] == "/dados/admin/cms/page/inicio"


def test_editor_receives_is_home_true_only_for_the_reserved_slug(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    assert c.post("/cms/new", data={"kind": "page", "slug": "outra", "title": "Outra",
                                    "section": "general", "note": "criar"},
                  headers={**ORIGIN, "X-Forwarded-Prefix": PREFIX},
                  follow_redirects=False).status_code == 303
    seen = _capture_render(c)
    assert c.get("/cms/page/inicio").status_code == 200
    assert seen["cms_editor.html"]["is_home"] is True
    assert c.get("/cms/page/outra").status_code == 200
    assert seen["cms_editor.html"]["is_home"] is False


def test_dashboard_reports_the_home_head_after_preparation(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    seen = _capture_render(c)
    assert c.get("/cms").status_code == 200
    home = seen["cms_list.html"]["home"]
    assert home["slug"] == HOME_SLUG
    assert home["title"] == "Início"
    assert home["published"] is False
    assert home["version"] == 1 and home["published_revision_id"] is None

    meta = env.meta("page", HOME_SLUG)
    assert c.post("/cms/page/inicio/publish",
                  data={"version": str(meta["version"]), "note": "publicar"},
                  headers=ORIGIN, follow_redirects=False).status_code == 303
    assert c.get("/cms").status_code == 200
    published = seen["cms_list.html"]["home"]
    assert published["published"] is True
    assert published["published_revision_id"] == 1


def test_stale_home_editor_form_is_409_and_writes_nothing_on_either_prefix(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    first = c.post("/cms/page/inicio/save",
                   data=page_form(1, title="Início", blocks=[
                       {"type": "text", "text": "Versão 2."}], note="guardar"),
                   headers=ORIGIN, follow_redirects=False)
    assert first.status_code == 303
    before_meta = env.meta("page", HOME_SLUG)
    before_history = env.revisions("page", HOME_SLUG)

    for headers in (ORIGIN, {**ORIGIN, "X-Forwarded-Prefix": PREFIX}):
        stale = c.post("/cms/page/inicio/save",
                       data=page_form(1, title="Início", blocks=[
                           {"type": "text", "text": "Perdida."}], note="stale"),
                       headers=headers, follow_redirects=False)
        assert stale.status_code == 409
        assert env.meta("page", HOME_SLUG) == before_meta
        assert env.revisions("page", HOME_SLUG) == before_history


def test_the_reserved_slug_cannot_be_created_or_duplicated_around_preparation(env):
    c = env.client()
    direct = page_create(c, slug=HOME_SLUG, title="Página inicial manual")
    assert direct.status_code == 422
    assert "reservado" in direct.text
    assert env.meta("page", HOME_SLUG) is None

    assert page_create(c, slug="origeme", title="Origem").status_code == 303
    meta = env.meta("page", "origeme")
    copied = c.post("/cms/page/origeme/duplicate",
                    data={"version": str(meta["version"]), "new_slug": HOME_SLUG,
                          "note": "copiar"},
                    headers=ORIGIN, follow_redirects=False)
    assert copied.status_code == 422
    assert "reservado" in copied.text
    assert env.meta("page", HOME_SLUG) is None


def test_home_preview_route_uses_the_home_shell_and_stays_script_free(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    chart_meta = env.meta("chart", "inflacao")
    assert c.post("/cms/chart/inflacao/publish",
                  data={"version": str(chart_meta["version"]), "note": "publicar"},
                  headers=ORIGIN, follow_redirects=False).status_code == 303
    assert _prepare(c).status_code == 303
    meta = env.meta("page", HOME_SLUG)
    assert c.post("/cms/page/inicio/save",
                  data=page_form(meta["version"], title="Início", blocks=[
                      {"type": "text", "text": "Rascunho da inicial."},
                      {"type": "chart", "chart_slug": "inflacao"}], note="guardar"),
                  headers=ORIGIN, follow_redirects=False).status_code == 303

    preview = c.get("/cms/page/inicio/preview",
                    headers={"X-Forwarded-Prefix": PREFIX})
    assert preview.status_code == 200
    assert "Pré-visualização" in preview.text
    assert 'class="hero"' in preview.text
    assert "Rascunho da inicial." in preview.text
    assert '<svg class="chart' in preview.text
    assert "/static/js/prumo-charts" not in preview.text
    assert "script-src" not in preview.headers["content-security-policy"]
    assert "/dados/admin/static/css/prumo.css" in preview.text
    assert 'href="/dados/admin/cms/page/inicio"' in preview.text


def test_prepared_flag_and_legacy_lock_helpers(env):
    cms = Cms(env.db_path, env.db_path)
    assert cms.home_prepared() is False
    assert cms.legacy_home_locked(HOME_SLUG) is False
    cms.prepare_home(actor="owner", note="preparar")
    assert cms.home_prepared() is True
    assert cms.legacy_home_locked(HOME_SLUG) is True
    assert cms.legacy_home_locked("outra") is False


def test_prepare_and_publication_leave_statistical_and_editorial_rows_unchanged(env):
    db = env.db()
    try:
        before = {
            table: db.conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("source", "series", "observation")
        }
        editorial = db.conn.execute(
            "SELECT (SELECT COUNT(*) FROM editorial_page), "
            "(SELECT COUNT(*) FROM editorial_slot), "
            "(SELECT COUNT(*) FROM editorial_event)").fetchone()
    finally:
        db.close()

    c = env.client()
    assert _prepare(c).status_code == 303
    meta = env.meta("page", HOME_SLUG)
    saved = c.post("/cms/page/inicio/save",
                   data=page_form(meta["version"], title="Início", blocks=[
                       {"type": "card", "series_id": "ine.hicp_yoy.PT",
                        "derived_key": None}], note="editar"),
                   headers=ORIGIN, follow_redirects=False)
    assert saved.status_code == 303
    assert c.post("/cms/page/inicio/publish",
                  data={"version": str(env.meta("page", HOME_SLUG)["version"]),
                        "note": "publicar"},
                  headers=ORIGIN, follow_redirects=False).status_code == 303

    db = env.db()
    try:
        for table, rows in before.items():
            assert db.conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() == rows
        assert db.conn.execute(
            "SELECT (SELECT COUNT(*) FROM editorial_page), "
            "(SELECT COUNT(*) FROM editorial_slot), "
            "(SELECT COUNT(*) FROM editorial_event)").fetchone() == editorial
    finally:
        db.close()


# --- the complete authored homepage ----------------------------------------------------------

def test_prepared_body_holds_the_complete_current_copy_and_no_live_facts(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    body = json.loads(env.revisions("page", HOME_SLUG)[0]["body_json"])
    hero, heading, card, themes, verification, sources = body["blocks"]
    assert hero == {
        "type": "hero", "eyebrow": "Dados oficiais · proveniência verificada",
        "title": "Estatísticas oficiais, com a proveniência à vista.",
        "note": "Cada valor liga à publicação original, à data em que foi recolhido e à "
                "verificação independente que o acompanhou.",
        "counts": True, "freshness": True,
        "actions": [{"label": "Explorar os dados", "href": "/temas/economy"},
                    {"label": "Como verificamos", "href": "/metodologia"}],
    }
    assert heading == {"type": "heading", "title": "Números em destaque",
                       "note": "Portugal. Valores publicados tal como a fonte os publica."}
    assert card["label"] == "Inflação (IHPC)"
    assert themes == {"type": "themes", "title": "Temas",
                      "note": "Todo o catálogo, por assunto.",
                      "themes": ["economy", "demography", "energy"]}
    assert verification["steps"] == [
        {"label": "Recolha", "text": "O ficheiro original é guardado intacto, com o endereço, "
                                     "a hora e o resumo criptográfico."},
        {"label": "Validação", "text": "Unidade, período, sinal e duplicados são verificados "
                                       "antes de qualquer valor ser aceite."},
        {"label": "Verificação independente", "text": "Uma amostra aleatória é comparada com "
                                                      "outra via da mesma instituição, exigindo "
                                                      "100% de coincidência."},
    ]
    assert verification["action"] == {"label": "Ler a metodologia completa",
                                      "href": "/metodologia"}
    assert sources == {"type": "sources", "title": "Instituições publicadas", "note": "",
                       "action": {"label": "Licenças, atribuições e fontes em avaliação",
                                  "href": "/fontes"}}
    raw = env.revisions("page", HOME_SLUG)[0]["body_json"]
    assert "2 séries" not in raw and "13/11/2026" not in raw and "Última recolha" not in raw


def test_home_preview_renders_the_complete_home_with_live_facts(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    meta = env.meta("page", HOME_SLUG)
    assert c.post("/cms/page/inicio/publish",
                  data={"version": str(meta["version"]), "note": "publicar"},
                  headers=ORIGIN, follow_redirects=False).status_code == 303
    preview = c.get("/cms/page/inicio/preview",
                    headers={"X-Forwarded-Prefix": PREFIX})
    assert preview.status_code == 200
    assert "Pré-visualização" in preview.text
    for text in (
            "Dados oficiais · proveniência verificada",
            "Estatísticas oficiais, com a proveniência à vista.",
            "2 séries de 1 instituições.",
            "Última recolha verificada: 13/11/2026, 00:00 UTC",
            "Números em destaque", "Inflação (IHPC)",
            "Temas", "Todo o catálogo, por assunto.",
            "A cadeia de verificação", "Recolha.", "Validação.",
            "Verificação independente.", "Ler a metodologia completa",
            "Instituições publicadas", "INE - Instituto Nacional de Estatística",
            "Licenças, atribuições e fontes em avaliação"):
        assert text in preview.text, text
    assert 'href="/dados/temas/economy">Explorar os dados' in preview.text
    assert 'href="/dados/metodologia">Como verificamos' in preview.text
    assert 'href="/dados/fontes">Licenças, atribuições e fontes em avaliação' in preview.text
    assert 'href="/dados/temas/energy"' in preview.text
    assert 'class="theme-count">2 séries' in preview.text
    assert "/dados/admin/static/css/prumo.css" in preview.text
    assert 'href="/dados/admin/cms/page/inicio"' in preview.text
    assert "/static/js/prumo-charts" not in preview.text


def test_the_seed_fits_the_full_twelve_card_current_homepage(tmp_path):
    core = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "registry" / "core.yaml").read_text())
    wanted = {item["series"] for item in pt.CURATED_HOME}
    registry = tmp_path / "full.yaml"
    registry.write_text(yaml.safe_dump(
        {"sources": core["sources"],
         "series": [row for row in core["series"] if row["id"] in wanted]},
        sort_keys=False))
    db_path = tmp_path / "full.sqlite3"
    specs = load_registry(registry)
    db = open_db(db_path)
    try:
        sync_registry(db, specs)
        for spec in specs:
            period = {"A": "2026", "S": "2026-S1", "Q": "2026-Q1", "M": "2026-01"}[
                spec.frequency]
            run = db.begin_run(spec.source.name, f"k-{spec.id}", FETCHED)
            fid = db.record_raw_fetch(
                source_name=spec.source.name, run_id=run, url="https://x",
                params_json=None, fetched_at=FETCHED, http_status=200,
                sha256="a" * 64, path="p", n_bytes=1, ok=True)
            db.write_observations(run, [
                (Observation.from_raw(spec.id, period, "1.5"), fid, FETCHED)])
            db.set_run_state(run, "verified")
    finally:
        db.close()

    cms = Cms(db_path, db_path)
    meta = cms.prepare_home(actor="owner", note="preparar a página inicial")
    draft = cms.get("page", HOME_SLUG)["draft"]
    assert len(draft.blocks) == 17  # hero + heading + 12 cards + 3 sections
    cards = [block for block in draft.blocks if block.type == "card"]
    assert [(card.series_id, card.label) for card in cards] == [
        (item["series"], item["label"]) for item in pt.CURATED_HOME]

    cms.publish("page", HOME_SLUG, meta["version"], actor="owner", note="publicar")
    reads.clear_cache()
    with TestClient(create_app(str(db_path))) as client:
        html = client.get("/").text
    assert html.count('<div class="cards">') == 1
    assert "12 séries de 3 instituições." in html
    assert "Última recolha verificada: 13/11/2026, 00:00 UTC" in html
    for item in pt.CURATED_HOME:
        assert f">{item['label']}</p>" in html
    assert "Instituições publicadas" in html
    assert "A cadeia de verificação" in html


def test_initializer_creates_once_and_refuses_an_existing_draft(tmp_path):
    path = tmp_path / "fresh"
    path.mkdir()
    env = Env(path)
    cms = Cms(env.db_path, env.db_path)

    prepared = cms.initialize_home(actor="deploy-script", prepare_note="inicializar conteúdo")
    assert prepared["status"] == "prepared"
    assert prepared["meta"]["published_revision_id"] is None
    assert [event["action"] for event in env.events("page", HOME_SLUG)] == ["created"]

    with pytest.raises(CmsConflict):
        cms.initialize_home(actor="deploy-script", prepare_note="repetir")
    with pytest.raises(CmsConflict):
        Cms(env.db_path, env.db_path).initialize_home(
            actor="deploy-script", prepare_note="inicializar", publish=True,
            publish_note="publicar conteúdo inicial")
    assert [event["action"] for event in env.events("page", HOME_SLUG)] == ["created"]


def test_initializer_publishes_a_fresh_home_and_then_leaves_it_untouched(tmp_path):
    path = tmp_path / "fresh-publish"
    path.mkdir()
    env = Env(path)
    cms = Cms(env.db_path, env.db_path)

    with pytest.raises(CmsRefused):
        cms.initialize_home(actor="deploy-script", prepare_note="inicializar", publish=True)
    assert env.meta("page", HOME_SLUG) is None

    result = cms.initialize_home(actor="deploy-script", prepare_note="inicializar",
                                 publish=True, publish_note="publicar conteúdo inicial")
    assert result["status"] == "published"
    assert result["meta"]["published_revision_id"] == 1
    events = env.events("page", HOME_SLUG)
    assert [(event["action"], event["actor"], event["note"]) for event in events] == [
        ("published", "deploy-script", "publicar conteúdo inicial"),
        ("created", "deploy-script", "inicializar"),
    ]
    before = env.revisions("page", HOME_SLUG)

    again = cms.initialize_home(actor="deploy-script", prepare_note="repetir",
                                publish=True, publish_note="repetir publicação")
    assert again["status"] == "already_published"
    assert env.revisions("page", HOME_SLUG) == before
    assert len(env.events("page", HOME_SLUG)) == 2


def test_home_editor_exposes_labelled_controls_for_every_authored_section(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    editor = c.get("/cms/page/inicio")
    assert editor.status_code == 200
    for value in ("hero", "heading", "themes", "verification", "sources"):
        assert f'value="{value}"' in editor.text
    assert 'name="block_eyebrow_0"' in editor.text
    assert 'value="Dados oficiais · proveniência verificada"' in editor.text
    assert 'name="block_counts_0" value="1" checked' in editor.text
    assert 'name="block_freshness_0" value="1" checked' in editor.text
    assert 'name="block_link_label_0_0"' in editor.text
    assert 'value="Explorar os dados"' in editor.text
    assert 'name="block_title_1"' in editor.text
    assert 'value="Números em destaque"' in editor.text
    assert 'name="block_label_2"' in editor.text
    assert 'value="Inflação (IHPC)"' in editor.text
    assert 'name="block_theme_3_0"' in editor.text
    assert 'value="economy" selected' in editor.text
    assert 'name="block_step_label_4_0"' in editor.text
    assert 'value="Recolha"' in editor.text
    assert 'name="block_link_href_5"' in editor.text
    assert 'value="/fontes"' in editor.text
    for name in ("add_eyebrow", "add_title", "add_note", "add_counts", "add_freshness",
                 "add_link_label_0", "add_theme_0", "add_step_label_0", "add_label"):
        assert f'name="{name}"' in editor.text, name
    assert 'data-show-for="hero"' in editor.text
    assert 'data-show-for="heading hero themes sources"' in editor.text
    assert 'data-show-for="verification"' in editor.text


def test_editor_route_can_edit_reorder_and_remove_the_authored_sections(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    card = {"type": "card", "series_id": "ine.hicp_yoy.PT", "derived_key": None,
            "label": "Inflação (IHPC)"}
    blocks = [
        {"type": "sources", "title": "Fontes em direto", "note": "",
         "action": {"label": "Ver fontes", "href": "/fontes"}},
        {"type": "heading", "title": "Números em destaque", "note": "Portugal."},
        card,
        {"type": "themes", "title": "Temas", "note": "Por assunto.",
         "themes": ["economy", "energy"]},
        {"type": "verification", "title": "A cadeia de verificação",
         "steps": [{"label": "Recolha", "text": "Ficheiro intacto."}],
         "action": {"label": "Metodologia", "href": "/metodologia"}},
        {"type": "hero", "eyebrow": "Abertura", "title": "Título novo", "note": "Nota nova.",
         "counts": True, "freshness": False,
         "actions": [{"label": "Ver temas", "href": "/temas/energy"}]},
    ]
    meta = env.meta("page", HOME_SLUG)
    saved = c.post("/cms/page/inicio/save",
                   data=page_form(meta["version"], title="Início", blocks=blocks,
                                  note="reordenar secções"),
                   headers=ORIGIN, follow_redirects=False)
    assert saved.status_code == 303
    meta = env.meta("page", HOME_SLUG)
    assert c.post("/cms/page/inicio/publish",
                  data={"version": str(meta["version"]), "note": "publicar"},
                  headers=ORIGIN, follow_redirects=False).status_code == 303
    preview = c.get("/cms/page/inicio/preview", headers={"X-Forwarded-Prefix": PREFIX})
    assert "Fontes em direto" in preview.text
    assert preview.text.index("Fontes em direto") < preview.text.index("Números em destaque") \
        < preview.text.index("Título novo")
    assert "Por assunto." in preview.text and "Ficheiro intacto." in preview.text
    assert 'href="/dados/temas/energy">Ver temas' in preview.text

    # Remove the first block through the ordinary control and save the whole form.
    meta = env.meta("page", HOME_SLUG)
    form = page_form(meta["version"], title="Início", blocks=blocks, note="remover fontes")
    form["remove_0"] = "1"
    removed = c.post("/cms/page/inicio/save", data=form, headers=ORIGIN,
                     follow_redirects=False)
    assert removed.status_code == 303
    published = c.post("/cms/page/inicio/publish",
                       data={"version": str(env.meta("page", HOME_SLUG)["version"]),
                             "note": "publicar remoção"},
                       headers=ORIGIN, follow_redirects=False)
    assert published.status_code == 303
    final = c.get("/cms/page/inicio/preview", headers={"X-Forwarded-Prefix": PREFIX})
    assert "Fontes em direto" not in final.text
    assert "Números em destaque" in final.text


def test_invalid_home_block_fields_are_422_and_write_nothing(env):
    c = env.client()
    assert _prepare(c).status_code == 303
    before_meta = env.meta("page", HOME_SLUG)
    before_history = env.revisions("page", HOME_SLUG)
    version = before_meta["version"]

    missing_href = page_form(version, title="Início", blocks=[
        {"type": "hero", "eyebrow": "", "title": "Título", "note": "",
         "counts": False, "freshness": False,
         "actions": [{"label": "Sem destino", "href": ""}]}], note="inválido")
    response = c.post("/cms/page/inicio/save", data=missing_href, headers=ORIGIN)
    assert response.status_code == 422
    assert "endereço" in response.text

    duplicate = page_form(version, title="Início", blocks=[
        {"type": "themes", "title": "Temas", "note": "",
         "themes": ["economy", "economy"]}], note="inválido")
    response = c.post("/cms/page/inicio/save", data=duplicate, headers=ORIGIN)
    assert response.status_code == 422
    assert "tema" in response.text

    out_of_range = page_form(version, title="Início", blocks=[
        {"type": "text", "text": "A"}], note="inválido")
    out_of_range["block_theme_0_9"] = "economy"
    response = c.post("/cms/page/inicio/save", data=out_of_range, headers=ORIGIN)
    assert response.status_code == 422

    beyond_blocks = page_form(version, title="Início", blocks=[
        {"type": "text", "text": "A"}], note="inválido")
    beyond_blocks["block_title_20"] = "Fora do limite"
    response = c.post("/cms/page/inicio/save", data=beyond_blocks, headers=ORIGIN)
    assert response.status_code == 422
    assert env.meta("page", HOME_SLUG) == before_meta
    assert env.revisions("page", HOME_SLUG) == before_history
