# Backoffice v1 - Tasks 3 and 4 implementer report

Plan: `docs/superpowers/plans/2026-11-14-backoffice-v1.md`. Branch `pipeline-rebuild`, not pushed, not deployed.

| Task | Commit | Files |
|---|---|---|
| 3 Overview and queue pages | `8bba499` feat(backoffice): overview and queue pages | `backoffice/{app,deps,reads}.py`, `backoffice/templates/{base,error,overview,queue}.html`, `requirements.txt` (+`jinja2>=3.1,<4`), `tests/backoffice/{conftest,test_app_overview}.py` |
| 4 Series list and provenance page | `55861b8` feat(backoffice): series list and provenance page | `backoffice/{app,reads}.py`, `backoffice/templates/{series_list,series_detail}.html`, `tests/backoffice/test_app_series.py` |

## What was built

- `backoffice.app.create_app(db_path, registry_path, now=None) -> FastAPI`. It loads the registry once at startup, so a bad registry fails fast. `now` is a `Callable[[], datetime]`, the same convention `build_status` uses. `app_from_env()` is the uvicorn factory: `uvicorn backoffice.app:app_from_env --factory`. It reads `PRUMO_DB_PATH` (default `/data/prumo.sqlite3`, the scheduler's default) and `PRUMO_REGISTRY` (default `registry/core.yaml`) through `backoffice/deps.py`.
- Routes are `GET`/`HEAD` only, declared with `api_route(..., methods=["GET","HEAD"])` so uptime probes get 200. The routes are `/healthz`, `/`, `/queue`, `/series` and `/series/{id}`. The OpenAPI and docs routes are disabled.
- Every DB read goes through `read_db_readonly`. A `ReadOnlyOpenError` (missing DB, or a schema older or newer than the code) is turned into a 503 `error.html` page with the refusal text by one exception handler. An unknown series is a 404 page.
- Layering:
  - `backoffice/reads.py` builds the page data from one read-only `Db` handle, using `Db` methods, `build_status`, `lagging_series` and `derive_queue`. It contains no SQL.
  - `app.py` does only HTTP and rendering.
  - No new `ingest/db.py` query was needed.
- Templates:
  - Jinja `Environment(autoescape=True)` is created explicitly.
  - The `link` filter turns only `https://` URLs into `<a>` links. Every other URL (`http:`, `javascript:` and so on) is shown as escaped text.
  - The `as_json` filter renders event details as plain escaped JSON text.
  - Every table sits in an `overflow-x:auto` wrapper, so pages work at phone width. The viewport meta tag is set.
  - Light and dark modes use CSS variables with `prefers-color-scheme`, and `html, body` have an explicit background.
  - There is no JavaScript.
- Overview mirrors `render_text`: totals with element ids `t-<key>`, then one row per source with blockers, stale/never counts, timestamps, scheduler and 24 h/7 d events. Below that, one collapsible block per source lists pending runs (with a STALE remedy), datasets and stale series links.
- Queue reads `recent_events(since=now-7d, kinds=[verification_failure, verification_escalated, revision], limit=200_000)`. That limit is large enough to count revision bursts per run (one Eurostat run is about 150 events). If the limit is ever reached, the page says the counts are a lower bound. Stuck pending runs come from `runs_in_state("pending-verification", older_than=now-STUCK_PENDING_AFTER)`, and lag from `lagging_series(specs, db.latest_fetched_periods(), today)`. The DB event kind stays `verification_failure`; the queue kind `verification_failed` is used only in the queue.
- Series list:
  - Filters: source, theme, geography, frequency, active (`yes`/`no`/empty; anything else gets a 422), and `q`, a case-insensitive substring of id, indicator_key or native_code.
  - 100 rows per page; `page` must be at least 1, otherwise 422.
  - The status label comes from `build_status`.
- Series detail:
  - Registry spec and licence: licence, attribution, `redistribution_ok`, and whether the source has an independent verification channel.
  - Status, from `build_status` run over the series' own source specs. Grouping is per source, so dataset identities are the same as with the full registry.
  - The newest 200 served rows, with the total count.
  - Raw fetches, verification items (match/MISMATCH, reason drawn, evidence) and quarantine, newest 200 each.
  - With `?period=`, the vintage table for that period: run state, origin, and a single `served` marker.
  - Legacy rows are labelled `legacy, unverified` and get a hatched amber `legacy` row class. They are never styled like verified rows. The vintages table uses the `origin` key added in Task 1.

## Tests (TDD: RED was confirmed before each implementation)

- RED, Task 3: collection failed with `ModuleNotFoundError: backoffice.app`.
- RED, Task 4: 11 of 11 failed, because the routes did not exist.
- `tests/backoffice/test_app_overview.py` (11 tests): the plan's 7 tests, plus:
  - `test_healthz`
  - `test_head_on_pages`
  - `test_queue_counts_revision_burst_beyond_default_page_sizes` (150 revision events)
  - `test_queue_shows_stuck_pending_with_remedy`
- The missing-DB test also asserts that the file is never created.
- `tests/backoffice/test_app_series.py` (11 tests): the plan's 8 tests, plus:
  - `test_list_shows_status_from_build_status`
  - `test_detail_shows_provenance_with_safe_links` (HTML in a quarantine raw value, a `javascript:` evidence URL, an https raw-fetch link)
  - `test_series_pages_refuse_missing_db_with_503`
- Value tokens are `0.10`, `-0.50` and `1200.000`. `1E-6` and `1.0E+3` are rejected by `Observation.from_raw`, as the Task 1-2 report noted.
- Results:
  - `tests/backoffice`: 33 passed.
  - `pytest tests --ignore=tests/ingest`: 112 passed, 1 warning (the existing starlette TestClient/httpx deprecation).
  - `ruff check ingest backoffice tests`: clean.
  - `pytest tests/ingest -m "not live"`: see the final line below.

## Local smoke run (no f0nix)

- Scratch DB: the real `registry/core.yaml` (1,344 active series) was synced into a fresh migrated DB, then test-style data was added for `eurostat.gdp_per_capita_eur.AT`:
  - verified and pending runs;
  - a revised period;
  - a quarantine row with an HTML raw value;
  - a failed verification item with a `javascript:` evidence URL;
  - a `verification_failure` event with a `<script>` detail;
  - 120 revision events.
- The app was served with `uvicorn backoffice.app:app_from_env --factory` on 127.0.0.1:18089.
- Every page returned 200 with no traceback (`/`, `/queue`, `/series`, a filtered page 2, the series page, its `?period=2023` page). `/series/nope` returned 404 and `?active=bad` returned 422. `HEAD /` returned 200.
- Each page rendered in under 0.15 s on this small DB.
- Overview totals (1344 / 0 / 1343 / 0 / 1) equal `python -m ingest --db <scratch> status` exactly.
- The queue showed `stuck_pending` and `verification_failed` (high), `revision_burst` (info) and 4 `blocked_source` (info).
- No `-wal`/`-shm` file appeared next to the scratch DB.

## Deviations and notes

1. **New module `backoffice/reads.py`**, not listed in the plan. It keeps data assembly out of the HTTP layer (separation of concerns) and makes the read functions directly usable with `read_db_readonly`.
2. **`/healthz` is liveness only.** It does not touch the DB, so a 503 from a schema mismatch does not make the container restart-loop. Task 6 may decide otherwise.
3. **Registry-inactive reasons (G4, from `registry/unmapped-*.md`) are not shown.** The plan's Task 4 does not list them. The list does show active/inactive, and the reasons stay in git.
4. **Performance on the production DB is unmeasured.** I have no f0nix access. `/`, `/queue` and `/series` each run the full `build_status`, the same work as `ingest status`. The series page runs it for one source only.
5. **Phone layout was checked only by construction:** the CSS scroll wrappers and the viewport meta tag. No browser screenshot was taken.
6. **The venv does not match the pins.** It has fastapi 0.162 and starlette 1.10, while `requirements.txt` pins fastapi `<0.136` and starlette `<1`. The code uses only APIs present in both ranges: `Jinja2Templates(env=...)` and `TemplateResponse(request, name, ...)`.
7. **The CLAUDE.md GitNexus impact and detect-changes steps were not run.** Those MCP tools are not available in this session. All changes are new files except one line in `requirements.txt`. No existing symbol was edited.
8. **Commit trailers** use the plan's exact `Claude Sonnet 5.5` line, as the controller instructed.

Final line of `pytest tests/ingest -m "not live"`: 1,562 passed, 7 deselected, 2 warnings in 516 s.
