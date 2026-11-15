# Task 7 report: `status` integration (derived layer v1)

Status: DONE. One commit on `pipeline-rebuild`: `feat(status): derived layer counts and staleness`.

## What changed
- `ingest/status.py`
  - `VERSION = 4` (comment: "v4 (derived layer v1): top-level `derived` (DerivedStatus)").
  - New `@dataclass(frozen=True) DerivedStatus(active_series, served_values, stale, never_computed, stale_series, last_run_id, last_run_state, last_run_at, failed_runs_7d)`.
  - `StatusReport.derived: DerivedStatus` is a required field right after `totals` and before the fields that have defaults. `build_status` keeps its signature.
  - `_derived_status(db, now)` builds it from `Db.derived_status_rows()`, `Db.derived_runs(1)` and the new `Db.derived_run_counts(since)`:
    - A series counts as `never_computed` when its base has served fetched data and no verified derived run covered it.
    - A series counts as `stale` when `base_latest_fetched_at` is later than `last_covered_at`. Both are parsed with `_parse_ts`, so they are compared as times, not as text.
    - A series whose base has no served data is neither: there is nothing to compute.
    - `last_run_*` is the newest derived run in any state. `last_run_at` is its `started_at`.
    - `failed_runs_7d` counts runs in state `failed` with `started_at >= now - 7d`. `DERIVED_FAILED_WINDOW` is set to 7 days.
  - `render_text` adds this line right after the "all sources" totals line: `derived: <n> active series; <served> served values; stale <k> / never computed <m>; last run <id> (<state>, <at>); failed runs 7d <f>`. When there is no run it prints `last run - (-, -)`. When there are stale series it adds `  DERIVED STALE <keys>`, capped by `STALE_LIST_CAP` with `(+N more)`.
- `ingest/db.py`: one new read, `Db.derived_run_counts(since) -> {state: count}`. It uses the same text-ordered `>=` convention as `event_totals`. All SQL stays in db.py.
- Tests:
  - New `tests/ingest/test_status_derived.py` with 12 tests:
    - the 7 named in the brief
    - stale judged as time, not text (a derive run stamped `+02:00`)
    - a failed run does not cover a series
    - the stale list is capped in the text
    - the text line when nothing is derived
    - status on a 0013 DB is refused, not crashed
  - Version assertion changed from 3 to 4 in `tests/ingest/test_status.py` and `tests/ingest/test_cli.py`. The test_cli change was also needed even though the brief only names test_status.
  - `tests/backoffice/test_queue.py`: its `_report()` helper builds `StatusReport` directly, so it now passes a zero `NO_DERIVED`. This is a test-only change; backoffice code is unchanged.

## Older DB (schema 0013, production until the deploy)
Decision: no in-code "derived not available (schema <14)" branch. That state cannot reach `build_status` through any real path:
- `open_db_readonly` (used by both the CLI `status` and the backoffice through `read_db_readonly`) refuses any DB whose applied migrations differ from the code's.
- Once this branch contains 0014, new status code on a 0013 DB stops at that gate with exit 2 and the message "schema is older than this code (missing migrations ['0014_derived_layer'])". It prints no traceback and runs no derived read.
- This behaviour dates from Task 2 (migration 0014). It is not new in Task 7.
- The test `test_status_on_a_pre_0014_database_is_refused_not_crashed` pins it.

Showing "not available" instead would mean relaxing the read-only schema gate, which is a policy change outside this task. I did not make it.

The current production flow is unaffected: old code reads a 0013 DB as before. The scheduler (writer) applies 0014 on its next start, and only after that do the new status and backoffice read.

## Backoffice and status VERSION (for Task 8 and the deploy order)
No backoffice code pins status `VERSION 3`. Backoffice imports `ingest.status.build_status` in process (`backoffice/reads.py:status_report`) and only shows `report.version` (`backoffice/templates/overview.html:5`). Its HTTP 503 does not come from the status version. It comes from the migration-set check in `ingest.db.open_db_readonly`, which reaches it through `read_db_readonly` (`backoffice/app.py` `refused` handler).

What this means:
- Old backoffice + DB migrated to 0014 gives 503 ("newer than this code").
- New backoffice + DB still at 0013 gives 503 ("older than this code").
- So the plan's deploy order holds: worker first so it migrates, then the backoffice, in the same deploy.
- The status v3 -> v4 bump on its own breaks no backoffice consumer. The only consumer of the JSON form is `python -m ingest status --json`. Nothing in this repo parses the version.

## Verification
- Red first: the new test file failed at import (`DerivedStatus` did not exist).
- Targeted tests (test_status_derived, test_status, test_status_readonly, test_task24_verification_status, test_cli, tests/backoffice): 132 passed.
- `.venv-ci/bin/ruff check ingest backoffice tests`: all checks passed.
- Full suite (`tests/ingest tests/backoffice tests/test_docker_contract.py`): 1846 passed, 7 deselected, 0 failed (10m52s).
- No `float` in the new code.

## Concerns
- `failed_runs_7d` compares `started_at` as text in SQL, like `event_totals`. That is only correct for stamps in `+00:00` form. Derived run stamps come from `now().isoformat()`, and `derived_run.started_at` has no CHECK forcing UTC, unlike fetched `observation.fetched_at`. Scheduler and CLI both pass UTC clocks today. The stale check is fully time-correct (parsed in Python).
- CLAUDE.md asks for GitNexus impact analysis and `detect_changes`. GitNexus tools were not available in this session, so I used grep for impact instead: `StatusReport(` is built only in `ingest/status.py` and `tests/backoffice/test_queue.py`.
