"""CMS storage lifecycle: immutable revisions, pointer swaps, CAS and restricted writes."""

import json
import sqlite3

import pytest

from ingest import cms
from ingest.db import (
    CmsConflict,
    CmsNotFound,
    CmsRefused,
    open_db,
    open_db_for_write,
)

PAGE = "precos"
CHART = "inflacao"


def _page(**overrides):
    data = {
        "title": "Precos e rendimento",
        "introduction": "Uma leitura da economia.",
        "section": "economy",
        "blocks": [
            {"type": "text", "text": "Paragrafo editorial."},
            {"type": "card", "series_id": "ine.hicp_yoy.PT", "derived_key": None},
            {"type": "chart", "chart_slug": "inflacao"},
        ],
    }
    data.update(overrides)
    return cms.canonical_for("page", data)


def _chart(**overrides):
    data = {
        "title": "Inflacao",
        "note": "Variacao homóloga.",
        "series_a": "ine.hicp_yoy.PT",
        "series_b": None,
        "derived_key": None,
        "window": "max",
        "scale": "single",
        "day": None,
    }
    data.update(overrides)
    return cms.canonical_for("chart", data)


def _compact(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _create(db, kind="page", slug=PAGE, body=None):
    return db.cms_create(kind, slug, body or (_page() if kind == "page" else _chart()),
                         actor="owner", note="criar")


def _state(db, kind="page", slug=PAGE):
    return (db.cms_get(kind, slug), db.cms_history(kind, slug), db.cms_events(kind, slug))


def test_create_returns_exact_metadata_and_appends_one_revision_and_event(db):
    body = _page()
    meta = _create(db, body=body)
    assert set(meta) == {
        "kind", "slug", "version", "draft_revision_id", "published_revision_id",
        "created_at", "updated_at"}
    assert meta["kind"] == "page" and meta["slug"] == PAGE
    assert meta["version"] == 1 and meta["published_revision_id"] is None
    assert meta["created_at"] == meta["updated_at"]
    assert db.cms_get("page", PAGE) == meta
    assert db.cms_list("page") == [meta]
    assert db.cms_list("chart") == []
    history = db.cms_history("page", PAGE)
    assert len(history) == 1
    assert history[0]["id"] == meta["draft_revision_id"]
    assert history[0]["body_json"] == body
    assert history[0]["actor"] == "owner"
    assert db.cms_revision("page", PAGE, history[0]["id"]) == history[0]
    assert db.cms_revision("page", "outra", history[0]["id"]) is None
    events = db.cms_events("page", PAGE)
    assert len(events) == 1
    assert events[0]["action"] == "created" and events[0]["version"] == 1
    assert events[0]["revision_id"] == history[0]["id"]
    assert events[0]["actor"] == "owner" and events[0]["note"] == "criar"
    assert set(events[0]) == {
        "id", "ts", "kind", "slug", "action", "version", "revision_id", "actor", "note"}


def test_save_moves_only_the_draft_and_bumps_once(db):
    first = _create(db)
    second_body = _page(title="Precos atualizados")
    second = db.cms_save("page", PAGE, 1, second_body, actor="owner", note="corrigir")
    assert second["version"] == 2
    assert second["draft_revision_id"] != first["draft_revision_id"]
    assert second["published_revision_id"] is None
    assert db.cms_revision("page", PAGE, second["draft_revision_id"])["body_json"] == second_body
    assert db.cms_revision("page", PAGE, first["draft_revision_id"])["body_json"] == _page()
    assert [e["action"] for e in db.cms_events("page", PAGE)] == ["saved", "created"]


def test_publish_points_at_the_current_draft_and_a_later_save_does_not_change_it(db):
    created = _create(db)
    published = db.cms_publish("page", PAGE, 1, actor="owner", note="publicar")
    assert published["version"] == 2
    assert published["published_revision_id"] == created["draft_revision_id"]
    assert published["draft_revision_id"] == created["draft_revision_id"]
    assert db.cms_list("page", published_only=True) == [published]

    draft_body = _page(title="Rascunho seguinte")
    saved = db.cms_save("page", PAGE, 2, draft_body, actor="owner", note="preparar")
    assert saved["published_revision_id"] == published["published_revision_id"]
    assert saved["draft_revision_id"] != saved["published_revision_id"]
    assert db.cms_revision("page", PAGE,
                           saved["published_revision_id"])["body_json"] == _page()
    assert db.cms_revision("page", PAGE, saved["draft_revision_id"])["body_json"] == draft_body
    assert [e["action"] for e in db.cms_events("page", PAGE)] == [
        "saved", "published", "created"]


def test_unpublish_clears_only_the_published_pointer_and_keeps_history(db):
    _create(db)
    published = db.cms_publish("page", PAGE, 1, actor="owner", note="publicar")
    draft_id = published["draft_revision_id"]
    published_id = published["published_revision_id"]
    unpub = db.cms_unpublish("page", PAGE, 2, actor="owner", note="retirar")
    assert unpub["version"] == 3
    assert unpub["published_revision_id"] is None
    assert unpub["draft_revision_id"] == draft_id
    assert db.cms_list("page", published_only=True) == []
    assert len(db.cms_history("page", PAGE)) == 1
    event = db.cms_events("page", PAGE)[0]
    assert event["action"] == "unpublished" and event["revision_id"] == published_id


def test_restore_creates_a_new_draft_copy_and_never_mutates_old_revisions(db):
    first = _create(db, body=_page(title="Primeira versao"))
    old_id = first["draft_revision_id"]
    v2 = db.cms_save("page", PAGE, 1, _page(title="Segunda versao"),
                     actor="owner", note="segunda")
    db.cms_publish("page", PAGE, 2, actor="owner", note="publicar")
    published_id = v2["draft_revision_id"]
    v4 = db.cms_save("page", PAGE, 3, _page(title="Terceira versao"),
                     actor="owner", note="terceira")
    old_row = db.cms_revision("page", PAGE, old_id)
    restored = db.cms_restore("page", PAGE, 4, old_id, actor="owner", note="recuperar")
    assert restored["version"] == 5
    assert restored["draft_revision_id"] not in {old_id, published_id, v4["draft_revision_id"]}
    assert restored["published_revision_id"] == published_id
    new_row = db.cms_revision("page", PAGE, restored["draft_revision_id"])
    assert new_row["body_json"] == old_row["body_json"]
    assert new_row["actor"] == "owner"
    assert db.cms_revision("page", PAGE, old_id) == old_row
    assert len(db.cms_history("page", PAGE)) == 4
    event = db.cms_events("page", PAGE)[0]
    assert event["action"] == "restored"
    assert event["revision_id"] == restored["draft_revision_id"]


def test_duplicate_copies_the_current_draft_to_an_independent_unpublished_document(db):
    source = _create(db)
    db.cms_publish("page", PAGE, 1, actor="owner", note="publicar fonte")
    draft_body = _page(title="Rascunho que sera copiado")
    source_draft = db.cms_save("page", PAGE, 2, draft_body, actor="owner", note="rascunho")
    source_before = _state(db)

    target = db.cms_duplicate("page", PAGE, "precos-copia", actor="owner", note="duplicar")
    assert target["version"] == 1
    assert target["published_revision_id"] is None
    assert set(target) == {
        "kind", "slug", "version", "draft_revision_id", "published_revision_id",
        "created_at", "updated_at"}
    target_history = db.cms_history("page", "precos-copia")
    assert len(target_history) == 1
    assert target_history[0]["body_json"] == draft_body
    assert target_history[0]["id"] != source_draft["draft_revision_id"]
    assert db.cms_events("page", "precos-copia")[0]["action"] == "duplicated"
    assert _state(db) == source_before

    db.cms_save("page", "precos-copia", 1, _page(title="So na copia"),
                actor="owner", note="editar copia")
    assert _state(db) == source_before


def test_every_mutation_is_stale_checked_and_stale_writes_nothing(db):
    _create(db)
    before = _state(db)
    version = before[0]["version"]
    revision = before[0]["draft_revision_id"]
    for call in (
            lambda: db.cms_save("page", PAGE, 0, _page(), actor="owner", note="x"),
            lambda: db.cms_publish("page", PAGE, 0, actor="owner", note="x"),
            lambda: db.cms_unpublish("page", PAGE, 0, actor="owner", note="x"),
            lambda: db.cms_restore("page", PAGE, 0, revision, actor="owner", note="x")):
        with pytest.raises(CmsConflict) as exc:
            call()
        assert exc.value.expected == 0
        assert exc.value.actual == version
        assert exc.value.kind == "page" and exc.value.slug == PAGE
        assert _state(db) == before
    assert db.cms_get("page", PAGE)["version"] == version


def test_missing_documents_are_clear_domain_errors(db):
    calls = (
        lambda: db.cms_save("page", "ausente", 0, _page(), actor="owner", note="x"),
        lambda: db.cms_publish("page", "ausente", 0, actor="owner", note="x"),
        lambda: db.cms_unpublish("page", "ausente", 0, actor="owner", note="x"),
        lambda: db.cms_restore("page", "ausente", 0, 1, actor="owner", note="x"),
        lambda: db.cms_duplicate("page", "ausente", "copia", actor="owner", note="x"),
    )
    for call in calls:
        with pytest.raises(CmsNotFound) as exc:
            call()
        assert exc.value.kind == "page" and exc.value.slug == "ausente"
    assert db.cms_get("page", "ausente") is None
    assert db.cms_list("page") == []
    assert db.cms_history("page", "ausente") == []
    assert db.cms_events("page", "ausente") == []


def test_refused_actions_write_nothing(db):
    created = _create(db)
    before = _state(db)
    with pytest.raises(CmsRefused):
        db.cms_unpublish("page", PAGE, 1, actor="owner", note="nada publicado")
    with pytest.raises(CmsRefused):
        db.cms_duplicate("page", PAGE, PAGE, actor="owner", note="mesmo slug")
    with pytest.raises(CmsRefused):
        db.cms_restore("page", PAGE, 1, 999_999, actor="owner", note="revisao alheia")
    assert _state(db) == before
    assert created["version"] == 1


def test_duplicate_target_must_not_exist(db):
    _create(db)
    _create(db, slug="precos-copia")
    before_source = _state(db)
    before_target = _state(db, slug="precos-copia")
    with pytest.raises(CmsRefused):
        db.cms_duplicate("page", PAGE, "precos-copia", actor="owner", note="colidir")
    assert _state(db) == before_source
    assert _state(db, slug="precos-copia") == before_target


def test_create_refuses_an_existing_slug_and_an_invalid_new_slug(db):
    _create(db)
    before = _state(db)
    with pytest.raises(CmsRefused):
        db.cms_create("page", PAGE, _page(), actor="owner", note="outra vez")
    assert _state(db) == before
    with pytest.raises(CmsRefused):
        db.cms_create("page", "Nao-Kebab", _page(), actor="owner", note="x")
    with pytest.raises(CmsRefused):
        db.cms_create("article", "artigo", _page(), actor="owner", note="x")
    assert db.cms_list("page") == [before[0]]


def test_only_canonical_typed_bodies_reach_storage(db):
    pretty = json.dumps(json.loads(_page()), ensure_ascii=False, indent=2)
    too_long = json.loads(_page())
    too_long["title"] = "x" * 161
    with_unit = json.loads(_page())
    with_unit["blocks"].append({"type": "text", "text": "x", "unit": "pct"})
    with_em_dash = json.loads(_page())
    with_em_dash["title"] = "a " + chr(0x2014)
    bad_bodies = (
        pretty,
        _chart(),
        json.dumps({"title": "Sem corpo tipado"}),
        _compact(too_long),
        _compact(with_unit),
        _compact(with_em_dash),
    )
    for body in bad_bodies:
        with pytest.raises(CmsRefused):
            db.cms_create("page", "mau", body, actor="owner", note="x")
    assert db.cms_get("page", "mau") is None

    meta = _create(db)
    before = _state(db)
    with pytest.raises(CmsRefused):
        db.cms_save("page", PAGE, meta["version"], json.dumps({"title": "solto"}),
                    actor="owner", note="x")
    assert _state(db) == before


def test_actor_and_note_are_required_and_bounded(db):
    for actor, note in ((None, "x"), ("", "x"), ("owner", "  "), ("x" * 201, "x"),
                        ("owner", "x" * 4001)):
        with pytest.raises(CmsRefused):
            db.cms_create("page", PAGE, _page(), actor=actor, note=note)
        assert db.cms_get("page", PAGE) is None


def test_a_corrupt_revision_cannot_be_restored_or_duplicated(db):
    meta = _create(db)
    bad = json.dumps({"title": "sem kind valido", "raw_value": "3.2"}, separators=(",", ":"))
    bad_id = db.conn.execute(
        "INSERT INTO cms_revision(kind, slug, body_json, created_at, actor) "
        "VALUES ('page', ?, ?, '2026-11-16T00:00:00+00:00', 'owner')", (PAGE, bad)).lastrowid
    db.conn.execute("UPDATE cms_document SET draft_revision_id = ? WHERE kind = 'page' "
                    "AND slug = ?", (bad_id, PAGE))
    before_version = db.cms_get("page", PAGE)["version"]
    history_count = len(db.cms_history("page", PAGE))
    event_count = len(db.cms_events("page", PAGE))
    with pytest.raises(CmsRefused):
        db.cms_publish("page", PAGE, meta["version"], actor="owner", note="x")
    with pytest.raises(CmsRefused):
        db.cms_restore("page", PAGE, meta["version"], bad_id, actor="owner", note="x")
    with pytest.raises(CmsRefused):
        db.cms_duplicate("page", PAGE, "copia", actor="owner", note="x")
    assert db.cms_get("page", PAGE)["version"] == before_version
    assert len(db.cms_history("page", PAGE)) == history_count
    assert len(db.cms_events("page", PAGE)) == event_count
    assert db.cms_get("page", "copia") is None


def test_a_failed_create_rolls_back_the_head_revision_and_event(db, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("falha a meio")

    monkeypatch.setattr(type(db), "_cms_insert_revision", boom)
    with pytest.raises(RuntimeError):
        db.cms_create("page", PAGE, _page(), actor="owner", note="criar")
    assert db.cms_get("page", PAGE) is None
    assert db.cms_list("page") == []
    assert db.conn.execute("SELECT COUNT(*) FROM cms_revision").fetchone()[0] == 0
    assert db.conn.execute("SELECT COUNT(*) FROM cms_event").fetchone()[0] == 0


def test_a_failed_save_rolls_back_revision_pointer_and_version(db, monkeypatch):
    created = _create(db)
    before = _state(db)

    def boom(*args, **kwargs):
        raise RuntimeError("falha no evento")

    monkeypatch.setattr(type(db), "_cms_audit_event", boom)
    with pytest.raises(RuntimeError):
        db.cms_save("page", PAGE, created["version"], _page(title="nao fica"),
                    actor="owner", note="x")
    assert _state(db) == before


def test_chart_documents_use_the_same_lifecycle(db):
    meta = _create(db, kind="chart", slug=CHART)
    assert db.cms_get("chart", CHART) == meta
    assert db.cms_list("page") == []
    chart = db.cms_history("chart", CHART)[0]
    assert json.loads(chart["body_json"])["series_a"] == "ine.hicp_yoy.PT"
    published = db.cms_publish("chart", CHART, 1, actor="owner", note="publicar")
    assert published["published_revision_id"] == chart["id"]
    assert db.cms_list("chart", published_only=True) == [published]
    assert db.cms_list("page", published_only=True) == []


def test_the_restricted_writer_allows_cms_tables_only(tmp_path):
    path = tmp_path / "prumo.db"
    open_db(path).close()
    db = open_db_for_write(path)
    try:
        meta = _create(db)
        db.cms_save("page", PAGE, meta["version"], _page(title="Guardado"),
                    actor="owner", note="guardar")
        assert db.cms_get("page", PAGE)["version"] == 2
        for statement in (
                "UPDATE observation SET value_text = 'x'",
                "DELETE FROM dataset_run",
                "INSERT INTO setting(key, value) VALUES ('x', 'y')",
                "UPDATE series SET active = 0",
                "CREATE TABLE extra(x)",
                "CREATE TEMP TABLE temp_extra(x)",
                "DROP TABLE cms_document"):
            with pytest.raises(sqlite3.DatabaseError):
                db.conn.execute(statement)
        with pytest.raises(sqlite3.DatabaseError):
            db.conn.execute("UPDATE cms_revision SET body_json = body_json")
        assert db.cms_get("page", PAGE)["version"] == 2
    finally:
        db.close()
