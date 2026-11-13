"""Migration 0007: source-scoped eligibility of legacy rows (Task 17A).

`legacy_served` stays the explicit GLOBAL switch (default 0, backward compatible). 0007 seeds
exactly ONE source-scoped permission, `legacy_served_source:worldbank` = '1': legacy World Bank
rows of ACTIVE, redistribution-cleared series become servable — with their honest original
fetched_at dates, legacy kind and NULL raw_fetch untouched — while every other source's legacy
rows stay unserved and the inactive PPP unit-conflict series are never exposed by the scoped
switch. A verified fetched row always beats legacy at the same period, and a FAILED fresh run
neither hides nor replaces old good data (its own rows never become eligible).
"""
import sqlite3

from ingest.db import MIGRATIONS_DIR, open_db
from ingest.models import Observation, SeriesSpec, SourceSpec
from ingest.registry import sync_registry

T = "2026-01-01T00:00:00+00:00"

WB = SourceSpec(name="worldbank", licence="CC BY 4.0", licence_url="http://l",
                attribution="WB", redistribution_ok=True)
EREDES = SourceSpec(name="eredes", licence="CC BY 4.0", licence_url="http://l",
                    attribution="E-REDES", redistribution_ok=True)
FRED = SourceSpec(name="fred", licence="UNVERIFIED", licence_url="http://l",
                  attribution="FRED", redistribution_ok=False)
DGEG = SourceSpec(name="dgeg", licence="UNVERIFIED", licence_url="http://l",
                  attribution="DGEG", redistribution_ok=False)


def _spec(source: SourceSpec, sid: str, active: bool = True) -> SeriesSpec:
    return SeriesSpec(id=sid, source=source, indicator_key=f"k_{sid}", role="primary",
                      theme="economy", geography="PT", frequency="A", unit="u", active=active)


def _fetched(db, spec, period, token, *, state="verified", dataset_key="ds"):
    run = db.begin_run(spec.source.name, dataset_key, T)
    fid = db.record_raw_fetch(source_name=spec.source.name, run_id=run, url="http://x",
                              params_json=None, fetched_at=T, http_status=200,
                              sha256=f"sha-{spec.id}-{period}-{token}", path="p",
                              n_bytes=1, ok=True)
    obs = Observation.from_raw(spec.id, period, token, decimal=spec.decimal)
    db.write_observations(run, [(obs, fid, T)])
    db.set_run_state(run, state, finished_at=T)
    return run


def _legacy(db, spec, period, token, fetched_at=T):
    run = db.legacy_run(spec.source.name, f"legacy:{spec.source.name}", T)
    obs = Observation.from_raw(spec.id, period, token, decimal=spec.decimal)
    db.write_legacy_observations(run, [(obs, fetched_at)])
    return run


def _served(db):
    return db.conn.execute(
        "SELECT series_id, period, value_text, fetched_at FROM served_observation "
        "ORDER BY 1, 2").fetchall()


def _set(db, key, value):
    db.conn.execute("INSERT OR REPLACE INTO setting(key, value) VALUES (?, ?)", (key, value))


def test_seed_is_worldbank_only_and_global_default_stays_zero(db):
    settings = dict(db.conn.execute("SELECT key, value FROM setting"))
    assert settings == {"legacy_served": "0", "legacy_served_source:worldbank": "1"}


def test_worldbank_active_legacy_available_without_the_global_flag(db):
    spec = _spec(WB, "wb.a")
    sync_registry(db, [spec])
    _legacy(db, spec, "2024", "9", fetched_at="2026-03-01T10:00:00+00:00")
    # honest original retrieval date and kind survive: the served row carries the legacy
    # fetched_at, not a refreshed timestamp
    assert _served(db) == [("wb.a", "2024", "9", "2026-03-01T10:00:00+00:00")]
    row = db.conn.execute("SELECT kind, raw_fetch_id FROM observation").fetchone()
    assert row == ("legacy-unverified", None)


def test_inactive_worldbank_series_not_exposed_by_the_scoped_flag(db):
    # the PPP unit-conflict analogue: the source is scoped-allowed, the series is not active
    spec = _spec(WB, "wb.ppp", active=False)
    sync_registry(db, [spec])
    _legacy(db, spec, "2024", "9")
    assert _served(db) == []


def test_other_sources_legacy_stay_unserved(db):
    specs = [_spec(EREDES, "e.a"), _spec(FRED, "f.a"), _spec(DGEG, "d.a", active=False)]
    sync_registry(db, specs)
    for s in specs:
        _legacy(db, s, "2024", "1")
    assert _served(db) == []


def test_a_scoped_key_is_generic_but_requires_licence_and_active(db):
    e_on, e_off, f = _spec(EREDES, "e.on"), _spec(EREDES, "e.off", active=False), _spec(FRED, "f.a")
    sync_registry(db, [e_on, e_off, f])
    for s in (e_on, e_off, f):
        _legacy(db, s, "2024", "1")
    _set(db, "legacy_served_source:eredes", "1")   # licensed + active only
    _set(db, "legacy_served_source:fred", "1")     # licence gate still wins
    assert _served(db) == [("e.on", "2024", "1", T)]


def test_scoped_legacy_revocation_and_reapproval_are_immediate(db):
    spec = _spec(WB, "wb.a")
    sync_registry(db, [spec])
    _legacy(db, spec, "2024", "9")
    assert len(_served(db)) == 1
    denied = SourceSpec(**{**WB.model_dump(), "redistribution_ok": False})
    sync_registry(db, [_spec(denied, "wb.a")])
    assert _served(db) == []
    sync_registry(db, [spec])  # reapproval
    assert _served(db) == [("wb.a", "2024", "9", T)]


def test_verified_fetched_beats_legacy_and_a_failed_fresh_run_hides_nothing(db):
    spec = _spec(WB, "wb.a")
    sync_registry(db, [spec])
    _legacy(db, spec, "2023", "7")
    _legacy(db, spec, "2024", "9")
    _fetched(db, spec, "2024", "2.0")                      # verified fresh vintage wins
    assert _served(db) == [("wb.a", "2023", "7", T), ("wb.a", "2024", "2.0", T)]
    _fetched(db, spec, "2023", "8.0", state="failed-verification", dataset_key="ds2")
    _fetched(db, spec, "2024", "3.0", state="failed-fetch", dataset_key="ds3")
    # failed fresh rows never become eligible and never hide the old good data
    assert _served(db) == [("wb.a", "2023", "7", T), ("wb.a", "2024", "2.0", T)]


def test_global_legacy_served_still_covers_inactive_series(db):
    """Backward compatibility of the explicit global switch (0005 semantics, unchanged)."""
    spec = _spec(WB, "wb.ppp", active=False)
    sync_registry(db, [spec])
    _legacy(db, spec, "2024", "9")
    _set(db, "legacy_served", "1")
    assert _served(db) == [("wb.ppp", "2024", "9", T)]


def test_upgrade_from_a_populated_0006_database(tmp_path):
    """Rows, kinds and NULL raw_fetch references migrate byte-identical; only serving changes."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute("CREATE TABLE schema_migration(version TEXT PRIMARY KEY, "
                 "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP) STRICT")
    for stem in ("0001_init", "0002_dataset_key", "0003_verification_replay",
                 "0004_verification_audit", "0005_served_licence_gate", "0006_pt15m"):
        conn.executescript(f"BEGIN;\n{(MIGRATIONS_DIR / f'{stem}.sql').read_text()}\n"
                           f"INSERT INTO schema_migration(version) VALUES ('{stem}');\nCOMMIT;")
    conn.execute("INSERT INTO source(id, name, licence, licence_url, attribution, "
                 "redistribution_ok) VALUES (1, 'worldbank', 'CC BY 4.0', 'u', 'WB', 1),"
                 "(2, 'eredes', 'CC BY 4.0', 'u', 'E-REDES', 1)")
    conn.execute("INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
                 "frequency, unit, active) VALUES ('wb.a', 1, 'k', 'primary', 'economy', 'PT', "
                 "'A', 'u', 1), ('wb.ppp', 1, 'k2', 'primary', 'economy', 'PT', 'A', 'u', 0),"
                 "('e.a', 2, 'k3', 'primary', 'energy', 'PT', 'A', 'u', 1)")
    conn.execute(f"INSERT INTO dataset_run(id, source_id, started_at, finished_at, state, "
                 f"dataset_key) VALUES (1, 1, '{T}', '{T}', 'verified', 'legacy:worldbank'),"
                 f"(2, 2, '{T}', '{T}', 'verified', 'legacy:eredes'),"
                 f"(3, 1, '{T}', '{T}', 'verified', 'wb-ds')")
    conn.execute(f"INSERT INTO raw_fetch(source_id, dataset_run_id, url, fetched_at, "
                 f"http_status, sha256, path, bytes, ok) VALUES (1, 3, 'http://x', '{T}', 200, "
                 f"'s', 'p', 1, 1)")
    conn.execute(f"INSERT INTO observation(series_id, period, value_text, value, kind, "
                 f"dataset_run_id, raw_fetch_id, fetched_at) VALUES "
                 f"('wb.a', '2024', '9', 9.0, 'legacy-unverified', 1, NULL, '2026-03-01T10:00:00+00:00'),"
                 f"('wb.ppp', '2024', '5', 5.0, 'legacy-unverified', 1, NULL, '{T}'),"
                 f"('e.a', '2024', '1', 1.0, 'legacy-unverified', 2, NULL, '{T}'),"
                 f"('wb.a', '2025', '2.0', 2.0, 'fetched', 3, 1, '{T}')")
    before = conn.execute("SELECT * FROM observation ORDER BY id").fetchall()
    # pre-migration (0005 semantics, global 0): only the fetched row is served
    assert conn.execute("SELECT series_id, period FROM served_observation").fetchall() == \
        [("wb.a", "2025")]
    conn.close()

    db = open_db(path)
    try:
        assert db.conn.execute("SELECT * FROM observation ORDER BY id").fetchall() == before
        assert db.conn.execute("SELECT COUNT(*) FROM observation WHERE kind = "
                               "'legacy-unverified' AND raw_fetch_id IS NULL").fetchone()[0] == 3
        assert _served(db) == [("wb.a", "2024", "9", "2026-03-01T10:00:00+00:00"),
                               ("wb.a", "2025", "2.0", T)]
    finally:
        db.close()
