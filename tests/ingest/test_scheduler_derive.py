"""Task 6: the scheduler derives after each VERIFIED base group, scoped to that group's series.

A derive outcome (report, nothing selected, or exception) is log-only: it never touches
scheduler_state, the retry/streak logic, or the `--once` exit code. No HTTP: runners and the
deriver are injected seams; scratch DBs only.
"""
from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from ingest import scheduler
from ingest.db import open_db
from ingest.derive import DeriveReport
from ingest.operations import GroupOutcome
from ingest.rawstore import RawStore
from ingest.scheduler import tick
from tests.ingest.test_scheduler import T0, _runner, _tiny_registry, _wb


@pytest.fixture
def db(tmp_path):
    d = open_db(tmp_path / "prumo.db")
    yield d
    d.close()


@pytest.fixture
def store(tmp_path):
    return RawStore(tmp_path / "raw")


def _recording_deriver(calls: list, result=None):
    def derive(_db, series_ids):
        calls.append(set(series_ids))
        if isinstance(result, Exception):
            raise result
        return result
    return derive


def test_verified_attempt_triggers_deriver_with_group_series_ids(db, store):
    a, b = _wb("wb.a.PT", "X.AAA"), _wb("wb.b.PT", "X.BBB")
    derive_calls: list = []
    report = DeriveReport(run_id=7, state="verified", n_series=1, n_written=3, n_skipped=0,
                          n_mismatch=0)
    records = tick(db, store, [a, b], now=lambda: T0, runner=_runner({}, []),
                   log=lambda r: None, deriver=_recording_deriver(derive_calls, report))
    assert derive_calls == [{"wb.a.PT"}, {"wb.b.PT"}]      # scoped to each group, not all keys
    assert [(r["event"], r["group"]) for r in records] == [
        ("attempt", "X.AAA"), ("derive", "X.AAA"), ("attempt", "X.BBB"), ("derive", "X.BBB")]
    derive = records[1]
    assert derive == {"schema": "prumo-scheduler", "version": 1, "ts": T0.isoformat(),
                      "event": "derive", "group": "X.AAA", "run_id": 7, "state": "verified",
                      "n_written": 3, "n_mismatch": 0}


def test_failed_attempt_never_derives(db, store):
    a = _wb("wb.a.PT", "X.AAA")
    derive_calls: list = []
    outcomes = {"X.AAA": GroupOutcome("worldbank", "X.AAA", "failed-operational", detail="x")}
    records = tick(db, store, [a], now=lambda: T0, runner=_runner(outcomes, []),
                   log=lambda r: None, deriver=_recording_deriver(derive_calls))
    assert derive_calls == []
    assert [r["event"] for r in records] == ["attempt"]
    # A runner exception (state 'error') never derives either.
    records = tick(db, store, [a], now=lambda: T0 + timedelta(hours=2),
                   runner=_runner({"X.AAA": RuntimeError("boom")}, []), log=lambda r: None,
                   deriver=_recording_deriver(derive_calls))
    assert derive_calls == [] and [r["state"] for r in records] == ["error"]


def test_none_report_emits_no_record(db, store):
    a = _wb("wb.a.PT", "X.AAA")
    derive_calls: list = []
    logged: list = []
    records = tick(db, store, [a], now=lambda: T0, runner=_runner({}, []), log=logged.append,
                   deriver=_recording_deriver(derive_calls, None))
    assert derive_calls == [{"wb.a.PT"}]
    assert [r["event"] for r in records] == ["attempt"] and logged == records


def test_derive_exception_is_logged_not_fatal(db, store):
    a, b = _wb("wb.a.PT", "X.AAA"), _wb("wb.b.PT", "X.BBB")
    derive_calls: list = []
    runner_calls: list = []
    logged: list = []
    records = tick(db, store, [a, b], now=lambda: T0, runner=_runner({}, runner_calls),
                   log=logged.append,
                   deriver=_recording_deriver(derive_calls, ValueError("poison base value")))
    assert [c[1] for c in runner_calls] == ["X.AAA", "X.BBB"]   # next group still attempted
    assert derive_calls == [{"wb.a.PT"}, {"wb.b.PT"}]
    assert logged == records
    errors = [r for r in records if r["event"] == "derive"]
    assert [(r["group"], r["state"], r["detail"]) for r in errors] == [
        ("X.AAA", "error", "ValueError: poison base value"),
        ("X.BBB", "error", "ValueError: poison base value")]
    assert all(r["schema"] == "prumo-scheduler" and r["version"] == 1 and r["ts"]
               for r in errors)
    attempts = [r for r in records if r["event"] == "attempt"]
    assert [r["state"] for r in attempts] == ["verified", "verified"]
    states = db.scheduler_states()
    assert len(states) == 2
    assert all(s.last_attempt_state == "verified" and s.failure_streak == 0
               and s.last_success_at == T0.isoformat() for s in states)


def test_once_exit_code_ignores_derive_failure(tmp_path):
    reg = _tiny_registry(tmp_path)
    logged: list = []
    code = scheduler.main(["--once", "--registry", str(reg), "--db", str(tmp_path / "p.db"),
                           "--raw-dir", str(tmp_path / "raw")],
                          now=lambda: T0, runner=_runner({}, []), log=logged.append,
                          deriver=_recording_deriver([], RuntimeError("derive broke")))
    assert code == 0
    assert [(r["event"], r["state"]) for r in logged] == [("attempt", "verified"),
                                                         ("derive", "error")]
    failed = DeriveReport(run_id=1, state="failed", n_series=1, n_written=0, n_skipped=0,
                          n_mismatch=2)
    code = scheduler.main(["--once", "--registry", str(reg), "--db", str(tmp_path / "q.db"),
                           "--raw-dir", str(tmp_path / "raw")],
                          now=lambda: T0, runner=_runner({}, []), log=lambda r: None,
                          deriver=_recording_deriver([], failed))
    assert code == 0                                  # a mismatching derive run is not exit-relevant


def _with_derived(reg: Path, derived: list[dict]) -> Path:
    doc = yaml.safe_load(reg.read_text())
    doc["derived"] = derived
    reg.write_text(yaml.safe_dump(doc, sort_keys=False))
    return reg


def test_main_refuses_invalid_derived_registry_before_lock(tmp_path):
    reg = _with_derived(_tiny_registry(tmp_path), [
        {"key": "derived.x", "base": "wb.ghost.PT", "formula": "period_change",
         "label": "Variação", "unit": "u"}])
    path = tmp_path / "invalid.db"
    calls: list = []
    with pytest.raises(ValueError, match="derived.x: unknown base"):
        scheduler.main(["--once", "--registry", str(reg), "--db", str(path),
                        "--raw-dir", str(tmp_path / "raw")], runner=_runner({}, calls),
                       deriver=_recording_deriver([]))
    assert calls == [] and not path.exists()
    assert not Path(str(path) + ".scheduler.lock").exists()
    assert not (tmp_path / "raw").exists()


def test_main_syncs_derived_series(tmp_path):
    reg = _with_derived(_tiny_registry(tmp_path), [
        {"key": "derived.one.mom", "base": "wb.one.PT", "formula": "period_change_pct",
         "label": "Variação mensal", "unit": "%"}])
    path = tmp_path / "p.db"
    derive_calls: list = []
    assert scheduler.main(["--once", "--registry", str(reg), "--db", str(path),
                           "--raw-dir", str(tmp_path / "raw")],
                          now=lambda: T0, runner=_runner({}, []), log=lambda r: None,
                          deriver=_recording_deriver(derive_calls)) == 0
    assert derive_calls == [{"wb.one.PT"}]
    d = open_db(path)
    try:
        rows = d.derived_series_rows()
    finally:
        d.close()
    assert [(r["key"], r["formula"], r["base_series_id"], r["unit"]) for r in rows] == [
        ("derived.one.mom", "period_change_pct", "wb.one.PT", "%")]


def test_default_deriver_runs_real_derive_scoped_to_group(tmp_path):
    """No injected deriver: the real run_derive runs for the verified group's derived series
    (no served inputs yet -> a verified run that writes nothing) with trigger 'scheduler'."""
    reg = _with_derived(_tiny_registry(tmp_path), [
        {"key": "derived.one.mom", "base": "wb.one.PT", "formula": "period_change",
         "label": "Variação mensal", "unit": "u"}])
    logged: list = []
    assert scheduler.main(["--once", "--registry", str(reg), "--db", str(tmp_path / "p.db"),
                           "--raw-dir", str(tmp_path / "raw")],
                          now=lambda: T0, runner=_runner({}, []), log=logged.append) == 0
    derive = [r for r in logged if r["event"] == "derive"]
    assert len(derive) == 1
    assert (derive[0]["group"], derive[0]["state"], derive[0]["n_written"],
            derive[0]["n_mismatch"]) == ("X.ONE", "verified", 0, 0)
    assert isinstance(derive[0]["run_id"], int)


def test_redefined_derived_key_logs_one_error_and_base_refresh_continues(tmp_path):
    """Review I1: a registry edit to an existing key's formula/base/params must not stop the
    worker. One 'derive' error record; base refresh runs; exit code as without the slip;
    the definition stored in the DB stays the one derive uses."""
    entry = {"key": "derived.one.mom", "base": "wb.one.PT", "formula": "period_change",
             "label": "Variação mensal", "unit": "u"}
    reg = _with_derived(_tiny_registry(tmp_path), [entry])
    path = tmp_path / "p.db"
    argv = ["--once", "--registry", str(reg), "--db", str(path),
            "--raw-dir", str(tmp_path / "raw")]
    assert scheduler.main(argv, now=lambda: T0, runner=_runner({}, []), log=lambda r: None,
                          deriver=_recording_deriver([])) == 0
    _with_derived(reg, [{**entry, "formula": "period_change_pct", "unit": "%"}])
    runner_calls: list = []
    derive_calls: list = []
    logged: list = []
    code = scheduler.main(argv, now=lambda: T0 + timedelta(days=30),
                          runner=_runner({}, runner_calls), log=logged.append,
                          deriver=_recording_deriver(derive_calls))
    assert code == 0
    assert [c[1] for c in runner_calls] == ["X.ONE"]          # base refresh still ran
    assert derive_calls == [{"wb.one.PT"}]                    # derive still runs (stored defs)
    errors = [r for r in logged if r["event"] == "derive"]
    assert len(errors) == 1
    assert errors[0]["state"] == "error" and errors[0]["group"] is None
    assert errors[0]["detail"].startswith("ValueError: derived.one.mom: formula/base/params")
    assert [r["event"] for r in logged if r["event"] == "attempt"] == ["attempt"]
    d = open_db(path)
    try:
        rows = d.derived_series_rows()
    finally:
        d.close()
    assert [(r["key"], r["formula"], r["unit"]) for r in rows] == [
        ("derived.one.mom", "period_change", "u")]
