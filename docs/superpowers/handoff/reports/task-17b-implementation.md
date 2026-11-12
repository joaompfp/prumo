# Task 17B implementation report - original-file manual capture/replay and cleanup

Branch `pipeline-rebuild`, four commits on top of 8ca4bb3 (17A). Task 17 stays OPEN for the
controller's whole-task review; no handoff/ledger/roadmap/plan staging, no deploy, no push,
no main.

## Commits

- `47a8243` feat(ingest): recorded-input contract - RawResponse.fetched_at, run
  input_origin, migration 0008 (`dataset_run.input_origin` in live/recorded/legacy;
  pre-0008 rows default 'live', legacy:<source> runs stamped 'legacy'; no old migration
  edited; SQL only in ingest/db.py + migrations)
- `f2c640a` feat(ingest): E-REDES verifier reads one CSV export per SAMPLED UTC day
  (seed-independent; ItemResult maps to its own day's response; envelope v1 2-response shape
  kept so recorded one-day evidence still replays)
- `9b8345c` feat(ingest): ingest/bundle.py + CLI capture/run --bundle/eredes day bounds +
  test_bundle.py + scoped propose-test fix
- `ddecc7a` chore(ops): entrypoint dead cron block removed; duckdb/pyarrow isolated to
  requirements-legacy.txt (only scripts/create_seed_db.py + scripts/ingest.py import them);
  ci.yml installs both files + ruffs ingest/; tests/README.md de-staled;
  docs/data/manual-refresh.md (PT-PT)

## Commands + real results (this session)

- `.venv-ci/bin/python -m pytest tests/ingest -q` -> **1300 passed, 7 deselected**, then one
  honest failure in test_licence_gate (pre-0008 synthetic run fixture gained the 'live'
  origin); fixed and re-run: `test_pipeline.py test_verify.py test_db.py
  test_legacy_import.py test_licence_gate.py` -> **243 passed**;
  `test_bundle.py test_cli.py test_status.py test_verifier_eredes.py test_scoped_legacy.py
  test_migration_pt15m.py test_independence.py` -> green (297 + 29 + 69 batches as iterated);
  the updated slow real-export test passes (`test_propose_registry.py` 10 passed incl. the
  `served_observation` assertions, REAL_EXPORT present; no hardcoded row counts).
- `.venv-ci/bin/ruff check ingest tests/ingest` -> only the two PRE-EXISTING nits on files I
  did not author (verifiers/independence.py I001 - left by 17A on purpose;
  test_verifier_eurostat.py F401). ruff-auto-fix on independence.py was reverted.
- `python -m ingest --help` / `run --help` verified: subcommands run/capture/status/verify/
  import-legacy/replay; run gained --bundle/--indicator/--from/--to; capture contract matches
  the brief (--output/--indicator/--from/--to/--timeout/--max-requests/--deadline).

## Public contracts added

- `python -m ingest capture worldbank --output DIR [--indicator CODE]` / `capture eredes
  --output DIR --from YYYY-MM-DD --to YYYY-MM-DD [--timeout --max-requests --deadline]`:
  full registered flow on a THROWAWAY TMPDIR DB (never opens --db/--raw-dir), recording
  wrapper over a bounded CaptureHttp (physical budget: every request incl. redirects counts;
  deadline checked BEFORE each request; retries=0). Exit 0 only when verified AND zero
  failure receipts; partial captures keep healthy files archived, seal an honest manifest
  with failure receipts, exit nonzero, and are refused by runs.
- `run worldbank --bundle DIR [--indicator CODE]` / `run eredes --bundle DIR --from D --to D`:
  load_bundle validates EVERY entry+byte before any DB open; PinnedHttp answers only exact
  pinned requests (no fallback); RecordedSource attaches ORIGINAL receipt fetched_at (pipeline
  validates, never falls back to 'now'); run/start/attempt times stay real; every attempt
  labelled recorded; stale bundles (held verified data strictly newer than the newest receipt)
  refused before insertion; legacy rows byte-identical afterwards (tested).
- E-REDES capture records the verifier CSV for EVERY window day (coverage pass via the
  registered verifier), so a fresh replay sample always finds its day pinned (tested with two
  days and two fresh seeds; seeds verified distinct).
- `ingest/bundle.py`: MAX_ENTRIES 4096, MAX_ENTRY_BYTES 64MB, MAX_TOTAL_BYTES 256MB; safe
  root-contained regular files only (traversal/absolute/symlink rejected); identical duplicate
  identities deduped pinning the FIRST receipt; CHANGED duplicates fail capture loudly.
- Status JSON/text now carry `input_origin` per dataset and pending run.
- test_propose_registry real-export test: replaced the outdated global `served == 0` with
  derived-set assertions (global gate 0, scoped setting 1, served legacy exactly == eligible
  active licenced WB set, other origins unserved, kind/dates preserved). No hardcoded counts.

## BLOCKED work (needs owner confirmation - tool safety stop)

The legacy-code DELETION step was attempted via `git rm` and blocked awaiting consent; NOT
performed. Pending deletion exactly as briefed: collectors/{eurostat,ine,bportugal,ren,
worldbank,fred,oecd,eredes,base}.py; scripts/{collect_scheduled,audit_nightly,
backfill_eu27,backfill_full,backfill_missing}.py; scripts/collectors/; scripts/maintenance/.
Pre-checks done: no surviving imports of them (grep across ingest/app/scripts/tests/sh/yml);
kept collectors (dgeg_fuel_api, dadosgov, habitacao, collect_new_indicators) do not import
collectors/base.py. Entrypoint cron already removed. Kept untouched per brief:
raw data/archives/seed DB, publisher fixtures, seed cleanup/Dockerfile/scheduler (T18),
collect_new_indicators.py (not listed as superseded). DOCS_MAP.md/SOURCES.md stale collector
references left for the T19 docs pass.

## Honest limits / notes for review

- Stale-bundle rule compares receipt times at source granularity (strictly-newer newest
  receipt); an equal-time re-import is an idempotent no-op via the identical-payload shortcut.
- Capture coverage for WB relies on the verification pass having fetched the CSV ZIP (a
  fully-failed group = nonzero exit, honest manifest); E-REDES explicitly backstops all days.
- Pyright (non-gate) red-herring on cli.py http_for rebinding; CI gate is pytest + ruff.
- GitNexus unavailable (read-only FTS failure, same as 17A): impact checks done with grep.
- A browser-downloaded WB ZIP without an HTTP receipt is NOT assignable a status; the manual
  doc instructs capture-tool use and declares that upload path unsupported.
