# Task 17 cleanup docfix - scoped quality re-review

Reviewer: docfix-quality-review subagent. Date: 2026-11-12. Branch: `pipeline-rebuild`
at `062fd65`. Scope: ONLY the docfix range `90e34f0..062fd65` plus the current
one-word working-tree correction in `collectors/README.md` ("branch reference" ->
"tag"). Verifies F1/F2 closure, final tag wording, runnability claims, and zero
implementation change. Read-only review; this report is the only written artifact.
Verdict: **APPROVED**.

## Docfix diff shape (`90e34f0..062fd65`)

- Exactly one commit in range: `062fd65 docs(task17): scoped cleanup docfix`.
- 6 files, 102 insertions / 17 deletions. Full diff inspected hunk by hunk:
  - `.coveragerc`: 1 `#` comment line (em dash -> hyphen).
  - `collectors/README.md`: prose only (hyphen style, partial-runnability
    correction, `legacy-ui-final` snapshot wording).
  - `docs/superpowers/handoff/reports/task-17-cleanup-docfix.md`: new report (+79).
  - `task-17-cleanup-implementation.md`: prose em-dash -> hyphen replacements.
  - `pytest.ini`: header comment only ("CAE Dashboard testing" -> "the Prumo test
    suite"), no parsed keys touched.
  - `tests/conftest.py`: module docstring line only ("maintenance-UI" ->
    "dashboard").
- Zero bytes changed in `collectors/*.py`, `app/`, `ingest/`, `scripts/`,
  `tests/test_task17_cleanup.py`, `.github/workflows/ci.yml`. No executable or
  test logic in the range.

## F1 (em-dash style) - CLOSED

- `grep -rn $'\u2014'` over all five edited files plus the new docfix report (at
  working-tree state, i.e. including the tag fix) returns exit 1: zero U+2014.
  Replacements are plain hyphens throughout.

## F2 (habitacao runnability precision) - CLOSED

- Ground truth verified against source: `collectors/habitacao.py` defines
  `_collect_housing_credit`; line 140 lazily imports
  `from bportugal import BPortugalClient`; `collectors/bportugal.py` is absent
  (deleted in `f8cb9b0`, confirmed via `git log --diff-filter=D`). That credit
  path would `ImportError` on this branch.
- `collectors/dadosgov.py` has no `bportugal` reference; both it and
  `habitacao.py` retain the bare `from base import standardize_rows, write_parquet`
  after a `sys.path` insert - README's "retained historical bare base imports"
  description holds.
- README now states runnability is partial (dadosgov standalone; habitacao
  housing-credit path broken) and "retention is for reading, not running".
  Accurate.

## legacy-ui-final wording - CLOSED (spec nit resolved)

- Working-tree hunk is exactly one word: "branch reference" -> "tag" on the
  `legacy-ui-final` line. Nothing else differs from `062fd65`
  (`git diff collectors/README.md` shows only that hunk).
- Ref independently verified: `git show-ref --verify refs/tags/legacy-ui-final`
  -> `a18a58a161e690d01ac53c3748cfa0b7d3f5cb6c` (2026-11-10, predates this
  branch). It is a tag; the corrected wording is now factually right, and no
  identical-tree claim remains.

## No behavior or configuration-value change

- `configparser` snapshot parity (sections/keys/values, sorted JSON) of
  `pytest.ini` and `.coveragerc` across `90e34f0`, `062fd65` and `HEAD`:
  identical for both files.
- Focused guards re-run with scratch env
  (`/home/joao/.hermes/cache/scratch/prumo-task17-clean-ci/bin/python`):
  `pytest tests/test_task17_cleanup.py -q` -> **47 passed in 0.49s**, with the
  working-tree tag wording in place. The README-touching guards stay green.

## Boundaries

- Working tree otherwise shows only pre-existing dirty `AGENTS.md`/`CLAUDE.md`
  (untouched) and untracked controller brief + prior review reports. No staged
  or unintended changes.
- F3-F6 optional guard hardening intentionally deferred: `tests/test_task17_cleanup.py`
  absent from the diff; no silent fixes.
- Parent-owned full-suite results (1382 passed / 7 deselected; CI rehearsal
  1382 passed, coverage 88%) inherited, not re-run here. No full suite, no
  network, no coverage run, no index edits, no git writes by this reviewer.
- This report does NOT close Task 17; controller owns closure.
