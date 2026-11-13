# Task 16 R1/R2 fix — independent spec re-review

Verdict: **PASS** (code acceptance of the two scoped findings at `5feb13f`; live E-REDES gate
remains controller-owned and unrun)

Scope per controller instruction: re-review *only* R1 (migrator FK atomicity) and R2 (raw
canonical PT15M in `normalize_period`) in commit diff `b62249d..5feb13f`, read-only. No network,
no full suite, no reopening of other source. HEAD verified `5feb13f` on `pipeline-rebuild`;
diff touches exactly 4 files (`ingest/db.py`, `ingest/models.py`,
`tests/ingest/test_migration_pt15m.py`, `tests/ingest/test_models.py`); controller-dirty
HANDOFF/ledger/plan and untracked reports are not part of the commit and were untouched by me.

## R1 — migrator FK atomicity: FIXED, independently reproduced

Diff confirms the claimed mechanism: each pending file runs as `BEGIN; <sql>; INSERT
schema_migration` with **no COMMIT in the script**; `PRAGMA foreign_key_check` executes inside
that open transaction; any violation raises before `COMMIT` and the `except` path rolls the
migration *and* its version record back together. The `if not pending: return` early-exit is
gone — a whole-database `foreign_key_check` now runs on every open (message changed to
"foreign key violations in database"). `open_db` closes the connection on `_migrate` failure.
Old migration SQL files are untouched (not in the diff), FK OFF/ON toggling preserved.

Fresh probe (own scratch `t16-fix-rereview-tsf4r8z7`, synthetic `0009_evil.sql` inserting a
ghost `series` row under FK-OFF, invisible to triggers — the exact scenario the check exists
to catch):

```
R1 first open raised: foreign key violations after migration 0009_evil: [('series', 1, 'source', 0)]
R1 rollback verified: applied versions = 0001_init,...,0006_pt15m | series rows = 0
R1 reopen raises again (no silent skip)
R1 open succeeds clean after bad file removed
R1 pre-existing corruption rejected on every open (x2)
```

Side-channel inspection (raw sqlite3, migrator bypassed) shows `schema_migration` contains
exactly 0001-0006 and zero `series` rows after the failed open — the original R1 outcome
(corrupt row + recorded version + silent second open) is no longer reachable.

Test-suite evidence (named tests, fresh run):
`test_bad_migration_rolls_back_atomically_no_corrupt_applied_version` PASSED,
`test_open_rejects_preexisting_corruption_with_no_pending_migrations` PASSED.

## R2 — PT15M matches raw string: FIXED, independently reproduced

Diff confirms: PT15M pattern now matches `text = raw` (fold skipped for PT15M only) with
uppercase `T` in the pattern; A/S/Q/M/D arms still match `_fold(raw)` and their patterns are
byte-identical to the parent commit. Inline comment now correctly documents raw matching
(the old comment claimed non-ASCII rejection while folding).

Fresh probe output:

```
rejected '２０２６-１１-１０Ｔ２３：４５：００＋００：００'   (fullwidth: digits/colon/plus/T — NFKD would have folded these)
rejected '2026-11-10t23:45:00+00:00'                       (lowercase t)
rejected ' 2026-11-10T23:45:00+00:00'                      (leading whitespace)
rejected '2026-11-10T23:45:00+00:00 '                      (trailing whitespace)
PT15M ok: 2026-11-10T23:45:00+00:00                         (canonical accepted, emitted == raw)
```

All three probe-verified violations from the original review (fullwidth accepted, lowercase
accepted, whitespace accepted) now raise `ValueError`.

## Preserved behavior (required invariants)

- **Old frequencies**: `normalize_period` A/S/Q/M/D arms verified live post-fix:
  `' 2026 '`→A `'2026'`, `'1º trimestre de 2026'`→Q `'2026-Q1'`,
  `'1º semestre de 2026'`→S `'2026-S1'`, `'Janeiro de 2026'`→M `'2026-01'`,
  `'2026-11-10'`→D unchanged. Tolerant fold path intact; only PT15M bypasses it.
- **Populated 0005 upgrade + licence gate**:
  `test_0006_upgrades_populated_0005_and_preserves_everything` PASSED as-is on the fix commit
  (observations, raw_fetch provenance, verification rows, settings, served view, licence gate,
  FK enforcement post-rebuild, repeated-open idempotence). Licence-gate SQL (0005) is not in
  the diff.
- Targeted offline run, fresh: `pytest tests/ingest/test_migration_pt15m.py
  tests/ingest/test_models.py tests/ingest/test_db.py -q` → **124 passed** (.venv-ci python,
  5.62 s). Not the full suite (controller-owned); no regression signal in the touched areas.

## Gaps

None within scope. Code acceptance for R1 and R2: **PASS**. Not marking Task 16 closed —
acceptance and the live gate remain controller-owned.

Re-reviewed by: independent spec re-reviewer (subagent), 2026-11-12.
