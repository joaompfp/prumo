# Task 6 report: scheduler hook (derive after each verified base group)

Status: DONE
Commit: 246ba3c `feat(scheduler): derive after verified base runs`
Files: `ingest/scheduler.py`, `tests/ingest/test_scheduler_derive.py` (new)

## What changed (`ingest/scheduler.py`)

- `Deriver = Callable[[Db, set[str]], DeriveReport | None]`; default
  `_derive_after(db, series_ids)` = `run_derive(db, base_series=series_ids, trigger="scheduler", now=_utc_now)`.
- `tick(..., deriver=_derive_after)`: after the group's `scheduler_attempt_finished` + `attempt`
  record, only when `outcome.state == "verified"`, calls `deriver(db, {s.id for s in group.specs})`.
  - report -> `{"schema": "prumo-scheduler", "version": 1, "ts", "event": "derive", "group", "run_id", "state", "n_written", "n_mismatch"}`
  - `None` -> no record
  - `Exception` -> `{schema, version, ts, event: "derive", group, state: "error", detail: "<Type>: <msg>"}`; the pass continues.
  - Only `Exception` is caught: `SystemExit` (SIGTERM handler) / `KeyboardInterrupt` still propagate, like the runner path.
  - The derive happens AFTER the attempt is persisted, so `scheduler_state` / streak / retry are untouched by construction.
- `serve(..., deriver=)` and `main(..., deriver=)` pass it through; `--once` exit code unchanged (counts only `event == "attempt"`), so a derive error or a `failed` (mismatch) derive run is not exit-relevant.
- `main` calls `load_derived(args.registry, specs)` right after `_plan(specs)`, before the DB dir, lock or SIGTERM handler (fail fast); `_locked_main` calls `sync_derived(db, derived)` right after `sync_registry`.
- Scope: `run_derive(base_series=...)` already selects only active derived series whose base is in the just-verified group, so a poison base value fails only that group's derived run, not all keys.

## Tests (`tests/ingest/test_scheduler_derive.py`, 8)

`test_verified_attempt_triggers_deriver_with_group_series_ids` (two groups -> two scoped calls, exact record),
`test_failed_attempt_never_derives` (failed-operational and runner exception),
`test_none_report_emits_no_record`,
`test_derive_exception_is_logged_not_fatal` (next group attempted; both states verified, streak 0, last_success set),
`test_once_exit_code_ignores_derive_failure` (exception and a `failed` report with mismatches -> exit 0),
`test_main_refuses_invalid_derived_registry_before_lock` (no DB, no lock file, no raw dir, runner never called),
`test_main_syncs_derived_series`,
plus extra `test_default_deriver_runs_real_derive_scoped_to_group` (real run_derive wiring, no injected deriver).
Existing `test_tick_emits_only_attempts_and_inactive_never_scheduled` passes unchanged (real deriver returns None with no derived series).

Red first: all 7 brief tests failed (`unexpected keyword argument 'deriver'`) before implementation.

## Verification

- `pytest tests/ingest/test_scheduler_derive.py tests/ingest/test_scheduler.py tests/ingest/test_scheduler_contract.py -q` -> 50 passed
- `ruff check ingest backoffice tests` -> clean
- Full suite `tests/ingest tests/backoffice tests/test_docker_contract.py -q` -> 1834 passed, 7 deselected, 3 warnings (10:42)

## Concerns / notes

- No restart/rebuild needed or done. Production `registry/core.yaml` has no `derived:` section, so a future deployed worker syncs an empty derived list and every derive call returns None (no records) until entries are added.
- A derive call shares the scheduler's DB connection and runs synchronously in the pass, so a large derive adds latency to the serial pass (acceptable at v1 sizes).
- The derive `ts` is taken after the deriver returns (completion time), consistent with the attempt record's `finished` timestamp.
- CLAUDE.md asks for GitNexus impact/detect_changes; those MCP tools are not available in this session, so blast radius was checked manually: `tick`/`serve`/`main` only gain a keyword argument with a default; `_locked_main` is private (sole caller `main`).
- `AGENTS.md` / `CLAUDE.md` remain modified in the worktree (pre-existing dirt), not staged.
