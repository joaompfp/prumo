# Task 24 report: re-review fixes (re-review 1 I-1, M-1, M-2, M-4, M-5; re-review 2 I1, M1-M6)

Branch `pipeline-rebuild`, base 267a487. Nothing was pushed or deployed. f0nix and the
production DB were not touched. AGENTS.md and CLAUDE.md were left unstaged, as found. The
GitNexus tools named in CLAUDE.md were not available in this session, so blast radius was
checked with grep and the targeted and full suites.

| commit | scope |
|---|---|
| abd01f4 | RR1 I-1, M-1, M-2, M-5: withdrawal cascade, CAS state writes, bounded orphan sweep, migration 0013. `db.py` also carries the Db reads used by the next commits. |
| df57740 | RR2 M4, M5, M6 and RR1 M-4: status, lag and read-only open |
| 3c11b34 | RR2 M3: World Bank exponent bound |
| 8d5f59c | RR2 I1, M1: previously-failed cells, verify-time reread, `reread_many`, empty evidence |
| 4e2f42a | `tests/ingest/test_task24_verification_status.py` (RR2 regressions) |
| 58b2f63 | docs (operations.md, methodology.md), CLI lists cascaded withdrawals, sampling test comment |

The commit trailers use `Claude Sonnet 5.5`, as the brief required.

## What changed

### RR1 I-1: withdrawal and the short-circuit
`Db.withdraw_run` now:
- refuses a run with no observations. The error says it is a short-circuit and that you
  should withdraw the run that wrote the rows.
- also withdraws, in the same transaction, every later run of the same `dataset_key` that is
  an unbroken chain of `verified` zero-row runs right after it. It stops at the first run that
  wrote rows or is in any other state. Each run gets its own `withdrawal` event, with
  `cascaded_from` set to the run that was named.
- returns the ids of every run it withdrew. The CLI prints them.

The next identical fetch then follows a withdrawn run, so it is re-ingested. Status stops
crediting the withdrawn short-circuits. `verified_run_receipts` only returns verified runs,
and the regression test checks that `last_confirmed_current` falls back to the older vintage.

The short-circuit check and its `running -> verified` change now happen in one transaction,
so a withdrawal cannot land between them.

Regression test: the review's sequence a/b/c, plus stop conditions for the cascade (a later
run that wrote rows; a failed run in between).

### RR1 M-1: compare-and-set and a bounded sweep
- Every pipeline exit from `running` is now `transition_run_state(run, 'running', X,
  finished_at=)`. That covers `finish`, the write transaction, the short-circuit path and
  `_close_interrupted`.
- `transition_run_state` gained the optional `finished_at` argument.
- If the CAS fails inside the write transaction, `RunClosedElsewhere` rolls back the rows.
  The run then records `operational_failure {stage: closed_elsewhere, attempted_state,
  found_state}` and returns the run's real state.
- Probe D is reproduced as a test: a second connection sweeps the run during the fetch. The
  run stays `failed-operational`, with 0 observations and the events `orphaned` then
  `closed_elsewhere`.
- `close_orphan_runs(at, min_age=ORPHAN_MIN_AGE)` sweeps a run only in two cases:
  - **Scheduler-started run.** Its dataset_key has a scheduler attempt marker that is still
    `running` and no later than the run's start (`swept_because:
    scheduler_attempt_interrupted`). This identifies scheduler-started runs without a schema
    change. It also covers the orphan the old 49a3602 container leaves at deploy, because
    that code already writes the markers.
  - **Old run.** It started at least 6 h ago (`ORPHAN_MIN_AGE`, `older_than_min_age`). An
    unparseable `started_at` also counts as old.
- A young manual run is left alone.
- Two Task 20 tests were updated to the new rule: the 1-hour orphan now needs 7 h, and the
  scheduler-start test now writes the scheduler marker.

### RR1 M-2 and M-5: migration 0013 (`0013_run_and_audit_guards.sql`)
No existing migration was edited. 0013 does three things:
1. `dataset_run_withdrawn_ins` is recreated with
   `OR EXISTS (... id = NEW.id AND state = 'withdrawn')`. `INSERT OR REPLACE` of a withdrawn
   id is refused; ordinary replaces still work.
2. `observation_fetched_at_ins` and `_upd` refuse fetched rows unless `fetched_at` is exactly
   `YYYY-MM-DDTHH:MM:SS+00:00` (25 chars) or the same with `.ffffff` (32 chars), which are
   the two `isoformat()` forms. Legacy rows are exempt and existing rows are not touched.
3. `verification_item` is rebuilt with identical columns and rows so that its `reason` CHECK
   accepts `previously-failed`. Nothing references the table and it has no index.

Synthetic test fixtures that used `'2026-01-01'` or `'2026-11-12'` as a fetched `fetched_at`
(`test_db.py`, `test_migration_pt15m.py`) now use real UTC spellings.

### RR1 M-4 (with M-2 of the status view)
- `status` marks a pending run older than 24 h as `STALE (interrupted verification? resolve
  with: python -m ingest verify <id>)`.
- It counts such runs in `totals.pending_stuck` and on the `all sources` line.
- operations.md documents the remedy in a new paragraph, "Interrupted verification".

### RR2 I1: sticky previously-failed cells
- `Db.previously_failed_keys(run_id)` returns the (series, period) of mismatched items. They
  come from failed verifications of earlier runs of the same key since that key's last
  `verified` run.
- Only items the verifier actually answered count (`observed_series_id` set). Outage and
  broken-verifier items are not carried.
- `design_sample(..., previously_failed=)` adds step 1b, `previously-failed`, which is
  uncapped. Its count is stored as `n_previously_failed` in `sample_design`.
- This works across `run_with_refetch` attempts and across separate calls (scheduler
  retries), because it follows the dataset_key history.

Tests use a deterministic-defect fixture: one monthly series of 432 cells with one wrong
history cell.
- **Fresh draws:** some seeds miss the defect, so detection probability is below 1.
- **Next attempt:** after one failed verification, all 200 draws of the next attempt include
  it as `previously-failed`, so the probability is 1.
- **End to end:** seeds are pinned so that attempts 2-5 would have missed the defect. They all
  fail on it, through 3 refetch attempts and a separate 2-attempt retry.
- **Recovery:** once the publisher fixes the cell, a verification passes and the chain
  resets.
- **At base:** the same end-to-end sequence ended `verified`, which serves the defect. That
  is exactly the review's concern.

### RR2 M1: reread at verify time, and empty evidence
- `_verify` re-reads every well-formed item from the evidence object it returned. It
  compares the re-read with the claim (`_claim_of`, now shared with `replay_check`). A
  disagreement, a raise or a wrong count fails the item with "replay would fail".
- `evidence == b""` fails with "empty evidence bytes".
- Performance: a per-item re-parse was measured on the fixtures at about 5 ms/item for World
  Bank and about 42 ms/item for FRED. That would add minutes to production census runs
  (45,915 World Bank items).
- So the Verifier protocol gained an **optional** `reread_many(evidence, items)`, which
  parses a shared response once. It is implemented for Eurostat, World Bank, FRED, OECD and
  E-REDES, and in each of them `reread` is `reread_many(evidence, [item])[0]`, so the two
  cannot diverge.
- REN, BPstat and INE keep the per-item path. Their responses are small or per item.
- All registration and independence tests still pass.

### RR2 M2
- methodology.md now says n tends to 299 (298.07, rounded up).
- The comment in `test_sampling.py` is fixed, and the test asserts
  `discovery_size(1e6) == 299`.

### RR2 M3
- `_plain` raises `ValueError` for |exponent| > `MAX_EXPONENT` (400).
- In `check`, that is a verifier raise, so the verification fails as drift, never as a pass.
- At base, `_plain('1E+401')` returned a 402-character string.

### RR2 M4
- `latest_fetched_periods` (`lag`) counts only `verified` and `pending-verification` runs.
- The `test_data_lag` seed now marks its run verified.
- A new test covers a failed run and a withdrawn run that hold an invented future period.

### RR2 M5
- `Db.audit_grade_fetched_at()` excludes runs whose passing verification is
  `pinned-bundle`. It uses an uncorrelated `NOT IN` so the query stays fast on the
  production observation table.
- `verified_run_receipts` gained a `pinned_bundle` column. A short-circuit onto a
  pinned-bundle run confirms nothing.
- A series whose verified data comes only from pinned-bundle runs is stale with
  `stale_reason=pinned_bundle_only`.
- `DatasetStatus.verifier_channel` reports the channel of the dataset's latest passed
  verification. The text shows `last verified via <channel>`.
- The status JSON schema is now **v3**. Two version assertions in tests were updated.

### RR2 M6
- `open_db_readonly(path, immutable=None)` now records `Db.immutable`. If the schema read
  fails with `DatabaseError` under immutable, it retries once with plain `mode=ro`.
- The new `read_db_readonly(path, read)` runs the whole report and retries once with plain
  `mode=ro` on `sqlite3.DatabaseError`, only when the first open was immutable.
- The CLI `status` and `lag` commands use it.

## Verification
- **RED.** The new re-review 1 tests were run against base 267a487 in a throwaway worktree:
  15 of 17 failed. The 2 that passed are guard and regression checks: the status
  credit-fallback check and the failed-run-in-between cascade stop. The re-review 2 I1/M1
  tests were run against 3c11b34, the commit before the verify fix: 5 failed, including the
  defect being served. The M3 behaviour at base was confirmed directly.
- **Upgrade path, test.** `test_0013_upgrades_a_populated_0012_database_without_changing_rows`
  builds a DB through 0012 with a verified run, verification, spec and item rows, a withdrawn
  run, an orphan, legacy rows and scheduler state. It applies 0013 and checks that all 12
  tables are row-identical, `integrity_check` is ok, the FK check is empty, and the schema
  only grew.
- **Upgrade path, real fixtures.** A probe built a DB through 0012 from the real recorded
  World Bank fixtures: 396 rows written, verified, then an identical re-fetch
  short-circuited. On that DB:
  - 0 fetched rows violated the 0013 spelling;
  - after 0013, all tables were identical, integrity was ok, the FK check was empty, and 396
    rows were served.
- **Full suites and ruff.** See the final results below.

## Not done (per brief)
Row-growth redesign, the root user, re-review 2 M7-M9, re-review 1 M-3 and M-6.

## Notes for the controller
- Deploying 0013 adds two triggers to `observation`, which cost a little on each insert. It
  also rebuilds `verification_item`. Production had 2,584 rows at the review snapshot, and
  the table grows by one item per census cell per verification, so the rebuild time scales
  with it. It should still be sub-second to seconds.
- The pre-deploy orphan of the old container is swept only if the old code had written its
  scheduler marker (49a3602 does) or after 6 h.

## Final results
- `.venv-ci/bin/python -m pytest tests/ingest -m "not live" -q`: **1552 passed, 7 deselected
  (live), 2 warnings** (510 s). Base was 1523 + 7 deselected.
- `.venv-ci/bin/python -m pytest tests --ignore=tests/ingest -q`: **79 passed, 1 warning**.
- `.venv-ci/bin/ruff check ingest tests app`: all checks passed.
