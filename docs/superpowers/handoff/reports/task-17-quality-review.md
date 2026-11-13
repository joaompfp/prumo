# Task 17 whole-task code QUALITY review (17A + 17B + fix pass 1) — independent

Reviewer: independent quality subagent (third pass). Scope: `pipeline-rebuild` @ eddb91c,
full diff bd773f6..eddb91c (both slices + R1-R5 fixes). Inputs read: task-17a-brief.md,
task-17b-brief.md, task-17-fix-1.md, task-17-fix-spec-review.md (spec re-review PASS);
the actual code/diff was then inspected directly, not the self-reports. Read-only: probes
only under /home/joao/.hermes/cache/scratch/t17q-*, no production/HTTP, no edits, no
deletion re-attempt (legacy-collector deletion stays owner-gated as already agreed).

## Verdict: REQUEST_CHANGES — ONE material provenance hole (F1), everything else holds

The acceptance items are genuinely implemented and verified by 362 passing focused tests;
one explicit acceptance criterion (receipt validation of future fetch times) is absent
and provably exploitable through the manual path this task exists for.

## Acceptance checklist (verified in code, not in reports)

- **run all / status / verify / replay / import-legacy CSV** (`ingest/cli.py:339-591`):
  all arg validation happens BEFORE any DB open/mutation; `--dry-run` and `--bundle`
  mutually isolated; dry-run opens only TMPDIR-scoped stores (`cli.py:244-246`).
  `verify <run_id>` refuses non-positive ids, unknown runs, legacy synthetic runs,
  non-pending states, registry-absent sources and verifiable:false sources, and hands
  ONLY the `ensure_verifier`-registered instance to `verify_run` (`cli.py:546-591`).
- **one verifier per source, WB per-indicator en/es**: `WorldBankVerifier(csv_language,
  indicator_locales)` validates codes (`_INDICATOR` fullmatch) and locale allowlist at
  construction, COPIES the map, exposes a copy-returning property
  (`verifiers/worldbank.py:262-296`); `operations.ensure_verifier` reuses only on the
  exact compatible configuration (`csv_language=='en'` and map equality), clear mismatch
  error otherwise, private registry never mutated (`operations.py:96-122`). Reviewed
  mapping `WB_INDICATOR_LOCALES` exact and explicit, no fallback (`operations.py:42`).
- **source-scoped WB legacy continuity**: migration 0007 recreates the licence-gated view
  with the global key kept default-off + `legacy_served_source:worldbank=1`, active+redist
  gated, fetched always beats legacy on tie (`0007_scoped_legacy_serving.sql`); legacy
  synthetic runs labelled `input_origin='legacy'` (`db.py:189-194`, `0008`).
- **explicit manual capture/replay, real statuses, original timestamps**: capture archives
  ACTUAL int status + ORIGINAL tz-aware `_utc_now()` receipt (`bundle.py:294-315`), atomic
  body+manifest writes, refuses existing non-empty output, changed-duplicate requests fail
  the capture loudly, identical duplicates pinned to the FIRST receipt; loader validates
  EVERY entry and body (schema/version/source/exact-key sets, url scheme http(s),
  status 100..599, tz-aware ISO, sha256 form, per-entry/total/member caps, safe relative
  regular non-symlink contained-under-root files, disagreement-rejecting duplicate
  identities, post-shape byte+hash verification) BEFORE any DB open (`bundle.py:385-481`,
  `cli.py:428-431`); `PinnedHttp` fails closed on any unpinned request and refuses partial
  bundles (`bundle.py:511-534`); run clock is real attempt time while raw_fetch/observation
  fetched_at is the receipt's ORIGINAL time with per-row response_index provenance and
  failed-validation (never silent 'now') on a malformed receipt
  (`pipeline.py:135-146, 88-90`).
- **per-day E-REDES CSV + capture covers all window days**: verifier fetches ONE export per
  SAMPLED UTC day, per-day envelope retains prior one-day replay compatibility, item maps to
  its own day (`verifiers/eredes.py:159-220`); `_capture_eredes_coverage` proactively records
  a genuine CSV for EVERY source window day through the same registered verifier/recording
  client (`cli.py:460-489`).
- **safe loader / killable HTTP worker / hard deadline**: bounded worker subprocess per
  physical request, joined at most the clamped share, terminate->kill escalation, byte cap
  enforced WHILE streaming, every physical request (redirects included) counts against
  `max_requests`, deadline checked pre-flight and post-flight with the late response
  DISCARDED (`bundle.py:140-246`); no secrets anywere in the capture path (keyless WB/E-REDES
  only, headers = User-Agent only, no env reads).
- **atomic stale guard + 0009**: per-group MIN(observation-backing receipts)-vs-MAX(held
  verified fetched) preflight BEFORE sync_registry plus an atomic in-transaction guard
  raising inside BEGIN IMMEDIATE, rolling the whole dataset back to terminal `blocked-stale`
  + `stale_refusal` (`pipeline.py:184-213`, `cli.py:281-336`); 0009 follows the proven 0006
  rebuild with `served_observation` recreated VERBATIM from 0007 (diff-confirmed readable
  copies), no history loss; legacy-run `legacy:` keys never count as held data.
- **DGEG blocked vs licence-withheld distinct, per-dataset failures visible**: run_source
  reports verifiable:false as non-exit-relevant `blocked` WITHOUT HTTP
  (`operations.py:239-243`); status keeps `not_verifiable`/`licence_withheld` blockers
  separate from technical failure; latest state is per DATASET from the authoritative
  grouping, pending runs attributed to their OWN source with historical keys kept visible
  and >24h stale flag (`status.py:140-242`).
- **polite cadence**: `_http_for` uses min active-spec throttle (default 1 rps), registry
  `timeout_s` (INE 300), retries=0 (`cli.py:200-209`).
- Controller-owned legacy-collector deletion: remains gated on owner approval — NOT a new
  quality bug; not re-attempted here.

## Finding F1 — MAJOR: bundle receipts and pipeline accept FUTURE fetch times

**What**: neither `BundleEntry` validation (`ingest/bundle.py:_entry_ts`, lines 110-120)
nor `RawResponse` receipt validation (`ingest/pipeline.py:_receipt_ts`, lines 54-66)
rejects a timestamp in the future; nothing else does either. `load_bundle`'s entry checks
verify format/tz only, and `_stale_bundle_groups` (cli.py) + `_guard_recorded_not_stale`
(pipeline.py) compare receipts against held data but never against the import-time clock.

**Why it matters**: the capture tooling runs on an arbitrary operator machine by design
(the task's whole premise — the server egress cannot reach the publisher). A capture
laptop with a wrong clock stamps receipts ahead of real time. Such a bundle:
1. passes `load_bundle` and `verify`-independent validation;
2. beats BOTH stale guards (held real-now data compares older than the future receipt), so
   future-stamped observations are written and become the served view's newest per
   (series, period) — provable false freshness: `status` then reports the data as fresh
   with a fabricated retrieval date;
3. LOCKOUT: afterwards every genuine bundle (receipts at real time) compares OLDER than
   the fake-future held data and is refused as stale (`held > oldest`), so the manual
   refresh path bricks itself until real time passes the fake date.
This directly breaks the briefed guarantee "no false freshness from manual import" and the
listed receipt-validation requirement (malformed/future time).

**Exact repro** (offline probe, /home/joao/.hermes/cache/scratch/t17q-*):

```python
future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
# manifest with one entry: fetched_at=future, status 200, real sha/bytes/file
b = load_bundle(root, source="worldbank")          # -> ACCEPTED
print(b.entries[0].fetched_at)                      # 2027-11-12T21:16:54.575277+00:00
_receipt_ts(future)                                 # -> accepted, normalized
held = datetime.now(timezone.utc).isoformat()
held > _receipt_ts(future)                          # -> False  => stale guard ACCEPTS the bundle
```
Probe output (real run):
```
A1 future receipt ACCEPTED by load_bundle, entry fetched_at = 2027-11-12T21:16:54.575277+00:00
A2 _receipt_ts(future) -> 2027-11-12T21:16:54.575277+00:00
A3 guard decision for future bundle: held 2026-11-12T21:16:54.579428+00:00 > oldest: False -> bundle ACCEPTED (would clobber/newest)
A4 naive correctly rejected
```

**Suggested fix**: reject `fetched_at > now + skew` (documented, small — e.g. 10 min) in
`_entry_ts` at load AND independently in `_receipt_ts` at write time (the pipeline must not
trust the loader for its own invariant), with tests: future receipt refused by load_bundle
and by a direct run_dataset recorded replay; equal-to-now accepted. Note `_utc_now()` in
bundle.py is already the honest clock to compare against.

## Minor findings (non-blocking)

- **M1** `bundle.py:238` redirect detection uses `"Location" in resp_headers` on the PLAIN
  dict piped back by the worker (line 87 `dict(resp.headers)`), losing requests'
  case-insensitivity. An HTTP/2 server (mandates lowercase field names) or any lowercase
  `location:` sender yields an unfollowed 3xx recorded as final. Fail-CLOSED (the adapter
  non-2xx path makes the capture honestly incomplete, rc 1), never data corruption, so
  minor. Fix: case-normalize lookup. Probed: fake transport returning
  `("301", ..., {"location": "https://.../y"})` -> `cap.get()` returned the 301 unfollowed,
  1 request total.
- **M2** (carried from fix-spec review, confirmed present): on the bundle replay path
  `cli._stale_bundle_groups` calls `operations.group_specs` unguarded (cli.py:300) — a
  malformed registry WB native_code raises ValueError as a traceback instead of the clean
  `blocked` outcome the live path produces (run_source catches it, operations.py:258-262).
  Pre-write, loud-not-silent; cosmetic robustness gap.
- **M3** `cli.py:334` `_group_oldest_receipt` swallows `Exception` wholesale for the
  predictive probe and silently skips the group (documented choice; the in-transaction
  guard still protects the write). Acceptable, but consider logging at least the probe
  failure to stderr so a systematically unreproducible plan is not invisible.

## Verification log (commands actually run, this tree)

- Focused suite: `.venv-ci/bin/python -m pytest tests/ingest/test_task17_fixes.py
  test_bundle.py test_cli.py test_status.py test_pipeline.py test_verify.py
  test_scoped_legacy.py test_verifier_eredes.py test_verifier_worldbank.py
  test_licence_gate.py test_independence.py -q` -> **362 passed** (84 s), no network.
- Offline probes above (future receipt, naive receipt, lowercase location, guard decision),
  all under /home/joao/.hermes/cache/scratch, PYTHONPATH against the task tree.
- Migration 0009: FK-checked-in-transaction rebuild identical in pattern to 0006; the
  earlier independent populated-DB probe (task-17-fix-spec-review.md) showed zero FK
  violations, byte-identical data tables and unchanged served set; the served view text in
  0009 matches 0007 verbatim (read side-by-side).
- Diff scope of the fix commits confirmed confined to cli/operations/pipeline/status/
  bundle/0009/tests/docs; no old migration edited; no collector deletion in the diff.

## Out of scope / unchanged risk register

- Legacy-collector deletion: still blocked on owner approval (known; not a defect).
- f3nix->api.worldbank.org egress timeout: documented premise of the manual path.
- Origin branch tip predates the fix pass until the controller pushes.

Task 17 stays OPEN; recommend one focused fix for F1 (+ M1 optionally), then the controller
gate. No shared handoff files edited; nothing committed by this review.
