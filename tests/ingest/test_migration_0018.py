"""Migration 0018: the editorial composition tables.

The schema is the contract the write path and the render path both rely on, so these tests
assert the constraints themselves (cap, closed vocabularies, cascade, FK) rather than the
DDL text: a later migration that weakens one of them must fail here.
"""

import shutil
import sqlite3

import pytest

from ingest import db as db_module
from ingest.db import MIGRATIONS_DIR, open_db


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%'")}


def _insert_page(conn, slug="inicio"):
    conn.execute("INSERT INTO editorial_page(slug) VALUES (?)", (slug,))


def _insert_series(conn, series_id, *, source_id=1, role="primary"):
    """The FK target must exist; the shape mirrors the registry's real rows."""
    conn.execute(
        "INSERT OR IGNORE INTO source(id, name, licence, licence_url, attribution, "
        "redistribution_ok) VALUES (?, 'INE', 'CC BY 4.0', 'https://www.ine.pt', 'INE', 1)",
        (source_id,))
    conn.execute(
        "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
        "frequency, unit, active) VALUES (?, ?, 'hicp_yoy', ?, 'economy', 'PT', 'M', "
        "'pct', 1)", (series_id, source_id, role))


@pytest.fixture
def conn(tmp_path):
    d = open_db(tmp_path / "prumo.db")
    yield d.conn
    d.close()


def test_tables_exist_and_are_strict(conn):
    sql = dict(conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'table' "
        "AND name LIKE 'editorial_%'").fetchall())
    assert set(sql) == {"editorial_page", "editorial_slot", "editorial_event"}
    for name, ddl in sql.items():
        assert "STRICT" in ddl, f"{name} is not STRICT"


def test_position_is_capped_at_eleven(conn):
    _insert_page(conn)
    for position in range(12):
        sid = f"ine.series_{position}.PT"
        _insert_series(conn, sid)
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'draft', ?, ?)", (position, sid))
    _insert_series(conn, "ine.series_12.PT")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'draft', 12, 'ine.series_12.PT')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'draft', -1, 'ine.series_0.PT')")


def test_state_and_action_vocabularies_are_closed(conn):
    _insert_page(conn)
    _insert_series(conn, "ine.hicp_yoy.PT")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'live', 0, 'ine.hicp_yoy.PT')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_event(ts, slug, action, version, note) "
            "VALUES ('2026-11-16T00:00:00Z', 'inicio', 'slot_added ', 1, 'x')")


def test_series_foreign_key_and_page_cascade(conn):
    _insert_page(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'draft', 0, 'ine.does_not_exist.PT')")
    _insert_series(conn, "ine.hicp_yoy.PT")
    conn.execute(
        "INSERT INTO editorial_slot(slug, state, position, series_id) "
        "VALUES ('inicio', 'draft', 0, 'ine.hicp_yoy.PT')")
    conn.execute("DELETE FROM editorial_page WHERE slug = 'inicio'")
    assert conn.execute("SELECT COUNT(*) FROM editorial_slot").fetchone()[0] == 0


def test_slot_without_a_page_is_refused(conn):
    _insert_series(conn, "ine.hicp_yoy.PT")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'draft', 0, 'ine.hicp_yoy.PT')")


def test_one_series_once_per_state_but_draft_and_published_are_independent(conn):
    _insert_page(conn)
    _insert_series(conn, "ine.hicp_yoy.PT")
    conn.execute(
        "INSERT INTO editorial_slot(slug, state, position, series_id) "
        "VALUES ('inicio', 'draft', 0, 'ine.hicp_yoy.PT')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'draft', 1, 'ine.hicp_yoy.PT')")
    conn.execute(
        "INSERT INTO editorial_slot(slug, state, position, series_id) "
        "VALUES ('inicio', 'published', 0, 'ine.hicp_yoy.PT')")
    assert conn.execute("SELECT COUNT(*) FROM editorial_slot").fetchone()[0] == 2


def test_one_position_once_per_state(conn):
    _insert_page(conn)
    _insert_series(conn, "ine.one.PT")
    _insert_series(conn, "ine.two.PT")
    conn.execute(
        "INSERT INTO editorial_slot(slug, state, position, series_id) "
        "VALUES ('inicio', 'draft', 0, 'ine.one.PT')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO editorial_slot(slug, state, position, series_id) "
            "VALUES ('inicio', 'draft', 0, 'ine.two.PT')")


def test_migration_is_additive(tmp_path, monkeypatch):
    """A database at 0017 and the same database after 0018 differ by exactly the new tables."""
    partial = tmp_path / "migrations_0017"
    partial.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if f.stem.startswith("0018"):
            continue
        shutil.copy(f, partial / f.name)
    monkeypatch.setattr(db_module, "MIGRATIONS_DIR", partial)
    path = tmp_path / "prumo.db"
    before = open_db(path)
    tables_before = _tables(before.conn)
    before.close()

    monkeypatch.undo()
    after = open_db(path)
    tables_after = _tables(after.conn)
    after.close()

    assert tables_after - tables_before == {
        "editorial_page", "editorial_slot", "editorial_event"}
    assert tables_before <= tables_after


def test_integrity_and_foreign_keys_clean(conn):
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_editorial_index_exists(conn):
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'editorial_%'")}
    assert "editorial_slot_state" in names
