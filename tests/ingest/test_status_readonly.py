"""Read-only CLI reports (Task 23, D-I2): `status` and `lag` open the system of record with
sqlite `mode=ro`, never migrate, never create a database file, refuse a missing file and a
schema older or newer than this code, and find the DB through PRUMO_DB_PATH like the image
and scheduler (PRUMO_DB is a deprecated fallback)."""
import hashlib
import shutil
import sqlite3

import pytest

import ingest.db as dbmod
from ingest.cli import main
from ingest.db import MIGRATIONS_DIR, ReadOnlyOpenError, open_db, open_db_readonly
from ingest.models import SeriesSpec, SourceSpec
from tests.ingest.test_cli import _write_registry

WB = SourceSpec(name="worldbank", licence="CC BY 4.0", licence_url="http://l",
                attribution="WB", redistribution_ok=True, verifiable=True)
SPEC = SeriesSpec(id="worldbank.gdp.PT", source=WB, indicator_key="gdp", role="primary",
                  theme="economy", geography="PT", frequency="A", unit="u",
                  native_code="NY.GDP.MKTP.KD.ZG:PRT")


@pytest.fixture
def reg(tmp_path):
    return _write_registry(tmp_path / "core.yaml", [SPEC])


def _snapshot(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.iterdir()) if p.is_file()}


def _db_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    open_db(d / "prumo.sqlite3").close()   # a fully migrated, cleanly closed WAL database
    return d


@pytest.mark.parametrize("command", [["status"], ["status", "--json"], ["lag"]])
def test_missing_db_is_refused_with_exit_2_and_nothing_is_created(tmp_path, reg, capsys,
                                                                  command):
    missing = tmp_path / "typo" / "prumo.sqlite3"
    rc = main(["--db", str(missing), "--registry", str(reg), *command])
    assert rc == 2
    assert "database not found" in capsys.readouterr().err
    assert not missing.exists() and not missing.parent.exists()


@pytest.mark.parametrize("command", [["status"], ["lag"]])
def test_report_never_writes_or_creates_files(tmp_path, reg, command):
    d = _db_dir(tmp_path)
    before = _snapshot(d)
    main(["--db", str(d / "prumo.sqlite3"), "--registry", str(reg), *command])
    assert _snapshot(d) == before            # no -wal/-shm sidecar, no byte changed


def test_report_reads_alongside_an_open_writer(tmp_path, reg, capsys):
    d = _db_dir(tmp_path)
    writer = open_db(d / "prumo.sqlite3")   # the running scheduler holds -wal/-shm
    try:
        writer.conn.execute("SELECT 1")
        assert main(["--db", str(d / "prumo.sqlite3"), "--registry", str(reg), "status"]) == 0
    finally:
        writer.close()
    assert "worldbank" in capsys.readouterr().out


def test_read_only_handle_refuses_writes(tmp_path):
    d = _db_dir(tmp_path)
    db = open_db_readonly(d / "prumo.sqlite3")
    try:
        with pytest.raises(sqlite3.OperationalError):
            db.conn.execute("INSERT INTO schema_migration(version) VALUES ('x')")
    finally:
        db.close()


def test_older_schema_is_refused_without_migrating(tmp_path, reg, capsys, monkeypatch):
    old = tmp_path / "old-migrations"
    old.mkdir()
    stems = sorted(f.name for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"))
    for name in stems[:-1]:
        shutil.copy(MIGRATIONS_DIR / name, old / name)
    path = tmp_path / "old.sqlite3"
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", old)
    open_db(path).close()
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)
    rc = main(["--db", str(path), "--registry", str(reg), "status"])
    err = capsys.readouterr().err
    assert rc == 2 and "older than this code" in err and stems[-1][:-4] in err
    conn = sqlite3.connect(path)
    try:  # nothing was applied by the read-only report
        assert len(conn.execute("SELECT * FROM schema_migration").fetchall()) == len(stems) - 1
    finally:
        conn.close()


def test_newer_schema_is_refused(tmp_path, reg, capsys):
    d = _db_dir(tmp_path)
    conn = sqlite3.connect(d / "prumo.sqlite3")
    conn.execute("INSERT INTO schema_migration(version) VALUES ('9999_from_the_future')")
    conn.commit()
    conn.close()
    rc = main(["--db", str(d / "prumo.sqlite3"), "--registry", str(reg), "status"])
    err = capsys.readouterr().err
    assert rc == 2 and "newer than this code" in err and "9999_from_the_future" in err


def test_a_file_without_prumo_schema_is_refused(tmp_path, reg, capsys):
    other = tmp_path / "other.sqlite3"
    conn = sqlite3.connect(other)
    conn.execute("CREATE TABLE t(x)")
    conn.close()
    assert main(["--db", str(other), "--registry", str(reg), "status"]) == 2
    assert "no schema_migration table" in capsys.readouterr().err
    with pytest.raises(ReadOnlyOpenError):
        open_db_readonly(other)


def test_cli_reads_prumo_db_path_like_the_image_and_scheduler(tmp_path, reg, monkeypatch,
                                                              capsys):
    d = _db_dir(tmp_path)
    monkeypatch.setenv("PRUMO_DB_PATH", str(d / "prumo.sqlite3"))
    monkeypatch.setenv("PRUMO_DB", str(tmp_path / "wrong.sqlite3"))
    assert main(["--registry", str(reg), "status"]) == 0
    assert not (tmp_path / "wrong.sqlite3").exists()
    capsys.readouterr()


def test_cli_falls_back_to_deprecated_prumo_db(tmp_path, reg, monkeypatch):
    d = _db_dir(tmp_path)
    monkeypatch.delenv("PRUMO_DB_PATH", raising=False)
    monkeypatch.setenv("PRUMO_DB", str(d / "prumo.sqlite3"))
    assert main(["--registry", str(reg), "status"]) == 0
