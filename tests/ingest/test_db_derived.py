"""Task 2 (derived layer v1): migration 0014, Db derived functions, the `served_derived` view."""
import json
import sqlite3

import pytest

import ingest.db as dbmod
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.derive import formula_label_pt
from ingest.models import FORMULAS, Observation, SourceSpec
from ingest.registry import sync_derived, sync_registry
from tests.ingest.derived_helpers import derived_spec, verified_values
from tests.ingest.fakes import SOURCE, spec

T1 = "2026-11-01T00:00:00+00:00"
T2 = "2026-11-02T00:00:00+00:00"
T3 = "2026-11-03T00:00:00+00:00"
NOW = "2026-11-14T00:00:00+00:00"
KEY = "derived.s1_pc"
NEW_TABLES = ("derived_series", "derived_run", "derived_observation", "derived_event")


def _setup(db, values=None, *, fetched_at=T1, run_key="k1"):
    sync_registry(db, [spec("s1", frequency="M")])
    run = verified_values(db, "s1", values or {"2024-12": "100", "2025-01": "102"},
                          fetched_at, run_key)
    sync_derived(db, [derived_spec(KEY, "s1", "period_change")])
    return run


def _dsid(db, key=KEY):
    return next(r["id"] for r in db.derived_series_rows(active_only=False) if r["key"] == key)


def _derive(db, period="2025-01", prev="2024-12", value="2", *, state="match",
            run_state="verified", key=KEY):
    """One derived row over the currently served inputs (period, prev), through Db."""
    inputs = db.served_fetched_inputs("s1")
    ids = [inputs[period][0], inputs[prev][0]]
    run = db.begin_derived_run(NOW, "cli", [key])
    db.write_derived_observations(run, NOW, [(_dsid(db, key), period, value, 0, json.dumps(ids))])
    oid = db.derived_observations_of_run(run)[-1]["id"]
    if state != "pending":
        db.set_derived_row_states([(oid, state)])
    if run_state != "computing":
        db.finish_derived_run(run, run_state, NOW, n_written=1, n_checked=1,
                              n_mismatch=int(state == "mismatch"))
    return run, oid, ids


def _served(db):
    return db.conn.execute("SELECT derived_key, period, value_text, derived_observation_id "
                           "FROM served_derived ORDER BY derived_key, period").fetchall()


# --- migration -------------------------------------------------------------------------------

def test_0014_applies_on_fresh_db_and_tables_are_strict(db):
    for t in NEW_TABLES:
        sql = db.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                              (t,)).fetchone()[0]
        assert sql.rstrip().endswith("STRICT"), t
    names = {n for (n,) in db.conn.execute("SELECT name FROM sqlite_master")}
    assert {"served_derived", "derived_run_withdrawn_ins", "derived_run_terminal",
            "derived_observation_immutable", "derived_observation_state_once"} <= names
    assert db.conn.execute("SELECT COUNT(*) FROM served_derived").fetchone() == (0,)
    with pytest.raises(sqlite3.IntegrityError):  # STRICT: text into an INTEGER column
        db.conn.execute("INSERT INTO derived_run(started_at, state, trigger, scope_json, "
                        "n_written) VALUES ('t', 'computing', 'cli', '[]', 'x')")
    _setup(db)
    with pytest.raises(sqlite3.IntegrityError):  # formula CHECK follows FORMULAS
        db.conn.execute("INSERT INTO derived_series(key, formula, base_series_id, label, "
                        "formula_label_pt, unit, active) "
                        "VALUES ('derived.x', 'ratio', 's1', 'l', 'f', 'u', 1)")


def _migrations_up_to(tmp_path, last):
    mig = tmp_path / f"mig{last}"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem[:4] <= last:
            (mig / f.name).write_bytes(f.read_bytes())
    return mig


OLD_TABLES = ("source", "series", "dataset_run", "raw_fetch", "observation", "quarantine",
              "verification", "verification_item", "verification_spec", "event", "setting",
              "scheduler_state")


def test_0014_upgrades_populated_0013_db_without_touching_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", _migrations_up_to(tmp_path, "0013"))
    p = tmp_path / "old.db"
    d = open_db(p)
    sync_registry(d, [spec("s1", frequency="M"), spec("s2")])
    verified_values(d, "s1", {"2024-12": "100", "2025-01": "102"}, T1, "k1")
    run2 = verified_values(d, "s2", {"2024": "5"}, T1, "k2")
    d.withdraw_run(run2, "defect", T2)
    leg = d.legacy_run("fake", "legacy:fake", "t")
    d.write_legacy_observations(leg, [(Observation.from_raw("s1", "2020-01", "7"), "2026-02-01Z")])
    d.scheduler_attempt_started("k", "fake", "g", "t")
    before = {t: d.conn.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall()
              for t in OLD_TABLES}
    served_before = d.conn.execute("SELECT * FROM served_observation ORDER BY id").fetchall()
    schema_before = {n for (n,) in d.conn.execute("SELECT name FROM sqlite_master")}
    assert "derived_series" not in schema_before
    d.close()

    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)
    d = open_db(p)
    after = {t: d.conn.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall()
             for t in OLD_TABLES}
    assert after == before
    assert d.conn.execute("SELECT * FROM served_observation ORDER BY id").fetchall() \
        == served_before
    assert d.conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert d.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    schema_after = {n for (n,) in d.conn.execute("SELECT name FROM sqlite_master")}
    assert schema_before < schema_after
    assert set(NEW_TABLES) | {"served_derived"} <= schema_after
    assert any(v.startswith("0014") for (v,) in d.conn.execute(
        "SELECT version FROM schema_migration"))
    d.close()


# --- registry sync -----------------------------------------------------------------------------

def test_sync_derived_deactivates_absent_keys(db):
    sync_registry(db, [spec("s1", frequency="M")])
    a = derived_spec("derived.a", "s1", "yoy_change_pct")
    b = derived_spec("derived.b", "s1", "rebase_100", params={"base_period": "2021-01"})
    sync_derived(db, [a, b])
    rows = db.derived_series_rows()
    assert [r["key"] for r in rows] == ["derived.a", "derived.b"]
    rb = rows[1]
    assert rb["params"] == {"base_period": "2021-01"} and rb["frequency"] == "M"
    assert rb["active"] is True and isinstance(rb["id"], int)
    assert rb["formula_label_pt"] == formula_label_pt("rebase_100", {"base_period": "2021-01"},
                                                      "s1")
    assert rb["formula_label_pt"] == ("Índice rebaseado (2021-01 = 100), calculado pelo Prumo "
                                      "a partir de s1")
    sync_derived(db, [a])  # b left the registry
    assert [r["key"] for r in db.derived_series_rows()] == ["derived.a"]
    assert [(r["key"], r["active"]) for r in db.derived_series_rows(active_only=False)] == [
        ("derived.a", True), ("derived.b", False)]
    sync_derived(db, [a, b])  # back again, same id
    assert [r["id"] for r in db.derived_series_rows()] == [rows[0]["id"], rb["id"]]


def test_schema_formula_check_accepts_exactly_the_registry_formulas(db):
    sync_registry(db, [spec("s1", frequency="M")])
    sync_derived(db, [derived_spec(f"derived.{f}", "s1", f, **(
        {"params": {"base_period": "2021-01"}} if f == "rebase_100" else {})) for f in FORMULAS])
    assert sorted(r["formula"] for r in db.derived_series_rows()) == sorted(FORMULAS)


def test_formula_labels_are_exact():
    assert formula_label_pt("period_change", {}, "x") == (
        "Variação face ao período anterior (diferença), calculada pelo Prumo a partir de x")
    assert formula_label_pt("period_change_pct", {}, "x") == (
        "Variação face ao período anterior (%), calculada pelo Prumo a partir de x")
    assert formula_label_pt("yoy_change", {}, "x") == (
        "Variação homóloga (diferença), calculada pelo Prumo a partir de x")
    assert formula_label_pt("yoy_change_pct", {}, "x") == (
        "Variação homóloga (%), calculada pelo Prumo a partir de x")


def test_sync_derived_refuses_redefining_an_existing_key(db):
    """A key's formula/base/params are its meaning: changing them would relabel rows computed
    under the old definition. A new definition needs a new key."""
    sync_registry(db, [spec("s1", frequency="M"), spec("s2", frequency="M")])
    sync_derived(db, [derived_spec("derived.a", "s1", "yoy_change")])
    for changed in (derived_spec("derived.a", "s1", "period_change"),
                    derived_spec("derived.a", "s2", "yoy_change")):
        with pytest.raises(ValueError, match="derived.a"):
            sync_derived(db, [changed])
    sync_derived(db, [derived_spec("derived.a", "s1", "yoy_change", label="Novo")])  # cosmetic ok
    assert db.derived_series_rows()[0]["label"] == "Novo"
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("UPDATE derived_series SET formula = 'period_change'")


# --- the served view ---------------------------------------------------------------------------

def test_view_serves_verified_matched_row_with_calculated_marker(db):
    _setup(db)
    run, oid, (id_t, id_p) = _derive(db)
    rows = db.served_derived_rows(KEY, 10)
    assert rows[0] == 1
    r = rows[1][0]
    assert r["is_calculated"] == 1
    assert r["attribution"] == "Fake — Calculado pelo Prumo"
    assert r["inputs"] == [{"series_id": "s1", "period": "2025-01", "observation_id": id_t},
                           {"series_id": "s1", "period": "2024-12", "observation_id": id_p}]
    assert (r["derived_key"], r["period"], r["value_text"], r["scale"], r["unit"]) == (
        KEY, "2025-01", "2", 0, "EUR")
    assert (r["formula"], r["base_series_id"], r["licence"], r["licence_url"]) == (
        "period_change", "s1", SOURCE.licence, SOURCE.licence_url)
    assert r["formula_label_pt"].startswith("Variação face ao período anterior (diferença)")
    assert (r["derived_run_id"], r["derived_observation_id"], r["computed_at"]) == (run, oid, NOW)
    assert r["label"] == f"Derivada {KEY}"
    assert r["input_ids"] == [id_t, id_p]


def test_view_excludes_pending_mismatch_and_unverified_runs(db):
    _setup(db)
    _derive(db, state="pending", run_state="computing")
    _derive(db, state="match", run_state="computing")
    _derive(db, state="mismatch", run_state="failed")
    _derive(db, state="match", run_state="failed")
    assert _served(db) == []
    _, oid, _ = _derive(db)
    assert _served(db) == [(KEY, "2025-01", "2", oid)]


def test_view_hides_row_whose_input_was_superseded(db):
    _setup(db)
    _derive(db)
    assert len(_served(db)) == 1
    verified_values(db, "s1", {"2024-12": "101"}, T2, "k2")  # revised input, derive not run
    assert _served(db) == []
    _, oid, _ = _derive(db, value="1")
    assert _served(db) == [(KEY, "2025-01", "1", oid)]
    assert db.conn.execute("SELECT COUNT(*) FROM derived_observation").fetchone() == (2,)


def test_view_follows_base_withdrawal_back_to_older_vintage(db):
    _setup(db)
    _, oid_a, _ = _derive(db)
    run_b = verified_values(db, "s1", {"2024-12": "101", "2025-01": "104"}, T2, "k2")
    _, oid_b, _ = _derive(db, value="3")
    assert _served(db) == [(KEY, "2025-01", "3", oid_b)]
    db.withdraw_run(run_b, "defect", T3)
    assert _served(db) == [(KEY, "2025-01", "2", oid_a)]


def test_view_excludes_inactive_base_series_and_withheld_licence(db):
    _setup(db)
    _derive(db)
    assert len(_served(db)) == 1
    sync_registry(db, [spec("s1", frequency="M").model_copy(update={"active": False})])
    assert _served(db) == []
    sync_registry(db, [spec("s1", frequency="M")])
    assert len(_served(db)) == 1
    withheld = SOURCE.model_copy(update={"redistribution_ok": False})
    sync_registry(db, [spec("s1", frequency="M").model_copy(update={"source": withheld})])
    assert _served(db) == []


def test_view_excludes_inactive_derived_series(db):
    _setup(db)
    _derive(db)
    sync_derived(db, [])
    assert _served(db) == []


def test_view_never_uses_legacy_inputs_even_when_legacy_served(db):
    _setup(db, {"2024-12": "100"})
    leg = db.legacy_run("fake", "legacy:fake", "t")
    db.write_legacy_observations(leg, [(Observation.from_raw("s1", "2025-01", "102"),
                                        "2026-02-01Z")])
    db.conn.execute("UPDATE setting SET value = '1' WHERE key = 'legacy_served'")
    leg_id = db.conn.execute("SELECT id FROM observation WHERE kind = 'legacy-unverified'"
                             ).fetchone()[0]
    assert db.conn.execute("SELECT COUNT(*) FROM served_observation WHERE id = ?",
                           (leg_id,)).fetchone() == (1,)
    assert "2025-01" not in db.served_fetched_inputs("s1")
    fetched = db.served_fetched_inputs("s1")["2024-12"][0]
    run = db.begin_derived_run(NOW, "cli", [KEY])
    db.write_derived_observations(run, NOW, [(_dsid(db), "2025-01", "2", 0,
                                              json.dumps([leg_id, fetched]))])
    oid = db.derived_observations_of_run(run)[0]["id"]
    db.set_derived_row_states([(oid, "match")])
    db.finish_derived_run(run, "verified", NOW, n_written=1, n_checked=1, n_mismatch=0)
    assert _served(db) == []
    assert db.observations_by_ids([leg_id, fetched, 999999]) == {
        leg_id: {"series_id": "s1", "period": "2025-01", "value_text": "102",
                 "kind": "legacy-unverified", "served": False},
        fetched: {"series_id": "s1", "period": "2024-12", "value_text": "100",
                  "kind": "fetched", "served": True}}


def test_view_picks_highest_id_among_eligible_versions(db):
    _setup(db)
    _derive(db, value="2")
    _, oid2, _ = _derive(db, value="2")
    _derive(db, value="9", state="mismatch", run_state="failed")  # higher id, not eligible
    assert _served(db) == [(KEY, "2025-01", "2", oid2)]


# --- guards ------------------------------------------------------------------------------------

def test_derived_observation_value_is_immutable(db):
    _setup(db)
    _, oid, _ = _derive(db)
    for col, val in (("value_text", "'3'"), ("period", "'2025-02'"), ("scale", "1"),
                     ("input_obs_ids_json", "'[]'"), ("computed_at", "'x'")):
        with pytest.raises(sqlite3.IntegrityError):
            db.conn.execute(f"UPDATE derived_observation SET {col} = {val} WHERE id = ?", (oid,))
    with pytest.raises(sqlite3.IntegrityError):  # REPLACE would bypass the UPDATE guard
        db.conn.execute("INSERT OR REPLACE INTO derived_observation(id, derived_series_id, "
                        "period, value_text, scale, input_obs_ids_json, computed_at, run_id) "
                        "SELECT id, derived_series_id, period, '3', scale, input_obs_ids_json, "
                        "computed_at, run_id FROM derived_observation WHERE id = ?", (oid,))


def test_row_state_changes_only_from_pending(db):
    _setup(db)
    run, oid, _ = _derive(db, state="pending", run_state="computing")
    db.set_derived_row_states([(oid, "mismatch")])
    for new in ("match", "pending"):
        with pytest.raises(sqlite3.IntegrityError):
            db.set_derived_row_states([(oid, new)])
    assert db.derived_observations_of_run(run)[0]["id"] == oid


def test_derived_run_terminal_states_guarded(db):
    _setup(db)
    run, _, _ = _derive(db)
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("UPDATE derived_run SET state = 'failed' WHERE id = ?", (run,))
    db.conn.execute("UPDATE derived_run SET state = 'withdrawn' WHERE id = ?", (run,))
    assert _served(db) == []
    for back in ("verified", "computing", "failed"):
        with pytest.raises(sqlite3.IntegrityError):
            db.conn.execute("UPDATE derived_run SET state = ? WHERE id = ?", (back, run))
    failed = db.begin_derived_run(NOW, "cli", [KEY])
    db.finish_derived_run(failed, "failed", NOW, n_written=0, n_checked=0, n_mismatch=0)
    for nxt in ("verified", "computing", "withdrawn"):
        with pytest.raises(sqlite3.IntegrityError):
            db.conn.execute("UPDATE derived_run SET state = ? WHERE id = ?", (nxt, failed))
    computing = db.begin_derived_run(NOW, "cli", [KEY])
    with pytest.raises(sqlite3.IntegrityError):  # withdrawn only from verified
        db.conn.execute("UPDATE derived_run SET state = 'withdrawn' WHERE id = ?", (computing,))
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("INSERT INTO derived_run(started_at, state, trigger, scope_json) "
                        "VALUES ('t', 'withdrawn', 'cli', '[]')")
    with pytest.raises(sqlite3.IntegrityError):  # a terminal run is never replaced
        db.conn.execute("INSERT OR REPLACE INTO derived_run(id, started_at, state, trigger, "
                        "scope_json) VALUES (?, 't', 'computing', 'cli', '[]')", (run,))


def test_finish_derived_run_is_compare_and_set(db):
    _setup(db)
    run = db.begin_derived_run(NOW, "scheduler", [KEY, "derived.other"])
    db.finish_derived_run(run, "verified", T3, n_written=4, n_checked=4, n_mismatch=0)
    with pytest.raises(ValueError):
        db.finish_derived_run(run, "failed", T3, n_written=4, n_checked=4, n_mismatch=0)
    with pytest.raises(ValueError):
        db.finish_derived_run(999, "verified", T3, n_written=0, n_checked=0, n_mismatch=0)
    other = db.begin_derived_run(NOW, "cli", [])
    with pytest.raises(ValueError):
        db.finish_derived_run(other, "withdrawn", T3, n_written=0, n_checked=0, n_mismatch=0)
    assert db.derived_runs(5) == [
        {"id": other, "started_at": NOW, "finished_at": None, "state": "computing",
         "trigger": "cli", "scope": [], "n_written": None, "n_checked": None,
         "n_mismatch": None},
        {"id": run, "started_at": NOW, "finished_at": T3, "state": "verified",
         "trigger": "scheduler", "scope": [KEY, "derived.other"], "n_written": 4,
         "n_checked": 4, "n_mismatch": 0}]


# --- reads -------------------------------------------------------------------------------------

def test_derived_status_rows_reports_coverage_and_base_latest(db):
    _setup(db)
    sync_derived(db, [derived_spec(KEY, "s1", "period_change"),
                      derived_spec("derived.s1_yoy", "s1", "yoy_change"),
                      derived_spec("derived.gone", "s1", "period_change", active=False)])
    run, _, _ = _derive(db)
    later = db.begin_derived_run("2026-11-15T00:00:00+00:00", "scheduler", [KEY])
    db.finish_derived_run(later, "failed", NOW, n_written=0, n_checked=0, n_mismatch=0)
    verified_values(db, "s1", {"2025-02": "103"}, T2, "k2")
    assert db.derived_status_rows() == [
        {"key": KEY, "base_series_id": "s1", "served_values": 1, "last_covered_run_id": run,
         "last_covered_at": NOW, "base_latest_fetched_at": T2},
        {"key": "derived.s1_yoy", "base_series_id": "s1", "served_values": 0,
         "last_covered_run_id": None, "last_covered_at": None, "base_latest_fetched_at": T2}]


def test_derived_reads_decode_json_and_mark_served_versions(db):
    _setup(db)
    run1, oid1, ids1 = _derive(db)
    verified_values(db, "s1", {"2024-12": "101"}, T2, "k2")
    run2, oid2, ids2 = _derive(db, value="1")
    dsid = _dsid(db)
    assert db.derived_known_inputs(dsid) == {("2025-01", json.dumps(ids1)),
                                             ("2025-01", json.dumps(ids2))}
    rows = db.derived_rows_of_series(KEY, 10)
    assert [(r["id"], r["served"], r["run_state"], r["input_ids"]) for r in rows] == [
        (oid2, True, "verified", ids2), (oid1, False, "verified", ids1)]
    o = db.derived_observations_of_run(run2)[0]
    assert {k: o[k] for k in ("id", "derived_series_id", "key", "formula", "params",
                              "base_series_id", "frequency", "period", "value_text", "scale",
                              "input_ids")} == {
        "id": oid2, "derived_series_id": dsid, "key": KEY, "formula": "period_change",
        "params": {}, "base_series_id": "s1", "frequency": "M", "period": "2025-01",
        "value_text": "1", "scale": 0, "input_ids": ids2}
    run = db.begin_derived_run(NOW, "cli", [KEY])
    db.add_derived_event(NOW, run, dsid, "2025-01", "zero_denominator", {"denominator": "0"})
    db.add_derived_event(NOW, run, None, None, "missing_base_period")
    assert db.conn.execute("SELECT derived_series_id, period, kind, detail_json "
                           "FROM derived_event ORDER BY id").fetchall() == [
        (dsid, "2025-01", "zero_denominator", '{"denominator": "0"}'),
        (None, None, "missing_base_period", None)]
    with pytest.raises(sqlite3.IntegrityError):
        db.add_derived_event(NOW, run, None, None, "other")


# --- fix round 1 (review I1-I3, M1, M3, M5) ----------------------------------------------------

def _insert_raw(db, run, inputs, *, state=None, dsid=None, period="2025-01"):
    cols = "derived_series_id, period, value_text, scale, input_obs_ids_json, computed_at, run_id"
    args = [dsid or _dsid(db), period, "1", 0, inputs, NOW, run]
    if state is not None:
        cols, args = cols + ", state", [*args, state]
    db.conn.execute(f"INSERT INTO derived_observation({cols}) "
                    f"VALUES ({', '.join('?' * len(args))})", args)


def test_rows_enter_only_a_computing_run_as_pending(db):
    """I1: a row can never be served without its run's verification."""
    _setup(db)
    ids = json.dumps([v[0] for v in db.served_fetched_inputs("s1").values()])
    run = db.begin_derived_run(NOW, "cli", [KEY])
    with pytest.raises(sqlite3.IntegrityError):  # born 'match'
        _insert_raw(db, run, ids, state="match")
    db.finish_derived_run(run, "verified", NOW, n_written=0, n_checked=0, n_mismatch=0)
    with pytest.raises(sqlite3.IntegrityError):  # into a verified run, even as pending
        db.write_derived_observations(run, NOW, [(_dsid(db), "2025-01", "9", 0, ids)])
    assert _served(db) == []


def test_row_state_changes_only_while_run_is_computing(db):
    """I1: a pending row of a finished run can never become 'match' afterwards."""
    _setup(db)
    run, oid, _ = _derive(db, state="pending", run_state="computing")
    db.finish_derived_run(run, "failed", NOW, n_written=1, n_checked=0, n_mismatch=0)
    with pytest.raises(sqlite3.IntegrityError):
        db.set_derived_row_states([(oid, "match")])
    assert _served(db) == []


def test_finish_verified_refused_while_rows_pending_or_mismatched(db):
    """I1: verification sets every row's verdict BEFORE finish; any pending or mismatched row
    keeps the run from 'verified' (Db check and trigger backstop)."""
    _setup(db)
    for state in ("pending", "mismatch"):
        run, _, _ = _derive(db, state=state, run_state="computing")
        with pytest.raises(ValueError, match=state):
            db.finish_derived_run(run, "verified", NOW, n_written=1, n_checked=1, n_mismatch=0)
        with pytest.raises(sqlite3.IntegrityError):
            db.conn.execute("UPDATE derived_run SET state = 'verified' WHERE id = ?", (run,))
        assert db.derived_runs(1)[0]["state"] == "computing"
        db.finish_derived_run(run, "failed", NOW, n_written=1, n_checked=1, n_mismatch=1)
    assert _served(db) == []
    with pytest.raises(sqlite3.IntegrityError):  # a run is born computing, never finished
        db.conn.execute("INSERT INTO derived_run(started_at, state, trigger, scope_json) "
                        "VALUES ('t', 'verified', 'cli', '[]')")


def test_view_refuses_inputs_from_another_series(db):
    """I2: inputs must be rows of the derived series' base series, whose source supplies the
    licence and attribution (reviewer reproduction: s2 under CC-BY-NC)."""
    _setup(db)
    other = SourceSpec(name="other", licence="CC-BY-NC", licence_url="http://o",
                       attribution="Other", redistribution_ok=True)
    sync_registry(db, [spec("s1", frequency="M"),
                       spec("s2", frequency="M").model_copy(update={"source": other})])
    verified_values(db, "s2", {"2024-12": "1", "2025-01": "2"}, T1, "k2", source="other")
    i2 = db.served_fetched_inputs("s2")
    run = db.begin_derived_run(NOW, "cli", [KEY])
    db.write_derived_observations(run, NOW, [(_dsid(db), "2025-01", "1", 0,
                                              json.dumps([i2["2025-01"][0], i2["2024-12"][0]]))])
    oid = db.derived_observations_of_run(run)[0]["id"]
    db.set_derived_row_states([(oid, "match")])
    db.finish_derived_run(run, "verified", NOW, n_written=1, n_checked=1, n_mismatch=0)
    assert _served(db) == []


@pytest.mark.parametrize("inputs", ["not json", '{"a": 1}', "[]", "[ID, ID]", '["ID"]',
                                    "[ID.0]", "[999999]", '"ID"'])
def test_input_list_must_be_distinct_existing_integer_ids(db, inputs):
    """I3: input_obs_ids_json is a non-empty JSON array of distinct integer observation ids."""
    _setup(db)
    i = str(db.served_fetched_inputs("s1")["2025-01"][0])
    run = db.begin_derived_run(NOW, "cli", [KEY])
    with pytest.raises(sqlite3.IntegrityError):
        db.write_derived_observations(run, NOW, [(_dsid(db), "2025-01", "1", 0,
                                                  inputs.replace("ID", i))])


@pytest.mark.parametrize("scope", ["not json", '{"a": 1}', '"derived.x"'])
def test_run_scope_must_be_a_json_array(db, scope):
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("INSERT INTO derived_run(started_at, state, trigger, scope_json) "
                        "VALUES ('t', 'computing', 'cli', ?)", (scope,))


def test_derived_history_is_never_deleted_or_replaced(db):
    """M1: derived rows, runs, events and series definitions are history."""
    _setup(db)
    run, oid, _ = _derive(db)
    db.add_derived_event(NOW, run, _dsid(db), "2025-01", "mismatch")
    for table in ("derived_observation", "derived_run", "derived_event", "derived_series"):
        with pytest.raises(sqlite3.IntegrityError):
            db.conn.execute(f"DELETE FROM {table}")
    with pytest.raises(sqlite3.IntegrityError):  # REPLACE would bypass the definition guard
        db.conn.execute("INSERT OR REPLACE INTO derived_series(key, formula, base_series_id, "
                        "label, formula_label_pt, unit, active) "
                        "VALUES (?, 'yoy_change', 's1', 'l', 'f', 'u', 1)", (KEY,))
    assert db.derived_series_rows()[0]["formula"] == "period_change"


def test_inputs_follow_the_stored_input_order(db):
    """M3: `inputs` lists the inputs in input_obs_ids_json order whatever the id order."""
    _setup(db)
    inp = db.served_fetched_inputs("s1")
    t, p = inp["2025-01"][0], inp["2024-12"][0]
    assert p < t
    for order in ([t, p], [p, t]):
        run = db.begin_derived_run(NOW, "cli", [KEY])
        db.write_derived_observations(run, NOW, [(_dsid(db), "2025-01", "2", 0,
                                                  json.dumps(order))])
        oid = db.derived_observations_of_run(run)[0]["id"]
        db.set_derived_row_states([(oid, "match")])
        db.finish_derived_run(run, "verified", NOW, n_written=1, n_checked=1, n_mismatch=0)
        row = db.served_derived_rows(KEY, 1)[1][0]
        assert [x["observation_id"] for x in row["inputs"]] == order


def test_rebase_label_without_base_period_names_the_param():
    """M5."""
    with pytest.raises(ValueError, match="base_period"):
        formula_label_pt("rebase_100", {}, "s1")
    with pytest.raises(ValueError, match="ratio"):
        formula_label_pt("ratio", {}, "s1")
