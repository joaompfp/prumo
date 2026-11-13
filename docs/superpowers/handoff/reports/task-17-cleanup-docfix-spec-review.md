# Task 17 cleanup docfix - scoped specification re-review

Reviewer: docfix-spec-review subagent. Date: 2026-11-12. Branch: `pipeline-rebuild`.
Scope: ONLY `90e34f0..062fd65` (the consented scoped docfix). Verifies F1/N1 and
F2/N2 closure, zero behavior/config-value change, and no consent widening.
Read-only review; this report is the only written artifact. Verdict: **PASS**.

## Commit range and diff shape

- Range contains exactly one commit: `062fd65 docs(task17): scoped cleanup docfix`.
- `git diff --stat 90e34f0..062fd65` = 6 files: `.coveragerc` (comment),
  `collectors/README.md` (prose), `task-17-cleanup-docfix.md` (new report, +79),
  `task-17-cleanup-implementation.md` (prose), `pytest.ini` (comment),
  `tests/conftest.py` (module docstring). Every hunk is a comment, docstring, or
  documentation line. No executable or test logic in the diff.
- Zero bytes changed in `collectors/*.py`, `app/`, `ingest/`, `scripts/`,
  `.github/workflows/ci.yml`, or `tests/test_task17_cleanup.py`. Retained
  collectors remain byte-for-byte per the brief's explicit consent.
- Working tree: the 6 files are clean at HEAD; controller's brief and spec/quality
  review reports remain untracked and unmodified. Pre-existing dirty
  `AGENTS.md`/`CLAUDE.md` untouched (not staged, not edited).

## F1/N1 (em-dash style) - CLOSED

- Pre-fix counts at `90e34f0` (grep U+2014): `collectors/README.md` 4 lines
  (matches docfix claim of 4x at lines 1/14/17/19), `.coveragerc` 1 line
  (comment, line 4), `task-17-cleanup-implementation.md` 8 lines / 9 occurrences
  (line 50 had two; docfix's "9x" is consistent).
- Post-fix at `062fd65`: 0 U+2014 in all five edited files AND in the new docfix
  report itself. Replacement is plain hyphen throughout.
- Reviewer reports brief/spec/quality: 0 U+2014, confirmed style-clean and not
  touched (publisher-original and old reports untouched).

## F2/N2 (habitacao runnability precision) - CLOSED

- Ground truth verified against source: `collectors/habitacao.py:133` defines
  `_collect_housing_credit`; line 140 lazily imports
  `from bportugal import BPortugalClient`; `collectors/bportugal.py` was deleted
  in `f8cb9b0`. That path would `ImportError` on this branch.
- `collectors/dadosgov.py` has no `bportugal` references; both it and
  `habitacao.py` retain the bare `from base import standardize_rows, write_parquet`
  after a `sys.path` insert (lines 28-29 / 26-28) - README's description of the
  retained historical base bare imports is accurate.
- README `collectors/README.md:14-19` now states runnability is partial
  (dadosgov standalone, habitacao credit path broken), and "retention is for
  reading, not running". The brief's rule "do not claim every retained legacy
  helper runs" is now satisfied.

## legacy-ui-final wording - corrected, with one residual nit

- README no longer asserts "the full pre-cleanup tree is tagged/available"; it now
  says a historical pre-rebuild snapshot exists on the reference and is "not
  asserted to match this branch's exact pre-cleanup tree". The N-finding driver is
  resolved: no identical-tree claim remains.
- Ref facts: `legacy-ui-final` is `refs/tags/legacy-ui-final` at `a18a58a1`
  (2026-11-10), predating this branch.
- **Nit (trivial, non-blocking):** new README text says "`legacy-ui-final` branch
  reference" - it is a tag, not a branch; the pre-fix text's "tagged" was the
  accurate term. Cosmetic wording only; optional future touch-up.

## No behavior or configuration-value change

- `configparser` parse of `pytest.ini` and `.coveragerc` at `90e34f0` vs
  `062fd65`: identical sections, keys, and values (pytest.ini: `[pytest]` keys
  testpaths/python_files/python_classes/python_functions/addopts/markers;
  .coveragerc: `[run]` source/branch, `[report]` exclude_lines). Both hunks are
  `#` comment lines only.
- `pytest.ini:2` header "CAE Dashboard testing" -> "the Prumo test suite" and
  `tests/conftest.py:3` docstring "maintenance-UI" -> "dashboard" are stale-label
  cleanups inside the brief's pytest.ini/conftest alignment scope (brief line 23).
  No parsed-value effect.
- Focused guards re-run with the scratch env
  (`/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci/bin/python`):
  `pytest tests/test_task17_cleanup.py -q` -> **47 passed in 0.53s** (includes the
  .coveragerc-consumption, pytest.ini-default, and conftest-bootstrap guards).

## Consent boundary and deferrals

- No consent widening: only the F1/F2-authorized files plus the brief-scoped
  pytest.ini/conftest touches; quality review recorded "scoped docfix already
  consented" for F1. Untracked controller artifacts were not staged.
- F3-F6 (optional `test_task17_cleanup.py` guard hardening): the guard file is
  absent from the diff - deliberately deferred, not silently fixed, as the docfix
  report states.
- Docfix report's own claims (47 guards green, config parity snapshots,
  ruff on app/ingest) were spot-verified where in scope here: guard run and
  config parity reproduced by this reviewer; ruff outcome is inherited unchanged
  from `90e34f0` since no `app/`/`ingest/` bytes moved.
- This review ran no full suite, no coverage, no network, no production action,
  and no git writes; controller-owned full CI is out of scope by design.
- This report does NOT close Task 17; controller owns closure.
