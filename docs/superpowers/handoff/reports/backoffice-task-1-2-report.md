# Backoffice v1 - Tasks 1 and 2 implementer report

Plan: `docs/superpowers/plans/2026-11-14-backoffice-v1.md`. Branch `pipeline-rebuild`, not pushed.

| Task | Commit | Files |
|---|---|---|
| 1 Read layer | `67082eb` feat(db): read-only queries for the backoffice | `ingest/db.py`, `tests/ingest/test_db_backoffice_reads.py` |
| 2 Review queue | `0564763` feat(backoffice): derive review queue | `backoffice/__init__.py`, `backoffice/queue.py`, `tests/backoffice/{__init__,test_queue,test_boundaries}.py` |

## Task 1 - `Db` read methods (as implemented)

All are SELECT-only, return plain dicts, keep numbers as the stored `value_text` token, and work on a `read_db_readonly` handle (tested).

- `series_observations(series_id, limit, offset=0) -> (total, rows)`: rows come from the `served_observation` view, newest period first. Keys: `period, value_text, status_flag, run_id, fetched_at, raw_sha, origin`. `origin` is `fetched` or `legacy`. `raw_sha` is `None` for legacy rows. An unknown or never-fetched series returns `(0, [])`.
- `series_vintages(series_id, period) -> list[dict]`: every stored row of that (series, period), in insertion (id) order. Keys: `run_id, run_state, fetched_at, value_text, status_flag, origin, served`. `served` is true only when the row's id is the id `served_observation` returns. Rows from withdrawn, pending and failed runs are included with their state.
- `series_quarantine(series_id, limit=200)`: newest first. Keys: `run_id, period` (`raw_period`), `raw_value, reason, created_at`.
- `series_verification_items(series_id, limit=200)`: newest first. Keys: `item_id, verification_id, run_id, period, expected_text, observed_text, evidence_url, match` (bool), `reason, created_at` (the verification's `created_at`).
- `series_raw_fetches(series_id)`: the distinct `raw_fetch` rows behind any of the series' observations, newest retrieval first. Keys: `sha256, url, fetched_at, http_status, run_id`.
- `recent_events(since, kinds, limit)`: newest first (`ts DESC, id DESC`). Keys: `id, ts, kind, run_id, detail`. `detail` is the parsed JSON, or `{}` when it is NULL. `kinds=None` means every kind and `kinds=[]` means none. `since` is compared as text, the same convention `event_totals` uses.
- `runs_in_state(state, older_than=None)`: oldest id first. Keys: `run_id, source, dataset_key, state, started_at, finished_at, input_origin`. `older_than` is compared as parsed UTC, not as text. A run whose `started_at` cannot be parsed is kept. An `older_than` value that is not ISO raises `ValueError`.
- Module helper `_origin(kind)` maps `legacy-unverified` to `legacy` and everything else to `fetched`.

## Task 2 - `backoffice/queue.py` (as implemented)

- `QueueItem(kind, severity: Literal["high","medium","info"], ref, summary, detail: dict)` is a frozen dataclass.
- `derive_queue(report, lagging, events, stuck_pending, now=None) -> list[QueueItem]` is a pure function with no DB access. Items are sorted by severity, then kind, then ref (string order).
- Constants: `EVENT_WINDOW = 7 d`, `REVISION_BURST = 100`, `STUCK_PENDING_AFTER = 24 h`. The caller uses `STUCK_PENDING_AFTER` as the cut-off when it calls `runs_in_state("pending-verification", older_than=now - STUCK_PENDING_AFTER)`.
- Rules:
  - Event kind `verification_failure` becomes queue kind `verification_failed`. Event kind `verification_escalated` keeps its name. Both are high, one item per event, ref `run:<id>` (or `event:<id>` when the event has no run).
  - `stuck_pending` is high. Its summary includes the remedy `python -m ingest verify <id>`.
  - `stale_series` is medium, one item per source with stale > 0, ref = source name.
  - `lagging_series` is medium, one item per `Lagging`, ref = series id.
  - `blocked_source` is info, one item per source with blockers.
  - `revision_burst` is info, one item per run with at least 100 revision events.
- Event detail is passed through verbatim as data (tested with `<script>` and `javascript:` strings).

## Deviations from the plan, with reasons

1. **`series_vintages` returns an extra `origin` key.** Review Focus 2 requires legacy-unverified rows to be labelled. Without this key, Task 4 could not tell legacy from fetched in the vintage table.
2. **The 7-day window also applies to `revision_burst`.** The plan names the window only for verification events. Without it, an old burst would sit in the queue forever. An event whose `ts` cannot be parsed is kept, because its age is unknown.
3. **Event kind name.** The real event kind is `verification_failure` (migration 0012). The queue kind keeps the plan's name `verification_failed`.
4. **Extra tests beyond the plan's list:**
   - `test_series_quarantine_items_and_raw_fetches`
   - `test_series_quarantine_respects_limit_newest_first`
   - `test_reads_work_on_a_read_only_handle`
   - `test_stale_and_lagging_are_medium`
   - `test_revision_burst_is_info_per_run_at_threshold`
   - `test_unrelated_event_kinds_are_ignored`
   - `tests/backoffice/test_boundaries.py`, which enforces "no SQL or sqlite3 in `backoffice/`" (a plan Global Constraint).
5. **Commit trailer.** I used `Claude Opus 5.5` (the model that actually wrote the code), not the plan's `Claude Sonnet 5.5`. The handoff says never to fabricate coauthor trailers.
6. **Test value token.** The plan's Task 4 example token `1E-6` is rejected by `Observation.from_raw` (`not a number`). Task 1 tests use `0.10` and `-0.50` to check that tokens are kept exactly. Task 4's `test_detail_shows_exact_value_text_not_float` will need a token the model accepts, or legacy-import spelling.

## Notes for Task 3

Fetch events for the queue with `recent_events(since=now-7d, kinds=["verification_failure","verification_escalated","revision"], limit=...)`. Set `limit` high enough to count revision bursts: a single Eurostat run produced 150 revision events.

## Test results

- `tests/ingest/test_db_backoffice_reads.py`: 10 passed. Before the implementation, all 9 original tests failed with `AttributeError` (methods missing).
- `tests/ingest/test_db.py`: 16 passed.
- `tests/backoffice`: 11 passed. Before the implementation, collection failed with `ModuleNotFoundError: backoffice.queue`.
- `pytest tests --ignore=tests/ingest`: 90 passed, 1 warning.
- `pytest tests/ingest -m "not live"`: 1,562 passed, 7 deselected, 2 warnings in 515 s.
- `ruff check ingest backoffice tests`: all checks passed.
