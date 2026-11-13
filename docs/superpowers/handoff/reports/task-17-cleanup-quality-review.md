# Task 17 cleanup - independent quality review

Reviewer: fresh quality-review subagent (read-only; written only this report).
Date: 2026-11-12. Branch `pipeline-rebuild`, scoped diff `cdc6579..90e34f0`
(cleanup `f8cb9b0` + implementation report `90e34f0`), reviewed after the
independent specification review PASS. All probes ran in the clean
requirements-only env `/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci/bin/python`
(Python 3.12, pytest 7.4.4, pytest-cov 4.1, ruff; duckdb/pyarrow absent -
verified `importlib.util.find_spec` -> None for both). No coverage run, no
network, no live markers, no full suite (controller is running both full
offline suites concurrently).

## Verdict: APPROVED

No blocking quality findings. Cleanup is correct, minimal, well-evidenced, and
the guard suite is genuinely useful. Four non-blocking observations below
(two already flagged by the spec reviewer, slated for the controller's scoped
docfix; two new minor guard-robustness notes, optional hardening only).

## Verified with evidence

1. **Exact deletion set, nothing else.** `git diff --name-status cdc6579..90e34f0`:
   23 deletions exactly matching the consent list; only sanctioned
   modifications (`.github/workflows/ci.yml`, `pytest.ini`, `tests/conftest.py`,
   `tests/README.md`, `ingest/verifiers/independence.py`) and sanctioned
   additions (`.coveragerc`, `collectors/README.md`, `tests/test_task17_cleanup.py`,
   implementation report). 471 insertions / 7381 deletions.
2. **Protected artifacts byte-identical.** `git diff --quiet cdc6579 90e34f0 -- <path>`
   clean for all 11: `collectors/{base,dadosgov,dgeg_fuel_api,habitacao,
   collect_new_indicators}.py`, `scripts/{create_seed_db,ingest}.py`,
   `Dockerfile`, `entrypoint.sh`, `requirements-legacy.txt`,
   `tests/ingest/conftest.py`. No registry/fixture/raw/archive/seed path in the
   diff. `scripts/collectors/` and `scripts/maintenance/` absent on disk.
3. **Focused suites green in the clean env.**
   - `$V/python -m pytest tests/test_task17_cleanup.py -q` -> 47 passed (0.52s).
   - `... tests/test_maintenance.py tests/ingest/test_cli.py tests/ingest/test_independence.py -q` -> 26 passed.
   - `... tests/ingest/test_verify.py -q` -> 177 passed (18.63s) - ingest verifier core intact post-cleanup.
   - `$V/python -m ruff check app/ ingest/` -> "All checks passed!".
   - `$V/python -m ingest --help` -> usage + subcommands OK.
4. **Live-deselection contract verified behaviorally, both directions.**
   `pytest tests/ingest/test_live_fred.py --collect-only -q` -> 1 deselected
   under default addopts; with the old CI expression `-m "not integration and
   not slow"` -> 1 collected (last `-m` wins over addopts; no live test carries
   an `integration` marker). The CI fix is a real behavior fix, not cosmetic.
5. **`.coveragerc` actually consumed by coverage.py** (the implementer's central
   claim), verified without running tests: `$V/python -m coverage debug config`
   from repo root -> `config_files_read: .coveragerc`, `branch: True`,
   `source: app / ingest`, `exclude_list` = the 6 configured lines. No
   `.coverage` data file created; tree stays clean.
6. **Suite arithmetic consistent.** `pytest tests/ --collect-only -q` ->
   1382/1389 collected, 7 deselected = baseline 1335 + 47 new guards, exactly
   the 7 live tests deselected by default. RED/GREEN claims are arithmetically
   reproducible: pre-cleanup the 32 failing guards are 23 retired-present + 1
   dirs-present + 1 README-missing assertion + 1 conftest-fixtures + 1
   .coveragerc-missing + 5 CI-contract failures; the 15 always-pass guards
   (9 preserved + 2 bare-base + 1 bootstrap + 1 pytest.ini default + 2
   import-hygiene) match "32 failed, 15 passed". GREEN 47+26=73 matches the
   implementation report.
7. **Architecture of the guards is appropriate.** AST for imports and fixture
   definitions (handles `@fixture`, `@pytest.fixture`, `@pytest.fixture(...)`),
   `configparser` for ini contracts, YAML parsing for CI, `shlex` for command
   tokenisation - behavior/config parsing over source-string grep, exactly the
   brief's preference. Import-hygiene guards are non-vacuous today: 41 active
   files scanned (app 4, ingest 37). The `term-missing` substring false
   positive the implementer reported was replaced by tokenised parsing - the
   fix is visible at `tests/test_task17_cleanup.py:262-272` and correct.
8. **The one source touch is minimal and safe.** `independence.py` diff is the
   import-block reorder only (same 6 names, same order inside the parens);
   13/13 independence tests pass; ruff gate green with zero unrelated churn.
9. **Security/dependency hygiene improved.** CI dropped its only
   DuckDB/pyarrow install path and the live-network re-entry; runtime
   `requirements.txt` + test deps only; retained `requirements-legacy.txt` is
   correctly scoped to two legacy scripts that CI no longer exercises. No
   secrets/paths regressions; deleted dirs gone; no lingering references to
   retired paths in active code, Dockerfile, or entrypoint (remaining hits are
   historical SDD/handoff/ledger docs and registry notes - `DOCS_MAP.md:
   167-170` staleness is consented Task-19 scope, spec review N3).
10. **Process hygiene.** Two commits, no co-author/model trailers; pre-existing
    dirty `AGENTS.md`/`CLAUDE.md` untouched and unstaged; controller-owned
    untracked reports not staged; no `.coverage*`/cache pollution; nothing
    pushed. The pre-existing `.github/` ignore rule explains the reported
    `git add -f` on the tracked workflow file - legitimate, and ci.yml is
    present at HEAD.

## Non-blocking findings

- **F1 (style, spec N1, docfix pending):** em dashes in new authored text -
  `collectors/README.md:1,14,17,19` and `.coveragerc:4` (comment). I checked
  the other new/changed files: `tests/test_task17_cleanup.py`,
  `tests/README.md`, `pytest.ini`, `.github/workflows/ci.yml` are clean; the
  implementation report's dashes the spec review listed are in the implementer
  report body. Severity: trivial; scoped docfix already consented.
- **F2 (doc precision, spec N2, docfix pending):** `collectors/README.md:16`
  "stay runnable as historical scripts" overstates `habitacao.py`, whose
  housing-credit path lazily imports the deleted `bportugal`
  (`collectors/habitacao.py:140`) and would `ImportError` there at runtime;
  `dadosgov.py` and CLI-arg parsing are unaffected. Byte-for-byte preservation
  itself was explicitly consented. Severity: minor, wording only.
- **F3 (new, guard robustness):** the `-m` tokenizer in
  `test_ci_never_reenables_live_tests` (`tests/test_task17_cleanup.py:268-271`)
  would misread a future `python -m pytest ...` CI form as marker selection
  `"pytest"` and fail with a misleading message. Reproduced:
  `shlex.split("python -m pytest tests/ --cov=app")` feeds "pytest" into
  marker_sel, tripping the `"not live"` assert. No false positive today -
  CI has exactly one pytest step, bare `pytest` (`ci.yml:38`). Severity:
  minor/latent; optional one-line guard (`if tok == "-m" and tokens[0] != "python"`-style
  or skipping the python prefix) in the same touch-up round.
- **F4 (new, guard robustness):** `test_ci_exercises_app_and_ingest_coverage`
  (`tests/test_task17_cleanup.py:258`) selects `max(pytest_runs, key=len)` -
  the longest pytest command; if CI later adds a second pytest step lacking
  `--cov` flags, this could misfire. Non-vacuous and correct today (one pytest
  step). Severity: minor; optional hardening to assert on all pytest runs.
- **F5 (new, guard hardening note):** `_active_py_files()` /
  `test_active_code_never_imports_retired_collectors` would pass vacuously if
  `app/` or `ingest/` were ever renamed or emptied (no non-empty precondition).
  Currently scans 41 files, so dormant. Severity: informational.
- **F6 (new, accepted blind spot):** `_imports_in` only yields absolute
  imports (`ast.ImportFrom` with `level == 0`); a relative cross-package import
  like `from ..collectors import eurostat` would be missed. Reproduced on
  synthetic AST. Practically unreachable (such an import from `ingest` would
  raise at collection time, and the full suite is the stronger backstop).
  Severity: informational.

None of F1-F6 blocks the cleanup: F1/F2 are covered by the consented scoped
docfix; F3-F6 are optional permanent-guard hardening with zero current effect.

## Limits (honest)

- Full offline suite and clean-environment CI rehearsal are controller-owned
  and running concurrently; deliberately not repeated (coverage also avoided
  to prevent `.coverage` interference; consumption verified via
  `coverage debug config` instead).
- RED phase cannot be re-executed post-cleanup; validated analytically with
  exact counts matching the implementation report (point 6).
- Implementer's GitNexus evidence not re-run; my probes are grep/AST/AST-level
  behavioral, which is the stronger guarantee for this boundary.
- Retained legacy helpers (`create_seed_db.py`, `scripts/ingest.py`,
  `collect_new_indicators.py`) were not executed (they need deleted clients or
  legacy libs by design); their retention per consent was verified statically.
