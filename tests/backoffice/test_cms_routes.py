"""Route-focused tests for the CMS editor: labelled forms, ordering, lifecycle and guards.

The editor is a thin form and status-code layer over `backoffice.cms`; these tests exercise
the whole cycle through the real app and the real service, with a real migrated database and
real INE source names so the eligibility rules are the production ones, not a mock.
"""

import json
import re
from urllib.parse import urlencode

import pytest
import yaml
from fastapi.testclient import TestClient

from backoffice.app import create_app
from backoffice.cms import Cms, CmsBusy
from backoffice.cms_routes import CMS_FORM_MAX_BYTES, MAX_FIELDS
from ingest import cms as documents
from ingest.cms import MAX_BLOCKS, MAX_STEPS, MAX_TEXT
from ingest.db import open_db
from ingest.models import Observation
from ingest.registry import load_derived, load_registry, sync_derived, sync_registry
from presentation.catalog import pt
from tests.backoffice.conftest import NOW, series_row

ORIGIN = {"Origin": "http://localhost"}
FETCHED = "2026-11-13T00:00:00+00:00"
DERIVED_KEY = "derived.hicp_yoy.PT.yoy_change_pct"
PREFIX = "/dados/admin"

SOURCES = {
    "ine": {"licence": "CC-BY-4.0", "licence_url": "https://ine.example/licence",
            "attribution": "INE", "redistribution_ok": True},
}
SERIES = [
    series_row("ine.hicp_yoy.PT", source="ine", indicator_key="hicp_yoy.PT.M",
               frequency="M", unit="%"),
    series_row("ine.unemployment_rate.PT", source="ine",
               indicator_key="unemployment_rate.PT.M", frequency="M", unit="%"),
]
DERIVED = [{"key": DERIVED_KEY, "base": "ine.hicp_yoy.PT", "formula": "yoy_change_pct",
            "unit": "pct"}]
SERVED = ("ine.hicp_yoy.PT", "ine.unemployment_rate.PT")


@pytest.fixture(autouse=True)
def _derived_title(monkeypatch):
    monkeypatch.setitem(pt.TITLES, DERIVED_KEY, "IHPC, variação homóloga (%)")


def _served(db, sid, period="2026-01"):
    run = db.begin_run("ine", f"k-{sid}", FETCHED)
    fid = db.record_raw_fetch(source_name="ine", run_id=run, url="https://x",
                              params_json=None, fetched_at=FETCHED, http_status=200,
                              sha256=f"sha-{sid}", path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(sid, period, "1.5"), fid, FETCHED)])
    db.set_run_state(run, "verified")


class Env:
    def __init__(self, tmp_path):
        self.registry = tmp_path / "core.yaml"
        self.registry.write_text(yaml.safe_dump(
            {"sources": SOURCES, "series": SERIES, "derived": DERIVED}, sort_keys=False))
        self.db_path = tmp_path / "prumo.sqlite3"
        specs = load_registry(self.registry)
        db = open_db(self.db_path)
        try:
            sync_registry(db, specs)
            sync_derived(db, load_derived(self.registry, specs))
            for sid in SERVED:
                _served(db, sid)
        finally:
            db.close()

    def client(self, *, writable=True):
        return TestClient(
            create_app(self.db_path, self.registry, now=lambda: NOW,
                       editorial_db_path=self.db_path if writable else None),
            base_url="http://localhost", follow_redirects=False)

    def db(self):
        return open_db(self.db_path)

    def meta(self, kind, slug):
        db = self.db()
        try:
            return db.cms_get(kind, slug)
        finally:
            db.close()

    def revisions(self, kind, slug):
        db = self.db()
        try:
            return db.cms_history(kind, slug)
        finally:
            db.close()

    def events(self, kind, slug):
        db = self.db()
        try:
            return db.cms_events(kind, slug)
        finally:
            db.close()


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def page_create(client, slug="precos", title="Preços no consumidor", **extra):
    data = {"kind": "page", "slug": slug, "title": title, "introduction": "",
            "section": "economy", "note": "criar página"}
    data.update(extra)
    return client.post("/cms/new", data=data, headers=ORIGIN)


def chart_create(client, slug="inflacao", title="Inflação em Portugal",
                 series_a="ine.hicp_yoy.PT", **extra):
    data = {"kind": "chart", "slug": slug, "title": title, "note_text": "Nota editorial.",
            "series_a": series_a, "series_b": "", "derived_key": "", "window": "max",
            "scale": "single", "day": "", "note": "criar gráfico"}
    data.update(extra)
    return client.post("/cms/new", data=data, headers=ORIGIN)


def page_form(version, title="Preços no consumidor", intro="", section="economy",
              blocks=(), op="save", note="guardar"):
    data = {"version": str(version), "title": title, "introduction": intro,
            "section": section, "block_count": str(len(blocks)), "note": note, "op": op}
    for index, block in enumerate(blocks):
        data[f"block_type_{index}"] = block["type"]
        data[f"block_text_{index}"] = block.get("text", "")
        data[f"block_series_{index}"] = block.get("series_id", "")
        data[f"block_derived_{index}"] = block.get("derived_key", "")
        data[f"block_chart_{index}"] = block.get("chart_slug", "")
        data[f"block_label_{index}"] = block.get("label", "")
        data[f"block_eyebrow_{index}"] = block.get("eyebrow", "")
        data[f"block_title_{index}"] = block.get("title", "")
        data[f"block_note_{index}"] = block.get("note", "")
        if block.get("counts"):
            data[f"block_counts_{index}"] = "1"
        if block.get("freshness"):
            data[f"block_freshness_{index}"] = "1"
        for position, action in enumerate(block.get("actions", [])):
            data[f"block_link_label_{index}_{position}"] = action["label"]
            data[f"block_link_href_{index}_{position}"] = action["href"]
        action = block.get("action")
        if action:
            data[f"block_link_label_{index}"] = action["label"]
            data[f"block_link_href_{index}"] = action["href"]
        for position, theme in enumerate(block.get("themes", [])):
            data[f"block_theme_{index}_{position}"] = theme
        for position, step in enumerate(block.get("steps", [])):
            data[f"block_step_label_{index}_{position}"] = step["label"]
            data[f"block_step_text_{index}_{position}"] = step["text"]
    return data


def test_dashboard_lists_both_kinds_create_forms_and_nav(env):
    r = env.client().get("/cms")
    assert r.status_code == 200
    for text in ("Páginas", "Gráficos", "Criar página", "Criar gráfico", "CMS"):
        assert text in r.text
    assert 'action="/cms/new"' in r.text
    assert 'href="/cms#paginas"' in r.text and 'href="/cms#graficos"' in r.text
    # choices show the statistical identity next to the reference
    assert "ine.hicp_yoy.PT" in r.text and "| Mensal |" in r.text
    assert "| Portugal |" in r.text and "INE" in r.text
    assert "| janeiro de 2026 |" in r.text      # served coverage, not an assumed range


def test_create_page_redirects_to_editor_and_records_the_actor(env):
    c = env.client()
    r = page_create(c)
    assert r.status_code == 303
    assert r.headers["location"] == "/cms/page/precos"
    meta = env.meta("page", "precos")
    assert meta["version"] == 1 and meta["draft_revision_id"] == 1
    assert meta["published_revision_id"] is None
    events = env.events("page", "precos")
    assert events[0]["action"] == "created"
    assert events[0]["actor"] == "local-developer"
    editor = c.get("/cms/page/precos")
    assert editor.status_code == 200
    assert "Preços no consumidor" in editor.text
    assert 'name="block_count" value="0"' in editor.text
    assert 'action="/cms/page/precos/save"' in editor.text
    assert "Motivo" in editor.text


def test_save_and_add_move_remove_blocks_in_order(env):
    c = env.client()
    assert page_create(c).status_code == 303
    first = {"type": "text", "text": "Primeiro parágrafo."}
    r = c.post("/cms/page/precos/save", data=page_form(1, blocks=[first]), headers=ORIGIN)
    assert r.status_code == 303

    add = page_form(2, blocks=[first], op="add")
    add.update({"add_type": "text", "add_text": "Segundo parágrafo."})
    assert c.post("/cms/page/precos/save", data=add, headers=ORIGIN).status_code == 303

    editor = c.get("/cms/page/precos")
    assert editor.text.index("Primeiro parágrafo.") < editor.text.index("Segundo parágrafo.")
    assert editor.text.count('name="block_type_') == 2

    move = page_form(3, blocks=[first, {"type": "text", "text": "Segundo parágrafo."}])
    move["move_up_1"] = "1"
    assert c.post("/cms/page/precos/save", data=move, headers=ORIGIN).status_code == 303
    editor = c.get("/cms/page/precos")
    assert editor.text.index("Segundo parágrafo.") < editor.text.index("Primeiro parágrafo.")

    latest = env.revisions("page", "precos")[0]
    body = json.loads(latest["body_json"])
    assert [b["text"] for b in body["blocks"]] == ["Segundo parágrafo.", "Primeiro parágrafo."]

    remove = page_form(4, blocks=[{"type": "text", "text": "Segundo parágrafo."},
                                  first])
    remove["remove_0"] = "1"
    assert c.post("/cms/page/precos/save", data=remove, headers=ORIGIN).status_code == 303
    body = json.loads(env.revisions("page", "precos")[0]["body_json"])
    assert [b["text"] for b in body["blocks"]] == ["Primeiro parágrafo."]


def test_stale_version_is_409_and_writes_nothing(env):
    c = env.client()
    assert page_create(c).status_code == 303
    assert c.post("/cms/page/precos/save",
                  data=page_form(1, blocks=[{"type": "text", "text": "A"}]),
                  headers=ORIGIN).status_code == 303
    before = env.revisions("page", "precos")
    r = c.post("/cms/page/precos/save",
               data=page_form(1, blocks=[{"type": "text", "text": "B"}]),
               headers=ORIGIN)
    assert r.status_code == 409
    assert "nothing was written" in r.text and "version 2" in r.text
    # The re-render keeps what the operator submitted and the version it was written against;
    # it does not silently adopt the fresh version and invite a blind resubmit.
    assert ">B</textarea>" in r.text and 'name="version" value="1"' in r.text
    assert 'name="version" value="2"' not in r.text
    assert env.meta("page", "precos")["version"] == 2
    assert env.revisions("page", "precos") == before


def test_validation_refusal_is_422_and_does_not_bump_the_version(env):
    c = env.client()
    assert page_create(c).status_code == 303
    r = c.post("/cms/page/precos/save",
               data=page_form(1, title="", blocks=[{"type": "text", "text": "A"}]),
               headers=ORIGIN)
    assert r.status_code == 422
    assert "title" in r.text.lower()
    assert env.meta("page", "precos")["version"] == 1
    assert len(env.revisions("page", "precos")) == 1


def test_form_error_keeps_every_submitted_page_value(env):
    c = env.client()
    assert page_create(c).status_code == 303
    before_meta = env.meta("page", "precos")
    before_history = env.revisions("page", "precos")

    r = c.post("/cms/page/precos/save",
               data=page_form(1, title="TÍTULO ESCRITO PELO OPERADOR",
                              intro="INTRODUÇÃO ESCRITA PELO OPERADOR", blocks=[
                                  {"type": "hero", "title": "Abertura",
                                   "actions": [{"label": "Ler", "href": ""}]}]),
               headers=ORIGIN)
    assert r.status_code == 422 and "endereço" in r.text
    assert "TÍTULO ESCRITO PELO OPERADOR" in r.text
    assert "INTRODUÇÃO ESCRITA PELO OPERADOR" in r.text
    assert 'value="Ler"' in r.text
    assert env.meta("page", "precos") == before_meta
    assert env.revisions("page", "precos") == before_history


def test_form_error_keeps_values_when_the_block_count_is_not_a_number(env):
    c = env.client()
    assert page_create(c).status_code == 303
    before_meta = env.meta("page", "precos")
    before_history = env.revisions("page", "precos")
    data = page_form(1, title="TÍTULO COM NÚMERO INVÁLIDO",
                     blocks=[{"type": "text", "text": "TEXTO PRESERVADO"}])
    data["block_count"] = "muitos"

    r = c.post("/cms/page/precos/save", data=data, headers=ORIGIN)
    assert r.status_code == 422 and "número de blocos" in r.text
    assert "TÍTULO COM NÚMERO INVÁLIDO" in r.text
    assert "TEXTO PRESERVADO" in r.text
    assert env.meta("page", "precos") == before_meta
    assert env.revisions("page", "precos") == before_history


def test_form_error_keeps_values_when_the_note_is_missing(env):
    c = env.client()
    assert page_create(c).status_code == 303
    before_meta = env.meta("page", "precos")
    before_history = env.revisions("page", "precos")

    r = c.post("/cms/page/precos/save",
               data=page_form(1, title="TÍTULO SEM MOTIVO",
                              intro="INTRODUÇÃO SEM MOTIVO", note=""),
               headers=ORIGIN)
    assert r.status_code == 422 and "motivo" in r.text
    assert "TÍTULO SEM MOTIVO" in r.text and "INTRODUÇÃO SEM MOTIVO" in r.text
    assert env.meta("page", "precos") == before_meta
    assert env.revisions("page", "precos") == before_history


def test_form_error_keeps_the_submitted_chart_title_and_note(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    before_meta = env.meta("chart", "inflacao")
    before_history = env.revisions("chart", "inflacao")
    data = {"version": "1", "title": "TÍTULO DO GRÁFICO", "note_text": "NOTA NOVA",
            "series_a": "ine.hicp_yoy.PT", "series_b": "", "derived_key": "",
            "window": "max", "scale": "single", "day": "", "note": ""}

    r = c.post("/cms/chart/inflacao/save", data=data, headers=ORIGIN)
    assert r.status_code == 422 and "motivo" in r.text
    assert "TÍTULO DO GRÁFICO" in r.text and "NOTA NOVA" in r.text
    assert env.meta("chart", "inflacao") == before_meta
    assert env.revisions("chart", "inflacao") == before_history


def test_a_submitted_xss_string_is_escaped_in_the_editor(env):
    c = env.client()
    assert page_create(c, title="<script>alert(1)</script>").status_code == 303
    r = c.get("/cms/page/precos")
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r.text

    assert page_create(c, slug="erro", title="Página").status_code == 303
    bad = page_form(1, title="Página", blocks=[
        {"type": "card", "series_id": "<script>alert(1)</script>"}])
    r = c.post("/cms/page/erro/save", data=bad, headers=ORIGIN)
    assert r.status_code == 422
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r.text
    assert env.meta("page", "erro")["version"] == 1


def test_duplicate_creates_an_independent_draft(env):
    c = env.client()
    assert page_create(c).status_code == 303
    assert c.post("/cms/page/precos/save",
                  data=page_form(1, blocks=[{"type": "text", "text": "Original."}]),
                  headers=ORIGIN).status_code == 303
    r = c.post("/cms/page/precos/duplicate",
               data={"version": "2", "new_slug": "copia", "note": "duplicar"},
               headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/cms/page/copia"
    copy = env.meta("page", "copia")
    assert copy["version"] == 1 and copy["published_revision_id"] is None
    body = json.loads(env.revisions("page", "copia")[0]["body_json"])
    assert body["blocks"][0]["text"] == "Original."
    assert env.meta("page", "precos")["version"] == 2


def test_stale_duplicate_form_is_409_and_creates_nothing(env):
    c = env.client()
    assert page_create(c).status_code == 303
    assert c.post("/cms/page/precos/save",
                  data=page_form(1, blocks=[{"type": "text", "text": "Original."}]),
                  headers=ORIGIN).status_code == 303
    source_before = env.meta("page", "precos")
    source_history = len(env.revisions("page", "precos"))
    source_events = len(env.events("page", "precos"))
    r = c.post("/cms/page/precos/duplicate",
               data={"version": "1", "new_slug": "copia", "note": "duplicar"},
               headers=ORIGIN)
    assert r.status_code == 409
    assert env.meta("page", "precos") == source_before
    assert len(env.revisions("page", "precos")) == source_history
    assert len(env.events("page", "precos")) == source_events
    assert env.meta("page", "copia") is None
    assert env.revisions("page", "copia") == [] and env.events("page", "copia") == []


def test_publish_diff_unpublish_and_restore_keep_live_content(env):
    c = env.client()
    assert page_create(c).status_code == 303
    assert c.post("/cms/page/precos/save",
                  data=page_form(1, blocks=[{"type": "text", "text": "Versão publicada."}]),
                  headers=ORIGIN).status_code == 303
    assert c.post("/cms/page/precos/publish",
                  data={"version": "2", "note": "publicar"},
                  headers=ORIGIN).status_code == 303
    meta = env.meta("page", "precos")
    assert meta["version"] == 3 and meta["published_revision_id"] == 2

    # A new draft leaves the live revision untouched and the editor shows the difference.
    assert c.post("/cms/page/precos/save",
                  data=page_form(3, blocks=[{"type": "text", "text": "Novo rascunho."}]),
                  headers=ORIGIN).status_code == 303
    assert env.meta("page", "precos")["published_revision_id"] == 2
    editor = c.get("/cms/page/precos")
    assert "Versão publicada." in editor.text and "Novo rascunho." in editor.text
    assert "Alterações face à versão em direto" in editor.text

    preview = c.get("/cms/page/precos/preview")
    assert preview.status_code == 200
    assert "Novo rascunho." in preview.text
    assert "/static/css/prumo.css" in preview.text
    assert c.get("/static/css/prumo.css").status_code == 200
    assert "script-src" not in preview.headers["content-security-policy"]

    assert c.post("/cms/page/precos/unpublish",
                  data={"version": "4", "note": "retirar"},
                  headers=ORIGIN).status_code == 303
    assert env.meta("page", "precos")["published_revision_id"] is None

    assert c.post("/cms/page/precos/restore",
                  data={"version": "5", "revision_id": "2", "note": "restaurar"},
                  headers=ORIGIN).status_code == 303
    meta = env.meta("page", "precos")
    assert meta["version"] == 6
    assert meta["published_revision_id"] is None  # restore is a draft, not a publish
    restored = json.loads(env.revisions("page", "precos")[0]["body_json"])
    assert restored["blocks"][0]["text"] == "Versão publicada."
    assert 2 in [r["id"] for r in env.revisions("page", "precos")]  # old history remains


def test_chart_create_edit_publish_and_usage(env):
    c = env.client()
    chart = chart_create(c)
    assert chart.status_code == 303
    assert chart.headers["location"] == "/cms/chart/inflacao"
    editor = c.get("/cms/chart/inflacao")
    assert 'name="series_a"' in editor.text and 'name="scale"' in editor.text
    assert "| % |" in editor.text and "| Mensal |" in editor.text
    assert "| Portugal |" in editor.text and "INE" in editor.text
    assert c.post("/cms/chart/inflacao/save",
                  data={"version": "1", "title": "Inflação em Portugal",
                        "note_text": "Nota revista.", "series_a": "ine.hicp_yoy.PT",
                        "series_b": "", "derived_key": "", "window": "10y",
                        "scale": "single", "day": "", "note": "guardar"},
                  headers=ORIGIN).status_code == 303
    assert c.post("/cms/chart/inflacao/publish",
                  data={"version": "2", "note": "publicar"},
                  headers=ORIGIN).status_code == 303
    assert env.meta("chart", "inflacao")["published_revision_id"] == 2
    preview = c.get("/cms/chart/inflacao/preview")
    assert preview.status_code == 200
    assert "Inflação em Portugal" in preview.text
    assert 'href="/cms/chart/inflacao"' in preview.text
    assert "script-src" not in preview.headers["content-security-policy"]

    assert page_create(c, slug="com-grafico", title="Página com gráfico").status_code == 303
    assert c.post("/cms/page/com-grafico/save",
                  data=page_form(1, title="Página com gráfico", blocks=[
                      {"type": "chart", "chart_slug": "inflacao"}]),
                  headers=ORIGIN).status_code == 303
    assert c.post("/cms/page/com-grafico/publish",
                  data={"version": "2", "note": "publicar página"},
                  headers=ORIGIN).status_code == 303

    usage = c.get("/cms/chart/inflacao")
    assert "Páginas que usam este gráfico" in usage.text
    assert "Página com gráfico" in usage.text
    assert 'href="/cms/page/com-grafico"' in usage.text
    page_preview = c.get("/cms/page/com-grafico/preview")
    assert page_preview.status_code == 200
    assert "Página com gráfico" in page_preview.text
    assert "script-src" not in page_preview.headers["content-security-policy"]


def test_card_block_with_a_calculated_line_renders_and_publishes(env):
    c = env.client()
    assert page_create(c, slug="cartao", title="Cartão com calculada").status_code == 303
    block = {"type": "card", "series_id": "ine.hicp_yoy.PT", "derived_key": DERIVED_KEY}
    assert c.post("/cms/page/cartao/save", data=page_form(1, title="Cartão com calculada",
                                                          blocks=[block]),
                  headers=ORIGIN).status_code == 303
    editor = c.get("/cms/page/cartao")
    assert 'value="ine.hicp_yoy.PT" selected' in editor.text
    assert f'value="{DERIVED_KEY}" selected' in editor.text
    assert c.post("/cms/page/cartao/publish",
                  data={"version": "2", "note": "publicar cartão"},
                  headers=ORIGIN).status_code == 303
    assert env.meta("page", "cartao")["published_revision_id"] == 2
    preview = c.get("/cms/page/cartao/preview")
    assert preview.status_code == 200
    assert "Cartão com calculada" in preview.text


def test_missing_documents_are_404_and_writable_mount_missing_is_503(tmp_path):
    env = Env(tmp_path)
    c = env.client()
    assert c.get("/cms/page/nao-existe").status_code == 404
    assert c.get("/cms/article/x").status_code == 404
    assert c.get("/cms/page/nao-existe/preview").status_code == 404
    assert c.post("/cms/page/nao-existe/save",
                  data=page_form(1, blocks=[{"type": "text", "text": "A"}]),
                  headers=ORIGIN).status_code == 404

    read_only = env.client(writable=False)
    assert read_only.get("/cms").status_code == 200
    r = page_create(read_only)
    assert r.status_code == 503
    assert "indisponível" in r.text


def test_busy_service_is_503(env, monkeypatch):
    c = env.client()
    assert page_create(c).status_code == 303

    def busy(*args, **kwargs):
        raise CmsBusy("database is busy")

    monkeypatch.setattr(Cms, "save", busy)
    r = c.post("/cms/page/precos/save",
               data=page_form(1, blocks=[{"type": "text", "text": "A"}]),
               headers=ORIGIN)
    assert r.status_code == 503
    assert "ocupado" in r.text


def test_forms_refuse_cross_origin_duplicate_fields_and_oversized_bodies(env):
    c = env.client()
    assert c.post("/cms/new", data={"kind": "page", "slug": "x", "title": "X",
                                    "section": "general", "note": "n"}).status_code == 403
    assert c.post("/cms/new", data={"kind": "page", "slug": "x", "title": "X",
                                    "section": "general", "note": "n"},
                  headers={"Origin": "https://evil.example"}).status_code == 403

    duplicate = (b"kind=page&slug=x&title=Um&title=Dois&section=general&note=n")
    r = c.post("/cms/new", content=duplicate,
               headers={**ORIGIN, "Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 422 and "repetido" in r.text

    assert page_create(c, slug="grande").status_code == 303
    too_many = page_form(1, blocks=[{"type": "text", "text": "A"}] * (MAX_BLOCKS + 1))
    r = c.post("/cms/page/grande/save", data=too_many, headers=ORIGIN)
    assert r.status_code == 422 and str(MAX_BLOCKS) in r.text

    huge = "x" * (CMS_FORM_MAX_BYTES + 1)
    r = c.post("/cms/page/grande/save",
               data=page_form(1, blocks=[{"type": "text", "text": huge}]), headers=ORIGIN)
    assert r.status_code == 413


def test_the_editor_field_bound_covers_the_rendered_max_block_page(env):
    c = env.client()
    assert page_create(c, slug="grande").status_code == 303
    meta = env.meta("page", "grande")
    blocks = [{"type": "text", "text": f"Paragrafo {i}"} for i in range(MAX_BLOCKS)]
    saved = c.post("/cms/page/grande/save",
                   data=page_form(meta["version"], title="Grande", blocks=blocks),
                   headers=ORIGIN, follow_redirects=False)
    assert saved.status_code == 303
    html = c.get("/cms/page/grande").text
    names = set(re.findall(r'name="([^"]+)"', html))
    assert len(names) <= MAX_FIELDS
    assert len(names) > 700  # every type's fields are rendered for a no-JS switch

    before = (env.meta("page", "grande")["version"], len(env.revisions("page", "grande")))
    flood = {"title": "Grande", "section": "general", "note": "n", "block_count": "0",
             "version": str(before[0])}
    flood.update({f"campo_ignorado_{i}": "" for i in range(MAX_FIELDS + 1)})
    response = c.post("/cms/page/grande/save", data=flood, headers=ORIGIN)
    assert response.status_code == 422
    assert (env.meta("page", "grande")["version"], len(env.revisions("page", "grande"))) == before


def test_every_action_and_redirect_uses_the_admin_prefix(env):
    c = env.client()
    r = c.get("/cms", headers={"X-Forwarded-Prefix": PREFIX})
    assert 'action="/dados/admin/cms/new"' in r.text
    assert 'href="/dados/admin/cms#paginas"' in r.text
    created = c.post("/cms/new", data={"kind": "page", "slug": "precos",
                                       "title": "Preços", "section": "economy",
                                       "note": "criar"}, headers={**ORIGIN,
                                                                  "X-Forwarded-Prefix": PREFIX})
    assert created.status_code == 303
    assert created.headers["location"] == "/dados/admin/cms/page/precos"
    editor = c.get("/cms/page/precos", headers={"X-Forwarded-Prefix": PREFIX})
    assert 'action="/dados/admin/cms/page/precos/save"' in editor.text
    assert 'href="/dados/admin/cms/page/precos/preview"' in editor.text
    assert 'action="/dados/admin/cms/page/precos/publish"' in editor.text
    assert 'action="/dados/admin/cms/page/precos/restore"' in editor.text
    assert 'action="/dados/admin/cms/page/precos/duplicate"' in editor.text
    saved = c.post("/cms/page/precos/save",
                   data=page_form(1, blocks=[{"type": "text", "text": "Com prefixo."}]),
                   headers={**ORIGIN, "X-Forwarded-Prefix": PREFIX})
    assert saved.status_code == 303
    assert saved.headers["location"] == "/dados/admin/cms/page/precos"
    preview = c.get("/cms/page/precos/preview",
                    headers={"X-Forwarded-Prefix": PREFIX})
    assert preview.status_code == 200
    assert "/dados/admin/static/css/prumo.css" in preview.text
    assert 'href="/dados/admin/cms/page/precos"' in preview.text
    # A valid but unrelated prefix is not reflected.
    ignored = c.get("/cms", headers={"X-Forwarded-Prefix": "/outro"})
    assert 'action="/cms/new"' in ignored.text


def test_preview_data_links_use_the_public_prefix_while_assets_use_admin(env):
    c = env.client()
    assert chart_create(c).status_code == 303
    assert c.post("/cms/chart/inflacao/publish",
                  data={"version": "1", "note": "publicar"}, headers=ORIGIN).status_code == 303
    assert page_create(c).status_code == 303
    saved = c.post("/cms/page/precos/save",
                   data=page_form(1, blocks=[{"type": "chart", "chart_slug": "inflacao"}]),
                   headers=ORIGIN)
    assert saved.status_code == 303
    preview = c.get("/cms/page/precos/preview", headers={"X-Forwarded-Prefix": PREFIX})
    assert preview.status_code == 200
    assert 'href="/dados/graficos/inflacao"' in preview.text
    assert "/dados/admin/graficos" not in preview.text
    assert 'href="/dados/paginas"' in preview.text
    assert "/dados/admin/static/css/prumo.css" in preview.text
    assert 'href="/dados/admin/cms/page/precos"' in preview.text


@pytest.mark.parametrize(("field", "value"), [
    ("version", "9" * 5000),
    ("version", "\u0661"),
    ("version", str(2**63)),
    ("block_count", "9" * 5000),
    ("block_count", "\u0661"),
    ("block_count", str(2**63)),
])
def test_unbounded_integer_form_fields_are_422_and_write_nothing(env, field, value):
    c = env.client()
    assert page_create(c).status_code == 303
    before = (env.meta("page", "precos")["version"], len(env.revisions("page", "precos")))
    data = page_form(1, blocks=[{"type": "text", "text": "A"}])
    data[field] = value
    assert c.post("/cms/page/precos/save", data=data, headers=ORIGIN).status_code == 422
    assert (env.meta("page", "precos")["version"],
            len(env.revisions("page", "precos"))) == before


@pytest.mark.parametrize("value", ["9" * 5000, "\u0661", str(2**63)])
def test_unbounded_restore_revision_is_422_and_writes_nothing(env, value):
    c = env.client()
    assert page_create(c).status_code == 303
    assert c.post("/cms/page/precos/save",
                  data=page_form(1, blocks=[{"type": "text", "text": "A"}]),
                  headers=ORIGIN).status_code == 303
    before = (env.meta("page", "precos")["version"], len(env.revisions("page", "precos")))
    response = c.post("/cms/page/precos/restore",
                      data={"version": "2", "revision_id": value, "note": "restaurar"},
                      headers=ORIGIN)
    assert response.status_code == 422
    assert (env.meta("page", "precos")["version"],
            len(env.revisions("page", "precos"))) == before


def test_diff_detects_a_text_change_after_the_display_limit(env):
    c = env.client()
    assert page_create(c).status_code == 303
    first = "x" * 130 + " A"
    second = "x" * 130 + " B"
    assert c.post("/cms/page/precos/save", data=page_form(
        1, blocks=[{"type": "text", "text": first}]), headers=ORIGIN).status_code == 303
    assert c.post("/cms/page/precos/publish",
                  data={"version": "2", "note": "publicar"}, headers=ORIGIN).status_code == 303
    assert c.post("/cms/page/precos/save", data=page_form(
        3, blocks=[{"type": "text", "text": second}]), headers=ORIGIN).status_code == 303
    editor = c.get("/cms/page/precos")
    assert "Alterações face à versão em direto" in editor.text
    assert "Bloco 1" in editor.text


def test_chart_day_outside_fifteen_minutes_is_refused_and_not_silently_cleared(env):
    c = env.client()
    assert chart_create(c, day="2026-11-10").status_code == 303
    editor = c.get("/cms/chart/inflacao")
    assert 'name="day" value="2026-11-10"' in editor.text
    assert "só para séries de 15 minutos" in editor.text
    response = c.post("/cms/chart/inflacao/publish",
                      data={"version": "1", "note": "publicar"}, headers=ORIGIN)
    assert response.status_code == 422
    assert "15 minutos" in response.text
    assert env.meta("chart", "inflacao")["published_revision_id"] is None
    assert "pré-visualização estática com os dados e a composição da página pública" in editor.text


def test_second_hero_is_refused_on_save_and_on_publish_without_writes(env):
    c = env.client()
    assert page_create(c).status_code == 303
    before = env.meta("page", "precos")
    history = env.revisions("page", "precos")
    events = env.events("page", "precos")

    # A new authoring write never creates a two-hero draft.
    two_heroes = page_form(1, blocks=[
        {"type": "hero", "title": "Primeiro"},
        {"type": "hero", "title": "Segundo"},
    ])
    refused = c.post("/cms/page/precos/save", data=two_heroes, headers=ORIGIN)
    assert refused.status_code == 422
    assert "cabeçalho de abertura" in refused.text
    assert env.meta("page", "precos") == before
    assert env.revisions("page", "precos") == history
    assert env.events("page", "precos") == events

    # A body stored before the invariant stays readable but can never be published.
    stored = documents.canonical_body(documents.parse_body("page", {
        "title": "Preços no consumidor",
        "introduction": "",
        "section": "economy",
        "blocks": [{"type": "hero", "title": "Primeiro"},
                   {"type": "hero", "title": "Segundo"}],
    }))
    db = env.db()
    try:
        db.cms_save("page", "precos", 1, stored, actor="owner", note="corpo antigo")
    finally:
        db.close()
    draft = env.meta("page", "precos")
    assert draft["version"] == 2 and draft["published_revision_id"] is None
    history = env.revisions("page", "precos")
    events = env.events("page", "precos")

    refused = c.post("/cms/page/precos/publish",
                     data={"version": "2", "note": "publicar"}, headers=ORIGIN)
    assert refused.status_code == 422
    assert "cabeçalho de abertura" in refused.text
    assert env.meta("page", "precos") == draft
    assert env.revisions("page", "precos") == history
    assert env.events("page", "precos") == events


def test_large_schema_valid_verification_block_survives_form_transport(env):
    c = env.client()
    assert page_create(c).status_code == 303
    long_text = "\U0001D11E" * MAX_TEXT
    data = page_form(1, blocks=[{"type": "verification", "title": "Cadeia longa"}])
    for position in range(MAX_STEPS):
        data[f"block_step_label_0_{position}"] = f"Passo {position + 1}"
        data[f"block_step_text_0_{position}"] = long_text
    # This valid body is over the old 128 KiB cap only because of UTF-8 percent-encoding.
    assert len(urlencode(data)) > 131_072

    saved = c.post("/cms/page/precos/save", data=data, headers=ORIGIN)
    assert saved.status_code == 303
    body = json.loads(env.revisions("page", "precos")[0]["body_json"])
    steps = body["blocks"][0]["steps"]
    assert len(steps) == MAX_STEPS
    assert all(len(step["text"]) == MAX_TEXT for step in steps)


def test_form_over_the_transport_cap_is_413_and_writes_nothing(env):
    c = env.client()
    assert page_create(c).status_code == 303
    before = env.meta("page", "precos")
    history = env.revisions("page", "precos")
    events = env.events("page", "precos")

    body = b"version=1&note=motivo&title=" + b"a" * (CMS_FORM_MAX_BYTES + 1)
    refused = c.post("/cms/page/precos/save", content=body, headers={
        **ORIGIN, "Content-Type": "application/x-www-form-urlencoded"})
    assert refused.status_code == 413
    assert env.meta("page", "precos") == before
    assert env.revisions("page", "precos") == history
    assert env.events("page", "precos") == events
