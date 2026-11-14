# Re-review 1: serving, withdrawal, interrupted runs, migrations 0011/0012 (f618106..267a487)

Reviewer: adversarial senior review, read-only on the checkout. Scope: Task 20 (migration 0011,
data-time serving, inactive gating, `withdrawn`, orphan sweep, SIGTERM, lock handling),
migration 0012 (Task 21), migration interplay, the Eurostat dataset-key change (task-23 note),
and a deployment dry run on a copy of the production DB.

Production DB handling: one `sqlite3` backup-API copy of
`f0nix:~/docker/stacks/web/appdata/prumo/prumo.sqlite3`, opened `mode=ro` (live WAL, max run
id 64, taken 2026-11-14 01:39 UTC). The copy was written to `/tmp` on f0nix, copied to the local
scratchpad, and the f0nix `/tmp` copy was deleted. The original was never opened writable. All
migration and probe work ran on local copies only.

## Strengths

- **0011/0012 are faithful rebuilds.** The schema of the production copy migrated 0010 -> 0012
  is object-for-object identical, after whitespace normalisation, to a fresh DB built 0001 ->
  0012. Both have the same 9 indexes (`dataset_run_key` recreated), 5 triggers and the view, and
  the same FK lists on all 8 child tables. Every pre-existing table is row-for-row identical
  (md5 of the ordered dump) after migration. `verification` changes only in its 4 new columns.
- **Fail-safe migrator.** Each file runs in one transaction with FKs off, and `foreign_key_check`
  runs before COMMIT. 0012 drops `dataset_run_withdraw_reviewed` before rebuilding `event` and
  then recreates it verbatim, which avoids the dangling-trigger RENAME failure. SIGTERM can only
  land between Python bytecodes, so it cannot split a migration.
- **The data-time tie-break is sound for the data that exists.** All 263,429 fetched rows use
  one spelling (`...+00:00`, 32 chars). `isoformat()` drops a zero fraction, and `'+'` (0x2B)
  sorts below `'.'` (0x2E), so `HH:MM:SS+00:00` < `HH:MM:SS.ffffff+00:00` still orders
  chronologically. Recorded receipts are normalised by `receipts.receipt_fetched_at`. Leaving
  the legacy id tie-break alone (mixed `Z`/fractional spellings, where `'Z'` > `'.'`) was the
  right call.
- **Withdrawal is well guarded in the normal paths.** It takes a reason, refuses legacy and
  non-verified runs, writes event + compare-and-set in one `BEGIN IMMEDIATE`, and is terminal
  against `UPDATE`. Withdraw-vs-verify and withdraw-vs-withdraw races serialise correctly.
- **Honest operational failures.** Write-stage `OperationalError` becomes `failed-operational`,
  and `except BaseException` closes interrupted runs. The SIGTERM handler is restored on return.
  The entrypoint `exec`s, so Python is PID 1 with its own handler, and PEP 475 lets the
  `SystemExit` escape a blocked socket read. The sweep closes exactly the orphan the *old*
  container leaves when it is stopped during the deploy: the old code has no handler and dies
  on SIGTERM.
- **Performance unchanged.** Full view scan: 1.59 s vs 1.52 s. A per-series lookup still uses
  `sqlite_autoindex_observation_1`.

## Issues

### Critical

None.

### Important

**I-1. A short-circuit run defeats withdrawal. The operator can withdraw an empty run with no
effect, and a withdrawn vintage is never re-ingested while the publisher's bytes stay the
same. Both contradict the runbook.**

- **Where:** `ingest/db.py:398-421` (`withdraw_run`), `ingest/pipeline.py:160,305-309`
  (`_same_as_previous_verified` looks only at the immediately previous run of the key),
  `docs/data/operations.md:395-404`.
- **Reproduced** (scratch probe `rr1/tools/probes.py`, A and A2):
  1. Run a (9.9) is verified. Run b gets identical bytes, so it short-circuits to `verified`
     with 0 rows.
  2. `withdraw_run(b)` is **accepted**, and 9.9 is still served. This is the natural mistake:
     b is the "latest verified run" that `status` points to.
  3. `withdraw_run(a)`: 1.0 is served (correct).
  4. The next identical fetch c has previous run b (`verified`), so c short-circuits to
     `verified`, writes 0 rows, and 1.0 stays served.

  The runbook says "the next scheduled run re-ingests them". The existing test
  (`test_same_bytes_after_withdrawal_are_reprocessed_not_short_circuited`) only covers the case
  where the withdrawn run is the latest one. Also, `status` (`verified_run_receipts`) credits b
  and c as "confirmed current" while the served value is the older vintage.
- **Impact today:** latent. The production copy has 0 verified short-circuit runs, because
  every source's bytes changed run to run. It does not block the deploy, but the first real
  withdrawal on a monthly World Bank group could hit it.
- **Fix (minimal):** in `withdraw_run`,
  - refuse a run with no observations ("short-circuit run; withdraw run N that holds the
    rows"), and
  - in the same transaction, also withdraw (each with its own `withdrawal` event,
    `cascaded_from`) every later `verified` zero-row run of the same `dataset_key` up to the
    next run that wrote rows.

  `previous_run` is then `withdrawn`, the next identical fetch is reprocessed, and the runbook
  sentence becomes true. Add the a/b/c test.

### Minor

**M-1. The orphan sweep can close a live manual run, which then resurrects itself.**

- **Where:** `ingest/scheduler.py:253`, `ingest/db.py:423-437`, `ingest/pipeline.py:119,194`.
- **What:** the sweep closes all `running` runs with no age bound. The review's own M1 fix
  suggested "older than N hours". The pipeline's later state writes are unconditional
  `set_run_state`.
- **Reproduced** (probe D): a run is mid-fetch, a second connection sweeps it (event
  `operational_failure`/`orphaned` + `failed-operational`), and the run then commits rows and
  `pending-verification`. The result is a run with a false "interrupted" event that can go on to
  be verified and served.
- **Plausibility:** the runbook puts manual commands in the **web** container
  (`docker exec prumo ...`, `operations.md:156-197`), which survives a `prumo-ingest` restart.
  "Stop the worker before a manual import" (`operations.md:419-420`) is the only guard, and
  starting the worker before the import finishes is an easy operator slip.
- **Fix:**
  - Pipeline state writes out of `running` should be compare-and-set
    (`transition_run_state(run_id, 'running', X)`). Inside the write transaction, a failed CAS
    raises and rolls back.
  - Optionally bound the sweep to runs whose `started_at` is older than, say, 6 h, or record
    the PID/host.

**M-2. The DB guard against leaving `withdrawn` is bypassable, so the runbook claim is
overstated.**

- **What:** `INSERT OR REPLACE INTO dataset_run(id, ..., state) VALUES (<withdrawn id>, ...,
  'verified')` is accepted with FKs ON (probe B). REPLACE's implicit delete fires no trigger,
  and the FK check passes because the id reappears. The withdrawn rows are served again.
  `operations.md:401-402` says "hand-written SQL included".
- **Fix:** extend `dataset_run_withdrawn_ins` with
  `OR EXISTS (SELECT 1 FROM dataset_run WHERE id = NEW.id AND state = 'withdrawn')`. A BEFORE
  INSERT trigger fires before REPLACE deletes the old row. Or soften the doc.
- Going *into* `withdrawn` by hand needs a hand-inserted `withdrawal` event (probe C). That is
  acceptable, because the event is the review record.

**M-3. Operational errors outside the write stage leave `running` runs for the life of the
process.**

- **What:** an `OperationalError` in `begin_run`/`record_raw_fetch`/`finish()` makes
  `_close_interrupted` retry the same locked DB (30 s) and swallow the failure. The run stays
  `running`, and `run_source` records `error` and continues. Only the next scheduler *start*
  sweeps it, and the scheduler runs for weeks.
- **Fix:** at the end of each `tick`, close this process's own `running` run ids that are no
  longer in flight (or retry `_close_interrupted` once after the busy period).

**M-4. Interrupted verification leaves `pending-verification` forever.**

- **What:** SIGTERM during `run_with_refetch`'s verify stage leaves the run
  `pending-verification`. Nothing sweeps it, and since Task 20 it counts as "held" for
  `max_held_fetched_at`. This is harmless for serving and visible in `status` after 24 h.
  Document that `verify <run_id>` is the remedy.

**M-5. No DB constraint on the fetched `fetched_at` spelling.** Serving correctness now depends
on every fetched row being `+00:00` UTC text (0011 header). Only `pipeline._iso`/`receipts`
enforce it. A cheap guard is a `BEFORE INSERT ON observation WHEN NEW.kind = 'fetched' AND
NEW.fetched_at NOT LIKE '%+00:00'` RAISE trigger in the next migration. There are no violations
today.

**M-6. Eurostat dataset key change (task-23 note). Assessment and minimal handling.**

- **Root cause:** the key is the sha256 of the sorted member ids. Deactivating
  `eurostat.hicp.EU27_2020` changes 329 -> 328 members, so a new key.
- **Measured effects on the dry run:**
  - At deploy the scheduler finds no `scheduler_state` row for the new key and runs Eurostat
    immediately. Otherwise it would next run 2026-11-15 01:36. That is one extra polite run of
    about 40 s.
  - The old key's `scheduler_state` row stays orphaned (eurostat: 2 rows after the dry run).
  - `status` shows Eurostat `latest attempt -` / `last verified never` until that first pass
    completes, minutes after deploy. Series staleness is unaffected (stale 0).
  - The identical-payload short-circuit loses its predecessor for one run. This is irrelevant
    in practice: production Eurostat never short-circuited (runs 12 and 63 each wrote about
    45.5k rows).
- **Unaffected:** the stale guard, revision detection and `served_fetched_values`, which are
  per series, not per key; and legacy keys (`legacy:eurostat`).
- **Minimal safe handling:**
  - Accept it. Do **not** re-key history by SQL: old runs genuinely covered 329 series.
  - Note it in the deploy log.
  - Optional follow-up: `status` lists `scheduler_state` keys not in the current plan as
    `retired`.

## Dry-run results (production copy, 2026-11-14 01:39 UTC snapshot)

| Check | Before (0010) | After 0011+0012 | After deploy start (sweep + registry sync) |
|---|---|---|---|
| schema_migration | 10 | 12 | 12 |
| integrity_check / foreign_key_check | ok / [] | ok / [] | ok / [] |
| dataset_run / event / observation | 64 / 182 / 424,692 | identical (md5) | identical (no orphans: sweep closed 0) |
| quarantine / raw_fetch / verification / verification_item | 34,077 / 403 / 39 / 2,584 | identical (verification +4 cols, backfilled 39 x `v1-python-random-sample`/`live`/`live`) | identical |
| scheduler_state / series / source / setting | 25 / 1,791 / 9 / 2 | identical; `verification_spec` 0 (new) | 26 (new Eurostat key); series metadata: active 1 (EU27_2020 -> 0), seasonal_adjustment 335, unit 23, geography 9 (Task 22 registry) |
| Active series (DB) | 1,345 | 1,345 | 1,344 |
| Served rows total | 172,537 | 172,537 (**byte-identical** TSV of every served row) | 172,224 |
| Served per source | bportugal 4,318; eredes 64,767; eurostat 45,503; ine 12,034; worldbank 45,915 | same | eurostat 45,190 (-313); others same |
| Migration runtime | - | 0.556 s (reopen 0.169 s) | sync 0.16 s; full `scheduler --once` start (stub runner) 4.6 s |
| DB size | 77,938,688 B | 77,987,840 B (+48 KiB, +0.06 %) | same |
| `python -m ingest status` | refused: "schema is older than this code (missing 0011, 0012)" (correct) | exit 0, 4.7 s; 1,344 active, stale 58 | same; `--json` parses, totals {active 1344, stale 58, never_fetched 0, never_verified 0} |
| Groups due at real now | - | - | eurostat (new key), ine, oecd, ren; 0 World Bank |

**Why serving did not change at migration.** There are 0 fetched rows on inactive series. There
are 0 (series, period) pairs where a higher-id fetched vintage has an older `fetched_at`, out of
64,338 multi-vintage keys. There are 0 equal-`fetched_at` duplicates. So neither 0011 change
(active gate, data-time tie-break) bites today.

**The -313 rows at registry sync** are exactly `eurostat.hicp.EU27_2020` (`active: true` ->
`false` in the registry, C-I1). That is intended. It produces no `series_deactivated` event,
which is correct: the series is still in the registry, so it was not "absent".

**124 stale vs 58 stale.**
- 124 was on the 2026-11-13 20:35 snapshot at 01:30.
- Re-run on that snapshot at 01:43, it gives 180. The 1-day window rolls past more of the
  2026-11-13 01:2x runs.
- On the fresh 01:39 copy it gives 58 (ine 38, oecd 6, ren 14). These are the groups last
  confirmed 2026-11-13 01:3x and due now.

All figures are clock-dependent and consistent. The 1,344 active count comes from the registry,
so it shows even before sync.

## Declined to judge

- **Row growth.** Every verified run re-inserts every row, even unchanged values. Eurostat
  writes about 45.5k rows per daily run, and production gained about 424k rows in about one
  day. This is a pre-existing vintage-per-run design, outside this batch, but worth an owner
  decision (multi-GB per year).
- Task 22 metadata relabels (335 seasonal_adjustment, 23 unit, 9 geography) on the production
  copy. They are outside my scope, and served values are unaffected (the view does not read
  them).
- The sample design v2 statistics (Task 21 verifier logic) beyond the 0012 schema/backfill.
- I did not run the full pytest suite. Task reports state 1523 + 79 passed.
- No GitNexus tools in this session; blast radius was checked by grep.

## Assessment

**Safe to deploy: Yes, with fixes recommended but not blocking.** The dry run is clean:
- migrations are atomic, fast (0.56 s) and lossless;
- the schema matches a fresh build;
- served output is byte-identical through migration, and changes only by the intended 313
  EU27_2020 rows at registry sync;
- `status` works;
- the old container's possible orphan is handled.

I-1 (withdrawal vs short-circuit) should be fixed before anyone uses `withdraw` in anger. Until
then, the runbook should tell operators to withdraw only the run that wrote the rows and to
expect no automatic re-ingest when the next fetch is byte-identical. M-1 and M-2 are cheap
hardening for the next migration/PR. Eurostat's key change needs no code before the deploy:
note it in the deploy log.
