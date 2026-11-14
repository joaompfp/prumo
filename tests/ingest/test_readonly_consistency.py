"""Backoffice review fixes on ingest.db.read_db_readonly / open_db_readonly (shared by the
backoffice and `python -m ingest status`):

- Important 3: an immutable read is only trusted when no writer appeared during it (no -wal
  file now, main file unchanged); otherwise the result is discarded and the read is redone
  with plain mode=ro. SQLite documents WRONG RESULTS (not only errors) for an immutable
  handle whose file changes underneath it.
- Minor 2: the whole read runs in one read transaction, so a multi-statement report is one
  snapshot even while a writer commits.
- Minor 3: an open failure that is not a missing schema reports the real sqlite error.
"""
import shutil
import sqlite3

import pytest

from ingest.db import ReadOnlyOpenError, open_db, open_db_readonly, read_db_readonly

T = "2026-11-14T00:00:00+00:00"


def _events(db) -> int:
    return db.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]


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


def test_writer_that_writes_and_exits_during_an_immutable_read_forces_a_redo(path):
    """No -wal left behind (the writer checkpointed and closed), but the main file changed."""
    seen = []

    def read(db):
        seen.append(db.immutable)
        n = _events(db)
        if len(seen) == 1:
            w = open_db(path)
            w.add_event(T, "revision", None, {})
            w.close()
        return n

    assert read_db_readonly(path, read) == 1
    assert seen == [True, False]


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


def test_wal_without_shm_on_a_read_only_dir_reports_the_real_open_error(tmp_path):
    """The crash case of the review: a -wal left by a killed writer, no -shm, read-only
    directory. It is NOT 'not a Prumo database'."""
    src = tmp_path / "src.db"
    w = open_db(src)
    w.add_event(T, "revision", None, {})
    ro = tmp_path / "ro"
    ro.mkdir()
    shutil.copy(src, ro / "p.db")
    shutil.copy(tmp_path / "src.db-wal", ro / "p.db-wal")  # no -shm
    w.close()
    ro.chmod(0o555)
    try:
        with pytest.raises(ReadOnlyOpenError) as e:
            open_db_readonly(ro / "p.db")
    finally:
        ro.chmod(0o755)
    msg = str(e.value)
    assert "not a Prumo database" not in msg
    assert "cannot open" in msg and "OperationalError" in msg
    assert "-shm" in msg  # the hint for this case


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
