"""Calculated-rate caveats (spec Decision 2): codes in the data layer, sentences in presentation.

- registry keys carry exactly the agreed caveat codes (six `sa_base`, three `stock_base`);
- an unknown code is refused; the sync stores sorted codes and exposes them as a list;
- migration 0017 keeps derived history, defaults existing rows to `[]` and serves `caveats`;
- the reader sentences claim nothing about the publisher's methodology.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import ingest.db as dbmod
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.models import DERIVED_CAVEATS, DerivedSpec
from ingest.registry import load_derived, load_registry, sync_derived, sync_registry
from presentation import caveat_text
from tests.ingest.derived_helpers import verified_values
from tests.ingest.fakes import spec

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "registry" / "core.yaml"
PROPOSED = ROOT / "registry" / "core.proposed.yaml"
T1 = "2026-11-01T00:00:00+00:00"
NOW = "2026-11-14T00:00:00+00:00"

SA = [f"derived.ipi_seasonal_cae_{c}.PT.yoy_change_pct" for c in ("TOT", "B", "C", "D", "E")] + [
    "derived.ipi_seasonal_cae_TOT.PT.period_change_pct"]
STOCK = ["derived.credit_housing.PT.yoy_change_pct", "derived.credit_consumer.PT.yoy_change_pct",
         "derived.deposits_households.PT.yoy_change_pct"]


def _dspec(**kw):
    return DerivedSpec(key="derived.a", base="s1", formula="yoy_change", unit="pp", **kw)


def test_registry_caveat_mapping_is_exact():
    derived = load_derived(CORE, load_registry(CORE))
    assert len(derived) == 23
    got = {d.key: d.caveats for d in derived}
    for k in SA:
        assert got[k] == ["sa_base"], k
    for k in STOCK:
        assert got[k] == ["stock_base"], k
    assert all(v == [] for k, v in got.items() if k not in SA + STOCK)
    assert CORE.read_bytes() == PROPOSED.read_bytes()


def test_spec_caveats_closed_list():
    assert DERIVED_CAVEATS == ("sa_base", "stock_base")
    assert _dspec().caveats == []
    assert _dspec(caveats=["sa_base"]).caveats == ["sa_base"]
    with pytest.raises(ValidationError):
        _dspec(caveats=["nope"])


def test_sync_stores_sorted_codes_and_reads_a_list(tmp_path):
    db = open_db(tmp_path / "c.sqlite3")
    try:
        sync_registry(db, [spec("s1", frequency="M")])
        sync_derived(db, [_dspec(caveats=["stock_base", "sa_base"]),
                          DerivedSpec(key="derived.b", base="s1", formula="yoy_change",
                                      unit="pp")])
        rows = {r["key"]: r["caveats"] for r in db.derived_series_rows()}
        assert rows == {"derived.a": ["sa_base", "stock_base"], "derived.b": []}
        stored = db.conn.execute("SELECT caveats_json FROM derived_series WHERE key = 'derived.a'"
                                 ).fetchone()[0]
        assert stored == '["sa_base", "stock_base"]'
        # caveats are a mutable field: a later sync changes them in place
        sync_derived(db, [_dspec(), DerivedSpec(key="derived.b", base="s1",
                                                formula="yoy_change", unit="pp")])
        assert {r["key"]: r["caveats"] for r in db.derived_series_rows()} == {
            "derived.a": [], "derived.b": []}
    finally:
        db.close()


def test_served_rows_carry_caveats(tmp_path):
    db = open_db(tmp_path / "s.sqlite3")
    try:
        sync_registry(db, [spec("s1", frequency="M")])
        verified_values(db, "s1", {"2024-12": "100", "2025-01": "102"}, T1, "k1")
        sync_derived(db, [DerivedSpec(key="derived.a", base="s1", formula="period_change",
                                      unit="pp", caveats=["sa_base"])])
        from ingest.derive import run_derive
        run_derive(db, keys=["derived.a"], trigger="cli", now=lambda: datetime.fromisoformat(NOW))
        total, rows = db.served_derived_rows("derived.a", 10)
        assert total == 1 and rows[0]["caveats"] == ["sa_base"]
    finally:
        db.close()


def _pre_0017(tmp_path):
    mig = tmp_path / "mig-pre-0017"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem[:4] < "0017":
            (mig / f.name).write_bytes(f.read_bytes())
    return mig


def test_migration_0017_keeps_data_and_defaults_to_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", _pre_0017(tmp_path))
    path = tmp_path / "old.sqlite3"
    db = open_db(path)
    sync_registry(db, [spec("s1", frequency="M")])
    verified_values(db, "s1", {"2024-12": "100", "2025-01": "102"}, T1, "k1")
    for n in range(23):
        db.conn.execute("INSERT INTO derived_series(key, formula, base_series_id, params_json, "
                        "unit, active) VALUES (?, 'period_change', 's1', '{}', 'pp', 1)",
                        (f"derived.k{n:02d}",))
    dsid = db.conn.execute("SELECT id FROM derived_series WHERE key = 'derived.k00'"
                           ).fetchone()[0]
    inputs = db.served_fetched_inputs("s1")
    ids = [inputs["2025-01"][0], inputs["2024-12"][0]]
    run = db.begin_derived_run(NOW, "cli", ["derived.k00"])
    db.write_derived_observations(run, NOW, [(dsid, "2025-01", "2", 0, json.dumps(ids))])
    oid = db.derived_observations_of_run(run)[0]["id"]
    db.set_derived_row_states([(oid, "match")])
    db.finish_derived_run(run, "verified", NOW, n_written=1, n_checked=1, n_mismatch=0)
    db.close()
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)

    old = sqlite3.connect(path)
    ids_before = dict(old.execute("SELECT key, id FROM derived_series").fetchall())
    obs_before = old.execute("SELECT * FROM derived_observation ORDER BY id").fetchall()
    old.close()
    assert len(ids_before) == 23

    db = open_db(path)
    c = db.conn
    assert dict(c.execute("SELECT key, id FROM derived_series").fetchall()) == ids_before
    assert c.execute("SELECT * FROM derived_observation ORDER BY id").fetchall() == obs_before
    assert {r[0] for r in c.execute("SELECT caveats_json FROM derived_series")} == {"[]"}
    assert "caveats" in {r[1] for r in c.execute("PRAGMA table_info(served_derived)")}
    assert c.execute("SELECT derived_key, value_text, caveats FROM served_derived").fetchall() \
        == [("derived.k00", "2", "[]")]
    assert c.execute("PRAGMA foreign_key_check").fetchall() == []
    # the 0014 guards survive: the definition is still immutable, caveats are not
    c.execute("UPDATE derived_series SET caveats_json = '[\"sa_base\"]' WHERE key = 'derived.k00'")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE derived_series SET formula = 'yoy_change' WHERE key = 'derived.k00'")
    db.close()


def test_caveat_wording_claims_nothing_about_the_publisher_method():
    for lang, official in (("pt", "não é a taxa oficial do editor"),
                           ("en", "not the publisher's official rate")):
        for code in DERIVED_CAVEATS:
            text = caveat_text(lang, code)
            assert "Prumo" in text and official in text
            low = text.lower()
            for claim in ("o ine calcula", "o banco de portugal calcula", "the publisher calculates",
                          "statistics portugal calculates"):
                assert claim not in low
