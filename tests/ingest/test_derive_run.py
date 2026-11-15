"""Task 5 (derived layer v1): run orchestration `derive.run_derive` and the `derive` CLI."""
import json
import sqlite3
from datetime import datetime, timezone

import pytest
import yaml

from ingest import derive
from ingest.cli import main
from ingest.db import open_db
from ingest.derive import DerivedValue, DeriveReport, run_derive
from ingest.registry import sync_derived, sync_registry
from tests.ingest.derived_helpers import derived_spec, verified_values
from tests.ingest.fakes import SOURCE, spec

T1 = "2026-11-01T00:00:00+00:00"
T2 = "2026-11-02T00:00:00+00:00"
T3 = "2026-11-03T00:00:00+00:00"
NOW = datetime(2026, 11, 14, tzinfo=timezone.utc)
S1 = {"2024-12": "100", "2025-01": "102.5", "2025-02": "99"}
PC, RB, S2PC = "derived.s1_pc", "derived.s1_rb", "derived.s2_pc"


def _now():
    return NOW


def _setup(db, derived=None):
    sync_registry(db, [spec("s1", frequency="M"), spec("s2", frequency="M")])
    verified_values(db, "s1", S1, T1, "k1")
    verified_values(db, "s2", {"2025-01": "1", "2025-02": "3"}, T1, "k2")
    sync_derived(db, derived if derived is not None else [
        derived_spec(PC, "s1", "period_change"),
        derived_spec(RB, "s1", "rebase_100", params={"base_period": "2025-01"})])


def _run(db, **kw):
    return run_derive(db, trigger=kw.pop("trigger", "cli"), now=_now, **kw)


def _served(db, key):
    return [(r["period"], r["value_text"], r["scale"], r["input_ids"])
            for r in db.served_derived_rows(key, 1000)[1]]


def _values(db, key):
    return {r["period"]: r["value_text"] for r in db.served_derived_rows(key, 1000)[1]}


def _events(db, run):
    return [(k, p, json.loads(d) if d else None) for k, p, d in db.conn.execute(
        "SELECT kind, period, detail_json FROM derived_event WHERE run_id = ? ORDER BY id",
        (run,))]


# --- run_derive ---------------------------------------------------------------------------------

def test_first_run_writes_and_verifies(db):
    _setup(db)
    rep = _run(db)
    assert rep == DeriveReport(run_id=rep.run_id, state="verified", n_series=2, n_written=5,
                               n_skipped=0, n_mismatch=0)
    [run] = db.derived_runs(10)
    assert (run["id"], run["state"], run["trigger"], run["scope"]) == (
        rep.run_id, "verified", "cli", [PC, RB])
    assert (run["n_written"], run["n_checked"], run["n_mismatch"]) == (5, 5, 0)
    assert run["started_at"] == run["finished_at"] == NOW.isoformat()
    assert _values(db, PC) == {"2025-01": "2.5", "2025-02": "-3.5"}
    assert _values(db, RB) == {"2024-12": "97.5610", "2025-01": "100.0000",
                               "2025-02": "96.5854"}
    ids = db.served_fetched_inputs("s1")
    base_row = next(r for r in _served(db, RB) if r[0] == "2025-01")
    assert base_row[3] == [ids["2025-01"][0]]  # rebase at its own base period: ONE id
    assert next(r for r in _served(db, PC) if r[0] == "2025-01")[3] == [
        ids["2025-01"][0], ids["2024-12"][0]]


def test_second_run_without_changes_writes_nothing_but_records_run(db):
    _setup(db)
    first = _run(db)
    served = {k: _served(db, k) for k in (PC, RB)}
    second = _run(db)
    assert second.run_id != first.run_id
    assert (second.state, second.n_series, second.n_written, second.n_mismatch) == (
        "verified", 2, 0, 0)
    runs = db.derived_runs(10)
    assert [r["state"] for r in runs] == ["verified", "verified"]
    assert (runs[0]["n_written"], runs[0]["n_checked"]) == (0, 0)
    assert {k: _served(db, k) for k in (PC, RB)} == served
    assert db.derived_observations_of_run(second.run_id) == []


def test_revision_adds_new_version_and_keeps_old(db):
    _setup(db)
    _run(db)
    old = {r["period"]: r["id"] for r in db.derived_rows_of_series(PC, 100)}
    verified_values(db, "s1", {"2025-01": "102.6"}, T2, "k1b")
    # before derive: the rows built on the superseded 2025-01 vintage are no longer served
    assert _values(db, PC) == {}
    rep = _run(db)
    assert rep.n_written == 2 + 3  # PC: 2025-01, 2025-02; RB: every period (base changed)
    assert _values(db, PC) == {"2025-01": "2.6", "2025-02": "-3.6"}
    versions = db.derived_rows_of_series(PC, 100)
    assert len(versions) == 4
    kept = {v["id"]: v for v in versions}
    for period, oid in old.items():
        assert kept[oid]["period"] == period and kept[oid]["state"] == "match"
        assert kept[oid]["served"] is False


def test_unchanged_periods_are_not_rewritten_after_a_partial_revision(db):
    sync_registry(db, [spec("s1", frequency="M")])
    verified_values(db, "s1", {"2024-11": "1", "2024-12": "2", "2025-01": "4"}, T1, "k1")
    sync_derived(db, [derived_spec(PC, "s1", "period_change")])
    _run(db)
    verified_values(db, "s1", {"2025-01": "5"}, T2, "k1b")
    rep = _run(db)
    assert rep.n_written == 1
    assert [r["period"] for r in db.derived_observations_of_run(rep.run_id)] == ["2025-01"]
    assert _values(db, PC) == {"2024-12": "1", "2025-01": "3"}


ALL = [derived_spec("derived.s1_pc", "s1", "period_change"),
       derived_spec("derived.s1_pcp", "s1", "period_change_pct"),
       derived_spec("derived.s1_yoy", "s1", "yoy_change"),
       derived_spec("derived.s1_yoyp", "s1", "yoy_change_pct"),
       derived_spec("derived.s1_rb", "s1", "rebase_100", params={"base_period": "2024-06"}),
       derived_spec("derived.s3_yoyp", "s3", "yoy_change_pct"),
       derived_spec("derived.s3_pc", "s3", "period_change")]


def _base_steps(db, step):
    """Base writes of the incremental-vs-full comparison, step 1..3."""
    if step == 1:
        sync_registry(db, [spec("s1", frequency="M"), spec("s3", frequency="Q")])
        verified_values(db, "s1", {f"{y}-{m:02d}": f"{100 + 3 * m + (y - 2024) * 7}.{m}"
                                   for y in (2024, 2025) for m in range(1, 13)
                                   if (y, m) <= (2025, 3)}, T1, "k1")
        verified_values(db, "s3", {"2023-Q4": "10", "2024-Q1": "0", "2024-Q2": "12.5",
                                   "2024-Q4": "11", "2025-Q1": "9.75"}, T1, "k3")
        sync_derived(db, ALL)
        return None
    if step == 2:  # revision of 2025-01 + a new period (run B); revision of 2025-02 (run C)
        verified_values(db, "s1", {"2025-01": "200.5", "2025-04": "130"}, T2, "k1b")
        verified_values(db, "s3", {"2024-Q1": "8"}, T2, "k3b")
        return verified_values(db, "s1", {"2025-02": "50"}, T3, "k1c")
    raise AssertionError(step)


def _snapshot(db):
    out = {}
    for d in ALL:
        out[d.key] = [(r["period"], r["value_text"], r["scale"],
                       [(i["series_id"], i["period"]) for i in r["inputs"]])
                      for r in db.served_derived_rows(d.key, 1000)[1]]
    return out


def test_incremental_equals_full_recompute(tmp_path):
    a, b = open_db(tmp_path / "a.db"), open_db(tmp_path / "b.db")
    try:
        _base_steps(a, 1)
        assert _run(a).state == "verified"
        run_c = _base_steps(a, 2)
        assert _run(a).state == "verified"
        a.withdraw_run(run_c, "defect", T3)  # step 3: withdrawal brings 2025-02 back to A
        assert _run(a).state == "verified"

        _base_steps(b, 1)
        run_c_b = _base_steps(b, 2)
        b.withdraw_run(run_c_b, "defect", T3)
        assert _run(b).state == "verified"

        snap_a, snap_b = _snapshot(a), _snapshot(b)
        assert snap_a == snap_b
        assert all(snap_a[d.key] for d in ALL)  # every formula served something
        pc = dict((p, v) for p, v, _, _ in snap_a["derived.s1_pc"])
        assert pc["2025-01"] == "64.38" and "2025-04" in pc  # revision B kept, C withdrawn
    finally:
        a.close()
        b.close()


def _wrong(real):
    def fake(formula, params, frequency, inputs):
        vals, skips = real(formula, params, frequency, inputs)
        return [DerivedValue(v.period, v.value_text + "1" if "." in v.value_text
                             else v.value_text + ".1", v.scale, v.input_ids)
                for v in vals], skips
    return fake


def test_mismatch_fails_run_and_nothing_served(db, monkeypatch):
    _setup(db)
    monkeypatch.setattr(derive, "compute", _wrong(derive.compute))
    rep = _run(db)
    assert (rep.state, rep.n_written, rep.n_mismatch) == ("failed", 5, 5)
    assert db.derived_runs(1)[0]["state"] == "failed"
    assert _served(db, PC) == [] and _served(db, RB) == []
    assert [k for k, _, _ in _events(db, rep.run_id)] == ["mismatch"] * 5
    monkeypatch.undo()
    rep2 = _run(db)  # a failed run's rows are not "known": the honest run rewrites them
    assert (rep2.state, rep2.n_written) == ("verified", 5)
    assert _values(db, PC) == {"2025-01": "2.5", "2025-02": "-3.5"}


def test_exception_marks_run_failed(db, monkeypatch):
    _setup(db)

    def boom(*a, **k):
        raise RuntimeError("verifier crashed")
    monkeypatch.setattr(derive, "verify_run", boom)
    with pytest.raises(RuntimeError, match="verifier crashed"):
        _run(db)
    [run] = db.derived_runs(10)
    assert (run["state"], run["finished_at"], run["n_written"]) == (
        "failed", NOW.isoformat(), 5)
    assert _served(db, PC) == []
    assert not db.conn.in_transaction


@pytest.mark.parametrize("error", [ValueError("bad token"), ArithmeticError("overflow")])
def test_compute_error_fails_run_with_event_and_serves_nothing(db, monkeypatch, error):
    _setup(db)
    real = derive.compute

    def flaky(formula, params, frequency, inputs):
        if formula == "rebase_100":
            raise error
        return real(formula, params, frequency, inputs)
    monkeypatch.setattr(derive, "compute", flaky)
    rep = _run(db)
    assert rep.state == "failed" and rep.n_errors == 1 and rep.n_mismatch == 0
    assert rep.n_written == 2  # the healthy series was computed and verified ...
    assert _served(db, PC) == []  # ... but nothing from a failed run is served
    rb = next(r["id"] for r in db.derived_series_rows() if r["key"] == RB)
    [(kind, period, detail)] = _events(db, rep.run_id)
    assert (kind, period) == ("compute_error", None)
    assert detail == {"error": f"{type(error).__name__}: {error}"}
    assert db.conn.execute("SELECT derived_series_id FROM derived_event WHERE run_id = ?",
                           (rep.run_id,)).fetchone() == (rb,)


def test_skip_events_are_written(db):
    sync_registry(db, [spec("s1", frequency="M")])
    verified_values(db, "s1", {"2024-12": "0", "2025-01": "5"}, T1, "k1")
    sync_derived(db, [derived_spec("derived.s1_pcp", "s1", "period_change_pct"),
                      derived_spec(RB, "s1", "rebase_100", params={"base_period": "2020-01"})])
    rep = _run(db)
    assert (rep.state, rep.n_written, rep.n_skipped) == ("verified", 0, 2)
    ids = db.served_fetched_inputs("s1")
    assert sorted((k, p, d) for k, p, d in _events(db, rep.run_id)) == [
        ("missing_base_period", None, {"input_ids": []}),
        ("zero_denominator", "2025-01",
         {"input_ids": [ids["2025-01"][0], ids["2024-12"][0]]})]


def test_skip_events_are_written_once_per_inputs(db):
    sync_registry(db, [spec("s1", frequency="M")])
    verified_values(db, "s1", {"2024-12": "0", "2025-01": "5"}, T1, "k1")
    sync_derived(db, [derived_spec("derived.s1_pcp", "s1", "period_change_pct"),
                      derived_spec(RB, "s1", "rebase_100", params={"base_period": "2020-01"})])
    reps = [_run(db) for _ in range(3)]
    assert [r.n_skipped for r in reps] == [2, 0, 0]
    assert [len(_events(db, r.run_id)) for r in reps] == [2, 0, 0]
    # a new vintage of the zero reference is a new skip with new inputs: recorded again
    verified_values(db, "s1", {"2024-12": "0.0"}, T2, "k1b")
    rep = _run(db)
    assert [(k, p) for k, p, _ in _events(db, rep.run_id)] == [("zero_denominator", "2025-01")]


def test_skip_events_of_a_failed_run_are_recorded_again(db, monkeypatch):
    sync_registry(db, [spec("s1", frequency="M")])
    verified_values(db, "s1", {"2024-11": "1", "2024-12": "0", "2025-01": "5"}, T1, "k1")
    sync_derived(db, [derived_spec("derived.s1_pcp", "s1", "period_change_pct")])
    monkeypatch.setattr(derive, "compute", _wrong(derive.compute))
    assert _run(db).state == "failed"
    monkeypatch.undo()
    rep = _run(db)
    assert rep.state == "verified" and rep.n_skipped == 1


def test_auto_rollback_does_not_mask_the_original_error(db, monkeypatch):
    _setup(db)

    def rolled_back(*a, **k):  # SQLite aborted the transaction itself (e.g. SQLITE_FULL)
        db.conn.execute("ROLLBACK")
        raise sqlite3.OperationalError("database or disk is full")
    monkeypatch.setattr(db, "write_derived_observations", rolled_back)
    with pytest.raises(sqlite3.OperationalError, match="disk is full"):
        _run(db)
    assert not db.conn.in_transaction
    assert db.derived_runs(10) == []  # the run row went with SQLite's rollback


def test_failed_recovery_does_not_mask_the_original_error(db, monkeypatch):
    _setup(db)

    def boom(*a, **k):
        raise RuntimeError("verifier crashed")

    def cannot_finish(*a, **k):
        raise ValueError("finish refused")
    monkeypatch.setattr(derive, "verify_run", boom)
    monkeypatch.setattr(db, "finish_derived_run", cannot_finish)
    with pytest.raises(RuntimeError, match="verifier crashed"):
        _run(db)
    assert not db.conn.in_transaction
    assert db.derived_runs(10) == []  # nothing recorded: the whole run rolled back


def test_base_series_filter_selects_dependents_only(db):
    _setup(db, [derived_spec(PC, "s1", "period_change"),
                derived_spec(S2PC, "s2", "period_change")])
    rep = _run(db, base_series={"s2"}, trigger="scheduler")
    assert (rep.n_series, rep.n_written) == (1, 1)
    run = db.derived_runs(1)[0]
    assert (run["scope"], run["trigger"]) == ([S2PC], "scheduler")
    assert {r["key"] for r in db.derived_observations_of_run(rep.run_id)} == {S2PC}
    assert _served(db, PC) == [] and _values(db, S2PC) == {"2025-02": "2"}


def test_keys_filter_selects_named_series_only(db):
    _setup(db, [derived_spec(PC, "s1", "period_change"),
                derived_spec(S2PC, "s2", "period_change")])
    rep = _run(db, keys=[PC])
    assert rep.n_series == 1 and db.derived_runs(1)[0]["scope"] == [PC]
    assert {r["key"] for r in db.derived_observations_of_run(rep.run_id)} == {PC}


def test_empty_selection_returns_none_without_run(db):
    _setup(db)
    assert _run(db, base_series={"s2"}) is None  # no derived series on s2
    assert _run(db, base_series=set()) is None
    assert _run(db, keys=[]) is None
    sync_derived(db, [])  # every key inactive
    assert _run(db) is None
    assert db.derived_runs(10) == []


def test_unknown_or_inactive_key_refused_without_run(db):
    _setup(db, [derived_spec(PC, "s1", "period_change"),
                derived_spec(S2PC, "s2", "period_change", active=False)])
    for keys in (["derived.nope"], [S2PC], [PC, "derived.nope"]):
        with pytest.raises(ValueError, match="unknown or inactive"):
            _run(db, keys=keys)
    with pytest.raises(ValueError, match="not both"):
        _run(db, keys=[PC], base_series={"s1"})
    assert db.derived_runs(10) == []


# --- CLI ----------------------------------------------------------------------------------------

def _registry(path, derived):
    path.write_text(yaml.safe_dump({
        "sources": {SOURCE.name: SOURCE.model_dump(exclude={"name"})},
        "series": [{**spec(s, frequency="M").model_dump(exclude={"source"}),
                    "source": SOURCE.name} for s in ("s1", "s2")],
        "derived": derived}, sort_keys=False, allow_unicode=True))
    return path


def _cli_entries():
    return [{"key": PC, "base": "s1", "formula": "period_change", "label": "Var", "unit": "EUR"},
            {"key": RB, "base": "s1", "formula": "rebase_100", "label": "Idx", "unit": "idx",
             "params": {"base_period": "2025-01"}},
            {"key": S2PC, "base": "s2", "formula": "period_change", "label": "Var2",
             "unit": "EUR", "active": False}]


def _cli_db(tmp_path):
    path = tmp_path / "prumo.sqlite3"
    db = open_db(path)
    try:
        sync_registry(db, [spec("s1", frequency="M"), spec("s2", frequency="M")])
        verified_values(db, "s1", S1, T1, "k1")
    finally:
        db.close()
    return path


def _derived_runs(path):
    db = open_db(path)
    try:
        return db.derived_runs(10)
    finally:
        db.close()


def test_cli_derive_exit_codes_and_output(tmp_path, capsys, monkeypatch):
    path, reg = _cli_db(tmp_path), _registry(tmp_path / "r.yaml", _cli_entries())
    argv = ["--db", str(path), "--registry", str(reg), "derive"]
    assert main(argv) == 0
    assert capsys.readouterr().out == (
        "derive run 1: verified; 2 series, 5 new values, 0 skipped, 0 mismatches\n")
    assert main([*argv, "--series", PC]) == 0
    assert capsys.readouterr().out == (
        "derive run 2: verified; 1 series, 0 new values, 0 skipped, 0 mismatches\n")
    verified_db = open_db(path)
    try:
        verified_values(verified_db, "s1", {"2025-03": "101"}, T2, "k1b")
    finally:
        verified_db.close()
    monkeypatch.setattr(derive, "compute", _wrong(derive.compute))
    assert main([*argv, "--series", PC, "--series", RB]) == 1
    assert capsys.readouterr().out == (
        "derive run 3: failed; 2 series, 2 new values, 0 skipped, 2 mismatches\n")
    monkeypatch.undo()
    assert main([*argv, "--series", "derived.nope"]) == 2
    err = capsys.readouterr().err
    assert "derived.nope" in err and "unknown or inactive" in err
    assert [r["state"] for r in _derived_runs(path)] == ["failed", "verified", "verified"]


def test_cli_derive_nothing_to_derive(tmp_path, capsys):
    path, reg = _cli_db(tmp_path), _registry(tmp_path / "r.yaml", [])
    assert main(["--db", str(path), "--registry", str(reg), "derive"]) == 0
    assert capsys.readouterr().out == "nothing to derive\n"
    assert _derived_runs(path) == []


def test_cli_missing_database_is_refused_without_creating_it(tmp_path, capsys):
    reg = _registry(tmp_path / "r.yaml", _cli_entries())
    fresh = tmp_path / "never.sqlite3"
    assert main(["--db", str(fresh), "--registry", str(reg), "derive"]) == 2
    assert "database not found" in capsys.readouterr().err
    assert not fresh.exists()


def test_cli_base_series_missing_from_database_is_refused(tmp_path, capsys):
    path = tmp_path / "prumo.sqlite3"
    db = open_db(path)
    try:
        sync_registry(db, [spec("s2", frequency="M")])  # s1, the base of PC/RB, never synced
    finally:
        db.close()
    reg = _registry(tmp_path / "r.yaml", _cli_entries())
    assert main(["--db", str(path), "--registry", str(reg), "derive"]) == 2
    err = capsys.readouterr().err
    assert "derive refused: base series ['s1'] not in the database (run 'run' first)" in err
    db = open_db(path)
    try:
        assert db.derived_runs(10) == []
        assert db.derived_series_rows(active_only=False) == []  # nothing synced either
    finally:
        db.close()


def test_cli_unknown_series_key_writes_nothing(tmp_path, capsys):
    reg = _registry(tmp_path / "r.yaml", _cli_entries())
    fresh = tmp_path / "never.sqlite3"
    for key in ("derived.nope", S2PC):  # unknown; inactive
        assert main(["--db", str(fresh), "--registry", str(reg), "derive",
                     "--series", key]) == 2
        assert key in capsys.readouterr().err
    assert not fresh.exists()  # refused before any DB open
    path = _cli_db(tmp_path)
    assert main(["--db", str(path), "--registry", str(reg), "derive", "--series", PC,
                 "--series", "derived.nope"]) == 2
    assert _derived_runs(path) == []
