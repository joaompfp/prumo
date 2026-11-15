"""Migration 0015 (observation_run index) and its out-of-order application after 0017."""
import pytest

import ingest.db as dbmod
from ingest.db import MIGRATIONS_DIR, open_db, open_db_readonly


def test_per_run_read_uses_observation_run(db):
    plan = db.conn.execute(
        "EXPLAIN QUERY PLAN SELECT 1 FROM observation WHERE dataset_run_id = ?", (1,)).fetchall()
    assert any("observation_run" in r[3] for r in plan), plan


def test_0015_applies_after_0017_and_readonly_gate_accepts(tmp_path, monkeypatch):
    mig = tmp_path / "mig-without-0015"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if not f.stem.startswith("0015"):
            (mig / f.name).write_bytes(f.read_bytes())
    path = tmp_path / "old.sqlite3"
    with monkeypatch.context() as m:
        m.setattr(dbmod, "MIGRATIONS_DIR", mig)
        old = open_db(path)
        done = {r[0] for r in old.conn.execute("SELECT version FROM schema_migration")}
        old.close()
    assert any(v.startswith("0017") for v in done) and not any(v.startswith("0015") for v in done)
    with pytest.raises(dbmod.ReadOnlyOpenError):  # 0015 not applied yet: the gate refuses
        open_db_readonly(path)
    db = open_db(path)  # real migrations dir: applies the late 0015
    try:
        names = {r[1] for r in db.conn.execute("PRAGMA index_list(observation)")}
        assert "observation_run" in names
    finally:
        db.close()
    open_db_readonly(path).close()
