"""Additional Task 18A contracts, offline only. Extends the inherited scheduler tests with
real operations/recorded-publisher integration, abrupt exits and populated migration audits.
No private verifier-registry mutation; no real publisher client is allowed in these tests.
"""
import os
import socket
import sqlite3
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
import requests
import yaml

import ingest.db as dbmod
import ingest.scheduler as scheduler
from ingest import operations
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.models import Observation, SourceSpec
from ingest.operations import GroupOutcome, group_specs
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.verifiers import get_verifier
from tests.ingest.test_scheduler import T0, _clock, _group, _runner, _tiny_registry, _wb
from tests.ingest.worldbank_fixtures import GDP_PTDES, POP_EUGRAT, FixtureHttp, specs_of
from tests.ingest.worldbank_verifier_fixtures import VerifyFixtureHttp

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network forbidden in scheduler tests")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(requests.Session, "send", refuse)


@pytest.fixture
def store(tmp_path):
    return RawStore(tmp_path / "raw")


def test_due_exact_microsecond_and_clock_rollback():
    group = _group(_wb("wb.time.PT", "X.TIME", schedule="12h"))
    boundary = T0 + timedelta(hours=12)
    assert not scheduler.due(group, T0, boundary - timedelta(microseconds=1))
    assert scheduler.due(group, T0, boundary)
    assert not scheduler.due(group, T0, T0 - timedelta(days=1))


def test_runner_sees_committed_inflight_marker_before_any_external_work(db, store):
    spec = _wb("wb.marker.PT", "X.MARKER")
    key = _group(spec).key()
    path = db.conn.execute("PRAGMA database_list").fetchone()[2]

    def runner(db, store, group, **kwargs):
        other = open_db(path)
        try:
            state = other.scheduler_state(key)
            assert state.last_attempt_state == "running"
            assert state.last_attempt_at == T0.isoformat()
            assert state.failure_streak == 1 and state.last_success_at is None
        finally:
            other.close()
        return [GroupOutcome("worldbank", group.label, "verified", run_id=1)]

    scheduler.tick(db, store, [spec], now=lambda: T0, runner=runner, log=lambda r: None)
    assert db.scheduler_state(key).last_attempt_state == "verified"


def test_retry_waits_from_completion_of_slow_failure(db, store):
    spec = _wb("wb.slow.PT", "X.SLOW")
    box, now = _clock(T0)
    calls = []

    def slow_failure(db, store, group, **kwargs):
        calls.append(group.label)
        box[0] += timedelta(hours=2)
        return [GroupOutcome("worldbank", group.label, "failed-fetch", run_id=1)]

    scheduler.tick(db, store, [spec], now=now, runner=slow_failure, log=lambda r: None)
    state = db.scheduler_state(_group(spec).key())
    assert state.last_attempt_at == T0.isoformat()
    assert state.last_finished_at == (T0 + timedelta(hours=2)).isoformat()
    box[0] = T0 + timedelta(hours=2, minutes=59)
    scheduler.tick(db, store, [spec], now=now, runner=slow_failure, log=lambda r: None)
    assert len(calls) == 1
    box[0] = T0 + timedelta(hours=3)
    scheduler.tick(db, store, [spec], now=now, runner=slow_failure, log=lambda r: None)
    assert len(calls) == 2


def test_repeated_interruption_consumes_next_backoff_and_preserves_last_success(tmp_path):
    path = tmp_path / "restarts.db"
    spec = _wb("wb.interrupted.PT", "X.INT", schedule="1d")
    key = _group(spec).key()
    db = open_db(path)
    db.scheduler_attempt_started(key, "worldbank", "X.INT", T0.isoformat())
    db.scheduler_attempt_finished(key, "verified", T0.isoformat())
    start = T0 + timedelta(days=1)
    db.scheduler_attempt_started(key, "worldbank", "X.INT", start.isoformat())
    db.close()
    db = open_db(path)
    try:
        calls = []

        def interrupted(db, store, group, **kwargs):
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            scheduler.tick(db, RawStore(tmp_path / "raw"), [spec],
                           now=lambda: start + timedelta(hours=1), runner=interrupted,
                           log=lambda r: None)
        state = db.scheduler_state(key)
        assert state.failure_streak == 2 and state.last_attempt_state == "running"
        assert state.last_success_at == T0.isoformat() and state.last_finished_at is None
        scheduler.tick(db, RawStore(tmp_path / "raw"), [spec],
                       now=lambda: start + timedelta(hours=4, minutes=59),
                       runner=_runner({}, calls), log=lambda r: None)
        assert calls == []
        scheduler.tick(db, RawStore(tmp_path / "raw"), [spec],
                       now=lambda: start + timedelta(hours=5), runner=_runner({}, calls),
                       log=lambda r: None)
        assert len(calls) == 1 and db.scheduler_state(key).failure_streak == 0
    finally:
        db.close()


def test_abrupt_process_exit_retains_marker_and_releases_lock(tmp_path):
    reg = _tiny_registry(tmp_path)
    path = tmp_path / "abrupt.db"
    raw = tmp_path / "raw"
    args = ["--once", "--db", str(path), "--raw-dir", str(raw), "--registry", str(reg)]
    code = """
import os, sys
from datetime import datetime
from ingest.scheduler import main

def die(db, store, group, **kwargs):
    os._exit(23)  # no finally blocks or connection/lock cleanup
main(sys.argv[1:], now=lambda: datetime.fromisoformat('2026-11-13T00:00:00+00:00'),
     runner=die, log=lambda r: None)
"""
    process = subprocess.run([sys.executable, "-c", code, *args], cwd=ROOT,
                             capture_output=True, text=True, timeout=30)
    assert process.returncode == 23, process.stderr
    calls = []
    assert scheduler.main(args, now=lambda: T0 + timedelta(minutes=59),
                          runner=_runner({}, calls), log=lambda r: None) == 0
    assert calls == []  # no lock leak; the committed in-flight marker prevents a retry
    assert scheduler.main(args, now=lambda: T0 + timedelta(hours=1),
                          runner=_runner({}, calls), log=lambda r: None) == 0
    assert len(calls) == 1


@pytest.mark.parametrize("bad_field,bad_value", [("schedule", "fortnightly"),
                                                ("native_code", "missing-country")])
def test_later_invalid_group_aborts_before_db_lock_or_network(tmp_path, bad_field, bad_value):
    reg = _tiny_registry(tmp_path)
    doc = yaml.safe_load(reg.read_text())
    other = {**doc["series"][0], "id": "wb.two.PT", "indicator_key": "two",
             "native_code": "X.TWO:PRT", bad_field: bad_value}
    doc["series"].append(other)
    reg.write_text(yaml.safe_dump(doc))
    path = tmp_path / "invalid.db"
    calls = []
    with pytest.raises(ValueError):
        scheduler.main(["--once", "--registry", str(reg), "--db", str(path),
                        "--raw-dir", str(tmp_path / "raw")], runner=_runner({}, calls))
    assert calls == [] and not path.exists()
    assert not Path(str(path) + ".scheduler.lock").exists()
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize("action", ["import", "help"])
def test_import_and_real_module_help_forbid_network_and_leave_paths_absent(tmp_path, action):
    path = tmp_path / "absent" / "db.sqlite3"
    raw = tmp_path / "raw"
    code = """
import runpy, sys

def audit(event, args):
    if event.startswith('socket.'):
        raise AssertionError('unexpected network during import/help: ' + event)
sys.addaudithook(audit)
if sys.argv.pop() == 'import':
    import ingest.scheduler
    print('imported')
else:
    sys.argv = ['ingest.scheduler', '--help', '--registry', '/does-not-exist/core.yaml']
    runpy.run_module('ingest.scheduler', run_name='__main__')
"""
    result = subprocess.run([sys.executable, "-c", code, action], cwd=ROOT,
                            env={**os.environ, "PRUMO_DB_PATH": str(path),
                                 "PRUMO_RAW_DIR": str(raw), "PYTHONDONTWRITEBYTECODE": "1"},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert ("--once" if action == "help" else "imported") in result.stdout
    assert not path.parent.exists() and not raw.exists()


def test_real_registry_default_paths_and_complete_authoritative_groups(tmp_path, monkeypatch):
    path = tmp_path / "env.db"
    raw = tmp_path / "env-raw"
    monkeypatch.setenv("PRUMO_DB_PATH", str(path))
    monkeypatch.setenv("PRUMO_RAW_DIR", str(raw))
    # The scheduler deliberately uses PRUMO_DB_PATH, not the older operations CLI variable.
    monkeypatch.setenv("PRUMO_DB", str(tmp_path / "wrong.db"))
    calls, records = [], []
    assert scheduler.main(["--once"], now=lambda: T0, runner=_runner({}, calls),
                          log=records.append) == 0
    specs = load_registry(scheduler.DEFAULT_REGISTRY)
    expected = []
    for name in sorted({s.source.name for s in specs}):
        active = [s for s in specs if s.source.name == name and s.active and s.source.verifiable]
        if active:
            expected.extend((name, g.label, tuple(s.id for s in g.specs))
                            for g in group_specs(active))
    assert [(name, label, ids) for name, label, at, ids in calls] == expected
    blocked = [r for r in records if r["event"] == "blocked"]
    assert [r["source"] for r in blocked] == ["dgeg"]
    assert path.exists() and not (tmp_path / "wrong.db").exists()
    assert all(name in {c[0] for c in calls} for name in ("ren", "fred", "oecd"))
    # The raw path is passed without creating an empty store tree or inventing evidence.
    assert not raw.exists()


def test_once_exit_failure_and_setup_failure_keeps_native_group_label(tmp_path):
    reg = _tiny_registry(tmp_path)
    path = tmp_path / "failed.db"
    records = []

    def runner(db, store, group, **kwargs):
        return [GroupOutcome("worldbank", "worldbank", "blocked", detail="setup failed")]

    assert scheduler.main(["--once", "--db", str(path), "--registry", str(reg)],
                          now=lambda: T0, runner=runner, log=records.append) == 1
    assert [(r["event"], r["group"], r["state"]) for r in records] == [
        ("attempt", "X.ONE", "blocked")]
    db = open_db(path)
    try:
        assert db.scheduler_state(group_specs(load_registry(reg))[0].key()).failure_streak == 1
    finally:
        db.close()


def test_lock_covers_runner_and_canonical_symlink_path_and_releases_on_interrupt(tmp_path):
    reg = _tiny_registry(tmp_path)
    path = tmp_path / "lock.db"
    alias = tmp_path / "alias.db"
    alias.symlink_to(path)
    args = ["--once", "--db", str(path), "--registry", str(reg)]

    def runner(db, store, group, **kwargs):
        with pytest.raises(SystemExit, match="already running"):
            scheduler.main(["--once", "--db", str(alias), "--registry", str(reg)],
                           runner=_runner({}, []), log=lambda r: None)
        raise KeyboardInterrupt

    assert scheduler.main(args, now=lambda: T0, runner=runner, log=lambda r: None) == 130
    assert scheduler.main(args, now=lambda: T0, runner=_runner({}, []), log=lambda r: None) == 0


def test_persistence_failure_is_fatal_before_runner(db, store, monkeypatch):
    calls = []

    def fail(*args):
        raise sqlite3.OperationalError("disk unavailable")

    monkeypatch.setattr(db, "scheduler_attempt_started", fail)
    with pytest.raises(sqlite3.OperationalError, match="disk unavailable"):
        scheduler.tick(db, store, [_wb("wb.fail.PT", "X.FAIL")],
                       runner=_runner({}, calls), log=lambda r: None)
    assert calls == []


class RecordedWorldBankHttp:
    """Original recorded JSON/CSV bytes, with explicit simulated HTTP failure statuses."""
    def __init__(self):
        self.source = FixtureHttp()
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        target = self.source if "/v2/country/" in url else self.verifier
        return target.get(url, params=params, headers=headers, timeout=timeout)


def test_registered_worldbank_path_is_per_group_and_preserves_dated_and_last_good_data(
        db, store, monkeypatch):
    specs = specs_of(GDP_PTDES + POP_EUGRAT)
    sync_registry(db, specs)
    legacy = db.legacy_run("worldbank", "legacy:worldbank", "2026-04-06T00:00:00+00:00")
    db.write_legacy_observations(legacy, [
        (Observation.from_raw(GDP_PTDES[0], "1959", "1.25"), "2026-04-06T00:00:00+00:00")])
    legacy_before = db.conn.execute("SELECT * FROM observation WHERE kind='legacy-unverified'").fetchall()
    http = RecordedWorldBankHttp()
    pop_key = ("SP.POP.TOTL", frozenset({"EU", "GR", "AT"}), 1)
    http.source.status[pop_key] = 500
    invocations, verifiers = [], []
    run_source = operations.run_source

    def observe(db, store, name, group_specs, **kwargs):
        invocations.append(tuple(s.id for s in group_specs))
        result = run_source(db, store, name, group_specs, **kwargs)
        verifiers.append(get_verifier(name))
        return result

    monkeypatch.setattr(operations, "run_source", observe)
    records = scheduler.tick(db, store, specs, now=lambda: T0,
                             http_for=lambda name: http, log=lambda r: None)
    assert [r["state"] for r in records] == ["verified", "failed-fetch"]
    assert invocations == [tuple(sorted(GDP_PTDES)), tuple(sorted(POP_EUGRAT))]
    good_key = _group(*specs_of(GDP_PTDES)).key()
    assert db.scheduler_state(good_key).failure_streak == 0
    http.source.status.clear()
    scheduler.tick(db, store, specs, now=lambda: T0 + timedelta(hours=1),
                   http_for=lambda name: http, log=lambda r: None)
    assert invocations[-1] == tuple(sorted(POP_EUGRAT)) and len(invocations) == 3
    assert all(v is verifiers[0] for v in verifiers)
    assert verifiers[0].indicator_locales == operations.WB_INDICATOR_LOCALES
    assert verifiers[0].csv_language == "en"
    held = db.conn.execute("SELECT * FROM observation ORDER BY id").fetchall()
    served = db.conn.execute("SELECT * FROM served_observation ORDER BY id").fetchall()
    assert served and db.conn.execute("SELECT COUNT(*) FROM verification WHERE passed=1").fetchone()[0] == 2
    http.source.status.update({key: 500 for key in http.source.calls})
    records = scheduler.tick(db, store, specs, now=lambda: T0 + timedelta(days=31),
                             http_for=lambda name: http, log=lambda r: None)
    assert [r["state"] for r in records] == ["failed-fetch", "failed-fetch"]
    assert db.conn.execute("SELECT * FROM observation ORDER BY id").fetchall() == held
    assert db.conn.execute("SELECT * FROM served_observation ORDER BY id").fetchall() == served
    assert db.conn.execute("SELECT * FROM observation WHERE kind='legacy-unverified'").fetchall() == legacy_before
    assert db.scheduler_state(good_key).last_success_at == T0.isoformat()


def test_source_exception_does_not_stop_a_different_source(db, store):
    fred = SourceSpec(name="fred", licence="withheld", licence_url="https://example.org",
                      attribution="test", redistribution_ok=False)
    a = _wb("wb.ok.PT", "X.OK")
    b = a.model_copy(update={"source": fred, "id": "fred.test", "native_code": "CODE"})
    calls = []
    records = scheduler.tick(db, store, [a, b], now=lambda: T0,
                             runner=_runner({"fred": RuntimeError("source exception")}, calls),
                             log=lambda r: None)
    assert [(r["source"], r["state"]) for r in records] == [("fred", "error"), ("worldbank", "verified")]


def _snapshot(db):
    tables = ("source", "series", "dataset_run", "observation", "raw_fetch", "quarantine",
              "event", "verification", "verification_item", "setting")
    return {table: db.conn.execute(f'SELECT * FROM "{table}" ORDER BY 1').fetchall()
            for table in tables}


def test_populated_upgrade_and_failed_migration_preserve_data_view_and_fk(tmp_path, monkeypatch):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    for file in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if file.stem < "0010":
            (migrations / file.name).write_bytes(file.read_bytes())
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", migrations)
    path = tmp_path / "populated.db"
    db = open_db(path)
    spec = _wb("wb.upgrade.PT", "X.UPGRADE")
    sync_registry(db, [spec])
    run = db.begin_run("worldbank", _group(spec).key(), T0.isoformat())
    raw = db.record_raw_fetch(source_name="worldbank", run_id=run, url="https://example.org",
                             params_json=None, fetched_at=T0.isoformat(), http_status=200,
                             sha256="test-only", path="test-only", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw(spec.id, "2025", "1.50"), raw, T0.isoformat())])
    db.set_run_state(run, "verified", T0.isoformat())
    db.conn.execute("INSERT INTO verification(dataset_run_id, seed, sample_size, passed, "
                    "created_at) VALUES (?, 7, 1, 1, ?)", (run, T0.isoformat()))  # 0009 shape
    db.add_event(T0.isoformat(), "revision", run, {"test": "kept"})
    legacy = db.legacy_run("worldbank", "legacy:worldbank", T0.isoformat())
    db.write_legacy_observations(legacy, [(Observation.from_raw(spec.id, "1959", "2.00"),
                                        "2026-04-06T00:00:00+00:00")])
    before = _snapshot(db)
    view = db.conn.execute("SELECT sql FROM sqlite_schema WHERE name='served_observation'").fetchone()
    served = db.conn.execute("SELECT * FROM served_observation ORDER BY id").fetchall()
    assert len(served) == 2
    db.close()
    target = migrations / "0010_scheduler_state.sql"
    original = (MIGRATIONS_DIR / target.name).read_bytes()
    target.write_bytes(original + b"\nINSERT INTO event(ts,dataset_run_id,kind) VALUES ('t',99999,'revision');\n")
    with pytest.raises(RuntimeError, match="foreign key violations"):
        open_db(path)
    raw_db = sqlite3.connect(path)
    try:
        assert raw_db.execute("SELECT name FROM sqlite_schema WHERE name='scheduler_state'").fetchall() == []
        assert raw_db.execute("SELECT version FROM schema_migration WHERE version LIKE '0010%'").fetchall() == []
    finally:
        raw_db.close()
    target.write_bytes(original)
    db = open_db(path)
    try:
        assert _snapshot(db) == before
        assert db.conn.execute("SELECT sql FROM sqlite_schema WHERE name='served_observation'").fetchone() == view
        assert db.conn.execute("SELECT * FROM served_observation ORDER BY id").fetchall() == served
        assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        with pytest.raises(sqlite3.IntegrityError):
            db.conn.execute("INSERT INTO event(ts,dataset_run_id,kind) VALUES ('t',99999,'revision')")
    finally:
        db.close()


def test_polite_source_clients_are_lazy_shared_and_reused_across_passes(db, store, monkeypatch):
    a = _wb("wb.client.a", "X.A").model_copy(update={"throttle_rps": 0.5})
    b = _wb("wb.client.b", "X.B")
    inactive = _wb("wb.client.dead", "X.DEAD", active=False).model_copy(
        update={"throttle_rps": 0.01})
    made, clients = [], []
    polite_http = operations.polite_http

    def factory(specs, name):
        made.append(name)
        return polite_http(specs, name)

    def runner(db, store, group, *, http_for, **kwargs):
        clients.append(http_for())
        return [GroupOutcome("worldbank", group.label, "failed-fetch")]

    box, now = _clock(T0)

    def sleep(seconds):
        box[0] += timedelta(seconds=seconds)

    monkeypatch.setattr(operations, "polite_http", factory)
    scheduler.serve(db, store, [a, b, inactive], now=now, sleep=sleep,
                    runner=runner, log=lambda r: None, max_ticks=6)
    assert made == ["worldbank"] and len(clients) == 4  # initial pass and +1h retry
    assert all(client is clients[0] for client in clients)
    assert clients[0].min_interval == 2.0  # most polite ACTIVE member, not inactive 0.01
    assert clients[0].timeout == operations.DEFAULT_CLIENT_TIMEOUT_S
    assert clients[0].retries == 0


@pytest.mark.parametrize("outcomes", [[],
    [GroupOutcome("worldbank", "X.BAD", "verified"), GroupOutcome("worldbank", "X.BAD", "verified")],
    [GroupOutcome("other", "X.BAD", "verified")],
    [GroupOutcome("worldbank", "wrong-group", "verified")]])
def test_malformed_runner_result_is_an_isolated_failure_not_freshness(db, store, outcomes):
    spec = _wb("wb.bad-result.PT", "X.BAD")
    records = scheduler.tick(db, store, [spec], now=lambda: T0,
                             runner=lambda *a, **kw: outcomes, log=lambda r: None)
    assert len(records) == 1 and records[0]["state"] == "error"
    state = db.scheduler_state(_group(spec).key())
    assert state is not None and state.failure_streak == 1 and state.last_success_at is None


def test_finishing_without_an_inflight_attempt_cannot_mint_success(db):
    with pytest.raises(ValueError, match="no in-flight"):
        db.scheduler_attempt_finished("absent", "verified", T0.isoformat())
    assert db.scheduler_state("absent") is None
    db.scheduler_attempt_started("key", "source", "group", T0.isoformat())
    db.scheduler_attempt_finished("key", "failed-fetch", T0.isoformat())
    before = db.scheduler_state("key")
    with pytest.raises(ValueError, match="no in-flight"):
        db.scheduler_attempt_finished("key", "verified", T0.isoformat())
    assert db.scheduler_state("key") == before
