# Task 17 final cleanup brief

Controller checkpoint: 2026-11-12 (live UTC clock checked at 23:22:37Z), branch pipeline-rebuild, base cdc6579. Owner asked to continue Task 17 after the previous report explicitly left legacy deletion pending. This authorizes the described cleanup only; no main merge or deployment. If a tool still refuses deletion, stop and report the exact refusal without bypassing the gate.

## Accepted boundary

Task 17 operational/manual implementation at d05e24b already passed independent spec and quality gates. Keep it unchanged. Controller baseline `.venv-ci/bin/python -m pytest tests -q`: 1335 passed, 7 live deselected, 3 warnings, 314.54 seconds, before any cleanup edits. Pre-existing dirty AGENTS.md and CLAUDE.md are generated GitNexus hunks, never stage/revert/edit them. The controller owns shared handoff, ledger, roadmap and this brief. The implementer owns the cleanup and its implementation report only.

Read-only discovery corrected a previous false dependency claim: dadosgov.py and habitacao.py import `from base import standardize_rows, write_parquet` after adding the collectors directory to sys.path. Preserve collectors/base.py. Prefix-only `from collectors` searches are insufficient.

## Exact cleanup

Delete superseded files only:

- collectors/eurostat.py, ine.py, bportugal.py, ren.py, worldbank.py, fred.py, oecd.py, eredes.py.
- scripts/collect_scheduled.py, audit_nightly.py, backfill_eu27.py, backfill_full.py, backfill_missing.py.
- Tracked legacy code under scripts/collectors/ and scripts/maintenance/.

Retain byte-for-byte: collectors/base.py, dadosgov.py, dgeg_fuel_api.py, habitacao.py, collect_new_indicators.py; scripts/create_seed_db.py and scripts/ingest.py; Dockerfile and entrypoint.sh; every publisher fixture, raw/archive/seed file and all registry/source definitions. Other legacy helpers not listed above are outside this deletion consent. collect_new_indicators.py depends on the retired clients: it is an explicitly retained historical artifact, NOT an operational entrypoint on this branch. Add a concise collectors/README.md explaining retained versus operational code, the current `python -m ingest` entrypoint and legacy-ui-final as the historical reference. Do not port or wrap that old script, add a compatibility layer, or claim every retained legacy helper runs. No active runtime/CI entrypoint may call it.

Clean .github/workflows/ci.yml: runtime requirements only, no DuckDB seed generation or CAE_DB_PATH; exercise maintenance app and ingest tests with coverage on both app and ingest; never run real live publisher tests. Run the full offline suite instead of replacing default `not live` with an expression that re-enables live tests. CI lint targets supported app/ingest code; retained historical collectors are not part of new runtime. Existing active-runtime Ruff failure is ONLY import ordering in ingest/verifiers/independence.py: a minimal order-only fix is in scope so the real lint gate passes. No unrelated legacy lint churn. Do not enable tests/ lint over the inherited unused import in test_verifier_eurostat.py unless separately addressed.

Remove unused old-UI fixtures from tests/conftest.py; preserve import-path bootstrap until direct pytest invocation is verified. No surviving test consumes these six fixtures (sample_painel_data, sample_indicators, sample_lenses, sample_headlines, temp_db, mock_env). Align pytest.ini and tests/README.md with the current offline/live and app+ingest coverage contract. Coverage configuration must actually be consumed by pytest-cov (use explicit CLI options or a supported .coveragerc; pytest.ini coverage sections alone are not enough).

Add focused permanent regression tests for the cleanup boundaries, active code not importing retired collectors/old DB libraries, retained bare-base consumers, CI no legacy seed/dependencies, and default CI selection excluding live. Prefer behavior/config parsing to a pile of source-string assertions where feasible. Do not execute network or native legacy database code. Run RED before cleanup, then GREEN on the focused tests, maintenance/CLI/independence tests, active-runtime Ruff, CLI help. Controller runs the full suites and clean-environment CI rehearsal.

## Process and deliverables

Use subagent ownership, separate structural cleanup from any behavior change (none requested). Fresh GitNexus exact-worktree alias prumo-pipeline indexed at cdc6579 with --skip-agents-md. Controller ran impact for all six removed test fixtures: zero indexed callers/processes, LOW; corroborated with test source search. Graph has parser warnings, so explicitly inspect imports including bare local modules. Before an additional existing-symbol edit, run impact; no unrelated protected-file edits. Run gitnexus detect-changes before committing, check actual staged diff, and commit only task-owned files. Never use git add -A. No fabricated coauthor/model trailers. No push (controller after reviews), scheduler, production mutation, new live recovery loop or source/licence changes.

Write docs/superpowers/handoff/reports/task-17-cleanup-implementation.md with exact commit(s), RED/GREEN commands/results, preserved boundaries and remaining issues. It cannot close Task 17; controller applies closure only after fresh independent specification and quality reviews. If a block/failure occurs, checkpoint tested narrow work and report it honestly.
