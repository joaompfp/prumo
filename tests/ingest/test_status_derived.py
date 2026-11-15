"""Task 7 (derived layer v1): `status` reports the derived layer (counts, staleness, last run,
failed runs in 7 days) as schema prumo-status v4."""
import json
import shutil
from datetime import datetime, timedelta, timezone

import ingest.db as dbmod
from ingest.cli import main
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.derive import run_derive
from ingest.registry import sync_derived, sync_registry
from ingest.status import STALE_LIST_CAP, DerivedStatus, build_status, render_text
from tests.ingest.derived_helpers import derived_spec, verified_values
from tests.ingest.fakes import spec
from tests.ingest.test_cli import _write_registry

T1 = "2026-11-01T00:00:00+00:00"
NOW = datetime(2026, 11, 14, tzinfo=timezone.utc)
LATER = NOW + timedelta(hours=6)
S1 = {"2024-12": "100", "2025-01": "102.5", "2025-02": "99"}
PC, RB = "derived.s1_pc", "derived.s1_rb"
SPECS = [spec("s1", frequency="M")]


def _setup(db):
    sync_registry(db, SPECS)
    verified_values(db, "s1", S1, T1, "k1")
    sync_derived(db, [derived_spec(PC, "s1", "period_change"),
                      derived_spec(RB, "s1", "rebase_100",
                                   params={"base_period": "2025-01"})])


def _derive(db, at=NOW):
    return run_derive(db, trigger="cli", now=lambda: at)


def _derived(db, at=LATER) -> DerivedStatus:
    return build_status(db, SPECS, now=lambda: at).derived


def _failed_run(db, at: datetime) -> int:
    run = db.begin_derived_run(at.isoformat(), "scheduler", [PC])
    db.finish_derived_run(run, "failed", at.isoformat(), n_written=0, n_checked=0,
                          n_mismatch=0)
    return run


def test_status_without_derived_series_reports_zeroes(db):
    sync_registry(db, SPECS)
    verified_values(db, "s1", S1, T1, "k1")
    assert _derived(db) == DerivedStatus(
        active_series=0, served_values=0, stale=0, never_computed=0, stale_series=(),
        last_run_id=None, last_run_state=None, last_run_at=None, failed_runs_7d=0)


def test_derived_fresh_after_derive(db):
    _setup(db)
    rep = _derive(db)
    assert _derived(db) == DerivedStatus(
        active_series=2, served_values=5, stale=0, never_computed=0, stale_series=(),
        last_run_id=rep.run_id, last_run_state="verified", last_run_at=NOW.isoformat(),
        failed_runs_7d=0)


def test_derived_stale_after_new_base_vintage(db):
    _setup(db)
    _derive(db)
    # a new verified base vintage fetched after the derive run, no derive since
    verified_values(db, "s1", {**S1, "2025-02": "98"}, (NOW + timedelta(hours=1)).isoformat(),
                    "k1")
    d = _derived(db)
    assert (d.stale, d.never_computed, d.stale_series) == (2, 0, (PC, RB))


def test_staleness_is_compared_as_time_not_text(db):
    _setup(db)
    # a run stamped with a non-UTC offset: 03:00+02:00 is 01:00Z
    _derive(db, at=datetime(2026, 11, 14, 3, tzinfo=timezone(timedelta(hours=2))))
    # base fetched at 02:00Z: textually EARLIER than the run's stamp, later in time
    verified_values(db, "s1", {**S1, "2025-02": "98"}, "2026-11-14T02:00:00+00:00", "k1")
    assert _derived(db).stale_series == (PC, RB)


def test_derived_never_computed(db):
    _setup(db)
    d = _derived(db)
    assert (d.active_series, d.never_computed, d.stale, d.served_values) == (2, 2, 0, 0)
    assert d.last_run_id is None and d.stale_series == ()


def test_failed_run_does_not_cover_series(db):
    _setup(db)
    run = _failed_run(db, NOW)
    d = _derived(db)
    assert (d.never_computed, d.last_run_id, d.last_run_state) == (2, run, "failed")


def test_failed_runs_7d_counted(db):
    _setup(db)
    _failed_run(db, LATER - timedelta(days=8))   # outside the window
    _failed_run(db, LATER - timedelta(days=6))
    _derive(db)                                   # verified: not counted
    _failed_run(db, LATER - timedelta(hours=1))
    assert _derived(db).failed_runs_7d == 2


def test_text_has_derived_line(db):
    _setup(db)
    rep = _derive(db)
    verified_values(db, "s1", {**S1, "2025-02": "98"}, (NOW + timedelta(hours=1)).isoformat(),
                    "k1")
    _failed_run(db, LATER - timedelta(hours=1))
    lines = render_text(build_status(db, SPECS, now=lambda: LATER)).splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith("all sources:"))
    # the failed run is the newest one; the served values are hidden by the new vintage
    last = rep.run_id + 1
    assert lines[i + 1] == (
        f"derived: 2 active series; 0 served values; stale 2 / never computed 0; last run "
        f"{last} (failed, {(LATER - timedelta(hours=1)).isoformat()}); failed runs 7d 1")
    assert lines[i + 2] == f"  DERIVED STALE {PC}, {RB}"


def test_text_stale_list_is_capped(db):
    sync_registry(db, SPECS)
    verified_values(db, "s1", S1, T1, "k1")
    keys = [f"derived.s1_pc{n:02d}" for n in range(STALE_LIST_CAP + 2)]
    sync_derived(db, [derived_spec(k, "s1", "period_change") for k in keys])
    _derive(db)
    verified_values(db, "s1", {**S1, "2025-02": "98"}, LATER.isoformat(), "k1")
    text = render_text(build_status(db, SPECS, now=lambda: LATER + timedelta(hours=1)))
    assert f"  DERIVED STALE {', '.join(keys[:STALE_LIST_CAP])} (+2 more)" in text.splitlines()


def test_text_line_when_nothing_derived(db):
    sync_registry(db, SPECS)
    lines = render_text(build_status(db, SPECS, now=lambda: LATER)).splitlines()
    assert ("derived: 0 active series; 0 served values; stale 0 / never computed 0; "
            "last run - (-, -); failed runs 7d 0") in lines
    assert not any("DERIVED STALE" in line for line in lines)


def test_json_has_derived_and_version_4(db):
    _setup(db)
    rep = _derive(db)
    doc = json.loads(build_status(db, SPECS, now=lambda: LATER).to_json())
    assert doc["schema"] == "prumo-status" and doc["version"] == 4
    assert doc["derived"] == {
        "active_series": 2, "served_values": 5, "stale": 0, "never_computed": 0,
        "stale_series": [], "last_run_id": rep.run_id, "last_run_state": "verified",
        "last_run_at": NOW.isoformat(), "failed_runs_7d": 0}


def test_status_on_a_pre_0014_database_is_refused_not_crashed(tmp_path, capsys, monkeypatch):
    """Production sits at 0013 until the deploy: the read-only gate refuses it cleanly
    (exit 2, names the missing migration) before any derived read runs."""
    old = tmp_path / "migrations-0013"
    old.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem < "0014":
            shutil.copy(f, old / f.name)
    path = tmp_path / "prod.sqlite3"
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", old)
    open_db(path).close()
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)
    reg = _write_registry(tmp_path / "core.yaml", SPECS)
    rc = main(["--db", str(path), "--registry", str(reg), "status"])
    err = capsys.readouterr().err
    assert rc == 2 and "older than this code" in err and "0014_derived_layer" in err
    assert "Traceback" not in err
