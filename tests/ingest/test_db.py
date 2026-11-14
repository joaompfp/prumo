import sqlite3

import pytest

from ingest.db import MIGRATIONS_DIR, open_db


def _series(db, sid="s1", frequency="A", unit="EUR"):
    c = db.conn
    c.execute("INSERT OR IGNORE INTO source(id,name,licence,licence_url,attribution,redistribution_ok)"
              " VALUES (1,'ine','CC-BY','http://l','INE',1)")
    c.execute(
        "INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,unit,active)"
        " VALUES (?,?,?,?,?,?,?,?,1)",
        (sid, 1, "gdp", "primary", "economy", "PT", frequency, unit),
    )


def _run(db, state="pending-verification"):
    cur = db.conn.execute(
        "INSERT INTO dataset_run(source_id,started_at,state) VALUES (1,'2026-01-01',?)", (state,))
    return cur.lastrowid


def _raw(db):
    cur = db.conn.execute(
        "INSERT INTO raw_fetch(source_id,url,fetched_at,http_status,sha256,path,bytes,ok)"
        " VALUES (1,'http://x','2026-01-01',200,'abc','p',1,1)")
    return cur.lastrowid


def _obs(db, run, raw, period="2025", value=1.0, series="s1", kind="fetched"):
    return db.conn.execute(
        "INSERT INTO observation(series_id,period,value_text,value,kind,dataset_run_id,raw_fetch_id,fetched_at)"
        " VALUES (?,?,?,?,?,?,?,'2026-01-01T00:00:00+00:00')",
        (series, period, str(value), value, kind, run, raw),
    ).lastrowid


def _served(db):
    return db.conn.execute("SELECT series_id,period,value FROM served_observation").fetchall()


def test_open_applies_migrations_once(tmp_path):
    p = tmp_path / "a.db"
    open_db(p).close()
    d = open_db(p)
    rows = d.conn.execute("SELECT version FROM schema_migration").fetchall()
    assert sorted(r[0] for r in rows) == sorted(f.stem for f in MIGRATIONS_DIR.glob("[0-9]*.sql"))
    assert len(rows) >= 2
    assert d.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert d.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_rejects_null_value(db):
    _series(db)
    run, raw = _run(db), _raw(db)
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute(
            "INSERT INTO observation(series_id,period,value,kind,dataset_run_id,raw_fetch_id,fetched_at)"
            " VALUES ('s1','2025',NULL,'fetched',?,?,'t')", (run, raw))


def test_rejects_empty_unit(db):
    with pytest.raises(sqlite3.IntegrityError):
        _series(db, unit="  ")


def test_rejects_bad_period_format(db):
    _series(db)
    run, raw = _run(db), _raw(db)
    with pytest.raises(sqlite3.IntegrityError):
        _obs(db, run, raw, period="Setembro de 2025")


def test_frequency_mismatch_rejected(db):
    _series(db, frequency="Q")
    run, raw = _run(db), _raw(db)
    with pytest.raises(sqlite3.IntegrityError):
        _obs(db, run, raw, period="2025")
    with pytest.raises(sqlite3.IntegrityError):
        _obs(db, run, raw, period="2025-Q5")
    _obs(db, run, raw, period="2025-Q4")


def test_fetched_observation_requires_raw_fetch(db):
    _series(db)
    run = _run(db)
    with pytest.raises(sqlite3.IntegrityError):
        _obs(db, run, None, kind="fetched")
    _obs(db, run, None, kind="legacy-unverified")


def test_duplicate_series_period_raw_rejected(db):
    _series(db)
    run, raw = _run(db), _raw(db)
    _obs(db, run, raw)
    with pytest.raises(sqlite3.IntegrityError):
        _obs(db, run, raw)


def test_served_view_excludes_unverified_runs(db):
    _series(db)
    run, raw = _run(db, "pending-verification"), _raw(db)
    _obs(db, run, raw)
    assert _served(db) == []
    db.conn.execute("UPDATE dataset_run SET state='verified' WHERE id=?", (run,))
    assert len(_served(db)) == 1


def test_served_view_returns_latest_vintage_only(db):
    _series(db)
    r1, f1 = _run(db, "verified"), _raw(db)
    _obs(db, r1, f1, value=1.0)
    r2, f2 = _run(db, "verified"), _raw(db)
    _obs(db, r2, f2, value=2.0)
    r3, f3 = _run(db, "failed-verification"), _raw(db)
    _obs(db, r3, f3, value=3.0)
    assert _served(db) == [("s1", "2025", 2.0)]



def test_legacy_never_hides_verified_fetched(db):
    _series(db, "Z")
    r1, f1 = _run(db, "verified"), _raw(db)
    _obs(db, r1, f1, period="2020", value=1.0, series="Z")
    r2 = _run(db, "verified")
    _obs(db, r2, None, period="2020", value=7.0, series="Z", kind="legacy-unverified")
    db.conn.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")
    assert _served(db) == [("Z", "2020", 1.0)]


def test_legacy_served_when_enabled_and_no_fetched(db):
    _series(db)
    run = _run(db, "verified")
    _obs(db, run, None, value=7.0, kind="legacy-unverified")
    db.conn.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")
    assert _served(db) == [("s1", "2025", 7.0)]


def test_legacy_hidden_when_setting_off(db):
    _series(db)
    run = _run(db, "verified")
    _obs(db, run, None, kind="legacy-unverified")
    assert _served(db) == []


def test_legacy_in_pending_run_hidden_even_when_enabled(db):
    _series(db)
    run = _run(db, "pending-verification")
    _obs(db, run, None, kind="legacy-unverified")
    db.conn.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")
    assert _served(db) == []


@pytest.mark.parametrize("vt", ["NULL", "''"])
def test_rejects_null_or_empty_value_text(db, vt):
    _series(db)
    run, raw = _run(db), _raw(db)
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute(
            "INSERT INTO observation(series_id,period,value_text,value,kind,dataset_run_id,raw_fetch_id,fetched_at)"
            f" VALUES ('s1','2025',{vt},1.0,'fetched',?,?,'t')", (run, raw))


def test_0002_adds_dataset_key_and_raw_fetch_run_link(db):
    cols = {r[1] for r in db.conn.execute("PRAGMA table_info(dataset_run)")}
    assert "dataset_key" in cols
    cols = {r[1] for r in db.conn.execute("PRAGMA table_info(raw_fetch)")}
    assert "dataset_run_id" in cols
