"""The CMS home integration boundary: dashboard context, prepare route and legacy gating.

The route is a thin form layer over `backoffice.cms`, guarded by the same origin check and
authenticated actor as every other CMS mutation. These tests use the real migrated fixture,
the real service and both Admin mount prefixes.
"""
import json

import pytest

from backoffice.cms import HOME_SLUG, Cms
from tests.backoffice.test_cms_routes import (
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
    assert [block["series_id"] for block in body["blocks"]] == ["ine.hicp_yoy.PT"]


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
