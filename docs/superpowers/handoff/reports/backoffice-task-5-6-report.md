# Backoffice v1 - Tasks 5 and 6 implementer report

Plan: `docs/superpowers/plans/2026-11-14-backoffice-v1.md`. Branch `pipeline-rebuild`, not pushed,
not deployed (Task 6 step 5, the deploy, is the controller's).

| Task | Commit | Files |
|---|---|---|
| 5 Verification replay view | `65338cf` feat(backoffice): replay a verification item from the browser | `backoffice/{app,deps,replay}.py`, `backoffice/templates/{item,series_detail}.html`, `tests/backoffice/test_app_replay.py` |
| 6 Container, compose, docs (+ healthz readiness, inactive reasons, status cache) | `6fc1c2c` feat(backoffice): container, compose and docs | `Dockerfile`, `.dockerignore`, `deploy/prumo-backoffice.yml`, `docs/data/operations.md`, `backoffice/{app,reads,registry_notes,ttl_cache}.py`, `backoffice/templates/series_detail.html`, `tests/test_docker_contract.py`, `tests/backoffice/{test_app_overview,test_app_series}.py` |

## Task 5 - `GET /verification/item/{item_id}`

- Wiring reused, not duplicated. The CLI `replay` command is a fresh re-fetch (`run_with_refetch`), not an
  item replay. The item replay is `ingest.verify.replay_check`; `replay_item` is only its boolean
  wrapper. The page calls `replay_check` so it can show the reason. The verifier comes from
  `ingest.operations.ensure_verifier(VERIFIER_OPS[source])`, the same path `python -m ingest verify`
  uses. The registry specs are passed for pre-0012 items.
- `backoffice/replay.py` maps the result to one outcome with its reason:
  - `None` -> `match`;
  - `"no evidence archived for this item"` or the archived file not on disk -> `evidence missing`;
  - `RawIntegrityError` (sha256 mismatch) -> `evidence corrupt`;
  - any other reason string -> `mismatch`;
  - a `ValueError` (legacy pre-0004 item, wrong source), no verifier for the source, or no raw store
    configured -> `cannot replay`.
- The page shows the stored claim verbatim: expected vs observed series, period, value token,
  decimal separator, unit and flag (with the verifier's not-compared reasons), reason drawn, fields
  compared, stored note, evidence URL (linked only if `https://`) and sha256. Unknown id -> 404;
  non-integer id -> 422; missing DB or schema mismatch -> 503. Item ids on the series page now link
  to it.
- Raw store: `PRUMO_RAW_DIR` (default `/data/raw`) via `backoffice/deps.py`, passed as
  `create_app(..., raw_dir=)`.
- Read-only proof (`test_replay_is_read_only`): every file under the data dir is made read-only and
  every directory non-writable, all 10 items still replay as `match`, and afterwards every file's
  sha256 and mtime_ns is unchanged and no `-wal`/`-shm`/`-journal` exists. The DB goes through
  `read_db_readonly`; the raw store is only `load`ed (read + re-hash).
- Fixture: a real recorded Banco de Portugal run (4,318 rows) verified by the real
  `BPortugalVerifier` (10 items with archived evidence), as in `tests/ingest/test_verifier_bportugal.py`.
- Tests (10): the plan's 4 (`test_replay_matches_for_genuine_item`, `..._corrupt_evidence`,
  `..._missing_evidence`, `test_unknown_item_404`) plus read-only, item without archived evidence,
  mismatch with reason, no raw store configured, missing DB -> 503, series page links. RED: all 10
  failed (`create_app() got an unexpected keyword argument 'raw_dir'`).

## Task 6

### Container and compose (`deploy/prumo-backoffice.yml`)

- Service `prumo-backoffice` with the same build context and Dockerfile. **Deviation:** its own image
  tag `prumo-backoffice:latest`, not `prumo-ingest:latest`. If it shared the worker's tag, a
  backoffice build would retag the worker's image, and the worker's next restart would silently pick
  up new code.
- Command: `uvicorn backoffice.app:app_from_env --factory --host 0.0.0.0 --port 8080 --workers 1`.
- Port `100.118.19.6:8089:8080` only. No labels, so no Traefik route.
- Volumes: `${DOCKER_DIR}/stacks/web/appdata/prumo:/data:ro`, plus `resolv.conf:ro`.
- Environment: `TZ`, `PRUMO_DB_PATH`, `PRUMO_RAW_DIR`, `PYTHONUNBUFFERED`. There is no FRED key.
- `mem_limit: 256m`, `no-new-privileges`, `restart: unless-stopped`, network `t2_proxy` (the same as
  the worker), the same json-file logging block. Healthcheck on `/healthz`: 30 s interval, 5 s timeout,
  3 retries, 20 s start period.
- `entrypoint.sh` does `mkdir -p /data`. That works on the `:ro` mount because the directory already
  exists.
- `Dockerfile` adds `COPY backoffice/ ./backoffice/`. `.dockerignore` re-includes `backoffice/` and
  `backoffice/**`. `requirements.txt` already has `jinja2>=3.1,<4` (Task 3).
- `tests/test_docker_contract.py` checks all of the above:
  - the exact COPY list and allow-list;
  - `jinja2` in the runtime requirements;
  - the exact compose keys, volumes, environment and port;
  - no labels;
  - the factory entry point is importable;
  - `backoffice/` templates and `registry/unmapped-*.md` exist;
  - the runbook section exists.
- No image was built locally: no Docker daemon is used, per the contract tests' convention.

### `/healthz`

The endpoint always returns 200 while the app runs. The JSON body is `{"status":"ok","db":"ready"}`.
When the DB check fails, the body is `{"status":"ok","db":"unavailable","db_detail":"..."}`. The check
is one `read_db_readonly` open plus the schema check, and it never creates the file. A missing DB and
a schema mismatch are both tested.

### Inactive-series reasons (G4): done

The parsing is cheap and deterministic. `backoffice/registry_notes.py` runs once at startup:
- It reads every `registry/unmapped-*.md` next to the registry file.
- For each inactive id named as an exact token on a line, it keeps that line verbatim, with its file
  and the nearest heading above it.
- Nothing is paraphrased. The files mix tables, bullets and prose, so the heading carries the reason
  category (for example "Unit conflicts").

The series page shows a "Why inactive" table. If no line names the series, it says "no reason found".
Text is autoescaped (tested with `<script>`).

Coverage on the real registry: all 447 inactive series have at least one note. A test enforces this,
so a newly inactivated series without a documented reason fails CI.

### Docs

`docs/data/operations.md` has a new "## Backoffice" section. It covers:
- the URL;
- the three read-only layers;
- that Tailscale is the only perimeter;
- the separate image tag;
- the `/healthz` contract;
- what each page shows;
- the deploy commands (`dc-web-up prumo-backoffice`, `curl` healthz, and the worker's StartedAt check).

### Status cache (TTL 30 s)

The cache was added because the larger, production-shaped DB exceeded 3 s (timings below).

- `backoffice/ttl_cache.py` holds one value with a lock. A failure, such as a 503 refusal, is never
  cached (tested).
- `create_app(..., status_ttl_s=30, monotonic=time.monotonic)` computes the full-registry
  `build_status` report at most once per 30 s.
- `/`, `/queue`, `/series` and `/series/<id>` share that report. The series page shows
  "From the status report generated <ts> (reused for up to 30 s)".
- **Refactor first:** `reads.queue`, `reads.series_statuses` and `reads.series_detail` now take the
  report as an argument instead of computing it. The suite stayed green before the cache was added.
- The series page used to run `build_status` over its own source only. It now uses the cached full
  report. The dataset identities are the same, because grouping is per source.
- Tests: `test_status_report_is_cached_for_the_ttl` checks that the result is unchanged at +29 s and
  recomputed at +31 s. `test_db_refusal_is_not_cached` covers the refusal case.

## Page latency on a real-size scratch DB (local, f3nix, no production data)

Both DBs were built with the real `registry/core.yaml` synced (1,344 active, 447 inactive series).
Each active dataset group got synthetic verified runs, through the real `Db` writers, with recent
`fetched_at`. `ingest status` reports 1,344 active, 0 stale, 0 never fetched.
- **A**: 242,420 fetched observations (1 vintage): annual 1965-2024, monthly 2000-2024, the 3
  E-REDES PT15M series × 40,000 quarter-hours, 150 Eurostat revision events. 42 MB.
- **B** (production-shaped, because every run re-inserts all rows): 3 vintage rounds plus about 121k
  legacy rows, 848,460 observations in total. 142 MB.

The app was served by `uvicorn backoffice.app:app_from_env --factory` on 127.0.0.1. Times are curl
`time_total` in seconds, steady state over 2-3 requests each.

| Page | A, no cache | B, no cache | A, cache (miss / hit) | B, cache (miss / hit) |
|---|---|---|---|---|
| `/healthz` | - | 0.003 | - | - |
| `/` | 0.92-0.97 | **3.12-3.22** | 0.99 / 0.003 | 3.14 / 0.002 |
| `/queue` | 1.06-1.10 | **3.76-3.95** | - / 0.13-0.15 | - / 0.61-0.63 |
| `/series` | 0.92-0.93 | **3.17-3.20** | - / 0.005-0.016 | - / 0.005-0.017 |
| `/series?page=5` | 0.92 | 3.13-3.25 | - / 0.005 | - / 0.005 |
| `/series/eurostat.gdp_per_capita_eur.AT` | 0.63-0.73 | 2.56-2.69 | - / 0.006-0.04 | - / 0.008-0.04 |
| `/series/eredes.production_total.PT` (40k rows, shows newest 200 of 40,000) | 0.56 | 2.76-2.80 | - / 0.13 | - / 0.55 |
| same with `?period=` vintages | - | 2.77-2.78 | - | - |
| `/series/worldbank.gdp_usd.PT` | 0.71 | 2.72-2.93 | - / 0.006 | - / 0.008 |

Notes on the measurements:
- Profiling B: `build_status` takes 3.19 s for the full registry. Of that, `observation_stats` is
  1.39 s, `audit_grade_fetched_at` 0.65 s, and per-series Python work about 1 s. It is 2.67 s for
  the World Bank source alone, because those queries scan the whole observation table regardless of
  source. With the cache, only one request every 30 s pays about 3 s.
- `/queue` with a warm cache is still 0.6 s on B, which is mostly `latest_fetched_periods`.
- I did not optimize `ingest/status.py` or `ingest/db.py`. That is out of scope, and those queries
  are shared with `ingest status`.
- Server RSS was about 90 MB per process, well under `mem_limit: 256m`.
- No `-wal`/`-shm` files appeared next to the scratch DBs.

Read-only open under a live writer (simulates the `:ro` mount):
- A WAL DB had an open `open_db` writer with an uncommitted-to-main event in `-wal`.
- I then made the DB, `-wal` and `-shm` files `0444` and the directory `0555`.
- `read_db_readonly` read the event correctly, and no file was left behind.
- This is a local simulation (EACCES), not the container's EROFS mount.

## Deviations and notes

1. Own image tag `prumo-backoffice:latest` (reason above). For deploy, the controller should expect
   `dc-web-up prumo-backoffice` to build a new image from the f0nix checkout. That checkout must
   contain `backoffice/`, so it has to be on a commit that includes this branch's backoffice work.
2. `paths_from_env()` now returns `(db, registry, raw_dir)`. `app_from_env` is its only caller.
3. `create_app` gained the keyword arguments `raw_dir`, `status_ttl_s` and `monotonic`. Existing
   callers are unaffected.
4. Not done: `read_only: true` rootfs for the container. It is cheap hardening, but I could not
   verify it without building the image. Left for the controller or a later pass.
5. The CLAUDE.md GitNexus impact and detect-changes steps were not run: those MCP tools are not
   available in this session. The changed existing symbols are `create_app`, `app_from_env`,
   `paths_from_env` and `reads.queue/series_statuses/series_detail` (renamed `reads.overview` ->
   `reads.status_report`). All are backoffice-internal, and the only callers are `backoffice/app.py`
   and the tests.
6. `AGENTS.md` and `CLAUDE.md` are untouched; their pre-existing dirt was left unstaged.
7. Commit trailers: `Claude Sonnet 5.5`, as the plan and controller instructed.

## Test results

- `tests/backoffice`: 50 passed (was 33 after Task 4: +10 replay, +2 healthz, +2 cache, +4 inactive reasons, -1 merged healthz).
- `pytest tests --ignore=tests/ingest`: 134 passed, 1 warning (the existing starlette TestClient deprecation).
- `pytest tests/ingest -m "not live"`: 1,562 passed, 7 deselected, 2 warnings in 532 s.
- `ruff check ingest backoffice tests`: all checks passed.
