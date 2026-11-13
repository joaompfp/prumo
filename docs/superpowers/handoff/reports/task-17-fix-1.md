# Task 17 fix pass 1 — independent-review findings R1-R5 (+ the sync_registry minor)

Fixer: scoped implementer subagent on `pipeline-rebuild`, base e48e2ba. Read-only input:
docs/superpowers/handoff/reports/task-17-spec-review.md. TDD: every fix landed with a RED
demonstration first (9 new tests failed on e48e2ba code) then GREEN. No old collectors were
touched (owner approval pending), no main/deploy/push, no handoff-ledger edits. Task 17
stays OPEN: independent re-review required.

Commits:
- `6c0f325` fix(ingest): R1-R4 code + migration 0009 + tests (`tests/ingest/test_task17_fixes.py`, 11 tests)
- `12e703b` docs(data): R5 manual-refresh guide + this report

## R1 — per-dataset-group stale-bundle continuity (CRITICAL)

What was wrong: `ingest/cli.py` compared source-wide MAX(bundle receipts) vs MAX(held
verified); a stale group piggybacked on a fresh sibling and its older rows would win the
served view's last-inserted tie-break per (series, period).

Fix:
- `ingest/cli.py::_stale_bundle_groups` + `_group_oldest_receipt`: per ACTUAL DatasetGroup,
  OLDEST ORIGINAL collector receipt backing an OBSERVATION (the real adapter re-driven over
  a fresh PinnedHttp, fetch+parse, receipts taken through each row's `response_index`) vs
  that group's held verified MAX (`db.max_verified_fetched_at`). Conservative MIN-vs-MAX.
  Dataset-metadata responses (E-REDES metadata) carry no rows and can neither boost nor doom
  a payload — caught when the naive collector-MIN refused the legitimate merged two-window
  E-REDES replay (`test_bundle.py::test_eredes_capture_and_multiday_bundle_replay_two_windows`
  regressed RED until receipts were scoped to observation-backing responses).
- Refusal prints one diagnosis per stale group (group label + held date + bundle receipt
  date) to stderr BEFORE any write; when EVERY selected group is stale the replay returns 1
  BEFORE `sync_registry` (review's minor note fixed). Partial refusal flows into
  `operations.run_all(..., blocked_groups={key: detail})`: stale groups report `blocked`
  with the detail while healthy groups still run.
- `ingest/pipeline.py::_guard_recorded_not_stale` — ATOMIC guard INSIDE the observation
  transaction (`db.transaction()` = BEGIN IMMEDIATE), all SQL via Db: per series, the run's
  oldest observation receipt vs held verified max. Covers a concurrent newer writer racing
  the CLI preflight. Refusal rolls the whole dataset write back atomically and finishes the
  run as the new terminal state `blocked-stale` + event `stale_refusal` (never
  `failed-validation`: nothing failed HTTP/format).
- `ingest/migrations/0009_blocked_stale_state.sql`: rebuilds `dataset_run` (state CHECK +
  'blocked-stale') and `event` (kind CHECK + 'stale_refusal') following the 0006 pattern
  (FK OFF at statement time via `_migrate`, `foreign_key_check` inside the transaction,
  `dataset_run_key` index recreated, `served_observation` recreated VERBATIM from 0007).
  No existing row changes.
- Unchanged semantics (regression-locked by tests): equal-time re-import = verified no-op;
  strictly newer bundle accepted; empty DB/legacy-only accepts any bundle; live runs are
  never stale-checked; `served` precedence untouched; no fake clock/precision.

Regressions (all in `tests/ingest/test_task17_fixes.py`, genuine recorded fixture bytes
only): `test_mixed_bundle_refuses_only_the_stale_group` (real recorded bundle older than
held + separately captured fresher code: POP refused with diagnosis, GDP verified, held POP
rows byte-identical, idempotent re-import rc 0 no-op),
`test_fully_stale_bundle_refused_before_sync_registry` (both groups stale -> rc 1, zero new
run rows, staged registry attribution change never reaches the DB),
`test_atomic_stale_guard_inside_observation_transaction` (direct `run_dataset` recorded
replay bypassing the preflight: `blocked-stale`, 0 written, `stale_refusal` event, served
still pinned to the newer run).

## R2 — pending runs keep their own source

`ingest/status.py`: `PendingRun` gains `source` (JSON v1 additive field); attribution is the
run's OWN source column (no current-grouping membership filter); sources known only through
pending runs still get a report row. `>24h` stale flag and `input_origin` preserved.
Regression: `test_pending_runs_stay_visible_under_their_own_source` — old source-wide key
`worldbank:0ldgr0up` (not derivable from today's per-indicator grouping) appears exactly
once under worldbank with `input_origin='recorded'`; a registry-absent `oldschool` source
appears with its pending run; zero pending ids discarded; JSON docs carry the `source` field.

## R3 — `run all` survives per-source setup failures

`ingest/operations.py::run_source`: `group_specs(active)` and `http_for()` are each wrapped;
failure returns a single `blocked` GroupOutcome (`source grouping failed:` /
`http client setup failed:`) and the remaining sources still run.
Regressions: `test_run_all_continues_when_http_client_construction_fails` (factory raises
for the alphabetically-first source eredes; both worldbank groups still verify),
`test_run_all_continues_when_one_sources_grouping_is_broken` (malformed WB native_code;
eredes still verifies end-to-end).

## R4 — capture deadline is a real wall-clock bound

`ingest/bundle.py::CaptureHttp`: before each physical request the budget check stands; each
request's timeout is now CLAMPED to the remaining whole-phase budget
(`eff = min(timeout, deadline - elapsed)`); a response whose transport finishes past the
deadline is DISCARDED (BundleError, never returned as success); the default transport runs
each physical request in a KILLABLE worker subprocess (`_capture_worker`, module-level,
spawn-safe, pipes back status/final_url/body/headers or `too-large`/`error`) which the
parent joins for at most the clamped share — a stalled server is terminated AT the deadline
(no unkillable threadpool, no hidden retry); redirect count stays bounded
(`MAX_REDIRECTS`), no auth; the per-entry byte cap is enforced WHILE streaming
(`iter_content`, drop at cap+1) instead of after an unbounded `resp.content` read. The
`--deadline` help text now says exactly this. `RequestsHttp` contract untouched.

Adjacent honest-receipt bug found while verifying (same `BundleRecorder.seal`): a capture
where EVERY request failed crashed with `FileNotFoundError` (root dir never created),
destroying the honest failure manifest. Fixed: `seal()` creates the root dir before the
atomic manifest write; regression `test_capture_with_every_request_failing_still_seals_an_honest_manifest`.

Regressions: `test_capture_timeout_is_clamped_to_the_remaining_deadline` (fake transport
observes [12.0, 7.0] under deadline 12 / timeout 30),
`test_capture_rejects_a_response_arriving_past_the_deadline` (fake clock; the late body is
never returned), `test_capture_kills_a_stalled_server_at_the_real_deadline` (loopback socket
accepts and hangs; deadline 1.5s vs timeout 30s: BundleError raised and the phase ends in
~1.5s, proving the kill), `test_capture_body_cap_is_enforced_while_streaming`
(monkeypatched 4096-byte cap vs >8KB loopback body).

## R5 — manual-refresh guide made runnable

`docs/data/manual-refresh.md` rewritten: real clone URL
`git clone https://github.com/joaompfp/prumo.git prumo-pipeline` + `git checkout
pipeline-rebuild`; TODAY state explicit (ingest not deployed: no container/crond; import
runs from the existing checkout `/home/joao/projects/prumo-pipeline` with `.venv-ci`);
isolated DB/raw under an operator dir `/home/joao/pacotes/manual/` (scratch
`/home/joao/.hermes/cache/scratch/...` noted for throwaways); no `/tmp` examples, no
`/data/...` claims for today (those paths are clearly labelled PLANNED task 18); exit-state
list now documents per-group stale refusal; date-vs-reference-period and HTTP-status
originality sections preserved. Plain hyphens.

Exercised for real (no invented output):
- `git ls-remote https://github.com/joaompfp/prumo.git HEAD refs/heads/pipeline-rebuild` ->
  `4cf6083… HEAD`, `bd773f6… refs/heads/pipeline-rebuild` (reachable; note the origin branch
  tip predates this fix pass until the controller pushes).
- Genuine fixture bundle built through the REAL capture CLI path (BundleRecorder + recorded
  genuine publisher bytes, registry scoped to the fixture indicator — the offline stand-in
  for the doc's capture-machine step): `capture worldbank --indicator SP.POP.TOTL` -> rc 0,
  2 entries sealed.
- §4 import command shape (verbatim; only `--registry <fixture registry>` added as the
  offline stand-in): `.venv-ci/bin/python -m ingest --registry … --db
  "$OP/db/prumo.sqlite3" --raw-dir "$OP/db/raw" run worldbank --bundle …/bm-pop-2026-11-12
  --indicator SP.POP.TOTL` -> `SP.POP.TOTL: verified (run 1, 198 obs, 0 quarantined)`, rc 0.
- Idempotent re-import -> `verified (run 2, 0 obs, 0 quarantined)`, rc 0.
- §4 status command -> `status --json` schema prumo-status v1, dataset `input_origin
  'recorded'`, `real_data_fetched_at` preserved as the ORIGINAL capture time.

## Verification log (exact commands, run on this fix's tree)

- RED before fixes: `.venv-ci/bin/python -m pytest tests/ingest/test_task17_fixes.py -q` ->
  9 failed (stalled-request test alone took 30s, proving the missing deadline enforcement;
  body-cap test did not raise).
- GREEN after: 10 passed; +seal fix test -> 11 passed.
- Regression set: `.venv-ci/bin/python -m pytest tests/ingest/test_task17_fixes.py
  test_bundle.py test_cli.py test_status.py test_pipeline.py test_verify.py
  test_scoped_legacy.py test_verifier_eredes.py test_verifier_worldbank.py
  test_independence.py test_licence_gate.py test_db.py test_migration_pt15m.py -q` ->
  382 passed, 2 warnings (92s).
- `ruff check ingest/ tests/ingest/test_task17_fixes.py docs/` -> 9 findings, ALL
  pre-existing and out of scope (declared I001 in `ingest/verifiers/independence.py`;
  tests/conftest.py; docs/ notebooks+scripts). Zero findings in files this pass touched.

## GitNexus impact check (incomplete graph — documented)

Local index refreshed: `gitnexus analyze` -> 9,436 nodes / 15,430 edges @ e48e2ba. Impact
queries could not run: the global index holds TWO repos named `prumo` plus others, so
`gitnexus impact run_all` -> "Multiple repositories indexed"; exact retry with the full
display name (`--repo "prumo (/home/joao/projects/prumo-pipeline)"`) -> "not found";
`--repo prumo` stays ambiguous; uid targets (`Function:ingest/operations.py:run_all`) ->
"not found". `gitnexus context run_all --repo prumo` works but only lists legacy
`scripts/` candidates. Blast radius was instead verified by the 382-test targeted suite
above (every caller of the changed functions lives in tests/ingest and passed).

## Known / unresolved findings (not part of this scope)

- f3nix egress to `api.worldbank.org` timed out during the live exercise (`curl (28)` after
  20s) — exactly the failure premise of the manual-refresh guide; capture must run on a
  machine whose route works, as documented.
- GitHub HEAD/pipeline-rebuild on origin predate this fix pass; the guide's clone gets the
  fixes only after the controller pushes.
- Superseded-legacy-collector deletion remains blocked on owner approval (unchanged).
- `Bundle.max_fetched_at()` is no longer consulted by the CLI stale guard (superseded by the
  per-group observation-backing receipts); left in place as public bundle API.
- Pre-existing uncommitted edits to `AGENTS.md`/`CLAUDE.md` were present in the working
  tree before this pass; left untouched and uncommitted.

Task 17 remains OPEN pending independent re-review of these fixes.
