# Task 17 cleanup - scoped docfix report

Author: docfix subagent. Date: 2026-11-12. Branch: `pipeline-rebuild`, parent `90e34f0`.
Scope: ONLY the approved review's documentation-precision (spec N2 / quality F2) and
plain-hyphen (spec N1 / quality F1) fixes, plus two stale comment/docstring touches
consented in the controller brief (pytest.ini header, tests/conftest.py docstring).
No code, no test logic, no configuration values, no preserved collector bytes changed.

## Findings addressed

- **F1/N1 (style):** em dashes (U+2014) in new authored cleanup text, replaced with
  plain hyphens at `collectors/README.md` (4x: lines 1, 14, 17, 19), `.coveragerc:4`
  (comment), and `task-17-cleanup-implementation.md` (9x: lines 1, 10, 12, 31,
  50 (2x), 57, 86, 107). Verified zero remaining via `grep -n $'\u2014'` (exit 1).
  Reviewer reports checked: spec/quality/brief contain **no** U+2014 - style-clean,
  left untouched. Publisher-original bytes and old reports not modified.
- **F2/N2 (doc precision):** `collectors/README.md` claimed `dadosgov.py` and
  `habitacao.py` "stay runnable as historical scripts". Corrected:
  `habitacao.py`'s housing-credit method (`_collect_housing_credit`, habitacao.py:140)
  lazily imports the retired `bportugal` client deleted in the cleanup, so that
  specific path would `ImportError` on this branch; `dadosgov.py` unaffected.
  README now says runnability is partial and retention is for reading, not running.
- **legacy-ui-final precision:** README asserted "The full pre-cleanup tree is
  tagged/available". The `legacy-ui-final` branch (last commit `a18a58a1`,
  2026-11-10) predates this branch; README now calls it a historical pre-rebuild
  snapshot reference, not asserted to match this branch's exact pre-cleanup tree.
- **pytest.ini:2:** header comment "CAE Dashboard testing" -> "the Prumo test
  suite" (comment only; parsed keys unchanged).
- **tests/conftest.py:3:** docstring "old maintenance-UI fixtures" -> "old
  dashboard fixtures" (docstring only; module behavior unchanged).

## Deferred (for controller, NOT implemented here - optional guard hardening)

- **F3:** `test_ci_never_reenables_live_tests` `-m` tokenizer would misread a future
  `python -m pytest ...` CI form. No false positive today (one bare `pytest` step).
- **F4:** `test_ci_exercises_app_and_ingest_coverage` selects `max(pytest_runs,
  key=len)`; could misfire if CI adds a second pytest step without `--cov` flags.
- **F5:** `_active_py_files()` lacks a non-empty precondition; guards would pass
  vacuously if `app/`/`ingest/` were renamed/emptied (currently 41 files scanned).
- **F6:** `_imports_in` yields absolute imports only; relative cross-package imports
  would be missed (practically unreachable; full suite is the backstop).

## Verification (fresh env, no coverage, no network)

Env: `/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci/bin/python` (Python 3.12.3).

- `$V -m pytest tests/test_task17_cleanup.py -q` -> **47 passed in 0.49s**
  (all cleanup guards green, including the README-presence, conftest-bootstrap,
  pytest.ini-default and .coveragerc-consumption guards touching edited files).
- `$V -m ruff check app/ ingest/` -> **All checks passed!**
- Config parity proof: `configparser` dump of `pytest.ini` + `.coveragerc` (all
  sections, keys, values, sorted JSON) identical before/after the comment edits
  (snapshots compared byte-for-byte). `pytest.ini`: testpaths, python_files,
  python_classes, python_functions, addopts, markers unchanged. `.coveragerc`:
  [run] source/branch, [report] exclude_lines unchanged.
- `gitnexus detect-changes --repo prumo-pipeline` -> 7 files / 8 symbols
  (all in pre-existing dirty `AGENTS.md`/`CLAUDE.md`, not staged), 0 affected
  processes, risk LOW. No index regeneration.

## Diff summary (staged paths only)

```
.coveragerc                                        |  2 +-
collectors/README.md                               | 18 +++++++++++------
.../reports/task-17-cleanup-implementation.md      | 16 ++++++++--------
pytest.ini                                         |  2 +-
tests/conftest.py                                  |  2 +-
```
plus this report. Pre-existing dirty `AGENTS.md`/`CLAUDE.md` and untracked
controller brief / spec & quality review reports explicitly NOT staged.

## Limits (honest)

- Full offline suite and clean-environment CI rehearsal are controller-owned and
  running concurrently; deliberately not repeated here. No coverage flags used.
- F2 correction verified statically against `collectors/habitacao.py:133-141`
  (lazy `from bportugal import BPortugalClient` inside `_collect_housing_credit`);
  the historical script was not executed.
- This commit does NOT close Task 17; controller owns closure.
