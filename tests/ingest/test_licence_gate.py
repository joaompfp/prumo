"""Serving licence gate (migration 0005, Ruling AD, spec §11.4).

`served_observation` serves a row only when the SERIES' publisher has source.redistribution_ok=1.
Verification is technical and does not authorize serving: a run can be `verified` while every one
of its rows is legally withheld (verified != served). Revoking or reapproving a source's
redistribution_ok through the normal registry sync takes effect IMMEDIATELY for existing rows —
fetched and legacy alike, legacy_served='1' included — without deleting any observation, run or
history row, and with every other serving rule (verified runs only, latest vintage wins, legacy
never hides fetched) unchanged.
"""
import sqlite3

from ingest.db import MIGRATIONS_DIR, open_db
from ingest.models import Observation, SeriesSpec, SourceSpec
from ingest.registry import sync_registry

T = "2026-01-01T00:00:00+00:00"

DENIED = SourceSpec(name="denied", licence="No reuse grant", licence_url="http://l",
                    attribution="Denied", redistribution_ok=False)
ALLOWED = SourceSpec(name="allowed", licence="CC BY 4.0", licence_url="http://l",
                     attribution="Allowed", redistribution_ok=True)


def _spec(source: SourceSpec, sid: str) -> SeriesSpec:
    return SeriesSpec(id=sid, source=source, indicator_key=f"k_{sid}", role="primary",
                      theme="energy", geography="PT", frequency="A", unit="GWh")


def _sync(db, source: SourceSpec, *sids: str) -> None:
    """Normal registry sync (upsert_source_and_series): how a licence toggle reaches the DB."""
    sync_registry(db, [_spec(source, sid) for sid in sids])


def _fetched(db, spec: SeriesSpec, period: str, token: str, *, dataset_key: str = "ds") -> int:
    run = db.begin_run(spec.source.name, dataset_key, T)
    fid = db.record_raw_fetch(source_name=spec.source.name, run_id=run, url="http://x",
                              params_json=None, fetched_at=T, http_status=200,
                              sha256=f"sha-{token}", path="p", n_bytes=1, ok=True)
    obs = Observation.from_raw(spec.id, period, token, decimal=spec.decimal)
    db.write_observations(run, [(obs, fid, T)])
    db.set_run_state(run, "verified", finished_at=T)
    return run


def _legacy(db, spec: SeriesSpec, period: str, token: str) -> int:
    run = db.legacy_run(spec.source.name, f"legacy-{spec.source.name}", T)
    obs = Observation.from_raw(spec.id, period, token, decimal=spec.decimal)
    db.write_legacy_observations(run, [(obs, T)])
    return run


def _served(db):
    return db.conn.execute(
        "SELECT series_id, period, value_text FROM served_observation ORDER BY 1, 2").fetchall()


def _count(db, table: str) -> int:
    return db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_verified_fetched_rows_of_denied_source_are_verified_but_never_served(db):
    (spec,) = [_spec(DENIED, "d1")]
    _sync(db, DENIED, "d1")
    _fetched(db, spec, "2025", "10.5")
    assert _served(db) == []
    # technical verification passed and the rows exist: verified != served
    assert db.conn.execute("SELECT state FROM dataset_run").fetchone()[0] == "verified"
    assert _count(db, "observation") == 1


def test_legacy_rows_of_denied_source_hidden_even_with_legacy_served(db):
    denied, allowed = _spec(DENIED, "d1"), _spec(ALLOWED, "a1")
    _sync(db, DENIED, "d1")
    _sync(db, ALLOWED, "a1")
    _legacy(db, denied, "2024", "7")
    _legacy(db, allowed, "2024", "8")
    assert _served(db) == []
    db.conn.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")
    assert _served(db) == [("a1", "2024", "8")]


def test_revocation_withdraws_and_reapproval_restores_existing_rows_immediately(db):
    fetched = _spec(ALLOWED, "a1")
    _sync(db, ALLOWED, "a1", "a2")
    _fetched(db, fetched, "2025", "1")
    _legacy(db, _spec(ALLOWED, "a2"), "2024", "2")
    db.conn.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")
    assert _served(db) == [("a1", "2025", "1"), ("a2", "2024", "2")]
    _sync(db, SourceSpec(**{**ALLOWED.model_dump(), "redistribution_ok": False}), "a1", "a2")
    assert _served(db) == []  # immediate revocation, fetched and legacy alike
    assert _count(db, "observation") == 2 and _count(db, "dataset_run") == 2  # nothing deleted
    _sync(db, ALLOWED, "a1", "a2")  # reapproval
    assert _served(db) == [("a1", "2025", "1"), ("a2", "2024", "2")]


def test_mixed_sources_only_the_allowed_side_is_served(db):
    _sync(db, DENIED, "d1")
    _sync(db, ALLOWED, "a1")
    _fetched(db, _spec(DENIED, "d1"), "2025", "10")
    _fetched(db, _spec(ALLOWED, "a1"), "2025", "20")
    assert _served(db) == [("a1", "2025", "20")]


def test_vintage_and_legacy_precedence_unchanged_inside_allowed_source(db):
    spec = _spec(ALLOWED, "a1")
    _sync(db, ALLOWED, "a1")
    _fetched(db, spec, "2025", "1.0", dataset_key="ds1")
    _fetched(db, spec, "2025", "2.0", dataset_key="ds2")  # newer vintage wins
    assert _served(db) == [("a1", "2025", "2.0")]
    _legacy(db, spec, "2024", "9")  # legacy only when no fetched row at that period
    _legacy(db, spec, "2025", "7")  # never hides the fetched vintage
    assert _served(db) == [("a1", "2025", "2.0")]
    db.conn.execute("UPDATE setting SET value='1' WHERE key='legacy_served'")
    assert _served(db) == [("a1", "2024", "9"), ("a1", "2025", "2.0")]


def test_unverified_runs_stay_hidden_for_allowed_and_denied_sources(db):
    _sync(db, ALLOWED, "a1")
    run = db.begin_run("allowed", "ds", T)
    fid = db.record_raw_fetch(source_name="allowed", run_id=run, url="http://x",
                              params_json=None, fetched_at=T, http_status=200, sha256="s",
                              path="p", n_bytes=1, ok=True)
    db.write_observations(run, [(Observation.from_raw("a1", "2025", "1"), fid, T)])
    db.set_run_state(run, "failed-verification", finished_at=T)
    assert _served(db) == []


def test_view_columns_are_exactly_the_observation_columns_in_order(db):
    want = [r[1] for r in db.conn.execute("PRAGMA table_info(observation)")]
    got = [r[1] for r in db.conn.execute("PRAGMA table_info(served_observation)")]
    assert got == want


def test_migrating_an_existing_0004_database_preserves_history_and_gates(tmp_path):
    """A real 0001-0004 database (schema from the migration scripts, rows written under the
    PRE-gate view semantics) migrates to 0005: the gate activates, every row survives."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute("CREATE TABLE schema_migration(version TEXT PRIMARY KEY, "
                 "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP) STRICT")
    for stem in ("0001_init", "0002_dataset_key", "0003_verification_replay",
                 "0004_verification_audit"):
        conn.executescript(f"BEGIN;\n{(MIGRATIONS_DIR / f'{stem}.sql').read_text()}\n"
                           f"INSERT INTO schema_migration(version) VALUES ('{stem}');\nCOMMIT;")
    conn.execute("INSERT INTO source(name, licence, licence_url, attribution, "
                 "redistribution_ok) VALUES ('denied', 'L', 'u', 'D', 0),"
                 "('allowed', 'L', 'u', 'A', 1)")
    conn.execute("INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
                 "frequency, unit, active) VALUES "
                 "('d1', 1, 'k_d1', 'primary', 'energy', 'PT', 'A', 'GWh', 1),"
                 "('a1', 2, 'k_a1', 'primary', 'energy', 'PT', 'A', 'GWh', 1)")
    conn.execute(f"INSERT INTO dataset_run(id, source_id, started_at, finished_at, state, "
                 f"dataset_key) VALUES (1, 1, '{T}', '{T}', 'verified', 'ds-d1'),"
                 f"(2, 2, '{T}', '{T}', 'verified', 'ds-a1')")
    conn.execute(f"INSERT INTO raw_fetch(source_id, dataset_run_id, url, fetched_at, http_status,"
                 f" sha256, path, bytes, ok) VALUES (1, 1, 'http://x', '{T}', 200, 'sd', 'p', 1, 1),"
                 f"(2, 2, 'http://x', '{T}', 200, 'sa', 'p', 1, 1),"
                 f"(2, 2, 'http://y', '{T}', 200, 'sb', 'p', 1, 1)")
    # two vintages of a1 (id order = vintage order), one denied vintage of d1 (older token)
    conn.execute(f"INSERT INTO observation(series_id, period, value_text, value, kind, "
                 f"dataset_run_id, raw_fetch_id, fetched_at) VALUES "
                 f"('a1', '2025', '1.0', 1.0, 'fetched', 2, 2, '{T}'),"
                 f"('d1', '2025', '9.0', 9.0, 'fetched', 1, 1, '{T}'),"
                 f"('a1', '2025', '2.0', 2.0, 'fetched', 2, 3, '{T}')")
    conn.execute("INSERT INTO quarantine(dataset_run_id, series_id, raw_period, raw_value, "
                 "reason, created_at) VALUES (1, 'd1', 'x', 'y', 'non_numeric', 't')")
    before_obs = conn.execute("SELECT * FROM observation ORDER BY id").fetchall()
    before_runs = conn.execute("SELECT * FROM dataset_run ORDER BY id").fetchall()
    before_quar = conn.execute("SELECT * FROM quarantine ORDER BY id").fetchall()
    # pre-migration view semantics: the denied row leaks (this is the defect 0005 closes)
    assert ("d1", "2025", "9.0") in conn.execute(
        "SELECT series_id, period, value_text FROM served_observation").fetchall()
    conn.close()

    db = open_db(path)
    try:
        versions = {r[0] for r in db.conn.execute("SELECT version FROM schema_migration")}
        assert {"0001_init", "0002_dataset_key", "0003_verification_replay",
                "0004_verification_audit", "0005_served_licence_gate"} <= versions
        # every row survived the view replacement byte-identical (nothing deleted, no rewrite)
        assert db.conn.execute("SELECT * FROM observation ORDER BY id").fetchall() == before_obs
        assert db.conn.execute("SELECT * FROM dataset_run ORDER BY id").fetchall() == before_runs
        assert db.conn.execute("SELECT * FROM quarantine ORDER BY id").fetchall() == before_quar
        # gate active: denied row withheld, allowed latest vintage served
        assert _served(db) == [("a1", "2025", "2.0")]
    finally:
        db.close()
