"""Migration 0006 (PT15M quarter-hourly frequency): schema extension must be additive and safe
on a POPULATED 0005 database - observations, raw provenance, verification rows, the served view
and the licence gate all preserved; existing A/S/Q/M/D enforcement unchanged; repeated open
idempotent (Task 16).
"""
import sqlite3

import pytest

import ingest.db as dbmod
from ingest.db import MIGRATIONS_DIR, open_db

PT15M_SERIES = {
    "id": "eredes.production_total.PT",
    "period": "2026-11-10T23:45:00+00:00",
}


def _migrations_up_to_0005(tmp_path):
    """A migrations directory holding exactly 0001..0005 (0006 filtered out)."""
    mig5 = tmp_path / "mig5"
    mig5.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem < "0006":
            (mig5 / f.name).write_bytes(f.read_bytes())
    return mig5


def _populate_0005(db):
    c = db.conn
    c.execute("INSERT INTO source(id,name,licence,licence_url,attribution,redistribution_ok)"
              " VALUES (1,'ine','CC-BY','http://l','INE',1),(2,'blocked','L','http://l','X',0)")
    c.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,"
              "unit,active) VALUES ('ine.gdp.PT',1,'gdp','primary','economy','PT','A','EUR',1)")
    c.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,"
              "unit,active) VALUES ('bl.x.PT',2,'x','primary','economy','PT','D','n',1)")
    c.execute("INSERT INTO dataset_run(source_id,started_at,finished_at,state,dataset_key)"
              " VALUES (1,'2026-01-01','2026-01-01','verified','k1')")
    c.execute("INSERT INTO dataset_run(source_id,started_at,finished_at,state,dataset_key)"
              " VALUES (2,'2026-01-02','2026-01-02','verified','k2')")
    c.execute("INSERT INTO raw_fetch(source_id,dataset_run_id,url,fetched_at,http_status,"
              "sha256,path,bytes,ok) VALUES (1,1,'http://x','2026-01-01',200,'a','p',3,1)")
    c.execute("INSERT INTO observation(series_id,period,value_text,value,kind,dataset_run_id,"
              "raw_fetch_id,fetched_at) VALUES ('ine.gdp.PT','2025','1.5',1.5,'fetched',1,1,"
              "'2026-01-01')")
    c.execute("INSERT INTO observation(series_id,period,value_text,value,kind,dataset_run_id,"
              "raw_fetch_id,fetched_at) VALUES ('bl.x.PT','2026-01-01','9',9.0,"
              "'legacy-unverified',2,NULL,'2026-01-02')")
    c.execute("INSERT INTO verification(dataset_run_id,seed,sample_size,passed,created_at)"
              " VALUES (1,7,1,1,'2026-01-01')")
    c.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")


def test_0006_fresh_db_accepts_pt15m(db):
    assert any(v.startswith("0006") for (v,) in
               db.conn.execute("SELECT version FROM schema_migration").fetchall())
    c = db.conn
    c.execute("INSERT INTO source(id,name,licence,licence_url,attribution,redistribution_ok)"
              " VALUES (1,'eredes','CC BY 4.0','http://l','E-REDES',1)")
    c.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,"
              "unit,active) VALUES (?,?,?,?,?,?,'PT15M','kWh',1)",
              (PT15M_SERIES["id"], 1, "k", "primary", "energy", "PT"))
    rid = c.execute("INSERT INTO dataset_run(source_id,started_at,state) "
                    "VALUES (1,'2026-11-12','verified')").lastrowid
    fid = c.execute("INSERT INTO raw_fetch(source_id,url,fetched_at,http_status,sha256,path,"
                    "bytes,ok) VALUES (1,'http://x','2026-11-12',200,'a','p',1,1)").lastrowid
    c.execute("INSERT INTO observation(series_id,period,value_text,value,kind,dataset_run_id,"
              "raw_fetch_id,fetched_at) VALUES (?,?,?,?,'fetched',?,?,'2026-11-12')",
              (PT15M_SERIES["id"], PT15M_SERIES["period"], "1459190.0", 1459190.0, rid, fid))
    # bad PT15M spellings / non-quarter minutes are still rejected
    for bad in ("2026-11-10T23:46:00+00:00", "2026-11-10T23:45:01+00:00",
                "2026-11-10T23:45:00Z", "2026-13-10T23:45:00+00:00",
                "2026-11-10T23:45:00+01:00", "2026-11-10"):
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO observation(series_id,period,value_text,value,kind,"
                      "dataset_run_id,raw_fetch_id,fetched_at) VALUES (?,?,?,1,'fetched',?,?,"
                      "'t')", (PT15M_SERIES["id"], bad, "1", rid, fid))
    # update trigger enforces too
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE observation SET period='2026-11-10T23:45:00' WHERE series_id=?",
                  (PT15M_SERIES["id"],))
    # A-series enforcement unchanged (pre-PT15M rules still live in the same triggers)
    c.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,"
              "unit,active) VALUES ('a1',1,'a','primary','economy','PT','A','EUR',1)")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO observation(series_id,period,value_text,value,kind,"
                  "dataset_run_id,raw_fetch_id,fetched_at) VALUES ('a1','2025-09',1,1,"
                  "'fetched',?,?,'t')", (rid, fid))


def test_0006_upgrades_populated_0005_and_preserves_everything(tmp_path, monkeypatch):
    mig5 = _migrations_up_to_0005(tmp_path)
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", mig5)
    p = tmp_path / "old.db"
    d = open_db(p)
    assert not [v for (v,) in d.conn.execute("SELECT version FROM schema_migration")
                if v.startswith("0006")]
    _populate_0005(d)
    d.close()

    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)  # real set incl. 0006
    d = open_db(p)
    assert any(v.startswith("0006") for (v,) in
               d.conn.execute("SELECT version FROM schema_migration"))
    preserved = {
        "observation": d.conn.execute("SELECT series_id, period, value_text FROM observation"
                                      " ORDER BY id").fetchall(),
        "raw_fetch": d.conn.execute("SELECT url, sha256 FROM raw_fetch").fetchall(),
        "verification": d.conn.execute("SELECT seed, sample_size, passed FROM verification")
                          .fetchall(),
        "setting": d.conn.execute("SELECT key, value FROM setting").fetchall(),
    }
    assert preserved["observation"] == [("ine.gdp.PT", "2025", "1.5"),
                                        ("bl.x.PT", "2026-01-01", "9")]
    assert preserved["verification"] == [(7, 1, 1)]
    assert preserved["setting"] == [("legacy_served", "1")]
    # served view + licence gate intact: ine (redistribution_ok=1) serves, blocked serves 0
    assert d.conn.execute(
        "SELECT series_id, period, value_text FROM served_observation ORDER BY series_id"
    ).fetchall() == [("ine.gdp.PT", "2025", "1.5")]
    # foreign keys still enforced after the series rebuild
    assert d.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        d.conn.execute("INSERT INTO observation(series_id,period,value_text,value,kind,"
                       "dataset_run_id,raw_fetch_id,fetched_at) VALUES ('ghost','2025','1',1,"
                       "'legacy-unverified',2,NULL,'t')")
    with pytest.raises(sqlite3.IntegrityError):
        d.conn.execute("DELETE FROM series WHERE id='ine.gdp.PT'")
    # PT15M usable on the migrated database
    d.conn.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,"
                   "frequency,unit,active) VALUES ('e.total.PT',1,'et','primary','energy','PT'"
                   ",'PT15M','kWh',1)")
    d.conn.execute("INSERT INTO observation(series_id,period,value_text,value,kind,"
                   "dataset_run_id,raw_fetch_id,fetched_at) VALUES ('e.total.PT',"
                   "'2026-11-10T23:45:00+00:00','5',5,'legacy-unverified',1,NULL,'t')")
    d.close()
    # repeated open is idempotent and keeps everything
    d = open_db(p)
    assert any(v.startswith("0006") for (v,) in
               d.conn.execute("SELECT version FROM schema_migration"))
    assert d.conn.execute("SELECT COUNT(*) FROM observation").fetchone()[0] == 3
    d.close()


# --- Common migrator atomicity (Task 16 spec review R1) ----------------------------------------


def _migrations_plus_bad(tmp_path):
    """The real migrations plus a synthetic 0007 that breaks a foreign key invisibly to the
    triggers (child row pointing at a nonexistent source, allowed only under FK OFF) - exactly
    the failure the common migrator's integrity check exists to catch."""
    mig = tmp_path / "mig7"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        (mig / f.name).write_bytes(f.read_bytes())
    (mig / "0007_bad.sql").write_text(
        "INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,"
        "unit,active) VALUES ('ghost.PT',999,'x','primary','economy','PT','A','n',1);\n")
    return mig


def test_bad_migration_rolls_back_atomically_no_corrupt_applied_version(tmp_path, monkeypatch):
    """R1: a migration that breaks foreign keys must fail INSIDE its own transaction, so
    neither the corrupt row nor its schema_migration record survives the failed open."""
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", _migrations_plus_bad(tmp_path))
    p = tmp_path / "probe.db"
    with pytest.raises(RuntimeError, match="foreign key violations"):
        open_db(p)
    raw = sqlite3.connect(p)  # side-channel inspection, no migrator involved
    try:
        applied = {r[0].split("_")[0]
                   for r in raw.execute("SELECT version FROM schema_migration")}
        assert applied == {"0001", "0002", "0003", "0004", "0005", "0006"}
        assert raw.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 0
    finally:
        raw.close()
    # Repeated open does not skip a recorded corrupt migration (none was recorded): it fails
    # again, and succeeds cleanly once the offending file is removed.
    with pytest.raises(RuntimeError, match="foreign key violations"):
        open_db(p)
    (tmp_path / "mig7" / "0007_bad.sql").unlink()
    d = open_db(p)
    assert d.conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 0
    d.close()


def test_open_rejects_preexisting_corruption_with_no_pending_migrations(tmp_path):
    """R1: corruption committed by the old non-atomic migrator (bad row + recorded version)
    is never silently accepted on a subsequent open with nothing pending - the check runs
    on every open."""
    p = tmp_path / "corrupt.db"
    open_db(p).close()
    raw = sqlite3.connect(p)
    raw.execute("PRAGMA foreign_keys=OFF")
    raw.execute("INSERT INTO series(id,source_id,indicator_key,role,theme,geography,frequency,"
                "unit,active) VALUES ('ghost.PT',999,'x','primary','economy','PT','A','n',1)")
    raw.execute("INSERT INTO schema_migration(version) VALUES ('0007_bad')")
    raw.commit()
    raw.close()
    with pytest.raises(RuntimeError, match="foreign key violations"):
        open_db(p)
    with pytest.raises(RuntimeError, match="foreign key violations"):  # repeatable, not one-shot
        open_db(p)
