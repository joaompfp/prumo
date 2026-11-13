# Task 18 independent specification review

Verdict: PASS

No blocking specification deviation was established in the reviewed code, image inputs, deployment candidate or current operations runbook. This passes the requested repository specification gate only. It does not close Task 18 production acceptance, the separate quality review, Task 19 or the final Project 1 audit.

## Scope and review boundary

- Worktree: `/home/joao/projects/prumo-pipeline`, branch `pipeline-rebuild`.
- Reviewed committed range: `bf27e36..19c6487`. Actual HEAD was `19c6487fdaf716fdd328249a0616a5040a0928df`.
- Also reviewed the existing uncommitted `docs/data/operations.md:22-23` adjustment: remove obsolete `CAE_DB_PATH`; explicitly configure `PRUMO_DB_PATH=/data/prumo.sqlite3` and `PRUMO_RAW_DIR=/data/raw`.
- Read the review brief, both implementation reports, slice briefs, relevant handoff/plan/ruling context, actual diff, runtime dependencies and focused tests. Implementation-report results were not substituted for reviewer execution.
- No implementation or repository-test edits, nested agents, full-suite duplication, network/publisher calls, image builds, deployment, infra edits, secret inspection, merge, push or commit. Only this report was added to the repository. Independent probe code and all test databases/raw stores were confined to `/home/joao/.hermes/cache/scratch`.
- Existing generated `AGENTS.md`/`CLAUDE.md` dirt, the operations prose adjustment and untracked controller briefs were left unchanged. The committed range itself does not alter the protected files.

## Findings and severity

Blocking findings: none.

Informational, accepted limits rather than change requests:

- The loop waits 900 seconds after each serial pass; it is not a wall-clock deadline or a promise of a pass starting every 15 minutes during slow work. A source can delay later groups. This is explicit in `ingest/scheduler.py:8-11,171-185` and `task-18-scheduler-implementation.md:101-105`; adding a watchdog, parallelism or whole-group deadline is outside this gate.
- The advisory lock coordinates scheduler CLI instances, not independent manual writers, hard-link aliases or distributed hosts. `ingest/scheduler.py:188-201,220-233`, `docs/data/operations.md:93-97,225-226,247-253` and the scheduler implementation report describe the ownership boundary. Manual import/catch-up must keep the worker stopped. The concurrent-status probe below used an already-migrated DB, not simultaneous schema migration or competing ingestion writers.
- Abrupt termination can leave a durable in-flight record without a terminal JSON line. State is committed before source work; a later retry is conservative. A completed attempt emits a JSON line, while persistence/log-output failures remain fatal. This is consistent with `ingest/scheduler.py:150-167` and the disclosed interruption limit at `task-18-scheduler-implementation.md:103`.
- Dockerfile/context/Compose tests validate repository inputs. They do not establish a built image, actual memory use, production routing, provisioned credentials or a healthy 24-hour operation.

## Acceptance evidence

### Scheduler cadence, retries and failure isolation

`ingest/cadence.py:20-45` is the shared interval authority: explicit positive h/d/w strings override frequency defaults, and a group uses its minimum member interval. `ingest/scheduler.py:52-89` handles UTC/naive timestamps, never-run groups, inclusive due boundaries and 1h/4h/12h-capped failure retry. `ingest/status.py:30-43,256-259` imports the same cadence instead of maintaining another copy. These intervals are refresh policy, not inferred publisher release dates.

`ingest/db.py:299-334` records the attempt start, increments the pessimistic failure streak and keeps prior success. Only `verified` resets the streak and advances success. Completed failures anchor retry at completion; interrupted attempts anchor at their persisted start. `0010_scheduler_state.sql:4-13` is an additive STRICT table, not a rewrite of dataset history.

Executed tests cover timezone/microsecond boundaries, never-run due, persisted retry/reset, reopened databases, repeated interruption and actual abrupt subprocess exit. Relevant cases are `tests/ingest/test_scheduler.py:91-195,219-241` and `tests/ingest/test_scheduler_contract.py:47-157`. The independent probe also checked all frequency defaults and an explicit two-week interval.

Source exceptions are isolated at `ingest/scheduler.py:152-167`; attempts log their authoritative source/group, state, run id, counts and detail through `:112-121`. Executed exception/JSON tests at `tests/ingest/test_scheduler.py:266-286,309-343` and `test_scheduler_contract.py:339-348` passed. The independent stdout-failure probe raised a simulated OSError, reopened the DB and observed `last_attempt_state='error'`, `failure_streak=1`, `last_success_at=None`; the +59-minute retry correctly made no attempt.

### Authoritative groups, registered verification and HTTP policy

`ingest/scheduler.py:63-78,92-109` filters active series, retains explicitly blocked DGEG and derives group identity from unchanged `operations.group_specs`. Exactly one full due group reaches unchanged `operations.run_source`; its actual registered `run_with_refetch` call remains at `ingest/operations.py:292-300`.

The World Bank grouping and per-indicator locale rules remain at `ingest/operations.py:57-60,85-101,114-136,189-193`. No private verifier-registry mutation was introduced. Executed recorded-fixture integration (`tests/ingest/test_scheduler_contract.py:281-336`) used the real operations/refetch/verification path: healthy and failed indicators were independent; only the failed sibling retried; verifier identity/configuration was retained; later failures did not alter held, served or dated legacy observations. This is offline recorded-response evidence, not fresh publisher acceptance.

The independent orchestration spy additionally observed group dispatch `[('wb.A.PT',), ('wb.B.PT',), ('wb.B.PT',)]` across the initial pass and +1h retry. It checked the registered verifier object, locale map, default English channel and `input_origin='live'`. Its refetch result was deliberately stubbed; the recorded integration above supplies execution of the real verifier path.

The client-policy refactor at `ingest/operations.py:44-55` and `ingest/cli.py:198-203` preserves the previous source timeout/throttle/retry policy. The independent real-registry probe constructed clients without making requests: every active source retained a 1-second minimum interval; INE retained 300 seconds, other sources 30 seconds, and both CLI/shared factories retained zero client retries. Lazy shared clients across groups/passes are exercised at `tests/ingest/test_scheduler_contract.py:411-439`.

### Persistence, legacy/licence preservation and shared API interaction

`git diff --numstat bf27e36..19c6487 -- ingest/migrations` returned only `13 0 ingest/migrations/0010_scheduler_state.sql`. Earlier migrations, adapters, verifiers, pipeline, legacy importer, registry/licence files, manual-refresh document, maintenance app and static files have no changes in the reviewed range. An AST scan found no execute/executemany/executescript/cursor call sites outside `ingest/db.py` in runtime Python.

Executed fresh/populated-upgrade and failed-migration tests (`tests/ingest/test_scheduler.py:439-535`; `test_scheduler_contract.py:358-408`) cover preserved rows/view, STRICT typing, rollback of schema plus migration record, foreign-key enforcement and integrity checks. Scheduler freshness uses its own table, not synthetic legacy dataset runs (`ingest/scheduler.py:81-89,148-151`; executed legacy test at `test_scheduler.py:199-216`). Scoped legacy/licence regressions also passed.

The independent shared-DB probe held a read-only WAL snapshot while `tick` wrote/finished an attempt. A separate connection saw the committed pre-run `('running', 1)` marker; the actual `python -m ingest ... status --json` CLI ran successfully during the attempt with socket operations forbidden. The original snapshot stayed consistent, then saw `('failed-fetch', 1)` after releasing its transaction. SQLite quick_check returned `ok`; foreign_key_check returned no rows. `app/main.py:1-20` remains maintenance/static-only and introduces no competing ingestion writer.

### CLI and deterministic startup contracts

`ingest/scheduler.py:204-237` exposes --once/help, packaged registry defaults and PRUMO_DB_PATH/PRUMO_RAW_DIR defaults; it validates schedules/grouping before opening the database/lock/client and canonicalizes the DB path before flock. Actual module help returned 0. Executed import/help socket-audit tests, lock collision/canonical-symlink tests and real-registry default tests passed (`test_scheduler_contract.py:160-265`).

An independent actual-module --once subprocess with an all-inactive DGEG registry returned 0, emitted exactly one blocked JSON record, selected the PRUMO_DB_PATH scratch database despite a conflicting PRUMO_DB, and created no dataset runs, scheduler attempts or raw store. Its socket audit forbade network. This verifies deliberate inactivity/blocking rather than inventing a successful fetch.

### Image, entrypoint and deployment candidate

`Dockerfile:3-17` copies app/static/ingest/registry, includes migrations through the ingest directory, removes historical collector/script/seed copies, supplies SQLite/raw defaults and preserves the uvicorn command, port and HTTP healthcheck. `.dockerignore:1-53` denies context by default, reincludes the runtime inputs and applies nested credential/env/cache/database exclusions afterward. `entrypoint.sh:1-6` contains only the shell/error setup, mkdir and exec.

All Docker input and executable-entrypoint tests passed (`tests/test_docker_contract.py:37-159`), including argument/PID/exit preservation and failure before command execution when mkdir fails. `/bin/sh -n entrypoint.sh` exited 0. No built-image or actual-context archive inspection was performed.

`deploy/prumo-ingest.yml:4-31` matches the candidate contract: distinct image, scheduler command, restart unless-stopped, 512m limit, no-new-privileges, disabled inherited web healthcheck, shared persistent data and resolv.conf mounts, t2_proxy, bounded json-file logs, only the FRED source-secret reference, and no published ports/AI coupling. Executed Compose input tests at `tests/test_docker_contract.py:162-206` passed. The parent-owned infra include/web-path/AI-coupling changes at `docs/data/operations.md:16-30` remain instructions, not external effects established here.

### Operator runbook

The current prose adjustment at `docs/data/operations.md:22-23` agrees with the reviewed image/worker paths and removes the obsolete CAE override. The CLI's older PRUMO_DB name is explicitly disclosed at `:34-38`; operator commands consistently place global --db/--raw-dir before their subcommand. Actual run/import-legacy help and parser probes agree with those commands.

Bootstrap stops any existing worker, imports the original CSV before scheduler startup and preserves source-scoped legacy labels/dates (`:83-113,137-152`). The E-REDES bounds at `:115-127` implement the reviewed exclusive upper boundary through the existing inclusive CLI. Independent execution of the documented GNU date arithmetic and actual `_eredes_bounds` parser yielded:

```text
CLI --to: 2026-11-12
actual internal window: ('2026-04-01T00:00:00+00:00', '2026-11-13T00:00:00+00:00')
```

The original `manual-refresh.md` is unchanged and authoritative; `operations.md:213-266` supplies only the deployed-container handoff and preserves recorded/original receipt dates. Rollback is stop-only with retained evidence and maintenance app (`:268-293`). The actual elapsed-time gate and explicit failed/withheld/source-group review are at `:295-349`, including DGEG, REN/FRED/OECD, World Bank failures and dated continuity. No automatic backup/alert, licence grant, unit conversion or invented fresh verification is introduced. All runbook Bash blocks passed syntax checks in the executed Docker-contract tests.

## Actual reviewer commands and results

All commands below ran from `/home/joao/projects/prumo-pipeline`, using Python 3.12.3 and the existing `.venv-ci` environment (pytest 9.2.0). This was not a clean requirements-only environment or full-suite run.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -m pytest -p no:cacheprovider \
  tests/ingest/test_scheduler.py tests/ingest/test_scheduler_contract.py \
  tests/test_docker_contract.py -q \
  --basetemp=/home/joao/.hermes/cache/scratch/task18-spec-focused
# 53 passed in 17.02s; exit 0

PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -m pytest -p no:cacheprovider \
  tests/ingest/test_cli.py tests/ingest/test_status.py \
  tests/ingest/test_scoped_legacy.py tests/ingest/test_licence_gate.py \
  tests/test_maintenance.py -q \
  --basetemp=/home/joao/.hermes/cache/scratch/task18-spec-regressions
# 40 passed, 1 warning in 23.95s; exit 0

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/joao/projects/prumo-pipeline \
  .venv-ci/bin/python -m pytest -p no:cacheprovider \
  /home/joao/.hermes/cache/scratch/task18_spec_independent_probe.py -q -s \
  --basetemp=/home/joao/.hermes/cache/scratch/task18-spec-independent-final
# 7 passed in 8.02s; exit 0

PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -m ingest.scheduler --help
PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -m ingest run --help
PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -m ingest import-legacy --help
/bin/sh -n entrypoint.sh
git diff --check bf27e36..19c6487
git diff --check -- docs/data/operations.md
# Each exited 0.
```

The first independent-probe execution was `2 failed, 5 passed in 9.37s`: my scratch fixture supplied invalid dotless World Bank native codes. The authoritative parser correctly rejected them. Only that scratch fixture and its expected labels were corrected to valid X.* codes; the final execution above passed. Those were reviewer-harness failures, not implementation defects or repository-test changes.

GitNexus queries `gitnexus query 'ingest scheduler run_source migration' -r prumo-pipeline` and the broader `gitnexus query 'scheduler' -r prumo-pipeline` returned no flows and emitted read-only FTS-initialization warnings. No index rebuild was attempted. Diff/source inspection and executable probes supplied the evidence; an empty graph result was not treated as proof of correctness.

## Gates still open

The controller still owns whole-suite/clean-environment acceptance, the separate quality gate, real image build/context verification, actual infra installation and secure FRED provisioning, production import/catch-up, public maintenance checks, measured resource/runtime behavior and the real 24-hour observation with per-group exceptions. This review accessed no production system and establishes none of those external effects. Full Project 1/Task 19 documentation and final audit closure remain outside scope.

Final verdict: PASS.
