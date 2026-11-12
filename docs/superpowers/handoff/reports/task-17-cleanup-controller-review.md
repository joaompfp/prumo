# Task 17 cleanup - controller acceptance

Accepted 2026-11-12. Task 17 is COMPLETE for its technical operational/manual and final cleanup scope. Runtime cleanup code: f8cb9b0, implementation report: 90e34f0, documentation-only correction: 062fd65. The controller also corrected the README's historical reference from branch to tag after checking refs/tags/legacy-ui-final = a18a58a161e690d01ac53c3748cfa0b7d3f5cb6c. No main merge, scheduler installation or deployment.

The owner's request to continue Task 17 followed the prior pending-deletion report. The exact remaining cleanup was executed successfully through git rm without a tool refusal. No earlier safety gate was bypassed. The earlier accepted CLI/status/replay/manual implementation and all source acceptances remain unchanged; this phase made no new publisher requests.

## Scope and preservation

The accepted removal set is 23 tracked legacy code files: eight superseded source collectors, five scheduled/audit/backfill scripts, eight files under scripts/collectors and two under scripts/maintenance. No other files were deleted.

collectors/base.py was deliberately NOT removed. The previous report's package-prefix-only import search missed the bare from base imports in dadosgov.py and habitacao.py after sys.path manipulation. The controller and independent reviewers checked these dependencies. All five retained collector implementations, legacy inspection scripts, Dockerfile, entrypoint, registry, publisher fixtures, seed/raw/archive data and manual-refresh instructions remain unchanged against cdc6579. Controller before/after SHA-256 checks also matched on the protected instruction files and retained implementation paths.

Some retained historical helpers are not runnable on the rebuilt branch. collect_new_indicators.py imports retired clients, and habitacao.py's housing-credit path lazily imports the retired bportugal client. They are not new-runtime entrypoints. collectors/README.md now records these limits without restoring a compatibility layer or claiming a successful legacy collection.

CI now installs requirements.txt only, without DuckDB/pyarrow or a synthetic DuckDB seed. It runs the full offline tests with app and ingest branch coverage. Removing the old marker override matters: a CLI -m expression replaces pytest.ini's default not-live expression and previously re-enabled publisher tests. Both independent reviewers reproduced that behavior using collection only. Ruff covers the supported app/ingest runtime; retained historical collectors remain outside that gate. The only runtime-source diff is import ordering in ingest/verifiers/independence.py.

## Independent review gates

- Whole cleanup specification PASS: task-17-cleanup-spec-review.md.
- Subsequent separate quality APPROVED: task-17-cleanup-quality-review.md.
- Documentation-only F1/F2 correction specification PASS: task-17-cleanup-docfix-spec-review.md.
- Subsequent separate quality APPROVED, including the controller's tag wording correction: task-17-cleanup-docfix-quality-review.md.

No Critical or Important finding remains open. Reviewer artifacts describe their actual bounded probes; no Claude authorship or model trailer was fabricated.

## Controller execution

Before edits, at cdc6579:

.venv-ci/bin/python -m pytest tests -q

Result: 1335 passed, 7 live deselected, 3 warnings in 314.54 seconds, pytest 9.2.0 / Python 3.12.3.

After cleanup, the same complete suite:

.venv-ci/bin/python -m pytest tests -q

Result: 1382 passed, 7 live deselected, 3 warnings in 316.54 seconds. This includes the 47 new permanent cleanup guards and the real legacy CSV-export test.

The controller created a new environment using only requirements.txt plus the CI lint tool. Python 3.12.3, pytest 7.4.4, pytest-cov 4.1.0; importlib discovery independently confirmed duckdb, pyarrow, pandas and PIL absent. The actual CI test command was exercised there:

PATH=/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci/bin:$PATH COVERAGE_FILE=/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci.coverage pytest tests/ --cov=app --cov=ingest --cov-branch --cov-report=term-missing

Result: 1382 passed, 7 live deselected, 3 warnings in 660.62 seconds. Aggregate app+ingest coverage was 88%, with branch coverage enabled. This is code coverage, not a relaxation of the independent-source 100%-sample-match requirement. The command ran locally with a fresh dependency environment, not on GitHub Actions; the external real-export CSV was available on this host.

The subsequent docfix changed only prose, module docstrings and comments. Controller and both scoped reviewers parsed pytest.ini and .coveragerc before/after and confirmed every configuration key/value identical. Focused final guards after the tag wording correction: 47 passed in 0.49 seconds. Final supported-runtime Ruff: all checks passed. git diff --check passed. No implementation or publisher bytes changed after the complete runs.

## Deferred and next gates

Optional guard-suite notes F3-F6 remain deferred: future python -m pytest token parsing, future multiple pytest-step selection, non-empty scan preconditions, and relative-import detection. The current CI command and 41 active Python files are covered; these notes have no current functional effect. Revisit when those contracts change rather than introducing speculative command parsing now.

Task 18 is next: scheduler, secure source credential provisioning, packaging/installation on f0nix, production catch-up/status inspection and the required 24-hour observation. None was performed in this cleanup. Task 19 methodology/source documents and final whole-branch review remain unstarted. The public app stays maintenance-only. Existing World Bank export-availability limits, DGEG ingestion blockers and REN/FRED/OECD redistribution gates are unchanged.

Pre-existing GitNexus-generated AGENTS.md and CLAUDE.md working-copy changes are still unstaged and uncommitted, byte-identical to the controller's intake. They are not part of Task 17 acceptance or its push.
