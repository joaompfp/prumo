# Task 17 cleanup - implementation report

Author: implementer subagent. Date: 2026-11-12. Branch: `pipeline-rebuild`, base `cdc6579`.
This report does NOT close Task 17; controller applies closure only after fresh
independent specification and quality reviews.

## Commits

- `f8cb9b0` `chore(cleanup): Task17 - delete retired legacy collectors/scripts, align CI
  and test config` - 31 files changed, 359 insertions(+), 7381 deletions(-).
- the follow-up `docs: Task17 cleanup implementation report` commit (report only;
  self-referencing hash omitted - the child commit of `f8cb9b0` in `git log`).

## What changed

Deletions (exact consent set, executed via `git rm`, no tool refusal):

- `collectors/{eurostat,ine,bportugal,ren,worldbank,fred,oecd,eredes}.py`
- `scripts/{collect_scheduled,audit_nightly,backfill_eu27,backfill_full,backfill_missing}.py`
- tracked legacy code under `scripts/collectors/` (8 files incl. `cae-collect`)
  and `scripts/maintenance/` (`merge_staging.py`, `normalize_db.py`)

Preserved (verified: none appear in `git diff --name-only cdc6579..f8cb9b0`):

- `collectors/{base,dadosgov,dgeg_fuel_api,habitacao,collect_new_indicators}.py`
  (byte-for-byte; `dadosgov.py`/`habitacao.py` keep bare
  `from base import standardize_rows, write_parquet` after sys.path manipulation)
- `scripts/{create_seed_db,ingest}.py`, `Dockerfile`, `entrypoint.sh`, registry
  definitions, all publisher fixtures, raw/archive/seed data
- unlisted legacy helpers (`scripts/{generate_share_cards,test_all_indicators}.py`,
  `scripts/run-standalone`) - outside deletion consent, untouched

Config / docs:

- `collectors/README.md` (new): retained = historical/unreconciled, NOT new runtime;
  `collect_new_indicators.py` depends on retired clients and is NOT runnable on this
  branch; supported entrypoint is `python -m ingest`; `legacy-ui-final` is the
  historical reference.
- `tests/conftest.py`: six unused old-UI fixtures removed (controller-impact LOW,
  0 callers, corroborated by source search); import-path bootstrap retained.
- `pytest.ini`: dead `[coverage:*]` sections replaced by a comment pointing at the
  real config.
- `.coveragerc` (new): `source = app,ingest`, `branch = true`, same exclude lines;
  actually consumed by pytest-cov (branch columns appear in CI-mirror run).
- `tests/README.md`: coverage/marker documentation aligned.
- `.github/workflows/ci.yml`: runtime `requirements.txt` only; no
  `requirements-legacy.txt`, no `create_seed_db.py` step, no `CAE_DB_PATH`; full
  offline suite `pytest tests/ --cov=app --cov=ingest --cov-branch --cov-report=
  term-missing` with pytest.ini's default `not live` selection (the old
  `-m "not integration and not slow"` override - which re-enabled live tests - removed);
  lint now targets `app/ ingest/` only.
- `ingest/verifiers/independence.py`: minimal import-order-only fix for the single
  inherited ruff I001 (GitNexus impact: 0 upstream callers, LOW, corroborated by
  source search; diff is the import block reformat only).

New permanent regression guards: `tests/test_task17_cleanup.py` (47 parametrized
checks) - removal set gone, preservation set present, bare-base consumers intact,
active `app/`/`ingest/` AST never imports retired collector roots nor duckdb/pyarrow,
conftest fixtures gone with bootstrap kept, `.coveragerc` consumed, CI workflow
contract (runtime requirements only, no seed/env, app+ingest coverage, no live
re-enabling via tokenized `-m` parse, lint scope). Filesystem/AST/YAML parsing only.

## RED / GREEN evidence

Environment: `/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci/bin/python`
(fresh requirements-only venv: Python 3.12.3, pytest 7.4.4, pytest-cov 4.1, ruff;
no duckdb/pyarrow), plus the venv's `ruff`.

- RED (before any cleanup):
  `$V/python -m pytest tests/test_task17_cleanup.py -q` → **32 failed, 15 passed**
  in 0.76s (the 15 passing are guards that hold in both states).
- GREEN (after cleanup):
  `$V/python -m pytest tests/test_task17_cleanup.py tests/test_maintenance.py
  tests/ingest/test_cli.py tests/ingest/test_independence.py --cov=app --cov=ingest
  --cov-branch -q` → **73 passed, 1 warning** in 27.84s.
  (One intermediate failure was a bug in my own test's naive `"-m" in cmd` substring
  check matching `term-missing`; fixed with shlex tokenisation, then green.)
- `$V/python -m ingest --help` → usage + subcommands printed, OK.
- `$V/ruff check app/ ingest/` → **All checks passed!** (after `--fix` applied the
  single I001).
- `$V/python -m pytest tests/ingest/test_verify.py -q` → 177 passed (20.11s).
- `gitnexus detect-changes --repo prumo-pipeline` → 7 files / 11 symbols,
  0 affected processes, risk LOW.
- Staged diff reviewed before commit; only task-owned paths staged (explicit `git
  add` list; `.github/workflows/ci.yml` is tracked but matched by a pre-existing
  `.github/` gitignore line - added with `git add -f` on that exact path).
  Pre-existing dirty `AGENTS.md` / `CLAUDE.md` left untouched and unstaged;
  controller's brief and handoff files not staged.

## Verification commands (for reviewers)

- `$V/python -m pytest tests/test_task17_cleanup.py tests/test_maintenance.py
  tests/ingest/test_cli.py tests/ingest/test_independence.py --cov=app --cov=ingest
  --cov-branch -q`
- `$V/ruff check app/ ingest/`
- `$V/python -m ingest --help`
- `git diff --name-only cdc6579..f8cb9b0` (check preserved paths absent)

## Remaining limitations (honest)

- Full offline suite (`pytest tests -q`, ~5 min) and clean-environment CI rehearsal
  are controller-run; not executed here. A transient `.coverage` data file from the
  mirror run was removed, not committed.
- GitNexus index has known parser warnings; import-hygiene guards are therefore
  AST-based in tests plus source searches, not graph-only.
- `tests/ingest/test_verifier_eurostat.py` inherited F401 (unused import) remains
  out of scope - tests/ are not linted and no edit was requested.
- `scripts/create_seed_db.py` and `scripts/ingest.py` still import duckdb/pyarrow
  by design (legacy inspection scripts; requirements-legacy.txt retained for them);
  they are simply no longer exercised in CI.
- No live/network tests executed; no scheduler/deployment work (Task 18), no wide
  root-docs rewrite (Task 19).
