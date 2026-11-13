# Task 2 report
Status: DONE. Commit: see `git log -1` on pipeline-rebuild ("ingest: sqlite schema + data-access module").
RED: `pytest tests/ingest` -> ModuleNotFoundError: No module named 'ingest.db' (conftest import).
GREEN: `pytest tests/ingest -q` -> 9 passed; full `pytest tests` -> 13 passed.
Files: ingest/__init__.py, ingest/db.py, ingest/migrations/0001_init.sql, tests/ingest/{__init__,conftest,test_db}.py
Design: STRICT tables; all constraints in SQL. Period vs frequency enforced by BEFORE INSERT / BEFORE UPDATE OF (series_id, period) triggers joining series.frequency (RAISE(ABORT) -> sqlite3.IntegrityError); M checks month 01-12, D also requires date(period)=period. kind/raw_fetch_id CHECK; UNIQUE(series_id,period,raw_fetch_id). setting table seeded legacy_served='0'. served_observation: latest id per (series,period) among rows from verified runs (legacy only when setting='1'); a later eligible row supersedes legacy.
Migration runner: executescript("BEGIN; <sql>; INSERT schema_migration; COMMIT;") with rollback on error; Db.transaction uses BEGIN IMMEDIATE; connection isolation_level=None. Db exposes `conn`.
Concerns: UNIQUE with NULL raw_fetch_id doesn't dedupe legacy rows (SQL NULL semantics). "Latest" uses observation.id, so ids must be monotonic with fetch order. ruff not installed in .venv-ci (not run). Period trigger is duplicated for insert/update (SQLite has no combined trigger).

## Fix round 1 (I-1, I-2)
Changed (ingest/migrations/0001_init.sql, edited in place): value_text is now `TEXT NOT NULL CHECK (length(value_text) > 0)`; served_observation's NOT EXISTS now hides a legacy row whenever any eligible fetched row exists for the same (series, period), regardless of id order; otherwise same-kind rows compete by highest id.
Tests added in tests/ingest/test_db.py: test_legacy_never_hides_verified_fetched, test_legacy_served_when_enabled_and_no_fetched, test_legacy_hidden_when_setting_off, test_legacy_in_pending_run_hidden_even_when_enabled, test_rejects_null_or_empty_value_text[NULL/''].
RED (before fix): 3 failed (legacy_never_hides, both value_text cases), 12 passed.
Command: /home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -v
Output (GREEN):
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.2.0, pluggy-1.7.0 -- /home/joao/projects/prumo-pipeline/.venv-ci/bin/python
cachedir: .pytest_cache
rootdir: /home/joao/projects/prumo-pipeline
configfile: pytest.ini
plugins: anyio-4.16.0
collecting ... collected 15 items

tests/ingest/test_db.py::test_open_applies_migrations_once PASSED        [  6%]
tests/ingest/test_db.py::test_rejects_null_value PASSED                  [ 13%]
tests/ingest/test_db.py::test_rejects_empty_unit PASSED                  [ 20%]
tests/ingest/test_db.py::test_rejects_bad_period_format PASSED           [ 26%]
tests/ingest/test_db.py::test_frequency_mismatch_rejected PASSED         [ 33%]
tests/ingest/test_db.py::test_fetched_observation_requires_raw_fetch PASSED [ 40%]
tests/ingest/test_db.py::test_duplicate_series_period_raw_rejected PASSED [ 46%]
tests/ingest/test_db.py::test_served_view_excludes_unverified_runs PASSED [ 53%]
tests/ingest/test_db.py::test_served_view_returns_latest_vintage_only PASSED [ 60%]
tests/ingest/test_db.py::test_legacy_never_hides_verified_fetched PASSED [ 66%]
tests/ingest/test_db.py::test_legacy_served_when_enabled_and_no_fetched PASSED [ 73%]
tests/ingest/test_db.py::test_legacy_hidden_when_setting_off PASSED      [ 80%]
tests/ingest/test_db.py::test_legacy_in_pending_run_hidden_even_when_enabled PASSED [ 86%]
tests/ingest/test_db.py::test_rejects_null_or_empty_value_text[NULL] PASSED [ 93%]
tests/ingest/test_db.py::test_rejects_null_or_empty_value_text[''] PASSED [100%]

============================== 15 passed in 2.83s ==============================
```
