# Task 17 cleanup - independent specification review

Reviewer: fresh spec-review subagent (read-only). Date: 2026-11-12. Branch `pipeline-rebuild`, scoped diff `cdc6579..90e34f0` (cleanup `f8cb9b0` + report `90e34f0`). Controller is running the full suite concurrently; this review ran only focused probes in the clean requirements-only env (`/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci/bin/python`), no coverage, no network.

## Verdict: PASS

No functional gaps found against the cleanup brief. Two non-blocking style/precision notes below, flag-only.

## Verified

1. **Exact deletion set.** `git diff --name-status cdc6579..90e34f0`: 23 deletions = the consented 8 collectors + 5 scripts + all 8 tracked files under `scripts/collectors/` + 2 tracked files under `scripts/maintenance/` (confirmed via `git ls-tree -r cdc6579` that those were the only tracked files in those dirs). Both dirs gone. Nothing else deleted.
2. **Byte-for-byte preservation.** `git diff --quiet cdc6579 90e34f0 -- <path>` IDENTICAL for `collectors/{base,dadosgov,dgeg_fuel_api,habitacao,collect_new_indicators}.py`, `scripts/{create_seed_db,ingest}.py`, `Dockerfile`, `entrypoint.sh`, `requirements-legacy.txt`, `tests/ingest/conftest.py`. No registry/fixture/raw/archive/seed path appears in the diff. Unlisted helpers (`generate_share_cards.py`, `test_all_indicators.py`, `run-standalone`) untouched.
3. **Bare-base consumers intact.** `collectors/dadosgov.py:28-29` and `collectors/habitacao.py:26-28` keep `sys.path.insert` + bare `from base import standardize_rows, write_parquet`; `collectors/base.py` preserved.
4. **No surviving consumers of retired modules** in active code. `app/`, `ingest/`, `tests/`, `scripts/` greps: retired collector roots imported only by retained historical artifacts (`collect_new_indicators.py:20-22`; lazy `from bportugal import` inside `collectors/habitacao.py:140`). duckdb/pyarrow imported only by `scripts/create_seed_db.py:26` and `scripts/ingest.py:138` (lazy, legacy inspection scripts, retained by consent). AST guards in `tests/test_task17_cleanup.py` encode this permanently. `test_verify.py:631` references `ingest.sources.eurostat` (new pipeline source), not the deleted file.
5. **conftest.** Six old-UI fixtures removed; zero consumers of those names anywhere under `tests/` (grep at HEAD); `sys.path` import bootstrap preserved; old conftest had no other content to lose.
6. **CI contract** (`.github/workflows/ci.yml`): runtime `requirements.txt` only (legacy install gone), no seed step, no `CAE_DB_PATH`, full offline suite `pytest tests/ --cov=app --cov=ingest --cov-branch --cov-report=term-missing`, lint `ruff check app/ ingest/`. Behaviorally verified in clean env: default addopts `-m "not live"` deselects 1/1 in `test_live_fred.py`; the old CI expression `-m "not integration and not slow"` collects the same live test (last `-m` wins over addopts). None of the 7 live-marked tests carries an `integration` marker, so the old command really did re-enable live publisher tests; the fix is genuine.
7. **Coverage config.** `.coveragerc` (new): `source = app, ingest`, `branch = true`. Claim that coverage.py never reads `[coverage:*]` from pytest.ini is correct (rcfile autodiscovery is `.coveragerc`/`setup.cfg`/`tox.ini`/`pyproject.toml`); pytest.ini sections replaced by a pointer comment. Actual consumption not re-executed here (see limits).
8. **Ruff gate.** `$V -m ruff check app/ ingest/` -> "All checks passed!". `independence.py` diff is the import-block reorder only.
9. **CLI/maintenance support.** `$V -m pytest tests/test_maintenance.py tests/ingest/test_cli.py tests/ingest/test_independence.py -q` -> 26 passed. `$V -m ingest --help` prints usage + subcommands.
10. **New regression guards.** `tests/test_task17_cleanup.py`: 47 checks, all passing in clean env (`47 passed in 1.01s`). RED claim independently plausible: exactly 15 assertions hold in both pre/post states (9 preserved-present + 2 bare-base + 1 bootstrap + 1 pytest.ini default + 2 import-hygiene), matching reported "32 failed, 15 passed". GREEN total 47+26=73 matches the report's 73.
11. **Suite consistency.** `$V -m pytest tests/ --collect-only -q` -> 1382/1389 collected, 7 deselected = baseline 1335 + 47 new, and exactly the 7 live tests deselected by default.
12. **Process hygiene.** Commits `f8cb9b0` + `90e34f0` only; no co-author/model trailers; working tree dirty only with pre-existing generated `AGENTS.md`/`CLAUDE.md` hunks and the untracked controller brief; no stray `.coverage*` data files. `.gitignore:49` `.github/` does match `ci.yml` (`git check-ignore --no-index -v`), so the `git add -f` note in the implementation report is accurate. `legacy-ui-final` branch exists, matching the README reference. Nothing pushed (branch ahead of origin by 2).

## Non-blocking notes (style/precision, not functional blockers)

- **N1 (style, flag-only):** em dashes (U+2014) used in new authored text despite the house plain-hyphens rule: `collectors/README.md:1,14,17,19`, `.coveragerc:4`, `task-17-cleanup-implementation.md:1,10,12,31,50,57,86,107`. Publisher originals untouched.
- **N2 (doc precision):** `collectors/README.md:14-16` says base.py is kept "so those two files stay runnable as historical scripts", but `collectors/habitacao.py:140` lazily imports the now-deleted `bportugal`, so habitacao's housing-credit path cannot run on this branch (dadosgov unaffected; `collect_new_indicators.py` is correctly marked NOT runnable). Preservation itself is byte-for-byte per explicit consent, so this is wording only.
- **N3 (known, consented):** stale references to deleted `scripts/collectors/` paths remain in `DOCS_MAP.md:167-170`; root-docs rewrite is explicitly Task 19 scope.

## Limits (honest)

- Full offline suite run and clean-environment CI rehearsal are controller-owned and were not repeated here (fullsuite running concurrently; coverage deliberately not used in my probes to avoid `.coverage` clashes). `.coveragerc` consumption is verified statically plus the implementer's mirror-run evidence, not by my own coverage run.
- RED phase cannot be re-executed post-cleanup; validated analytically instead (point 10).
- Graph (GitNexus) evidence from the implementer was not re-run; my import checks are grep/AST-based, which is the stronger guarantee here anyway.
