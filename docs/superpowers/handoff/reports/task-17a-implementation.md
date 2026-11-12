# Task 17A implementation report — operational CLI/status/replay, per-indicator World Bank isolation & scoped dated legacy serving

Branch `pipeline-rebuild` at `bd773f6`; all work in four commits on top. Task 17A only — this is
NOT "Task 17 complete" (17B adds the original-file bundle/capture, manual-update instructions
and safe legacy cleanup). Task remains open for controller review after 17B.

## Commits

- `f9c85ed` feat(ingest): per-indicator export locale map on WorldBankVerifier
- `d96b3de` feat(ingest): migration 0007 — WB-scoped serving of dated legacy rows
- `a83b2a3` feat(ingest): operational CLI, status projection and run orchestration
- `427bb98` test(ingest): ensure_verifier reuse contract

Touched paths only; `task-17-design.md` stays untracked (unapproved research proposal, NOT
followed — the subprocess-per-locale idea is replaced by the accepted per-indicator locale
configuration on one registered instance). No handoff/ledger/plan/roadmap staging, no push,
no deploy, no main.

## Commands + real results

- `.venv-ci/bin/python -m pytest tests/ingest/test_verifier_worldbank.py -q` → **52 passed**
  (incl. 8 new per-indicator locale tests; the static allowlist + subprocess independence
  guards still pass with the configured instance registered).
- `.venv-ci/bin/python -m pytest tests/ingest/test_scoped_legacy.py tests/ingest/test_licence_gate.py tests/ingest/test_migration_pt15m.py` → **21 passed**
  (0006-populated-DB upgrade test updated: its pinned `setting` snapshot now honestly includes
  the 0007-seeded `legacy_served_source:worldbank=1`; nothing else changed there).
- `.venv-ci/bin/python -m pytest tests/ingest/test_cli.py tests/ingest/test_status.py tests/ingest/test_scoped_legacy.py tests/ingest/test_verifier_worldbank.py -q` → **80 passed**.
- Neighbouring suites (db/pipeline/verify/independence/registry/locale/CLI/status/legacy):
  **289 passed** — no live marker, no 4-min full suite (controller runs it).
- `.venv-ci/bin/ruff check` on all touched paths → clean (a pre-existing import-order nit in
  `ingest/verifiers/independence.py` exists on a path I didn't author; left for the controller's
  scope, untouched on purpose).

Real CLI smoke (no network; empty scratch DB, full registry, this afternoon):

    $ python -m ingest --db $S/p.db --raw-dir $S/raw status
    prumo status (schema prumo-status v1) - generated 2026-11-12T19:48:56.958105+00:00
    staleness = our refresh policy (schedule or defaults A/S=30d, Q=7d, M/D/PT15M=1d), not a publisher release date
    bportugal: 10 active / 0 inactive series; latest attempt - (-); last verified never; data as of none; events {}
    dgeg: 0 active / 17 inactive series BLOCKED (not_verifiable, licence_withheld); ...
    fred: 12 active / 8 inactive series BLOCKED (licence_withheld); ...
    oecd: 6 active / 0 inactive series BLOCKED (licence_withheld); ...
    ren: 14 active / 0 inactive series BLOCKED (licence_withheld); ...
    worldbank: 930 active / 52 inactive series; ...
    $ python -m ingest replay --from ２０２６-０４   → exit 2  "--from must be an ASCII YYYY-MM month, got '２０２６-０４'"
    $ python -m ingest replay --from 2099-01       → exit 2  "--from '2099-01' is in the future ..."

`--help` lists exactly the contract subcommands: `run <source|all> [--dry-run]`,
`status [--json]`, `verify <run_id>`, `import-legacy <csv>`, `replay --from YYYY-MM`, with
global `--db` (`$PRUMO_DB` or `/data/prumo.sqlite3`), `--raw-dir` (`$PRUMO_RAW_DIR` or
`/data/raw`), `--registry` (canonical `registry/core.yaml`).

## Public contracts (no plugin framework, no event bus)

- `ingest/cli.py` — argparse/printing ONLY. `main(argv=None, *, http_for=None) -> int`; the
  `http_for(name)` seam is the test injection point (default: per-source `RequestsHttp` with
  min registry throttle (default 1 rps), registry `timeout_s` (INE 300) and **0 client
  retries**). Dry-run opens only a throwaway DB/raw store under TMPDIR (`--db`/`--raw-dir`
  never opened; test asserts the real paths never come into existence). Bad args (unknown
  source, non-ASCII/future/out-of-range month, non-positive run id, non-CSV legacy path →
  clear DuckDB explanation) exit 2 before any DB open or mutation.
- `ingest/operations.py` — domain operations: `RunRequest(window=None|explicit E-REDES day
  bounds)` (the public contract 17B's manual tiny-window procedures can use), `group_specs`
  (THE authoritative grouping; status derives dataset identity from it),
  `SOURCE_FACTORIES`/`VERIFIER_OPS` (lazy: FRED key absence raises in the factory and blocks
  ONLY fred), `ensure_verifier` (register once; reuse a pre-registered instance only when
  configuration-compatible, else a clear "incompatible configuration" error; the private
  registry is never touched), `run_source`/`run_all` → `RunReport` with per-group
  `GroupOutcome` and `exit_code()` (1 iff an ACTIVE, verifiable source did not verify;
  DGEG-style blocked is reported but never fails the aggregate). Normal runs and replay go
  through `run_with_refetch` ONLY (max_attempts default 3).
- `ingest/status.py` — `build_status(db, specs, *, now=None) -> StatusReport` (typed,
  `to_dict()`/`to_json()` with `schema="prumo-status" version=1`) + `render_text`. Read-only;
  the CLI status command accepts no timestamp input.
- SQL: only `ingest/db.py` (new read methods: `source_list`, `series_list`, `runs_overview`,
  `observation_stats`, `event_totals`, `verification_overview`, `run_series_ids`, `run_info`)
  and migrations. No other module gained a SQL string.

## Binding decisions as implemented

1. **World Bank per-indicator isolation**: `group_specs` turns the 930 active series into 18
   datasets (one per native indicator code, all its registered geographies); `run worldbank`
   iterates them sequentially, a failed `failed-fetch` group (e.g. the birth-rate CSV outage
   analogue, tested through a recorded-fixture 500) never blocks the healthy groups; public CLI
   stays `run worldbank`.
2. **One WorldBankVerifier per process** with explicit `indicator_locales={"NY.GDP.MKTP.KD.ZG":
   "es", "SL.UEM.TOTL.ZS": "es"}` (the reviewed 2026-11-12 mapping; default behavior unchanged
   when the map is omitted). Codes/locales validated eagerly; the input dict is copied (caller
   mutation + accessor mutation cannot change verification); no automatic fallback between
   locales (a mapped-locale failure never even touches /v2/en/); evidence URLs prove the locale
   used per indicator.
3. **Migration 0007**: seeds ONLY `legacy_served_source:worldbank=1`; the served view keeps the
   0005 licence gate and fetched-beats-legacy precedence and adds the scoped branch
   (`kind='legacy-unverified' AND series.active AND source-scoped setting=1 AND
   redistribution_ok=1`). Global `legacy_served` default 0 unchanged (backward compat test
   included). Inactive PPP-conflict WB series NOT exposed; eredes/dgeg/fred legacy NOT enabled
   (no keys; licence gate still wins); licence revocation is immediate; a failed fresh run
   never hides or becomes eligible over old good data; legacy kind/NULL raw_fetch/original
   fetched_at untouched (upgrade test asserts byte-identical rows).
4. **verify <run_id>**: resolves the run's source, refuses legacy runs / wrong state / unknown
   id / registry-absent or inactive series / unverifiable source, then calls `verify_run` ONLY
   with `get_verifier(source)`'s instance (after `ensure_verifier`). This command necessarily
   verifies an EXISTING pending run; everything else uses `run_with_refetch`.
5. **replay --from YYYY-MM**: strict ASCII month, future rejected before any mutation; fresh
   normal fetches via `run_with_refetch`; E-REDES gets the explicit window
   `['<month>-01T00:00:00+00:00', today-UTC-day-start)`; other sources fetch their full native
   window (help text states honestly that missing vintages are NOT recreated). Legacy rows/runs
   byte-identical afterwards; legacy runs receive NO verification rows (tested).
6. **Status honesty**: real `fetched_at` of retained data reported separately from
   `last_verified`/`latest_attempt`; legacy synthetic `verified` runs never count as
   verification evidence (`availability: legacy-unverified`, `last_verified: null`, legacy row
   counts + original date kept so the data's AGE is visible); latest attempt excludes legacy
   runs entirely; per-DATASET latest state (a healthy final WB indicator cannot conceal an
   earlier failed one — tested both directions); pending-verification runs listed with the >24h
   staleness flag; events are total counts per kind; staleness = OUR refresh policy
   (`schedule` else A/S=30d, Q=7d, M/D/PT15M=1d) documented in the JSON `staleness_policy`
   block; never_fetched/never_verified are explicit null reasons; the Ruling-D idempotent
   shortcut run invents no new verification and does not advance the stored data date (tested);
   blocked (`licence_withheld`, `not_verifiable`) is separate from technical failure and the
   all-inactive DGEG reads `BLOCKED (not_verifiable, licence_withheld)`.

## Test notes

- Offline end-to-end CLI exercises use the recorded genuine WB publisher bytes only
  (`FixtureHttp` JSON + `VerifyFixtureHttp` CSV ZIPs through a URL-routing double):
  run→serve→status, per-group failure isolation, import-legacy→replay dated-legacy continuity,
  and verify of a real pending run. Double/synthetic cases (DGEG blocked, FRED key missing,
  arg errors, unit mismatches) are labelled as such, not publisher results.
- Dry-run isolation is asserted by the continued non-existence of the requested real paths.

## Process notes / limitations for review

- GitNexus: index for this repo exists but its `augment` query path fails read-only here
  (FTS write attempt); impact analysis before existing-symbol edits was done with grep instead
  (`WorldBankVerifier`: test files + entry point only; constructor change is purely additive).
- Pyright (dev-env only, not the project gate) flags the pre-existing `expected_format`
  ClassVar/protocol variance on adapter classes; factory functions therefore carry no `Source`
  return annotation. CI gate (pytest + ruff) is green.
- `status` needs no network or credentials; `run fred` without `FRED_API_KEY` is BLOCKED with
  a clear detail and never prints any key.
- No scheduler/deploy/main changes, no legacy-collector deletion, no cleanup — 17B scope.

## Remaining for 17B (not started)

- Original-file bundle/capture evidence for the legacy WB continuity decision, manual-update
  procedures (tiny-window replay via the `RunRequest.window` contract is ready), and safe
  legacy cleanup (quarantined-row review, old collector removal after owner confirmation).
- Controller reviews Task 17 after BOTH slices; this task is intentionally left OPEN.
