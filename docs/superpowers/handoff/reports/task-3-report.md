# Task 3 report
Status: DONE. Commit 5bef97e.
RED: pytest tests/ingest -> "ModuleNotFoundError: No module named 'ingest.registry'" (2 collection errors).
One mid-way failure: "3º Trimestre" (NFKD turns º into "o"); regex fixed.
GREEN: 52 passed in 3.03s (15 db + 22 models + 11 registry... all tests/ingest).
Files: ingest/models.py, ingest/registry.py, ingest/db.py (+Db.upsert_source_and_series), registry/core.yaml, tests/ingest/test_models.py, tests/ingest/test_registry.py, requirements.txt (+pydantic>=2, pyyaml).
Design: SeriesSpec.source is an embedded SourceSpec (name, licence, licence_url, attribution, redistribution_ok); YAML `series[].source` is the source name. schedule/throttle_rps not in SQL. Extras: unknown YAML keys rejected (extra=forbid); duplicate series ids rejected; 0 primaries for a key rejected.
Concerns: none significant. D-frequency normalization (ISO date) added beyond brief cases.

## Fix round 1 (I-1, I-2)
Observation.value is now validated against parse_number(value_text, decimal) (model validator; decimal via validation context); bool/str value rejected; Observation.from_raw(series_id, period, value_text, decimal=".", ...) parses. parse_number(text, decimal=".") is strict per ruling H (declared decimal, thousands only in exact 3-digit groups with one consistent separator, ASCII digits, outer whitespace stripped). SeriesSpec.decimal added (default "."), not in SQL. Tests added for all listed cases.
Command: `.venv-ci/bin/python -m pytest tests/ingest -v`
```
tests/ingest/test_registry.py::test_registry_rejects_unknown_source PASSED [ 96%]
tests/ingest/test_registry.py::test_registry_rejects_duplicate_series_id PASSED [ 97%]
tests/ingest/test_registry.py::test_sync_registry_idempotent PASSED      [ 98%]
tests/ingest/test_registry.py::test_sync_registry_updates_changed_fields PASSED [100%]

============================== 91 passed in 3.13s ==============================
```
