# Task 23 report: final-review part D fixes (D-I1, D-I2, D-M1, D-M2, D-M3, D-M4, D-M5, D-M7, D-M8, D-M10)

Branch `pipeline-rebuild`, base 2392dd4. Nothing was pushed or deployed. f0nix and the
production DB were not touched. AGENTS.md and CLAUDE.md were left unstaged, as found. The
GitNexus impact/detect-changes tools named in CLAUDE.md were not available in this session;
blast radius was checked with grep and the targeted plus full suites instead.

| commit | scope |
|---|---|
| ec9c027 | refactor: scheduler backoff + next-eligible time moved to `ingest/cadence.py` (no behaviour change) |
| 2e9b59d | D-M1: `blocked` logged once per process start from `main()`; `tick()` emits only attempts |
| 88844e4 | D-I2: `status`/`lag` open the DB strictly read-only; CLI reads `PRUMO_DB_PATH` |
| 23bb7e8 | D-I1, D-M2, D-M3, D-M4, D-M10: status staleness, counts, event windows, scheduler view |
| b430ade | docs: staleness definition (methodology.md) and read-only report (operations.md) |
| 14da4d8 | D-M5, D-M8: legacy `static/` and dead `app/config.py` removed; HEAD answers 200 |
| f3a7c82 | D-M7: `requirements-dev.txt`; test-only packages out of the image |

## What changed

### D-I1: staleness that does not false-flag unchanged data
- Each series now has two retrieval fields:
  - `real_data_fetched_at`: the latest observation `fetched_at` of the retained data. This
    field is unchanged.
  - New `last_confirmed_current`: the latest publisher retrieval of a run that is still
    `verified` and either
    - wrote that series' observations, or
    - is an identical-payload short-circuit whose matched run is still `verified` and holds
      that series. The matched run is the immediately previous run of the dataset, which is
      what the pipeline compares against, followed back through earlier short-circuits.
- For a short-circuit, the time used is the maximum `raw_fetch.fetched_at` of that run. For a
  recorded replay, this is the receipt's original time, never the import time.
- `stale` is judged on `last_confirmed_current` against the existing refresh policy
  (`ingest.cadence`).
- A failed, pending or withdrawn run confirms nothing. A short-circuit whose matched vintage
  was later withdrawn confirms nothing either.
- Legacy-only series are always `stale=True` with the new reason `legacy_unverified`. Legacy
  rows never confirm currency, however recent their original date. This tightens the
  previous age-based check, which could in principle have called a recent legacy row fresh.
- Never-fetched and never-verified series still have `stale=null` with their reason.
- Text `status` output now shows:
  - an `all sources:` total line;
  - per source: `stale N / never fetched N / never verified N` (active series only),
    `last confirmed current`, `data fetched`, and up to 10 `STALE` ids with `(+N more)`.
- JSON adds the per-source `stale`, `never_fetched`, `never_verified` and `stale_series`
  fields, and the report-level `totals`. The report schema version is now **2**, because
  the meaning of `stale` changed.
- D-M3: events are counted for the last 24h, the last 7d and lifetime (`events_24h`,
  `events_7d`, `events`). `Db.event_totals(since=)` takes an optional lower bound.
- D-M4: each dataset has a `scheduler` view built from `scheduler_state`:
  - last state, where `running` means in flight, or interrupted if the worker is not
    mid-attempt;
  - finish time, last success and failure streak;
  - `next_eligible_at`, computed by the same `ingest.cadence.next_eligible_at` that the
    scheduler's `_ready` now uses.

  The source line summarises the number of retrying datasets, the maximum streak, and the
  number running or interrupted.
- D-M2: `pending_stale_after_hours` is now 24 (it used `total_seconds`; before, it reported 0).
- D-M10: datasets are sorted by label. Latest-attempt and verification timestamps are
  compared after parsing, not as text.
- New Db reads, all SQL in `ingest/db.py`:
  - `verified_run_receipts()`, one query using an uncorrelated `IN (SELECT dataset_run_id
    FROM observation)`;
  - `series_of_runs(ids)`, one scan;
  - `scheduler_states()`;
  - `event_totals(since)`.
- Docs: the definition is in `docs/data/methodology.md`, in the status section and in the
  short-circuit paragraph. The operator view is in `docs/data/operations.md`.

### D-I2: a strictly read-only report
- New `ingest.db.open_db_readonly(path)`:
  - It opens the DB with SQLite `mode=ro` and `PRAGMA query_only=ON`. It runs no migration
    and no journal-mode change.
  - It raises `ReadOnlyOpenError` for a missing file, a file without `schema_migration`, a
    schema older than the code (applied migrations missing), and a schema newer than the
    code (unknown applied migrations).
- A read-only WAL open creates `-wal`/`-shm` sidecars that it cannot remove. When no `-wal`
  file exists, there is no open writer, so the DB is opened `immutable=1` and no file is
  created. When a writer is running, the plain `mode=ro` open reads its committed state.
  - Residual edge, documented in the docstring: a writer that starts during a few-second
    immutable read is not seen by that read. The report may then be stale or error out.
    The database itself cannot be harmed.
- `status` and `lag` use the read-only open and exit 2 with `<command> refused: ...` on stderr.
- The CLI default DB is now `PRUMO_DB_PATH`, then the deprecated `PRUMO_DB`, then
  `/data/prumo.sqlite3`. The workaround paragraph in operations.md was replaced. The runbook
  commands still pass `--db`/`--raw-dir`, so they remain correct for the deployed image too.

### D-M1: one blocked record per process start
- `scheduler.report_blocked(specs, now=, log=)` is called from `_locked_main` right after
  `sync_registry`, for both `--once` and serve. It logs only and writes nothing to the DB.
- `tick()` emits only `attempt` records.
- The old per-pass test was replaced:
  - `test_tick_emits_only_attempts_and_inactive_never_scheduled`: a second tick returns `[]`;
  - `test_blocked_source_reported_once_per_process_start_not_per_pass`: serve mode, 3 passes,
    exactly one blocked record, emitted first.

### D-M5 / D-M8: served legacy tree, dead config, HEAD
- The maintenance app needs only `static/images/prumo/favicon.svg`. The other 80 tracked
  `static/` files were deleted, including `static/js/sections/analise.js` with the Haiku
  panel, the AI CSS and the i18n strings. They are recoverable at the `legacy-ui-final` tag.
- `app/config.py` was dead legacy config: DuckDB paths, `site.json`, the `.openclaw` skills
  dir and model-prompt languages. Only `STATIC_DIR` was used. The file is removed and
  `STATIC_DIR` now lives in `app/main.py`.
- The `static/` mount, the Dockerfile `COPY static/` and the `.dockerignore` rules are kept,
  so the docker contract and the f0nix `:ro` bind mount of `static/` keep working.
  `/static/js/sections/analise.js` now returns 404.
- `/healthz` and the catch-all maintenance route are `api_route(methods=["GET","HEAD"])`, so
  `HEAD /`, `HEAD /healthz` and deep paths return 200.
- New tests in `tests/test_maintenance.py`:
  - a HEAD probe;
  - the static tree is exactly the favicon, served with 200, and the legacy JS returns 404;
  - `app/config.py` is gone;
  - `test_no_ai_remnants_in_static_or_current_docs`.
- That last test scans text files in `static/`, `docs/` and the root docs for
  `claude-max-proxy`/`anthropic`/`haiku`. The existing code-file test is unchanged. Allowed:
  - `docs/superpowers/`;
  - an explicit historical list: `ROADMAP.md`, `OPENSOURCE.md`,
    `docs/operations/PHASE_1_SUMMARY.md`, `docs/operations/PHASE_4_MONITORING.md` and
    `docs/testing/2026-03-01-v9-report.md`.

  These are now listed under "Historical references" in DOCS_MAP.md as describing the
  retired AI dashboard.
- README now documents favicon-only `/static` and HEAD 200, replacing "HEAD returns 405".

### D-M7: test packages out of the image
- `requirements.txt` holds runtime only: fastapi, starlette, uvicorn, requests, pydantic and
  pyyaml.
- New `requirements-dev.txt`: `pytest>=9,<10` (aligned with the 9.2.0 actually used),
  `pytest-cov>=5` and `httpx`.
- The Dockerfile is unchanged and still installs `requirements.txt` only. The deny-by-default
  `.dockerignore` excludes the dev file.
- CI installs both files. README shows the dev install.
- New contract test: `test_test_only_packages_stay_out_of_the_production_image`.

## Tests
- RED first for each item:
  - the new status tests failed with `AttributeError: last_confirmed_current`, missing
    counts, the 0-hour policy and unsorted datasets;
  - the read-only tests failed on import;
  - the scheduler tests showed blocked records per tick;
  - the maintenance tests showed 405 on HEAD, the 81-file static tree, config.py and the AI
    hits;
  - the dev-requirements test failed.
- Regression test required by the brief, through the real pipeline and verification
  (`tests/ingest/test_status.py`):
  - `test_identical_refetch_30h_later_is_confirmed_current_not_stale`: a monthly series is
    fetched and verified at T0, then the identical bytes are re-fetched at T0+30h. The second
    run is a short-circuit `verified` run with 0 rows. At T0+31h the series has
    `real_data_fetched_at=T0`, `last_confirmed_current=T0+30h` and `stale=False`.
  - `test_no_verified_run_within_the_policy_window_is_stale`: 25h after the last
    confirmation, the series is stale.
  - Also: a failed re-fetch never confirms; a short-circuit onto a withdrawn vintage confirms
    nothing; recent legacy rows stay stale; counts and totals; the capped STALE list; event
    windows; scheduler streak/interrupted/next-eligible; label sort; 24h policy.
- `tests/ingest/test_status_readonly.py` (12 tests):
  - a missing DB gives exit 2 and creates no file or parent dir (status, status --json, lag);
  - status/lag leave the DB directory byte-identical (no sidecars);
  - status works beside an open writer;
  - the read-only handle refuses writes;
  - older and newer schemas are refused, and nothing is applied;
  - a non-Prumo file is refused;
  - `PRUMO_DB_PATH` beats `PRUMO_DB`, and `PRUMO_DB` still works as a fallback.
- Real-data smoke on a scratch copy of the 2026-11-13 20:35 production snapshot (the copy was
  migrated to 0012 first, then deleted):
  - The unmigrated copy was refused as "older than this code (missing 0011, 0012)".
  - The migrated copy reported in about 4 s, with 1,344 active series and 0 never
    fetched/verified.
  - 124 series were stale at the real clock 2026-11-14 01:30 UTC. That is correct: the
    snapshot predates the 01:2x re-fetches.
- Full suites (final run): see the next section.

## Full-suite result
- `.venv-ci/bin/python -m pytest tests/ingest -m "not live" -q`: **1523 passed, 7 deselected,
  2 warnings, 0 failed** (470 s).
- `.venv-ci/bin/python -m pytest tests --ignore=tests/ingest -q`: **79 passed, 1 warning**.
- `.venv-ci/bin/ruff check ingest/ app/`: all checks passed.

## Findings outside scope (reported, not changed)
- **Eurostat dataset history is orphaned after a registry change (pre-existing).**
  - The dataset key is a hash of the group's member ids. Task 22 deactivated
    `eurostat.hicp.EU27_2020`, so the current 328-series group key differs from the key every
    past Eurostat run used.
  - On the snapshot, `status` therefore shows Eurostat with `latest attempt -` and no dataset
    line. The old code did the same. Series-level staleness still works, because it comes
    from observations and the run chain.
  - After the next deploy, the scheduler sees a new key and will run Eurostat immediately,
    with no persisted retry state.
  - Worth an owner/controller decision: whether status should also show orphaned keys of a
    source.
- Within one long run, all series of a short-circuit are credited with the run's last
  `raw_fetch` time. INE runs span about 13 minutes, so this is a minutes-level
  over-statement, accepted.

## Declined / not done
- **D-M6:** not done, out of scope.
  - Running as root is unchanged. It is not trivial: live `prumo.sqlite3`, `raw/` and the
    lock file are `root:root`.
  - A `USER` change needs a controlled `chown` of appdata on f0nix and a matching worker
    uid. That is a deployment change.
- **D-M9:** not done, out of scope.
- **D-M11:** not done, out of scope. AGENTS.md and CLAUDE.md were left as found.
- **C1 (committed FRED key):** not in this brief, untouched.
- AGENTS.md still says `pip install -r requirements.txt` for tests. The file is protected and
  was not edited. README documents the dev file.
- HANDOFF.md still says HEAD returns 405 and describes the `PRUMO_DB` workaround. It is a
  controller-owned file and was not edited.
- None of this is deployed: the deployed 49a3602 image keeps the old status, per-pass
  `blocked` lines, HEAD 405 and the legacy static tree until an authorized rebuild. The
  first rebuild must run the scheduler (the writer) before a read-only `status`, because
  `status` now refuses a database that is not yet migrated to 0012. This is expected and
  documented.
