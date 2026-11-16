"""Migration 0019: additive CMS tables, composite pointer FKs and append-only guards."""

import shutil
import sqlite3

import pytest

import ingest.db as db_module
from ingest.db import (
    MIGRATIONS_DIR,
    open_db,
    open_db_for_write,
    open_db_readonly,
)


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%'")}


def _new_document(conn, kind="page", slug="inicio", version=1):
    conn.execute(
        "INSERT INTO cms_document(kind, slug, version, created_at, updated_at) "
        "VALUES (?, ?, ?, '2026-11-16T00:00:00+00:00', '2026-11-16T00:00:00+00:00')",
        (kind, slug, version))


def _new_revision(conn, kind="page", slug="inicio", body='{"blocks":[]}'):
    revision_id = conn.execute(
        "INSERT INTO cms_revision(kind, slug, body_json, created_at, actor) "
        "VALUES (?, ?, ?, '2026-11-16T00:00:00+00:00', 'owner')",
        (kind, slug, body)).lastrowid
    conn.execute(
        "UPDATE cms_document SET draft_revision_id = ? WHERE kind = ? AND slug = ?",
        (revision_id, kind, slug))
    return revision_id


def _new_event(conn, kind="page", slug="inicio", revision_id=None, action="created",
               version=1, note="criar"):
    conn.execute(
        "INSERT INTO cms_event(ts, kind, slug, action, version, revision_id, actor, note) "
        "VALUES ('2026-11-16T00:00:00+00:00', ?, ?, ?, ?, ?, 'owner', ?)",
        (kind, slug, action, version, revision_id, note))


@pytest.fixture
def conn(tmp_path):
    d = open_db(tmp_path / "prumo.db")
    yield d.conn
    d.close()


def test_three_cms_tables_exist_and_are_strict(conn):
    sql = dict(conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'table' "
        "AND name LIKE 'cms_%'").fetchall())
    assert set(sql) == {"cms_document", "cms_revision", "cms_event"}
    for name, ddl in sql.items():
        assert "STRICT" in ddl, f"{name} is not STRICT"


def test_kind_action_and_version_vocabularies_are_closed(conn):
    with pytest.raises(sqlite3.IntegrityError):
        _new_document(conn, kind="article")
    with pytest.raises(sqlite3.IntegrityError):
        _new_document(conn, version=-1)
    _new_document(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _new_revision(conn, kind="article")
    with pytest.raises(sqlite3.IntegrityError):
        _new_event(conn, action="slot_added", revision_id=1)
    with pytest.raises(sqlite3.IntegrityError):
        _new_event(conn, action="created", revision_id=1, version=0)


def test_body_must_be_a_json_object(conn):
    _new_document(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _new_revision(conn, body="[]")
    with pytest.raises(sqlite3.IntegrityError):
        _new_revision(conn, body="not json")
    with pytest.raises(sqlite3.IntegrityError):
        _new_revision(conn, body='"text"')


def test_pointer_cannot_target_another_document_or_a_missing_revision(conn):
    _new_document(conn, slug="um")
    _new_document(conn, slug="dois")
    first = _new_revision(conn, slug="um")
    second = _new_revision(conn, slug="dois")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE cms_document SET draft_revision_id = ? WHERE kind = 'page' "
            "AND slug = 'um'", (second,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE cms_document SET published_revision_id = ? WHERE kind = 'page' "
            "AND slug = 'um'", (second,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE cms_document SET draft_revision_id = 999999 WHERE kind = 'page' "
            "AND slug = 'um'")
    conn.execute(
        "UPDATE cms_document SET published_revision_id = ? WHERE kind = 'page' "
        "AND slug = 'um'", (first,))
    assert conn.execute(
        "SELECT draft_revision_id, published_revision_id FROM cms_document "
        "WHERE kind = 'page' AND slug = 'um'").fetchone() == (first, first)


def test_revision_and_event_identity_is_the_same_document(conn):
    _new_document(conn, slug="um")
    _new_document(conn, slug="dois")
    first = _new_revision(conn, slug="um")
    second = _new_revision(conn, slug="dois")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cms_revision(kind, slug, body_json, created_at, actor) "
            "VALUES ('page', 'sem-documento', '{}', 't', 'owner')")
    with pytest.raises(sqlite3.IntegrityError):
        _new_event(conn, slug="um", revision_id=second)
    _new_event(conn, slug="um", revision_id=first)
    assert conn.execute("SELECT COUNT(*) FROM cms_event").fetchone()[0] == 1


def test_revisions_and_events_are_append_only(conn):
    _new_document(conn)
    revision_id = _new_revision(conn)
    _new_event(conn, revision_id=revision_id)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE cms_revision SET actor = 'outro' WHERE id = ?", (revision_id,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM cms_revision WHERE id = ?", (revision_id,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE cms_event SET note = 'outra'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM cms_event")


def test_document_identity_is_immutable_and_documents_are_not_deleted(conn):
    _new_document(conn, slug="um")
    _new_revision(conn, slug="um")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE cms_document SET slug = 'dois' WHERE slug = 'um'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE cms_document SET kind = 'chart' WHERE slug = 'um'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE cms_document SET created_at = 'outra' WHERE slug = 'um'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM cms_document WHERE slug = 'um'")


def _insert_series(conn):
    conn.execute(
        "INSERT INTO source(id, name, licence, licence_url, attribution, redistribution_ok) "
        "VALUES (1, 'INE', 'CC BY 4.0', 'https://www.ine.pt', 'INE', 1)")
    conn.execute(
        "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
        "frequency, unit, active) VALUES ('ine.hicp_yoy.PT', 1, 'hicp_yoy', 'primary', "
        "'economy', 'PT', 'M', 'pct', 1)")


def _migrations_through_0018(tmp_path):
    partial = tmp_path / "migrations_0018"
    partial.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if f.stem[:4] <= "0018":
            shutil.copy(f, partial / f.name)
    return partial


def _non_cms_schema(conn):
    return dict(conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'cms_%' AND name <> 'schema_migration'").fetchall())


def _editorial_rows(conn):
    return {
        "editorial_page": conn.execute("SELECT * FROM editorial_page ORDER BY slug").fetchall(),
        "editorial_slot": conn.execute(
            "SELECT * FROM editorial_slot ORDER BY slug, state, position").fetchall(),
        "editorial_event": conn.execute("SELECT * FROM editorial_event ORDER BY id").fetchall(),
        "source": conn.execute("SELECT * FROM source ORDER BY id").fetchall(),
        "series": conn.execute("SELECT * FROM series ORDER BY id").fetchall(),
        "dataset_run": conn.execute("SELECT * FROM dataset_run ORDER BY id").fetchall(),
        "raw_fetch": conn.execute("SELECT * FROM raw_fetch ORDER BY id").fetchall(),
        "observation": conn.execute("SELECT * FROM observation ORDER BY id").fetchall(),
    }


def test_filled_0018_database_upgrades_to_0019_without_touching_existing_data(
        tmp_path, monkeypatch):
    partial = _migrations_through_0018(tmp_path)
    path = tmp_path / "prumo.db"
    monkeypatch.setattr(db_module, "MIGRATIONS_DIR", partial)
    before = open_db(path)
    _insert_series(before.conn)
    run_id = before.conn.execute(
        "INSERT INTO dataset_run(source_id, started_at, state) "
        "VALUES (1, '2026-11-01T00:00:00+00:00', 'verified')").lastrowid
    raw_id = before.conn.execute(
        "INSERT INTO raw_fetch(source_id, url, fetched_at, http_status, sha256, path, bytes, ok) "
        "VALUES (1, 'https://www.ine.pt/x', '2026-11-01T00:00:00+00:00', 200, 'abc', 'p', 1, 1)"
    ).lastrowid
    before.conn.execute(
        "INSERT INTO observation(series_id, period, value_text, value, kind, dataset_run_id, "
        "raw_fetch_id, fetched_at) VALUES ('ine.hicp_yoy.PT', '2026-10', '2.1', 2.1, 'fetched', "
        "?, ?, '2026-11-01T00:00:00+00:00')", (run_id, raw_id))
    before.conn.execute("INSERT INTO editorial_page(slug, version) VALUES ('inicio', 1)")
    before.conn.execute(
        "INSERT INTO editorial_slot(slug, state, position, series_id) "
        "VALUES ('inicio', 'draft', 0, 'ine.hicp_yoy.PT')")
    before.conn.execute(
        "INSERT INTO editorial_event(ts, slug, action, version, note) "
        "VALUES ('2026-11-16T00:00:00+00:00', 'inicio', 'published', 1, 'publicar')")
    schema_before = _non_cms_schema(before.conn)
    rows_before = _editorial_rows(before.conn)
    tables_before = _tables(before.conn)
    before.close()
    monkeypatch.undo()

    after = open_db(path)
    try:
        assert _tables(after.conn) - tables_before == {
            "cms_document", "cms_revision", "cms_event"}
        assert tables_before <= _tables(after.conn)
        assert _non_cms_schema(after.conn) == schema_before
        assert _editorial_rows(after.conn) == rows_before
        assert after.conn.execute("SELECT COUNT(*) FROM cms_document").fetchone()[0] == 0
        assert "0019_statistics_cms" in {
            r[0] for r in after.conn.execute("SELECT version FROM schema_migration")}
        assert after.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert after.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        after.close()

    open_db_readonly(path).close()
    writable = open_db_for_write(path)
    try:
        assert writable.conn.execute("SELECT COUNT(*) FROM cms_event").fetchone()[0] == 0
    finally:
        writable.close()


def test_a_failed_cms_migration_leaves_no_partial_schema(tmp_path, monkeypatch):
    """The migrator's transaction keeps a half-created 0019 out of the database."""
    bad_dir = tmp_path / "migrations_bad"
    bad_dir.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        (bad_dir / f.name).write_bytes(f.read_bytes())
    (bad_dir / "0019_statistics_cms.sql").write_text(
        "CREATE TABLE cms_document(x INTEGER) STRICT;\n"
        "CREATE TABLE cms_broken(;\n")
    monkeypatch.setattr(db_module, "MIGRATIONS_DIR", bad_dir)
    path = tmp_path / "broken.db"
    with pytest.raises(sqlite3.OperationalError):
        open_db(path)
    conn = sqlite3.connect(path)
    try:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        applied = {r[0] for r in conn.execute("SELECT version FROM schema_migration")}
    finally:
        conn.close()
    assert "cms_document" not in names
    assert "0019_statistics_cms" not in applied
