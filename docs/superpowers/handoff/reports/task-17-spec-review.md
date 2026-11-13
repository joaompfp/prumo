# Task 17 independent SPEC review (17A + 17B) — whole task

Reviewer: independent subagent. Scope: commit e48e2ba on pipeline-rebuild (diff bd773f6..e48e2ba),
briefs task-17a/b-brief.md and implementation reports task-17a/b-implementation.md only. Read-only:
no implementation edits, no commits. Offline probes run in /home/joao/.hermes/cache/scratch/t17-review
(probes.py; scratch DBs/bundles only). No network, no production paths.

## Verdict: REQUEST_CHANGES

The slice is substantially built as briefed (per-indicator WB isolation, scoped legacy serving,
recorded-bundle mechanics, honest legacy/status semantics, E-REDES per-day verifier, capture
security). Four reproducible technical gaps remain against binding requirements (no silent data
loss, pending-state visibility, run-all resilience, bounded capture), plus one doc blocker.

## Blocking technical gaps (reproduced offline)

### 1. Stale-bundle guard is source-wide MAX vs MAX — a stale group slips through and can replace newer verified data (silent serving regression)

- ingest/cli.py:256-268: `existing = db.max_verified_fetched_at(ids)` over ALL selected active
  source series, compared to `bundle.max_fetched_at()` = MAX over ALL bundle receipts
  (ingest/bundle.py:415-421). Neither side is scoped to the dataset group actually replayed.
- Probe S4 (real CLI path, real registry): held verified data for indicator group
  BX.KLT.DINV.WD.GD.ZS at fetched_at 2026-06-01; bundle receipts: that indicator at 2026-05-01
  (older) + another indicator at 2026-11-10 (fresh). Printed: `existing=2026-06-01
  newest=2026-11-10 -> refuses? False`; group-scoped comparison would refuse (`True`). The real
  `python -m ingest run worldbank --bundle ...` emitted NO `refusing an outdated bundle`
  (rc=1 only from downstream failed-fetch of the synthetic bodies).
- Consequence (code-derived): with a genuine complete bundle the replay verifies and inserts
  fetched rows with NEWER observation ids but OLDER fetched_at; migration 0007's served view
  tie-breaks same-kind rows by `n.id > e.id` (ingest/migrations/0007_scoped_legacy_serving.sql,
  last lines) — i.e. the LAST INSERTED verified run wins per (series, period). A stale
  receipt therefore silently replaces newer verified data in serving, exactly the
  old-collector-JSON-plus-fresh-CSV scenario the controller flagged. Violates the brief's
  "refuse outdated source/group bundle before insertion" and old-data continuity.
- Fix direction: compare per dataset group — newest receipt pinned to that group's own requests
  vs that group's held verified max — and refuse/skip the stale groups individually.

### 2. Pending-verification runs with historical (unmapped) dataset keys vanish from status

- ingest/status.py:164-172 builds PendingRun with `label_of_key.get(key, key)` but PendingRun
  carries NO source field; attribution at status.py:237-239 filters by membership in the
  CURRENT grouping's label set. A key not derivable from today's grouping policy (any pre-17A
  source-wide WB key, or any registry id change) matches nothing and is dropped from every
  source — invisible pending state, violating "pending run ids/start dates listed" and
  "pending state visible even if others healthy".
- Probe S2b: inserted pending run (dataset_key `worldbank:0ldgr0up`, 25h old) alongside two
  mapped pending runs; `build_status` JSON shows runs [2, 3] under worldbank; historical run 4
  appears in NO source's pending_runs ("visible anywhere: False").
- Fix direction: attribute pending runs by the run's own source column (already selected in
  db.runs_overview but discarded) and list unmapped keys explicitly.

### 3. run all aborts entirely if HTTP client construction fails for one source

- ingest/operations.py:254 `http = http_for()` sits OUTSIDE the per-source try/except; run_all
  (269-283) does not guard run_source either. Group fetch errors (256-266) and source/verifier
  factory failures (244-253) are contained, but client construction is not — a registry
  misconfiguration raising in RequestsHttp, or any injected factory failure, kills every
  remaining source.
- Probe S5: http_for raising RuntimeError -> `run_all RAISED boom:bportugal -> loop aborted;
  dataset runs started before abort: []`. Violates "run all continues on failure".
- Fix direction: wrap http_for() like the factory/verifier steps and report 'blocked'.
  (The existing contained behavior for FRED key absence and DGEG is covered by
  test_cli.py:128 and passes.)

### 4. CaptureHttp: global deadline checked only before transport; per-request timeout never clamped

- ingest/bundle.py:143-158: `_budget()` checks the deadline before each physical request, but
  the timeout handed to the transport is the full per-request value (`eff`, line 158). The
  network phase can therefore exceed the "whole capture deadline" by up to one full timeout
  (default 30s past a 300s deadline), which the CLI help ("whole capture deadline in seconds")
  and the 17B report ("deadline checked BEFORE each request") overstate.
- Probe S1: deadline 10s, timeout 30s, transport consuming 25s -> request completed at t=25s
  (`deadline exceeded by 15.0s WITHOUT any error; timeout passed to transport: [30.0]`); the
  NEXT request is correctly budget-refused. Budget stays finite (bounded by deadline+timeout
  and max_requests) but is not the contracted bound.
- Fix direction: clamp each request's timeout to the remaining deadline, or document the
  effective bound honestly.

### 5. Doc blocker: manual-refresh guide not runnable as written

- docs/data/manual-refresh.md:19 `git clone <url do repositório> prumo-pipeline` — unresolved
  placeholder; the brief requires the exact tested commands a user can run on another machine
  without reading source. Everything else in the guide (commands, paths, exit states,
  capture-then-bundle flow, current vs future container paths, pyyaml/requests present in
  requirements.txt) checked out. Insert the real clone URL/path.

## Verified as meeting the brief (probes + reading)

- Invalid bundle never opens the DB: probe S6 — corrupted-bytes bundle, rc=2, target DB file
  never created; manifest validation (schema/version/source/keys, url/params shape, status int
  100-599, tz-aware timestamps normalized to UTC, sha256 hex, byte caps, traversal/absolute/
  symlink rejection, identical-duplicate dedupe pinning FIRST receipt, changed-duplicate hard
  fail) all read in ingest/bundle.py:307-403 and confirmed consistent; per-body re-hash on read
  (Bundle.body) present. PinnedHttp refuses partial (failure-carrying) bundles and answers only
  exact pinned requests; no network fallback.
- Recorded origin honesty: RawResponse.fetched_at validated by ingest/pipeline.py:45-58
  (_receipt_ts) — bad receipt -> failed-validation, never a silent 'now'; run started_at stays
  the actual attempt time; run_with_refetch labels EVERY attempt via input_origin
  (verify.py:264-290); migration 0008 stamps legacy runs 'legacy', additive only.
- Status honesty: probe S3 — legacy-only series shows availability 'legacy-unverified',
  last_verified null, original 2026-02-27 fetched date, legacy row count; source last_verified
  null; legacy synthetic 'verified' run excluded from attempts and from verification evidence
  (legacy_keys filter, status.py:177-187). Pending staleness threshold is CORRECT (probe S2a:
  25h -> stale True, 10h -> False); the 17A report's `timedelta.seconds` worry does not apply
  (comparison is on the full delta; PENDING_STALE_AFTER.seconds//3600 = 24 is exact here).
  Per-dataset latest state from the authoritative grouping; blocked vs technical failure kept
  separate; DGEG all-inactive reads BLOCKED.
- Registration/independence guards unweakened: tests/ingest/test_independence.py 13 passed;
  eredes_verifier_entry.py diff only re-orders the call assertion (metadata first); WB
  indicator_locales validated eagerly and copied, no fallback; ensure_verifier reuse contract
  with clear mismatch error; no private-registry mutation. No helper sharing between
  parsers/verifiers introduced by the E-REDES per-day change (verifier reads its own reviewed
  endpoint; capture coverage reuses the REGISTERED verifier itself, not collector helpers).
- E-REDES per-SAMPLED-day CSV (verifiers/eredes.py): one export per sampled UTC day, item
  mapped to its own day's response, cross-day duplicate datahora rejected, per-day evidence
  keeps the v1 2-response envelope so one-day recorded evidence still replays; capture
  backfills EVERY window day (cli.py:412-430). Bounds validation (strict ASCII days, non-empty,
  not today/future) at cli.py:181-195 happens before any DB open.
- Scoped legacy serving (0007): seeds ONLY legacy_served_source:worldbank=1; global
  legacy_served default 0 kept; scoped branch requires active series + redistribution_ok=1;
  fetched-beats-legacy precedence intact.
- CLI contract: argparse validation precedes DB open/mutation; dry-run never touches real
  paths; run continues across group/source failures; verify <run_id> refuses legacy/wrong
  state/unknown id/inactive/unverifiable and uses get_verifier's instance; replay never
  verifies legacy (legacy byte-identical assertion exists in tests).
- Targeted suites re-run (offline): `pytest tests/ingest/test_bundle.py test_cli.py
  test_status.py test_scoped_legacy.py test_verifier_eredes.py test_verifier_worldbank.py
  test_independence.py test_licence_gate.py -q` -> 141 passed. `ruff check ingest/` -> only the
  declared pre-existing I001 in verifiers/independence.py.
- No credentials beyond the keyless channels: capture restricted to worldbank/eredes; FRED
  explicit FRED_API_KEY only, missing key blocks only fred.
- Cleanup state: entrypoint.sh dead cron block REMOVED (retained old collectors cannot activate
  a schedule); requirements split isolates duckdb/pyarrow to requirements-legacy.txt with CI
  installing both. The superseded-collector DELETION is a known pending item blocked on owner
  approval (tool gate) — NOT counted here as a code defect; its pre-checks (no surviving
  imports) are documented in the 17B report.

## Minor notes (not blocking)

- Stale-bundle refusal runs after open_db+sync_registry (cli.py:252-258): registry metadata can
  be written before the refusal. Bundle validation itself is correctly pre-DB (S6). Acceptable
  if deliberate; worth a comment.
- status.py:203-207: a registry-absent source present only in DB rows reports verifiable=True
  by default (no spec0); acceptable read-only fallback, flag for awareness.

Task 17 remains OPEN. Re-review after fixes for items 1-5 should focus on the per-group stale
comparison, pending-run source attribution, the http_for guard, and the doc URL.
