"""B1 regression: INSERT OR REPLACE cannot rewrite CMS history.

SQLite fires the internal DELETE of a REPLACE only when `recursive_triggers` is ON, so the
append-only triggers in 0019 need both writable openers to enable it. The restricted opener
must also refuse turning it back off.
"""

import sqlite3

import pytest

from ingest import cms
from ingest.db import open_db, open_db_for_write

OPENERS = (("open_db", open_db), ("open_db_for_write", open_db_for_write))
TARGETS = ("cms_document", "cms_revision", "cms_event")


@pytest.fixture(params=OPENERS, ids=[name for name, _ in OPENERS])
def writable(request, tmp_path):
    _, opener = request.param
    path = tmp_path / "prumo.db"
    open_db(path).close()
    db = opener(path)
    try:
        yield db
    finally:
        db.close()


def _seed(conn):
    conn.execute(
        "INSERT INTO cms_document(kind, slug, version, created_at, updated_at) "
        "VALUES ('page', 'inicio', 1, '2026-11-16T00:00:00+00:00', "
        "'2026-11-16T00:00:00+00:00')")
    revision_id = conn.execute(
        "INSERT INTO cms_revision(kind, slug, body_json, created_at, actor) "
        "VALUES ('page', 'inicio', '{\"title\":\"Original\"}', "
        "'2026-11-16T00:00:00+00:00', 'owner')").lastrowid
    conn.execute(
        "UPDATE cms_document SET draft_revision_id = ? "
        "WHERE kind = 'page' AND slug = 'inicio'", (revision_id,))
    event_id = conn.execute(
        "INSERT INTO cms_event(ts, kind, slug, action, version, revision_id, actor, note) "
        "VALUES ('2026-11-16T00:00:00+00:00', 'page', 'inicio', 'created', 1, ?, "
        "'owner', 'criar')", (revision_id,)).lastrowid
    return revision_id, event_id


def _snapshot(conn):
    return {
        "cms_document": conn.execute(
            "SELECT * FROM cms_document ORDER BY kind, slug").fetchall(),
        "cms_revision": conn.execute(
            "SELECT * FROM cms_revision ORDER BY id").fetchall(),
        "cms_event": conn.execute(
            "SELECT * FROM cms_event ORDER BY id").fetchall(),
    }


def _replacement(target, revision_id, event_id):
    stamp = "2000-01-01T00:00:00+00:00"
    if target == "cms_document":
        return (
            "INSERT OR REPLACE INTO cms_document(kind, slug, version, created_at, "
            f"updated_at) VALUES ('page', 'inicio', 99, '{stamp}', '{stamp}')",
            (),
            "a CMS document is unpublished, never deleted",
        )
    if target == "cms_revision":
        return (
            "INSERT OR REPLACE INTO cms_revision(id, kind, slug, body_json, created_at, "
            f"actor) VALUES (?, 'page', 'inicio', '{{\"title\":\"Substituido\"}}', "
            f"'{stamp}', 'intruder')",
            (revision_id,),
            "cms_revision rows are append-only",
        )
    return (
        "INSERT OR REPLACE INTO cms_event(id, ts, kind, slug, action, version, revision_id, "
        f"actor, note) VALUES (?, '{stamp}', 'page', 'inicio', 'published', 99, ?, "
        "'intruder', 'inject')",
        (event_id, revision_id),
        "cms_event rows are append-only",
    )


@pytest.mark.parametrize("target", TARGETS)
def test_insert_or_replace_is_refused_and_changes_nothing(writable, target):
    revision_id, event_id = _seed(writable.conn)
    before = _snapshot(writable.conn)
    statement, params, message = _replacement(target, revision_id, event_id)
    with pytest.raises(sqlite3.IntegrityError, match=message):
        writable.conn.execute(statement, params)
    assert _snapshot(writable.conn) == before


@pytest.mark.parametrize("opener", [open_db, open_db_for_write],
                         ids=["open_db", "open_db_for_write"])
def test_every_writable_opener_enables_recursive_triggers(opener, tmp_path):
    path = tmp_path / "prumo.db"
    open_db(path).close()
    db = opener(path)
    try:
        assert db.conn.execute("PRAGMA recursive_triggers").fetchone() == (1,)
    finally:
        db.close()


@pytest.mark.parametrize("statement", ["PRAGMA recursive_triggers=OFF",
                                       "PRAGMA recursive_triggers=0"])
def test_the_restricted_writer_cannot_turn_recursive_triggers_off(statement, tmp_path):
    path = tmp_path / "prumo.db"
    open_db(path).close()
    db = open_db_for_write(path)
    try:
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            db.conn.execute(statement)
        assert db.conn.execute("PRAGMA recursive_triggers").fetchone() == (1,)
    finally:
        db.close()


def _page(title):
    return cms.canonical_for("page", {
        "title": title,
        "introduction": "",
        "section": "economy",
        "blocks": [],
    })


def test_the_lifecycle_still_works_through_both_writable_openers(writable):
    first = writable.cms_create("page", "precos", _page("Primeira"), actor="owner",
                                note="criar")
    original = first["draft_revision_id"]
    saved = writable.cms_save("page", "precos", 1, _page("Segunda"), actor="owner",
                              note="guardar")
    published = writable.cms_publish("page", "precos", 2, actor="owner",
                                     note="publicar")
    unpub = writable.cms_unpublish("page", "precos", 3, actor="owner", note="retirar")
    restored = writable.cms_restore("page", "precos", 4, original, actor="owner",
                                    note="recuperar")
    copied = writable.cms_duplicate("page", "precos", "precos-copia", actor="owner",
                                    note="duplicar")

    assert [first["version"], saved["version"], published["version"], unpub["version"],
            restored["version"], copied["version"]] == [1, 2, 3, 4, 5, 1]
    assert published["published_revision_id"] == saved["draft_revision_id"]
    assert unpub["published_revision_id"] is None
    assert restored["draft_revision_id"] not in {
        original, saved["draft_revision_id"], published["published_revision_id"]}
    assert len(writable.cms_history("page", "precos")) == 3
    assert [e["action"] for e in writable.cms_events("page", "precos")] == [
        "restored", "unpublished", "published", "saved", "created"]
    assert [e["action"] for e in writable.cms_events("page", "precos-copia")] == [
        "duplicated"]
