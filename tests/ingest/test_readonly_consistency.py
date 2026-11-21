"""Backoffice review fixes on ingest.db.read_db_readonly / open_db_readonly (shared by the
backoffice and `python -m ingest status`):

- An immutable read is only trusted when no writer appeared during it (no -wal file now,
  main file stamp unchanged); otherwise the result is discarded and the read is redone
  with a freshly evaluated open. SQLite documents WRONG RESULTS (not only errors) for an
  immutable handle whose file changes underneath it.
- An immutable read ERROR is retried only when that writer evidence exists; without it the
  original error propagates. Two races in a row fail closed with a clear message.
- Minor 2: the whole read runs in one read transaction, so a multi-statement report is one
  snapshot even while a writer commits.
- Minor 3: an open failure that is not a missing schema reports the real sqlite error.
"""
import hashlib
import shutil
import sqlite3

import pytest

import ingest.db as dbmod
from ingest.db import ReadOnlyOpenError, open_db, open_db_readonly, read_db_readonly

T = "2026-11-14T00:00:00+00:00"


def _events(db) -> int:
    return db.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]


def _tree(directory):
    """Name -> (size, mtime_ns, sha256) of every file in the directory."""
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns,
                     hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(directory.iterdir()) if p.is_file()}


@pytest.fixture
def path(tmp_path):
    p = tmp_path / "p.db"
    open_db(p).close()  # writer gone: no -wal, the next read opens immutable
    assert not (tmp_path / "p.db-wal").exists()
    return p


def test_writer_starting_during_an_immutable_read_forces_a_plain_redo(path):
    seen, writer = [], []

    def read(db):
        seen.append(db.immutable)
        n = _events(db)
        if not writer:  # a writer (scheduler restart, manual CLI) starts mid-read
            w = open_db(path)
            w.add_event(T, "revision", None, {})
            writer.append(w)
        return n

    try:
        assert read_db_readonly(path, read) == 1  # the redo sees the committed event
    finally:
        for w in writer:
            w.close()
    assert seen == [True, False]


def test_immutable_read_error_retries_only_after_writer_evidence(path):
    seen, writer = [], []

    def read(db):
        seen.append(db.immutable)
        if len(seen) == 1:
            w = open_db(path)
            w.add_event(T, "revision", None, {})
            writer.append(w)
            raise sqlite3.DatabaseError("database disk image is malformed")
        return _events(db)

    try:
        assert read_db_readonly(path, read) == 1
    finally:
        for w in writer:
            w.close()
    assert seen == [True, False]


def test_immutable_read_error_without_writer_evidence_is_not_retried(path):
    seen = []

    def read(db):
        seen.append(db.immutable)
        raise sqlite3.DatabaseError("database disk image is malformed")

    with pytest.raises(sqlite3.DatabaseError, match="malformed"):
        read_db_readonly(path, read)
    assert seen == [True]


def test_writer_that_writes_and_exits_during_an_immutable_read_forces_a_redo(path):
    """No -wal left behind (the writer checkpointed and closed), but the main file changed.
    The redo opens immutable again with a fresh stamp and writes nothing."""
    seen, after_write = [], []

    def read(db):
        seen.append(db.immutable)
        n = _events(db)
        if len(seen) == 1:
            w = open_db(path)
            w.add_event(T, "revision", None, {})
            w.close()
            after_write.append(_tree(path.parent))
        return n

    assert read_db_readonly(path, read) == 1
    assert seen == [True, True]
    assert _tree(path.parent) == after_write[0]  # the redo created no sidecar


def test_two_writer_races_fail_closed_with_a_changed_during_read_error(path):
    seen = []

    def read(db):
        seen.append(db.immutable)
        n = _events(db)
        w = open_db(path)
        w.add_event(T, "revision", None, {})
        w.close()
        return n

    with pytest.raises(ReadOnlyOpenError, match="changed during the read"):
        read_db_readonly(path, read)
    assert seen == [True, True]


def test_quiet_immutable_read_is_kept(path):
    seen = []

    def read(db):
        seen.append(db.immutable)
        return _events(db)

    assert read_db_readonly(path, read) == 0
    assert seen == [True]


def test_read_runs_in_one_snapshot_while_a_writer_commits(path):
    writer = open_db(path)  # live writer: plain mode=ro
    try:
        writer.conn.execute("SELECT 1")

        def read(db):
            before = _events(db)
            writer.add_event(T, "revision", None, {})  # commits between two statements
            return before, _events(db), db.conn.in_transaction

        before, after, in_txn = read_db_readonly(path, read)
    finally:
        writer.close()
    assert in_txn is True
    assert before == after == 0


def test_ingest_status_reads_one_snapshot(path):
    """`python -m ingest status` goes through the same helper (ingest/cli.py)."""
    import inspect

    from ingest import cli
    assert "read_db_readonly(db_path, read)" in inspect.getsource(cli.main)


def test_wal_without_shm_is_refused_without_writing_even_in_a_writable_directory(tmp_path):
    """A -wal left by a killed writer, no -shm, writable directory. The reader must refuse
    before connecting: a plain mode=ro open would create the sidecars and recover them."""
    src = tmp_path / "src.db"
    w = open_db(src)
    try:
        w.add_event(T, "revision", None, {})
        assert (tmp_path / "src.db-wal").is_file()
        copy = tmp_path / "copy"
        copy.mkdir()
        shutil.copy(src, copy / "p.db")
        shutil.copy(tmp_path / "src.db-wal", copy / "p.db-wal")  # no -shm
    finally:
        w.close()
    before = _tree(copy)
    with pytest.raises(ReadOnlyOpenError, match="-shm"):
        open_db_readonly(copy / "p.db")
    with pytest.raises(ReadOnlyOpenError, match="-shm"):
        read_db_readonly(copy / "p.db", _events)
    assert _tree(copy) == before


def test_explicit_plain_read_of_a_quiet_database_creates_no_sidecars(path):
    before = _tree(path.parent)
    try:
        db = open_db_readonly(path, immutable=False)
    except ReadOnlyOpenError:
        pass  # refusing a sidecar-creating open is acceptable
    else:
        db.close()
    assert _tree(path.parent) == before


def test_symlink_with_a_live_writer_reads_the_committed_wal_rows(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    target = real / "p.db"
    open_db(target).close()  # the schema is checkpointed into the main file
    writer = open_db(target)
    try:
        writer.add_event(T, "revision", None, {})
        link = tmp_path / "link.db"
        link.symlink_to(target)
        seen = []

        def read(db):
            seen.append(db.immutable)
            return _events(db)

        assert read_db_readonly(link, read) == 1
        assert seen == [False]  # the -wal is found through the canonical target
    finally:
        writer.close()


def test_symlink_detects_a_writer_that_starts_and_exits_during_the_read(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    target = real / "p.db"
    open_db(target).close()
    link = tmp_path / "link.db"
    link.symlink_to(target)
    seen, after_write = [], []

    def read(db):
        seen.append(db.immutable)
        n = _events(db)
        if len(seen) == 1:
            w = open_db(target)
            w.add_event(T, "revision", None, {})
            w.close()
            after_write.append(_tree(real))
        return n

    assert read_db_readonly(link, read) == 1
    assert seen == [True, True]
    assert _tree(real) == after_write[0]


def test_immutable_schema_error_without_writer_evidence_is_not_retried(path, monkeypatch):
    calls = []

    def boom(conn):
        calls.append(1)
        raise sqlite3.DatabaseError("database disk image is malformed")

    monkeypatch.setattr(dbmod, "_applied_migrations", boom)
    before = _tree(path.parent)
    with pytest.raises(ReadOnlyOpenError, match="cannot open the database read-only"):
        open_db_readonly(path)
    assert calls == [1]
    assert _tree(path.parent) == before


def test_immutable_schema_error_retries_after_a_writer_appears(path, monkeypatch):
    calls, writer = [], []
    real = dbmod._applied_migrations

    def boom_once(conn):
        calls.append(1)
        if len(calls) == 1:
            w = sqlite3.connect(path, isolation_level=None)
            w.execute("PRAGMA journal_mode=WAL")
            w.execute("INSERT INTO event(ts, kind) VALUES (?, 'revision')", (T,))
            writer.append(w)
            raise sqlite3.DatabaseError("database disk image is malformed")
        return real(conn)

    monkeypatch.setattr(dbmod, "_applied_migrations", boom_once)
    try:
        db = open_db_readonly(path)
        try:
            assert db.immutable is False
            assert _events(db) == 1
        finally:
            db.close()
    finally:
        for w in writer:
            w.close()
    assert calls == [1, 1]


def test_missing_schema_still_says_not_a_prumo_database(tmp_path):
    other = tmp_path / "other.sqlite3"
    conn = sqlite3.connect(other)
    conn.execute("CREATE TABLE t(x)")
    conn.close()
    with pytest.raises(ReadOnlyOpenError, match="no schema_migration table"):
        open_db_readonly(other)


def test_a_file_that_is_not_sqlite_reports_the_sqlite_error(tmp_path):
    junk = tmp_path / "junk.sqlite3"
    junk.write_bytes(b"this is not a database at all" * 100)
    with pytest.raises(ReadOnlyOpenError) as e:
        open_db_readonly(junk)
    assert "DatabaseError" in str(e.value) and "not a database" in str(e.value)
