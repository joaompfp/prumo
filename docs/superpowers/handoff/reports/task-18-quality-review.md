# Task 18 independent quality review

No actionable quality defects were established in the requested scope. The specification gate's PASS was treated as prior context, not as a substitute for inspecting the changes and executing independent probes.

## Scope and execution boundary

- Reviewed `bf27e36..19c6487`, including the cadence/client-policy refactors, scheduler, additive persistence, image, deployment candidate, tests and runbook. Also reviewed the initially uncommitted `docs/data/operations.md:22-23` adjustment removing `CAE_DB_PATH` and specifying the SQLite/raw paths.
- Read `task-18-review-brief.md`, `task-18-spec-review.md`, both implementation reports, relevant runtime dependencies and focused tests.
- Initial HEAD was `19c6487fdaf716fdd328249a0616a5040a0928df`. At the closing scope check, HEAD had advanced concurrently to `f562ba5abebe358d60e8a5ac64f4728924ec7bbe`, and the operations adjustment and previously untracked reports were no longer local changes. This verdict covers the requested range and inspected prose adjustment; it does not certify all later commits at the closing HEAD.
- No implementation edits, nested agents, publisher/network calls, secret access, configuration changes, image builds, merge, push or deployment were performed. This report is the only file written by this reviewer. Existing protected `AGENTS.md`/`CLAUDE.md` dirt was not edited.
- No pytest suite was rerun. The controller-reported result of 1435 passed, 7 live deselected and 3 warnings remains controller evidence.
- Independent Python probes ran inline through `PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -c '…'` from `/home/joao/projects/prumo-pipeline`, using Python 3.12.3 / SQLite 3.45.1. Probe payloads were supplied directly to the terminal tool, not saved as files. Databases used `:memory:`; raw-store doubles retained bytes in dictionaries. Audit hooks rejected socket activity and filesystem mutations. The lock probe used an anonymous memfd without writing bytes; the packaging probe permitted only anonymous-pipe I/O and `/bin/bash -n` subprocesses.

## Findings

### Critical

None established.

### Important

None established.

### Minor

None established. The disclosed operational limits below are not speculative change requests.

## Reliability and restart/backoff

`ingest/scheduler.py:52-89` separates healthy cadence from failure eligibility and normalizes timestamps to UTC. `ingest/cadence.py:20-45` supplies the shared interval policy. `ingest/db.py:309-334` commits the pessimistic start marker before work, retains prior success across failures, clears the old finish timestamp at each start and resets the streak only for `verified`. The scheduler finishes persistence before emitting its terminal record (`ingest/scheduler.py:145-167`).

P1 exercised every length-four sequence over `verified`, `failed-fetch`, interruption and a 37-minute slow failure. An independently computed model checked the streak, retained success, attempt/finish timestamps, JSON-record count and eligibility immediately before and exactly at each deadline. Each transition was serialized, closed and deserialized into a new SQLite connection before the next decision. This covered repeated interruptions, failure after prior success, completion-anchored slow failures, reset to a seven-day healthy interval and the capped retry sequence.

Actual output:

```text
P1-state-model: PASS
sequences=256 transitions=1024 serialized_reopens=1024 boundary_checks=2048 disk_writes=0
```

This is state-reopen/model evidence, not a newly executed disk/WAL reboot or power-loss test. The real abrupt-process/reopened-file tests were inspected at `tests/ingest/test_scheduler_contract.py:133-157` and the prior specification review's execution evidence was read; those tests were not duplicated.

P6 exercised the actual `_instance_lock` context manager and Linux `flock` (`ingest/scheduler.py:188-201`) against independently opened descriptions of an anonymous memfd. Only path opening was redirected in memory. The probe checked the requested lock pathname, `O_CREAT|O_RDWR`, mode `0600`, overlapping-owner rejection, release after normal exit and reacquisition after `KeyboardInterrupt`.

```text
P6-POSIX-lock: PASS
lock_open_calls=4 real_flock_collisions=1 reacquired_after_interrupt=true disk_writes=0
```

The canonical path and lifetime wiring are present at `ingest/scheduler.py:220-237`. This probe does not establish production filesystem locking semantics, hard-link alias protection or coordination with separate manual CLI writers.

## Registered integration, isolation and data preservation

The scheduler sends exactly one authoritative group to unchanged `operations.run_source` (`ingest/scheduler.py:92-96,152-161`). World Bank grouping and locale/verifier authority remain at `ingest/operations.py:85-101,114-136,189-193`; real execution reaches registered `run_with_refetch` at `:292-300`. Source clients remain lazy and shared across passes (`ingest/scheduler.py:99-109,178-181`), with the extracted timeout/throttle/zero-client-retry policy at `ingest/operations.py:44-55` and `ingest/cli.py:198-203`.

P2 used the real scheduler, operations, pipeline and registered World Bank verifier with the committed JSON/CSV fixture doubles. Unlike a fetch-only failure test, the population collector succeeded while its independent verifier returned HTTP 500. The real verification/refetch path exhausted its budget without making the failed data served. The GDP sibling verified. After repairing only the verifier route at +1h, only population retried, retaining the same registered verifier. Later injected source exceptions left all held/served observations and the original dated legacy row unchanged. Default stdout was parsed back as JSON and compared with the returned attempt records.

```text
P2-real-WB-verification-retry: PASS
initial_live_run_counts={failed-verification: 3, verified: 1}
initial_log_lines=2
retry_groups=[SP.POP.TOTL]
later_outage_states=[failed-fetch, failed-fetch]
held_observations=991 served_observations=397
legacy_unchanged=true registered_verifier_reused=true disk_writes=0
```

The terminal log is per scheduler group attempt, not per internal verification refetch. Interrupted work cannot promise a terminal log line. Ordinary source failures remain isolated; persistence/log-output failures remain fatal rather than becoming fabricated successes. Existing fatal-persistence and malformed-outcome tests were inspected at `tests/ingest/test_scheduler_contract.py:268-278,442-464`.

These are explicitly offline fixture/failure-injection results. They establish neither new publisher retrieval nor current source availability.

## SQL migration and shared-database integration

The range adds only `ingest/migrations/0010_scheduler_state.sql` to the migrations directory: `git diff --numstat bf27e36..19c6487 -- ingest/migrations` returned `13 0` for that file. Its STRICT table is separate from dataset runs, observations, serving views and licence settings (`0010_scheduler_state.sql:4-13`). Runtime SQL remains within `ingest/db.py`; P5's AST call-site scan found no `execute`, `executemany`, `executescript` or `cursor` calls elsewhere under `ingest/`.

P4 used the real migrator with an in-memory selection of the original migrations through 0009, populated the registry, dated legacy observations and an audit event, then snapshotted every existing application table and the serving-view definition/results. An in-memory 0010 payload with an appended FK violation was rejected: both the new table and its migration record rolled back. The original migration then applied idempotently across repeated migrator calls. Existing table contents, legacy dates/precision and serving-view results remained identical. Negative and noninteger failure streaks were refused; foreign keys remained enabled.

```text
P4-populated-migration: PASS
preserved_tables=10 served_legacy_rows=1
failed_upgrade_rolled_back=true repeat_upgrade_idempotent=true strict=true
foreign_keys=true integrity=ok disk_writes=0
```

Migration transaction/FK handling remains at `ingest/db.py:340-391`. The web app remains maintenance/static-only (`app/main.py:1-20`) and introduces no competing ingestion writer. The existing status CLI opens the database without syncing registry or ingesting (`ingest/cli.py:342-349`). The prior specification review's already-migrated concurrent-read probe was read, but simultaneous migration/writer behavior was not newly exercised here. Bootstrap and manual-update instructions correctly keep the worker stopped during independent writes (`docs/data/operations.md:83-107,225-253`).

## Security

P3 exercised the actual registered FRED path with a synthetic, explicitly supplied marker instead of reading any credential. Recorded API/table fixtures verified a real registry series internally, while `redistribution_ok=false` kept its observations out of the serving view. Additional cases injected a request exception containing a credential-shaped URL and a response body echoing the marker. Neither failure archived a raw object; the marker was absent from the database dump, scheduler records and saved evidence. Successful final URLs were also given the synthetic query parameter to exercise removal before archival. The independent table channel received no key parameters.

```text
P3-FRED-security-and-withholding: PASS
good:  state=verified     observations=417 raw_objects=3 served=0 marker_leaked=false
throw: state=failed-fetch observations=0   raw_objects=0 served=0 marker_leaked=false
echo:  state=failed-fetch observations=0   raw_objects=0 served=0 marker_leaked=false
actual_credentials_read=false disk_writes=0
```

The relevant existing protection is `ingest/sources/fred.py:360-399`; the new log boundary is `ingest/scheduler.py:115-121,162-167`. The image copies no historical collector/script/seed directories and introduces no secret build argument (`Dockerfile:3-12`). Context inputs are denied by default with final nested credential/cache/database exclusions (`.dockerignore:1-53`). The candidate has no published ports/Traefik labels or AI coupling, references only the FRED source secret, applies no-new-privileges and bounds container logs (`deploy/prumo-ingest.yml:4-31`). These are reviewed input contracts, not proof of a built archive or provisioned production credentials.

## Config, image and runbook

P5 directly executed the relevant existing Docker/Compose input-contract functions without starting pytest or creating their temporary entrypoint fixture. It syntax-checked every runbook Bash block, compiled the embedded Python blocks, loaded/planned the real registry and exercised module help under the no-network/no-database audit guard with deliberately absent registry/database paths.

```text
P5-image-compose-runbook-help: PASS
input_contract_checks=9 bash_blocks_syntax_checked=11 embedded_python_blocks_compiled=2
planned_groups=25 blocked_sources=[dgeg] runtime_sql_outside_db=[]
module_help_exit=0 disk_writes=0 image_built=false
```

The first P5 attempt stopped in the reviewer's audit hook because opening an anonymous subprocess stdin pipe was classified as a filesystem write. The hook was narrowed to permit anonymous pipes while retaining file-write rejection; the final execution above passed. No implementation change was made. The optional execute-code wrapper was also refused before execution; all probes were subsequently executed through the normal terminal tool.

Additional executed commands, all exit 0:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/ruff check --no-cache \
  ingest/cadence.py ingest/cli.py ingest/db.py ingest/operations.py \
  ingest/scheduler.py ingest/status.py tests/ingest/test_scheduler.py \
  tests/ingest/test_scheduler_contract.py tests/test_docker_contract.py
# All checks passed!
/bin/sh -n entrypoint.sh
git diff --check bf27e36..19c6487
git diff --check -- docs/data/operations.md
```

The prose adjustment at `docs/data/operations.md:22-23` agrees with the worker/image contract; commands compensate explicitly for the older operations CLI's `PRUMO_DB` variable (`:34-38`). The entrypoint is only mkdir plus exec (`entrypoint.sh:1-6`), and the web command/port/HTTP healthcheck remain (`Dockerfile:13-17`). The worker deliberately disables that inherited HTTP healthcheck (`deploy/prumo-ingest.yml:14-15`).

Runbook review found the required original-CSV-before-worker order, source-scoped dated continuity and inclusive CLI `--to` yesterday for the exclusive current UTC day-start E-REDES window (`docs/data/operations.md:93-127`). Manual refresh remains authoritative; container handoff retains original capture bounds and receipt dates (`:213-266`). Rollback stops the worker while preserving schema/evidence and maintenance service (`:268-293`). The 24-hour procedure requires real elapsed time and per-group exceptions (`:295-349`). No automatic backup, alert, legal authorization or fresh-success claim is added.

## Accepted limits and remaining production evidence

- Scheduling is serial with a 900-second pause after each completed pass (`ingest/scheduler.py:8-11,171-185`). Slow/hung work can delay later groups and subsequent passes. This is not a wall-clock 15-minute guarantee or a new watchdog requirement.
- The scheduler lock coordinates scheduler CLI instances; it does not protect independent CLI writers or distributed hosts. Interrupted work retains a pessimistic marker and can retry conservatively. No exactly-once publisher work or complete crash-time terminal log is claimed.
- There is no worker HTTP health endpoint or invented idle-success heartbeat. Process uptime and a disabled inherited web healthcheck cannot establish source freshness (`docs/data/operations.md:40-42,156-173`).
- Legacy rows retain their dates and `legacy-unverified` status. Failed source/World Bank groups remain explicit; DGEG stays blocked, and REN/FRED/OECD licence withholding remains independent of technical verification (`docs/data/operations.md:338-349`). No all-core-fresh or all-core-available claim is justified.
- Actual image/context verification, production infra integration, secure credential provisioning, resource/runtime behavior, original-data bootstrap/catch-up, public maintenance checks and the future 24-hour observation still require controller evidence. No networking or production work was done in this review. These are disclosed deployment gates, not defects invented to block the reviewed code. Task 19 and final Project 1 closure are not established.

APPROVED
