# Task 17 fix re-review (R1-R5 + migration 0009 populated-safety) — independent

Reviewer: independent subagent (second pass). Scope: commit eddb91c on `pipeline-rebuild`,
diff e48e2ba..eddb91c, fix report task-17-fix-1.md, original review task-17-spec-review.md.
Read-only: no code edits, no commits. Offline only (no network, no full suite — controller
running): 6 targeted test files + a populated-DB migration probe in
/home/joao/.hermes/cache/scratch/t17-rereview-0009v6.

## Verdict: PASS

All five review findings are genuinely fixed, the new migration 0009 is populated-safe, and
no touched contract regressed. Two cosmetic residuals below are NOT blocking.
(Probe note: its single flagged 'schema_migration changed' line is the migration bookkeeping
table recording 0009's own application — expected and correct; every DATA table compared
byte-identical.)

## Evidence re-run on this tree

- Targeted tests (offline, clean env): `.venv-ci/bin/python -m pytest
  tests/ingest/test_task17_fixes.py test_status.py test_bundle.py test_cli.py
  test_pipeline.py test_verify.py -q` -> **252 passed** (includes all 11 new fix tests and
  the touched-contract suites).
- Populated-DB 0009 probe (built a DB stopped at 0008 with FK-linked source/series/
  dataset_run/raw_fetch/observation/event + seeded settings, one redistribution_ok=1 and one
  redistribution_ok=0 source, a verified run, then applied 0009 via the real `_migrate`):
```
served before/after 0009: [('series-1',)] -> [('series-1',)]
blocked-stale + stale_refusal writable on populated migrated DB: OK
old migration files diff vs e48e2ba: ''
ERRORS: ['table schema_migration changed across 0009']
```

## Per-finding verification

### R1 — per-group stale-bundle continuity: FIXED
- `cli._stale_bundle_groups` compares, per ACTUAL DatasetGroup, the OLDEST receipt backing
  an OBSERVATION (real adapter re-driven over a fresh PinnedHttp; rows mapped through
  `response_index`, so dataset-metadata/verifier responses — which carry no rows — can
  neither boost nor doom freshness) against that group's held verified MAX. MIN-vs-MAX is
  conservative on both sides, matching the required semantics (oldest collector receipt, not
  fresh CSV/meta).
- Fully-stale replay returns 1 BEFORE `sync_registry` (the review's minor note is fixed: a
  refused bundle no longer rewrites registry metadata). Partial refusal flows through
  `run_all(..., blocked_groups=...)`; healthy groups still run and verify.
- `pipeline._guard_recorded_not_stale` runs INSIDE `db.transaction()` (BEGIN IMMEDIATE): an
  old recorded receipt loses to held verified data ATOMICALLY even under a race with a
  concurrent newer writer; the whole dataset write rolls back and the run finishes in the
  new terminal state 'blocked-stale' + event 'stale_refusal' (never failed-validation).
  `verify.py` only accepts `pending-verification` runs, so blocked-stale is genuinely
  terminal; equal-time re-import stays a verified no-op via the identical-payload
  short-circuit (strict `>`), live runs are never checked (recorded-only branch).
- Migration 0009: rebuild pattern identical to proven 0006 (FK OFF at statement time via
  `_migrate`, per-file transaction, `foreign_key_check` inside before commit);
  `served_observation` recreated VERBATIM from 0007 (diff empty), event table columns
  preserved with additive-only CHECK, `dataset_run_key` index recreated. Populated-DB probe
  above: zero FK violations, all pre-existing rows byte-identical, served set unchanged,
  licence gate still excludes a redistribution_ok=0 source, new states writable. No old
  migration file edited (git diff of 0001/0005/0006/0007/0008: empty). Auto-discovered via
  `_migrate`'s glob; db.py correctly untouched.

### R2 — historical pending keys visible exactly once: FIXED
`PendingRun` carries the run's OWN `source` column (additive JSON field); attribution is
`p.source == name` and the source list is unioned with `{p.source for p in pending}`, so a
source known only through old pending runs gets a row and each pending run appears under
exactly one source. Stale (>24h) flag and input_origin preserved. Locked by
test_pending_runs_stay_visible_under_their_own_source (old source-wide key + registry-absent
source, zero pending ids discarded).

### R3 — per-source setup failures contained: FIXED
`run_source` wraps `group_specs` (ValueError — grep-verified the ONLY raise type in
operations' grouping paths) and `http_for()` (Exception) into single 'blocked' GroupOutcomes;
`run_all` continues with the remaining sources. Locked by
test_run_all_continues_when_http_client_construction_fails and
test_run_all_continues_when_one_sources_grouping_is_broken.

### R4 — real wall-clock capture deadline: FIXED
Per physical request the timeout is CLAMPED to the remaining phase budget, a response
finishing past the deadline is DISCARDED (BundleError, never returned), and the default
transport runs each request in a killable worker subprocess joined at most its clamped share
(terminate -> kill escalation; no unkillable threadpool). Byte cap enforced WHILE streaming
(iter_content, drop at cap+1). `--deadline` help text now states exactly this. Honest-capture
bonus: `seal()` creates the root dir so an all-failed capture still seals its failure
manifest. Locked by the 4 new capture tests (clamped [12.0, 7.0], late discard, real 1.5s
kill of a stalled loopback server, streaming cap) — these are REAL mechanisms, not post-hoc
checks.

### R5 — manual-refresh guide runnable: FIXED
Real clone URL `https://github.com/joaompfp/prumo.git` (matches `git remote get-url origin`)
+ `git checkout pipeline-rebuild`; TODAY state honest (no container/crond; import from the
existing checkout with `.venv-ci`, isolated operator dir `/home/joao/pacotes/manual/`);
`/data/...` clearly labelled PLANNED task 18; no `/tmp`; exit states document the per-group
stale refusal. Fix report shows the §4 import command was exercised for real via the offline
fixture path (rc 0, 198 obs, idempotent re-import no-op). No invented deployment claims.

## Untouched-contract checks (no regression)
- Diff scope: cli/operations/pipeline/status/bundle/0009/tests/docs ONLY — verify.py,
  db.py, verifiers/, registration code, 0001-0008 SQL all untouched. Value precision and
  verifier registration semantics unchanged.
- No collector deletion in the diff (owner-approval tool gate; known pending item, not a new
  bug). Bundle validation pre-DB behavior untouched.

## Minor residuals (non-blocking, cosmetic)
- M1: on the BUNDLE replay path, `cli._stale_bundle_groups` calls `operations.group_specs`
  unguarded — a malformed registry there crashes the CLI with a traceback. This is pre-write
  (sync_registry not yet run, no data loss) and the live path is clean via the run_source
  guard. Failures fail loud, not silent.
- M2: `_group_oldest_receipt` calls the source factory outside its try; only reachable for
  sources without capture support (FRED), which the documented flows never bundle.

## Process note
The 15-tool-call cap was exceeded by ~4 calls: the populated-DB probe needed 4 harness-side
iterations (probe-script bugs: pk handling, environment PYTHONPATH leakage into the CI venv,
migrations' seeded `setting` key). No failure was ever imputed to product code; the final
probe and the 252-test run above are the verdict's basis.

Task 17: fixes verified; recommend the controller proceed with its gate (push/deploy and the
separately-gated collector-deletion approval remain outside this review).
