### Task 2: SQLite schema and data-access module

**Files:**
- Create: `ingest/__init__.py`, `ingest/db.py`, `ingest/migrations/0001_init.sql`, `tests/ingest/__init__.py`, `tests/ingest/test_db.py`, `tests/ingest/conftest.py`

**Interfaces:**
- Produces: `ingest.db.open_db(path: str | Path) -> Db` (WAL, `foreign_keys=ON`, runs pending migrations, records them in `schema_migration`); class `Db` with context-managed `transaction()`; all later tasks add methods to `Db`.
- Tables (STRICT, all with CHECK/UNIQUE/FK): `source(id, name UNIQUE, licence, licence_url, attribution, redistribution_ok INTEGER CHECK IN (0,1))`; `series(id TEXT PK, source_id FK, indicator_key, role CHECK IN ('primary','cross_check'), theme CHECK IN ('economy','demography','energy'), geography, frequency CHECK IN ('A','S','Q','M','D'), unit NOT NULL, multiplier, seasonal_adjustment, base_year, native_code, url, active)`; `raw_fetch(id, source_id, url, params_json, fetched_at, http_status, sha256, path, bytes, ok INTEGER)`; `dataset_run(id, source_id, started_at, finished_at, state CHECK IN ('running','fetched','failed-fetch','failed-validation','pending-verification','verified','failed-verification'))`; `observation(id, series_id FK, period, value_text, value REAL NOT NULL, status_flag, kind CHECK IN ('fetched','legacy-unverified'), dataset_run_id FK, raw_fetch_id FK NULL only when kind='legacy-unverified', fetched_at, released_at, UNIQUE(series_id, period, raw_fetch_id))`; `quarantine(id, dataset_run_id, series_id, raw_period, raw_value, reason, created_at)`; `event(id, ts, dataset_run_id, kind CHECK IN ('fetch_failure','format_change','revision','cross_check_gap','verification_failure','refetch'), detail_json)`; `verification(id, dataset_run_id, seed, sample_size, passed INTEGER, created_at)`; `verification_item(id, verification_id, series_id, period, expected_text, observed_text, evidence_url, match INTEGER)`; view `served_observation` = latest `observation` per (series, period) from a `dataset_run` in state `verified` (legacy rows only until superseded, and only when `legacy_served` setting is 1, default 0).
- Constraints that must be enforced by the DB: `period` GLOB patterns per frequency; `unit` non-empty; `value` NOT NULL; unique raw per observation; `observation.kind='fetched'` requires `raw_fetch_id`.

- [ ] **Step 1: Write failing tests** in `tests/ingest/test_db.py` (use `tmp_path`): `test_open_applies_migrations_once`; `test_rejects_null_value`; `test_rejects_empty_unit`; `test_rejects_bad_period_format` (`"Setembro de 2025"`); `test_fetched_observation_requires_raw_fetch`; `test_duplicate_series_period_raw_rejected`; `test_served_view_excludes_unverified_runs` (insert observation in a `pending-verification` run → view empty; flip run to `verified` → 1 row); `test_served_view_returns_latest_vintage_only`.
- [ ] **Step 2: Run** `pytest tests/ingest/test_db.py -v` → FAIL.
- [ ] **Step 3: Implement** `open_db`, `Db.transaction`, `schema_migration` runner (applies `NNNN_*.sql` in order inside a transaction), and `0001_init.sql` per the table list above.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** (`ingest: sqlite schema + data-access module`).

---

