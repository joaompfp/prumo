# Final whole-branch review: Part A (core store and data model)

Branch `pipeline-rebuild` @ 6b938fd, base `legacy-ui-final` (a18a58a). Read-only review.
Scope: `ingest/db.py`, `ingest/migrations/0001-0010`, `models.py`, `pipeline.py`, `rawstore.py`,
`validate.py`, `flags.py`, `registry.py`, `legacy_import.py`, `http.py`, `receipts.py`, and the
tests that cover them.

Evidence: 393 tests in the core-store files passed (test_db, test_migration_pt15m, test_models,
test_pipeline, test_rawstore, test_validate, test_flags, test_registry, test_legacy_import,
test_http, test_licence_gate, test_scoped_legacy, test_task17_fixes, test_task17_fix2), with live
tests excluded. Two probe scripts against fresh migrated DBs:
`/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/probe.py` and `probe2.py`.

## Strengths

- **SQL stays in one module.** No non-test module under `ingest/` issues SQL. Everything goes
  through `Db`, and the schema lives only in numbered migrations.
- **Atomic migrator.** `_migrate` (db.py:340-379) runs each file inside one transaction with
  foreign keys OFF. It runs `PRAGMA foreign_key_check` inside that transaction, before COMMIT, so
  a migration and its `schema_migration` row roll back together. The check repeats on every
  open. After all migrations, the foreign keys of the rebuilt `series`, `dataset_run` and `event`
  tables still point at the right tables (probe P6, SQLite 3.45.1). The two triggers and two
  indexes are recreated. Upgrading a populated 0001-0004 database is tested through to HEAD
  (test_licence_gate.py:135) and keeps rows byte-identical.
- **The served gate is in the view.** `served_observation` serves only verified runs, only
  sources with `redistribution_ok = 1`, and never lets a legacy row hide a fetched one. Because
  the gate is a view, revoking a licence takes effect at once and deletes nothing. The
  per-series lookup is fully indexed (checked with EXPLAIN QUERY PLAN).
- **Numbers are handled strictly.** The decimal separator is declared per series, never
  guessed. Thousands separators are accepted only in groups of exactly 3, and the regex uses
  ASCII ranges. `RawRow` refuses non-str tokens, so `"1.10"` cannot silently become `1.1`. The
  `Observation` model checks that `value` is the parse of `value_text`. Revisions are compared on
  the verbatim token. The DB trigger enforces the period format against `series.frequency`, and
  PT15M accepts exactly one canonical UTC spelling.
- **Raw evidence comes first.** Each response is stored in the content-addressed raw store
  (atomic tmp, fsync, replace) and gets a `raw_fetch` row as it arrives. Pages received before a
  mid-pagination failure are kept. Each observation is linked to the exact payload it came from.
  `RawStore.load` checks the path stays inside the store and re-hashes the file.
- **Failures are explicit.** Unknown flag codes, receipts with a bad or future timestamp,
  out-of-range `response_index` and duplicate periods all fail closed. Nothing defaults to
  'normal' or to 'now'. The verify state change is a compare-and-set, and observation writes,
  revision events and the state change happen in one `BEGIN IMMEDIATE` transaction.
- **Legacy rows are kept separate.** Legacy rows are imported as `legacy-unverified` with no
  `raw_fetch_id`, under synthetic runs marked `input_origin = 'legacy'`. They never count toward
  `max_verified_fetched_at` or scheduler freshness. Known suspect-scale INE rows are quarantined
  rather than rescaled.

## Issues

### Critical

None found.

### Important

**I1. An older recorded replay can permanently displace newer live data that is still
pending verification.**
- **Where:** `ingest/pipeline.py:191-218` and `ingest/db.py:252-263`. The tie-break is in
  `ingest/migrations/0009_blocked_stale_state.sql:66-71`, where `n.id > e.id` decides.
- **What:** The stale guard compares the recorded bundle's oldest receipt only against
  `max_verified_fetched_at`, which counts only `r.state = 'verified'`. The served view picks the
  winning vintage by insertion id, not by `fetched_at`.
- **Reproduced in probe2.py:**
  1. A live run is written on 2026-11-13 and stays `pending-verification`.
  2. A recorded bundle with receipts from 2026-11-01 for the same series passes the guard and is
     inserted with higher ids.
  3. Both runs are verified.
  4. The view serves the 2026-11-01 value `1.0` instead of the 2026-11-13 value `2.0`.

  Nothing flags this, and later live runs fix it only when they write that same period again.
- **Why:** This serves stale data while newer verified data is held, which is the failure the
  guard exists to prevent. It also contradicts the guarantee in the `StaleRecordedError`
  docstring ("a concurrent newer writer is never displaced"). The manual recorded-replay CLI does
  not take the scheduler's `.scheduler.lock`, so the window is real whenever an operator replays a
  bundle while the scheduler has a run between write and verify. The same root cause (insertion
  order instead of data time) also applies to two overlapping live runs whose write transactions
  commit in the reverse of their fetch order.
- **Fix:**
  - In `max_verified_fetched_at`, or a sibling query used by the guard, count fetched rows from
    runs in `('pending-verification', 'verified')`.
  - Better still, make the view's tie-break `(fetched_at, id)` instead of `id` alone, so serving
    order equals data time by construction.
  - Add a regression test: a pending live run, then an older recorded replay, then both
    verified, and the newer value is served.

**I2. Inactivating or removing a series does not stop serving its fetched rows, and nothing can
withdraw a verified vintage.**
- **Where:** `ingest/migrations/0009_blocked_stale_state.sql:60` (`WHERE o.kind = 'fetched'` has
  no `s.active` term), `ingest/db.py:37-61` (registry sync never touches series or sources that
  left the registry), and the `transition_run_state` usage (`verified` is terminal).
- **What:** Probe P1: a verified fetched row is still served after its series is synced with
  `active: false`. A series or source deleted from `registry/core.yaml` keeps its last
  `active` and `redistribution_ok` values forever.
- **Why:** The project's documented remedy for a definition or unit defect found after the fact
  is "mark inactive":
  - Ruling W: discontinued or rebased series are set `active: false`.
  - The 52 World Bank PPP series with a unit conflict are inactive.
  - The FRED unit and concept conflicts are inactive.

  That remedy only hides legacy rows. Any series that was fetched and verified before being
  inactivated keeps serving under the registry unit now known to be wrong. Verification is a
  50-item sample, so a wrong-but-verified vintage is possible. The only ways to withdraw it today
  are revoking the whole source's licence or hand-written SQL, which deletes or rewrites
  history.
- **Fix:**
  - Gate fetched rows on `s.active = 1` in a new view migration, as already done for scoped
    legacy rows. The existing test that covers inactive series under the global legacy switch
    shows that choice was made deliberately for legacy rows, so state the fetched-row policy
    explicitly either way.
  - Have `upsert_source_and_series` (or a reviewed CLI) set `active = 0` for registry-absent
    series.
  - If a single wrong vintage must be withdrawable without losing history, add a reviewed
    terminal state such as `verified -> withdrawn` with an event.

### Minor

- **M1. Orphan `running` runs.** `pipeline.py:102,139,104-110`: a raw-store or DB exception in
  `_record`, or in `finish()` itself, propagates out of `run_dataset` and leaves the run
  `running` forever (probe P4: `OSError('disk full')` gives `(1, 'running')`). The same happens
  on SIGTERM. Nothing is served, but the run history says nothing true. Fix: wrap the run body
  in a try/finally that records `failed-fetch` or a dedicated terminal state with the error,
  plus a startup sweep that closes `running` runs older than N hours.
- **M2. Lock contention recorded as a format change.** `pipeline.py:186-187`: any write-stage
  exception becomes `failed-validation` plus `event(format_change)`, including
  `sqlite3.OperationalError: database is locked`. The connection uses the default 5 s busy
  timeout (`db.py:383`), and the scheduler and CLI can contend. This misleads the audit trail,
  which then says the publisher changed format. Fix: give `OperationalError` its own reason or
  state, and set an explicit `timeout=`.
- **M3. No revision history for withheld sources.** `db.py:108-112`: `served_fetched_values`
  reads through the licence-gated view, so sources with `redistribution_ok = 0`
  (REN/FRED/OECD) never emit `revision` events. Their vintages remain reconstructable from
  `observation`. If such a source is later licensed, its first served revision history has
  gaps. Fix: compare against the latest verified fetched row without the licence join.
- **M4. Flags are not constrained in the database.** `0001_init.sql:55`: `status_flag` is
  free text (probe P7 stored `'whatever'`), and `validate._blank_to_none` lets an adapter omit
  it. The FLAGS policy ("exactly one of FLAGS, 'normal' explicit") is enforced only by adapter
  discipline. Fix: add `CHECK (status_flag IS NULL OR status_flag IN (...))` for fetched rows,
  or validate in `validate._check`.
- **M5. Two spellings of UTC in `observation.fetched_at`.** Legacy rows store `...Z`
  (`legacy_import.py:69-70`), fetched rows store `...+00:00`, and `scheduler_state` mixes them
  too. Lexical comparison across the two spellings is wrong within the same second. No current
  query mixes them, but status and docs code could. Fix: normalize to one spelling.
- **M6. Redirects may downgrade to plain HTTP.** `http.py:67-69`: an https URL can redirect to
  http, which opens a man-in-the-middle path for injected values. Independent verification
  mitigates this. Fix: refuse https-to-http downgrades.
- **M7. Raw-store durability and audit gaps.** `rawstore.py:24-36`:
  - There is no fsync of the parent directory after `os.replace`, so a crash can lose the file
    while the `raw_fetch` row commits.
  - A corrupt existing file is silently overwritten by `save` with no record of the
    corruption.
  - `raw_fetch.path` is stored as given, so a relative `--raw-dir` makes it relative to the
    current directory (`scheduler.py:226`, `cli.py:256`).

  Fix: fsync the directory, raise or log on mismatch, and store paths relative to the store
  root.
- **M8. A bad receipt discards its response bytes.** `pipeline.py:130-136`: an invalid receipt
  ends the run before `_record`, so that response's bytes are not kept as evidence (earlier
  ones are). Fix: record first, then fail.
- **M9. Non-ASCII digits fail the whole run.** `models.py:24-32`: the period patterns use
  `\d`, which matches non-ASCII digits that NFKD does not fold (e.g. Arabic-Indic). The
  canonical period then carries those digits, the DB trigger aborts the write transaction, and
  the whole dataset ends `failed-validation` instead of quarantining one row. This fails closed.
  Fix: use `[0-9]`, as PT15M already does.
- **M10. `value` is lossy for long tokens.** `observation.value` is REAL. Tokens with more
  than about 15-17 significant digits are lossy there (probe P8), although `value_text` is
  exact. Fix: document that consumers and the app must treat `value_text` as authoritative.
- **M11. Vintages can mix across runs with no signal.** The view keeps, per period, the latest
  verified row from any run. A period the publisher has dropped stays served from an older
  vintage, and a windowed or partial refetch (e.g. E-REDES) yields a series assembled from
  different runs. No event flags periods present in the served view but absent from a
  full-history refetch. Fix: optionally emit a `format_change` or `withdrawn` event when a
  full-history dataset no longer contains a served period.

## Declined to judge

- **Verification sample size and design** (50 items, stratified on the latest period per
  series): this belongs to Part B.
- **Flag mappings ruled lossy** (`§` maps to normal, Eurostat `f` (forecast) maps to
  estimated): these are deliberate, recorded review rulings (Task 9/10 M2), not code defects.
- **Naive legacy timestamps assumed UTC** (`legacy_import.fetched_at_utc`): this is a
  documented ruling about the f0nix collectors, and I cannot check it from code.
- **The identical-payload short-circuit marks a run `verified` without its own verification**
  (Ruling D): this is the intended semantics. It reprocesses after any non-verified previous run
  and keyed on series ids only, so a registry `decimal`/unit fix does not force a re-parse until
  the bytes change. I note this for awareness only.
- **`requests` decodes Content-Encoding**, so the stored "verbatim" body is the decoded entity,
  not the wire bytes: this is acceptable for value provenance, and the sha256 is consistent.
- **Global `legacy_served = '1'` serves inactive series too**: this is explicitly tested and
  intended (test_scoped_legacy.py:130). The setting defaults to '0'.
- **Concurrent first-open migrations**: they fail with "locked" or a UNIQUE error and roll back.
  This is safe; I did not go further.

## Assessment

**Ready to merge: With fixes.** The core store is careful. SQL is confined to `db.py`,
migrations are atomic and verified against foreign keys, the licence and verified-only gates are
in the view, and numeric tokens and periods are handled strictly and fail closed, so I found no
path for an unlicensed or unverified fetched number to reach `served_observation`. Two
trust-relevant gaps remain and should be closed first: I1 (serving picks the winning vintage by
insertion order rather than data time, so an older recorded replay can silently replace newer
data) and I2 (`active = false`, the documented remedy for definition and unit defects, does not
withdraw already-served fetched rows).
