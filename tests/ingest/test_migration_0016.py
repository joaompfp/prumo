"""Migration 0016: the derived data layer carries codes only (reader text lives in presentation/).

- existing derived history (series ids, observations, events) survives the reshaping untouched;
- `unit` becomes a closed code ('%' -> pct, 'p.p.' -> pp, 'balance', 'index 2015=100' ->
  index_2015_100), refused by the model and by the schema otherwise;
- `served_derived` loses formula_label_pt / label and serves the publisher's attribution only;
- after syncing the real registry, no derived_series / served_derived value is prose.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import ingest.db as dbmod
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.derive import run_derive
from ingest.models import DERIVED_UNITS, DerivedSpec
from ingest.registry import load_derived, load_registry, sync_derived, sync_registry
from tests.ingest.derived_helpers import verified_values
from tests.ingest.fakes import spec

CORE = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
T1 = "2026-11-01T00:00:00+00:00"
NOW = "2026-11-14T00:00:00+00:00"
OLD_UNITS = {"derived.a": ("%", "pct"), "derived.b": ("p.p.", "pp"),
             "derived.c": ("balance", "balance"), "derived.d": ("index 2015=100",
                                                                "index_2015_100")}


def _migrations_before_0016(tmp_path):
    mig = tmp_path / "mig-pre-0016"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem[:4] < "0016":
            (mig / f.name).write_bytes(f.read_bytes())
    return mig


def _old_shape_db(tmp_path, monkeypatch):
    """A database at the deployed (pre-0016) schema with derived history written through the
    old column set: four series (one per old unit text), one served row and one event."""
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", _migrations_before_0016(tmp_path))
    path = tmp_path / "old.sqlite3"
    db = open_db(path)
    sync_registry(db, [spec("s1", frequency="M")])
    verified_values(db, "s1", {"2024-12": "100", "2025-01": "102"}, T1, "k1")
    for key, (unit, _) in OLD_UNITS.items():
        db.conn.execute(
            "INSERT INTO derived_series(key, formula, base_series_id, params_json, label, "
            "formula_label_pt, unit, active) VALUES (?, 'period_change', 's1', '{}', "
            "'Variação', 'Variação face ao período anterior (diferença), calculada pelo Prumo "
            "a partir de s1', ?, 1)", (key, unit))
    dsid = db.conn.execute("SELECT id FROM derived_series WHERE key = 'derived.a'").fetchone()[0]
    inputs = db.served_fetched_inputs("s1")
    ids = [inputs["2025-01"][0], inputs["2024-12"][0]]
    run = db.begin_derived_run(NOW, "cli", ["derived.a"])
    db.write_derived_observations(run, NOW, [(dsid, "2025-01", "2", 0, json.dumps(ids))])
    oid = db.derived_observations_of_run(run)[0]["id"]
    db.set_derived_row_states([(oid, "match")])
    db.add_derived_event(NOW, run, dsid, "2024-12", "zero_denominator")
    db.finish_derived_run(run, "verified", NOW, n_written=1, n_checked=1, n_mismatch=0)
    db.close()
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)
    return path


def _dump(conn, table):
    return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()


def test_migration_0016_keeps_data(tmp_path, monkeypatch):
    path = _old_shape_db(tmp_path, monkeypatch)
    old = sqlite3.connect(path)
    before = {t: _dump(old, t) for t in ("derived_observation", "derived_event", "derived_run")}
    ids_before = dict(old.execute("SELECT key, id FROM derived_series").fetchall())
    served_before = old.execute("SELECT derived_key, period, value_text, attribution "
                                "FROM served_derived").fetchall()
    old.close()
    assert len(served_before) == 1 and "Calculado" in served_before[0][3]

    db = open_db(path)
    c = db.conn
    assert {t: _dump(c, t) for t in before} == before
    assert dict(c.execute("SELECT key, id FROM derived_series").fetchall()) == ids_before
    assert dict(c.execute("SELECT key, unit FROM derived_series").fetchall()) == {
        k: new for k, (_, new) in OLD_UNITS.items()}
    cols = {r[1] for r in c.execute("PRAGMA table_info(derived_series)")}
    assert not {"label", "formula_label_pt"} & cols
    view_cols = {r[1] for r in c.execute("PRAGMA table_info(served_derived)")}
    assert not {"label", "formula_label_pt"} & view_cols
    served = c.execute("SELECT derived_key, period, value_text, unit, attribution "
                       "FROM served_derived").fetchall()
    assert served == [("derived.a", "2025-01", "2", "pct", "Fake")]
    assert c.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert c.execute("PRAGMA foreign_key_check").fetchall() == []
    # the 0014 guards are back on the rebuilt table
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE derived_series SET formula = 'yoy_change' WHERE key = 'derived.a'")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("DELETE FROM derived_series")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT OR REPLACE INTO derived_series(key, formula, base_series_id, unit, "
                  "active) VALUES ('derived.a', 'yoy_change', 's1', 'pct', 1)")
    with pytest.raises(sqlite3.IntegrityError):  # unit is a closed code list in the schema too
        c.execute("INSERT INTO derived_series(key, formula, base_series_id, unit, active) "
                  "VALUES ('derived.z', 'yoy_change', 's1', '%', 1)")
    db.close()


def test_derived_spec_rejects_unknown_unit():
    assert DERIVED_UNITS == ("pct", "pp", "balance", "index_2015_100")
    for unit in DERIVED_UNITS:
        assert DerivedSpec(key="derived.a", base="s1", formula="yoy_change", unit=unit).unit == unit
    for bad in ("%", "p.p.", "EUR", ""):
        with pytest.raises(ValidationError):
            DerivedSpec(key="derived.a", base="s1", formula="yoy_change", unit=bad)
    with pytest.raises(ValidationError):  # reader text is not a registry field any more
        DerivedSpec(key="derived.a", base="s1", formula="yoy_change", unit="pp", label="x")


def test_data_layer_has_no_portuguese_prose(tmp_path):
    specs = load_registry(CORE)
    derived = load_derived(CORE, specs)
    assert len(derived) == 23
    db = open_db(tmp_path / "p.sqlite3")
    try:
        sync_registry(db, specs)
        sync_derived(db, derived)
        # one verified base value so served_derived has rows and the ASCII scan covers the view
        base = next(d.base for d in derived if d.formula == "period_change")
        source = next(sp.source.name for sp in specs if sp.id == base)
        verified_values(db, base, {"2024-12": "100", "2025-01": "102"}, T1, "k1", source=source)
        run_derive(db, keys=[next(d.key for d in derived if d.base == base
                                  and d.formula == "period_change")],
                   trigger="cli", now=lambda: datetime.fromisoformat(NOW))
        rows = db.conn.execute("SELECT * FROM derived_series").fetchall()
        assert len(rows) == 23
        served = db.conn.execute("SELECT * FROM served_derived").fetchall()
        assert served, "the scan must see at least one served row"
        publisher_text = {"attribution", "licence", "licence_url"}  # the publisher's own words
        cur = db.conn.execute("SELECT * FROM served_derived")
        served_cols = [c[0] for c in cur.description]
        series_cols = [c[1] for c in db.conn.execute("PRAGMA table_info(derived_series)")]
        for cols, table in ((series_cols, rows), (served_cols, served)):
            for row in table:
                for k, v in zip(cols, row):
                    assert k in publisher_text or not isinstance(v, str) or v.isascii(), (k, row)
        assert {r["unit"] for r in db.derived_series_rows()} <= set(DERIVED_UNITS)
    finally:
        db.close()
