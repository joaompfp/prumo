# Testing

## Layout

- `tests/ingest/`: the reviewed ingestion pipeline (registry, sources, verifiers, pipeline,
  verification, db/migrations, CLI, status, raw store, bundle capture/replay). Publisher bytes
  in `tests/ingest/fixtures/<source>/` are genuine recorded responses, sha256-pinned by each
  MANIFEST.json; tests that mutate them use labelled overrides and never alter fixture files.
- `tests/test_maintenance.py` + `tests/conftest.py`: the maintenance-mode web app (FastAPI)
  fixtures.

## Run

```bash
.venv-ci/bin/python -m pytest tests -q          # everything except -m live
.venv-ci/bin/python -m pytest tests -m live -s  # hits real publisher APIs (never in CI)
```

Markers (pytest.ini): `live` (network, deselected by default via `-m "not live"`),
`slow`, `integration`, `unit`. Coverage config for both `app` and `ingest` lives in
`.coveragerc` (consumed by pytest-cov); CI passes explicit
`--cov=app --cov=ingest --cov-branch` flags.
