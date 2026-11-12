# Task 16 spec-review R1/R2 fix report

Commit: `5feb13f36795582419cbfcd79805a9a2e59a629d`
(`fix(ingest): Task 16 R1/R2 - atomic migration FK check, raw PT15M normalize_period`)
Scope: exactly the two findings of `task-16-spec-review.md`. Nothing else changed.

## R1 — migrator integrity check now atomic (`ingest/db.py`)

- `_migrate` runs each pending file as `BEGIN; <sql>; INSERT schema_migration` via
  `executescript` **without COMMIT**, then runs `PRAGMA foreign_key_check` **inside that open
  transaction** and only then `COMMIT`. Any failure (SQL error or FK violation) hits the
  `except` path and `ROLLBACK`s the migration *and* its version record together — a later open
  re-attempts the file instead of silently keeping a corrupt applied version.
- The `if not pending: return` early-exit is gone: a whole-database `foreign_key_check` now
  runs on **every open**, so a DB left corrupt by the old non-atomic migrator (bad row +
  recorded version, the reviewer's probe3 scenario) is never silently accepted.
- `open_db` closes the connection if `_migrate` raises (no leaked WAL handle). Nothing else
  in `db.py` changed; FK OFF/ON toggling and per-file ordering preserved.

## R2 — PT15M arm of `normalize_period` matches raw (`ingest/models.py`)

- PT15M pattern now matches the **raw string** (`text = raw` for PT15M only) with uppercase
  `T` in the pattern: no NFKD fold, no case fold, no strip, no unicode normalization.
  Fullwidth digits/tokens, lowercase `t`, and whitespace-padded spellings now raise
  `ValueError` instead of being canonicalized.
- A/S/Q/M/D arms unchanged — still matched against `_fold(raw)`; all pre-existing tests pass
  unmodified.

## Tests (TDD: 6 new cases failed before the fix, all pass after)

`tests/ingest/test_migration_pt15m.py` (new):
- `test_bad_migration_rolls_back_atomically_no_corrupt_applied_version` — synthetic
  `0007_bad.sql` (ghost `series` row, `source_id=999`, invisible to triggers, FK-OFF only):
  first `open_db` raises `RuntimeError`, side-channel inspection shows `schema_migration` ==
  exactly 0001..0006 and zero `series` rows; repeated open re-raises; after deleting the bad
  file, open succeeds clean.
- `test_open_rejects_preexisting_corruption_with_no_pending_migrations` — hand-corrupted DB
  (ghost row + `0007_bad` version recorded, simulating the old migrator's outcome) is rejected
  on every subsequent open with nothing pending.

`tests/ingest/test_models.py` (4 new reject cases in
`test_normalize_period_pt15m_rejects_noncanonical`): lowercase `t`, leading whitespace,
trailing whitespace, fullwidth digits/colon/plus/T.

Preserved behavior regression check: `test_0006_upgrades_populated_0005_and_preserves_everything`
(populated 0005 → 0006 upgrade, served view, licence gate, idempotent re-open) passes as-is.

## Verification actually run

- `.venv-ci/bin/python -m pytest tests/ingest/test_models.py tests/ingest/test_migration_pt15m.py
  tests/ingest/test_db.py tests/ingest/test_source_eredes.py tests/ingest/test_verifier_eredes.py
  tests/ingest/test_pipeline.py -q` → **223 passed** (Python 3.12.3, pytest 9.2.0, 20.9 s).
  Red run before the fix: exactly the 6 new cases failed, 31 others passed.
- `ruff check` on the four touched files → clean.
- GitNexus: `impact _migrate`/`open_db`/`normalize_period` ran (index stale at 03639ee, queried
  with `-r prumo-pipeline`); `detect-changes` before commit — only the 4 files staged;
  controller-dirty `HANDOFF.md`/`progress-ledger.md`/plan and untracked review/discovery
  reports untouched. No push, no network, no fixture changes.

Not done here (controller-owned): full-suite run, live E-REDES acceptance gate, staging of
handoff/plan/ledger docs, independent re-review of this fix.
