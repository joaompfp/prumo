# collectors/ — retained historical code (not the runtime)

Everything in this directory is **retained for historical reference only**. It is not
imported by, and must not be wired into, the rebuilt ingestion pipeline.

The supported entrypoint on this branch is:

```bash
.venv-ci/bin/python -m ingest --help
```

What remains here and why:

- `base.py` — still consumed by `dadosgov.py` and `habitacao.py` via a bare
  `from base import standardize_rows, write_parquet` after they put this directory
  on `sys.path`. Kept so those two files stay runnable as historical scripts.
- `dadosgov.py`, `dgeg_fuel_api.py`, `habitacao.py` — historical manual collectors,
  unreconciled with the reviewed ingest pipeline.
- `collect_new_indicators.py` — depends on the retired clients (`bportugal`, `ine`,
  `eurostat`, …) that were deleted in the Task 17 cleanup. It is **NOT runnable** on
  this branch and exists only as a historical artifact. Do not port, wrap, or call it.

The full pre-cleanup tree is tagged/available on the `legacy-ui-final` reference.
New collection code belongs in `ingest/sources/` with an independent verifier in
`ingest/verifiers/`; see `tests/ingest/` for the supported contract.
