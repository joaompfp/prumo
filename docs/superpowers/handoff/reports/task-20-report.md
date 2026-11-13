# Task 20 report: final-review part A fixes (I1, I2, M1, M2)

Branch `pipeline-rebuild`, base f618106. Commits: 7c56ba0 (code + tests), 7833d30 (docs),
plus this report. No push, no deploy, f0nix and the production DB untouched. AGENTS.md and
CLAUDE.md left as found (unstaged).

## What changed

### A-I1: serving follows data time
- New migration `ingest/migrations/0011_data_time_serving_and_withdrawal.sql` (no existing
  migration edited). The served view's tie-break for fetched rows is now
  `(fetched_at, id)`: the newest retrieval time wins and the higher id only breaks ties.
  Legacy rows keep the id rule. They are imported in sorted `fetched_at` order, and they mix
  `...Z` with `....ffffffZ` spellings, which do not compare correctly as text within one
  second. Fetched rows all use the single `+00:00` spelling from `pipeline._iso` and
  `receipts`.
- The stale guard now also counts runs in `pending-verification`.
  `Db.max_verified_fetched_at` is renamed to `Db.max_held_fetched_at`, which counts
  `verified` and `pending-verification` runs only, not failed or withdrawn ones. It is used
  by the in-transaction guard in `pipeline.py` and by the CLI per-group preflight in
  `cli.py`, so the two stay consistent.

### A-I2: inactive series, registry removal, withdrawal
- In the view, fetched rows are eligible only when `s.active = 1`. Legacy eligibility is
  unchanged: the global switch still serves inactive legacy rows (an intended, tested
  behaviour), and the scoped switch still requires `active`. Under the old view, the global
  legacy switch also let fetched rows of inactive series through. That path is now closed.
- `Db.upsert_source_and_series` (registry sync) sets `active = 0` on every active series
  missing from the given registry. It emits `event(series_deactivated, {series_id,
  reason: absent_from_registry})` once per transition and keeps the rows. All production
  callers pass the whole registry (scheduler, CLI, legacy import). The operations manual
  warns never to point a writing command at a partial registry together with the
  production `--db`.
- Withdrawal adds a new terminal run state, `withdrawn`, settable only through
  `Db.withdraw_run(run_id, reason, at)`. In one transaction it checks the run (a non-empty
  reason, a run that exists, not legacy, state `verified`), writes
  `event(withdrawal, {reason, previous_state})` and then does a compare-and-set
  `verified -> withdrawn`. Three triggers in 0011 enforce this in the database:
  - a run cannot be inserted as `withdrawn`;
  - `withdrawn` is terminal;
  - a run can become `withdrawn` only from `verified`, only if it is non-legacy, and only
    when a withdrawal event already exists for it.

  Hand-written SQL and the generic state setters therefore fail. Withdrawn runs are never
  served, because the view requires `verified`. A new CLI command,
  `python -m ingest withdraw <run_id> --reason R`, prints the refusal and returns exit code
  2 on a ValueError.
- Documented in `docs/data/operations.md`, in the new section "Withdrawing data, inactive
  series and interrupted runs", with a bash fence that `bash -n` checks. The "Served stage
  and vintages" paragraph of `docs/data/methodology.md` is updated to match.
  Stated limitation: withdrawal removes one vintage. If the publisher still returns the same
  values, the next run re-ingests them (tested). Inactivation is the persistent remedy.

### A-M1: no orphan `running` runs
- `run_dataset` wraps the work after `begin_run` in `except BaseException`. If the run is
  still `running`, it is closed as `failed-operational` with
  `event(operational_failure, {stage: interrupted, error})`, and the original exception is
  then re-raised. A secondary DB failure during that cleanup is swallowed so the original
  exception propagates.
- The scheduler installs a SIGTERM handler that raises `SystemExit(143)`, so finally paths
  run on `docker stop`. The previous handler is restored when `main` returns.
- At start, under its instance lock and before registry sync, the scheduler calls
  `Db.close_orphan_runs(now)`. It closes every leftover `running` run as
  `failed-operational` with stage `orphaned`, which covers OOM and SIGKILL. This assumes no
  manual CLI writer runs at the same time, which the runbook already requires.

### A-M2: lock contention is operational
- `ingest.db` re-exports `OperationalError` (so the pipeline does not import sqlite3) and
  opens connections with an explicit 30 s busy timeout (`BUSY_TIMEOUT_S`).
- In the write stage, an `OperationalError` such as `database is locked` now ends the run as
  `failed-operational` with `event(operational_failure, {stage: write})`. It used to end as
  `failed-validation` with a `format_change` event.

## Tests added (`tests/ingest/test_task20_serving.py`, 16 tests, RED first)
All 15 initial tests were run against the unchanged code and failed for the expected reasons:
- the replay ended `pending-verification` instead of `blocked-stale`;
- the view served `1.0` instead of `2.0`;
- inactive series stayed served;
- `withdraw_run` and the CLI `withdraw` command did not exist;
- interrupted runs stayed `running`;
- `busy_timeout` was 5000;
- 0011 did not exist.

After the fix all of them pass. The tests are:
- the review probe sequence: a live run on 2026-11-13 stays pending, a 2026-11-01 bundle is
  replayed (now `blocked-stale`), both runs are verified, and `2.0` is served;
- view-only: an older vintage inserted last still loses, and equal `fetched_at` falls back
  to id;
- an inactive series is hidden and then served again after reactivation; it stays hidden
  under the global legacy switch;
- a series removed from the registry is deactivated, with one event and its history kept;
- withdrawal: the older vintage returns; the event and reason are recorded; withdrawn data
  is excluded from `max_held_fetched_at`; refusals cover an empty reason, a pending run, a
  run that is already withdrawn and a legacy run; triggers refuse `set_run_state` and
  `transition_run_state` into `withdrawn` and out of it;
- the same bytes after a withdrawal are reprocessed, not short-circuited;
- the CLI `withdraw` command (missing `--reason`, success, refused second withdrawal);
- interrupted runs (OSError, SystemExit) end `failed-operational` with an event;
  `close_orphan_runs`; the scheduler start closes orphans, and the SIGTERM handler raises
  `SystemExit(143)` and is restored;
- a locked write is recorded as `operational_failure` with no `format_change`; the busy
  timeout is at least 30 s;
- migration: a DB populated through 0010 (verified and old-inserted-last vintages,
  verification item, failed run, orphan running run, legacy row, scheduler state, quarantine)
  upgrades to 0011 with all 11 tables byte-identical. The served value changes from the
  defective `1.0` to `2.0`. Foreign keys, indexes and triggers are intact, and reopening is
  idempotent.

## Verification
- Targeted core suites (test_db, migration_pt15m, pipeline, licence_gate, scoped_legacy,
  task17_fixes/fix2/live_fix, status, registry, legacy_import, verify, bundle): 330 passed.
- Non-ingest suites (`tests --ignore=tests/ingest`): 74 passed, including the runbook and
  docker-contract shell checks of operations.md.
- Full suite `.venv-ci/bin/python -m pytest tests/ingest -m "not live" -q`: 1413 passed, 7 deselected (live), 2 warnings (386 s).
- `ruff check ingest tests/ingest/test_task20_serving.py`: clean.

## Declined / notes
- Minors M3 to M11 were not touched, as scoped.
- No source-level deactivation for sources removed from the registry. It was not in scope:
  their series are deactivated, which already stops serving.
- Legacy tie-break deliberately unchanged (reason above). Normalizing the UTC spelling (M5)
  is out of scope.
- `close_orphan_runs` runs only at scheduler start, not in the CLI, because the CLI holds no
  lock that excludes a concurrent scheduler.
- The project CLAUDE.md asks for GitNexus impact analysis before edits. No GitNexus tools
  were available in this session. Blast radius was checked by grep instead: there are 2
  callers of the renamed `max_held_fetched_at`; production callers of
  `upsert_source_and_series` are `registry.sync_registry` only; state strings are used
  generically in `status`, `verify` and `operations`.
- Production impact when deployed (not done here): 0011 rebuilds `dataset_run` and `event`
  on the 1,345-series DB. The served output can change only where a fetched vintage with an
  older `fetched_at` had the higher id, or where a series is inactive and has verified
  fetched rows (for example the World Bank PPP or FRED conflict series, if any were fetched
  before inactivation). That should be checked on a copy before deploying.
