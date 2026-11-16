"""open_db_for_write: the backoffice's only writable handle.

The point of this opener is what it refuses. A writable handle on a database the worker has
not migrated (or one newer than this code) would let a write land on a table shape this code
does not know, so every refusal here is asserted as behaviour, not as a message.
"""

import shutil
import sqlite3

import pytest

from ingest import db as db_module
from ingest.db import (MIGRATIONS_DIR, SchemaMismatchError, _expected_migrations,
                       open_db, open_db_for_write)

CURRENT = sorted(_expected_migrations())[-1]


@pytest.fixture
def path(tmp_path):
    p = tmp_path / "prumo.db"
    db = open_db(p)
    db.close()
    return p


def _sql(path, statement, params=()):
    conn = sqlite3.connect(str(path), isolation_level=None)
    try:
        return conn.execute(statement, params).fetchall()
    finally:
        conn.close()


def test_opens_an_exactly_current_database(path):
    db = open_db_for_write(path)
    try:
        assert db.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.conn.execute("SELECT COUNT(*) FROM editorial_page").fetchone()[0] == 0
    finally:
        db.close()


def test_refuses_an_older_schema(path):
    _sql(path, "DELETE FROM schema_migration WHERE version = ?", (CURRENT,))
    with pytest.raises(SchemaMismatchError) as exc:
        open_db_for_write(path)
    assert exc.value.expected - exc.value.applied == {CURRENT}
    assert "missing migrations" in str(exc.value)
    assert CURRENT in str(exc.value)


def test_refuses_a_newer_schema(path):
    _sql(path, "INSERT INTO schema_migration(version) VALUES ('0019_from_the_future')")
    with pytest.raises(SchemaMismatchError) as exc:
        open_db_for_write(path)
    assert exc.value.applied - exc.value.expected == {"0019_from_the_future"}
    assert "unknown migrations" in str(exc.value)


def test_never_migrates(tmp_path, monkeypatch):
    """A 0017 database stays at 0017: the refusal must not apply the pending migration."""
    partial = tmp_path / "migrations_0017"
    partial.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if f.stem.startswith("0018"):
            continue
        shutil.copy(f, partial / f.name)
    monkeypatch.setattr(db_module, "MIGRATIONS_DIR", partial)
    old = tmp_path / "old.db"
    open_db(old).close()
    monkeypatch.undo()

    with pytest.raises(SchemaMismatchError):
        open_db_for_write(old)
    names = {r[0] for r in _sql(
        old, "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "editorial_page" not in names
    applied = {r[0] for r in _sql(old, "SELECT version FROM schema_migration")}
    assert CURRENT not in applied


def test_refuses_a_missing_file_without_creating_it(tmp_path):
    missing = tmp_path / "nope.db"
    with pytest.raises(FileNotFoundError):
        open_db_for_write(missing)
    assert not missing.exists()
    assert not (tmp_path / "nope.db-wal").exists()


def test_refuses_a_file_that_is_not_a_database(tmp_path):
    junk = tmp_path / "junk.db"
    junk.write_bytes(b"this is not sqlite, it is a text file" * 100)
    with pytest.raises(SchemaMismatchError) as exc:
        open_db_for_write(junk)
    assert "cannot read the database" in str(exc.value)


def test_foreign_keys_are_enforced(path):
    db = open_db_for_write(path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            db.conn.execute(
                "INSERT INTO editorial_slot(slug, state, position, series_id) "
                "VALUES ('inicio', 'draft', 0, 'no.such.series')")
    finally:
        db.close()


def test_a_refusal_leaks_no_handle(path):
    """The refusal must close the connection: a leaked writable handle holds the WAL lock."""
    _sql(path, "DELETE FROM schema_migration WHERE version = ?", (CURRENT,))
    for _ in range(5):
        with pytest.raises(SchemaMismatchError):
            open_db_for_write(path)
    # Restore the record and write: a handle left open by a refusal would hold the lock.
    _sql(path, "INSERT INTO schema_migration(version) VALUES (?)", (CURRENT,))
    db = open_db_for_write(path)
    try:
        db.conn.execute("INSERT INTO editorial_page(slug) VALUES ('inicio')")
        assert db.conn.execute("SELECT COUNT(*) FROM editorial_page").fetchone()[0] == 1
    finally:
        db.close()
