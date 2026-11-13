# Task 18A scheduler implementation

## Scope and authorship

Implemented slice A only on `pipeline-rebuild`. Scheduler code/tests commit: `95b418016f64f6cc6b01ee8de6cad91c517663ce`.

The first implementer (Kimi/Ollama) authored the prerequisite refactors `2562656` (shared `ingest.cadence`) and `aa89fed` (shared `operations.polite_http`) and the inherited, initially untracked `tests/ingest/test_scheduler.py`. Those refactors are unchanged. The replacement implementer supplied the scheduler, additive persistence, supplemental contract tests and this report, retaining and correcting the inherited tests rather than claiming their original authorship. No coauthor trailers were invented.

A concurrent slice B commit, `bb6fdeb`, appeared while this work was running. Its packaging/deployment files were preserved and excluded from the slice A commit. No nested agents, live publisher calls, merge, push, deployment, configuration changes, messages or emails were performed by this implementer. Shared HANDOFF/progress-ledger and protected AGENTS.md/CLAUDE.md were not edited or staged.

## Delivered behavior

- `python -m ingest.scheduler` performs serial passes with a 900-second pause after each pass; `--once` executes one pass. `--help` and import require no network, database, raw store or source credentials.
- Defaults: `PRUMO_DB_PATH=/data/prumo.sqlite3`, `PRUMO_RAW_DIR=/data/raw`, and packaged `registry/core.yaml`. Explicit `--db`, `--raw-dir`, `--registry` override them. The older operations CLI's `PRUMO_DB` variable is not the scheduler variable.
- Registry loading, schedule parsing and authoritative grouping finish before opening the database, lock or any HTTP client. Active series only are grouped through `operations.group_specs`; unverifiable sources, including fully inactive DGEG, remain explicitly blocked in each pass's JSON output.
- `due(group, last_success, now)` uses shared cadence intervals, including explicit registry schedules and the minimum member interval. Boundaries are inclusive. Naive timestamps are interpreted as UTC; aware timestamps compare by instant.
- Exactly one full authoritative due group is passed to unchanged `operations.run_source`, retaining its registered `run_with_refetch` path. Healthy World Bank groups retain independent schedules when siblings fail. The single registered World Bank verifier and explicit per-indicator locale map are preserved without private-registry mutation.
- Lazy polite clients are shared per source across groups and continuous passes. Registry throttle/timeout policy and zero client retries come from the existing shared factory; existing bounded verification refetch behavior is unchanged.
- Additive migration `0010_scheduler_state.sql` follows existing `0009`; no earlier migration was overwritten. `Db` exposes typed scheduler state plus start/finish methods. All runtime SQL remains in `ingest/db.py` and the migration.
- Each start autocommits a pessimistic in-flight marker and increments the failure streak before running the source. Only a verified result resets the streak and advances last success. Failed attempts retry after 1h, 4h, then a 12h cap. Completed failures wait from completion; interrupted attempts wait from their start. Start and finish timestamps remain separate.
- Scheduler freshness comes only from its own attempts. Existing dataset runs, particularly synthetic legacy verified runs, never initialize scheduler success. Failed attempts retain prior success and never remove or relabel last-good or owner-permitted dated data.
- One advisory file lock beside the canonical database path covers the CLI's lifetime, including registry sync and all runner work. Relative/symlink aliases share the lock. The lock file is deliberately not unlinked, avoiding inode replacement races.
- Flushed JSON lines use `schema=prumo-scheduler`, `version=1`, UTC timestamp, event/source/group/state/run id/counts/detail. One completed attempt yields one line; blocked-source visibility is a separate event. Source exceptions become isolated failed attempts. Persistence/log-output failures remain fatal rather than being disguised as healthy operation.
- `--once` returns 1 for an attempted group that does not verify, 0 for successful/idle or deliberately unverifiable-only passes. Lock collision refuses startup. KeyboardInterrupt returns 130 with cleanup; abrupt termination leaves its already committed marker.

## RED and GREEN evidence

All pytest database/probe paths were under `/home/joao/.hermes/cache/scratch`. Python was `.venv-ci/bin/python` (3.12.3); lint was `.venv-ci/bin/ruff`.

Initial RED:

```text
.venv-ci/bin/python -m pytest tests/ingest/test_scheduler.py -q --basetemp=/home/joao/.hermes/cache/scratch/task18a-red
ERROR during collection: ModuleNotFoundError: No module named 'ingest.scheduler'
```

Intermediate RED after introducing the module/migration, before the Db attempt methods:

```text
.venv-ci/bin/python -m pytest tests/ingest/test_scheduler.py -q --basetemp=/home/joao/.hermes/cache/scratch/task18a-red-state
12 failed, 7 passed in 4.64s
```

Failures included absent scheduler persistence methods and the inherited nullable-state assumption. Inherited-test corrections also fixed a World Bank source-name/group-label confusion, an assertion that accidentally regrouped inactive series, incorrect success/streak tuple indices, and the false assumption that SQLite STRICT rejects losslessly coercible integer-to-TEXT values. Strictness tests now test genuine BLOB/TEXT and noninteger/INTEGER violations with diagnostic matches. Import order and ambiguous comprehension variable lint errors were corrected.

Initial scheduler GREEN:

```text
.venv-ci/bin/python -m pytest tests/ingest/test_scheduler.py tests/ingest/test_scheduler_contract.py -q --basetemp=/home/joao/.hermes/cache/scratch/task18a-green
35 passed in 16.32s
```

Final focused regression, including the subsequently added contract cases:

```text
.venv-ci/bin/python -m pytest tests/ingest/test_scheduler.py tests/ingest/test_scheduler_contract.py tests/ingest/test_db.py tests/ingest/test_cli.py tests/ingest/test_status.py tests/ingest/test_registry.py tests/ingest/test_scoped_legacy.py tests/ingest/test_licence_gate.py -q --basetemp=/home/joao/.hermes/cache/scratch/task18a-focused
116 passed in 48.47s

.venv-ci/bin/ruff check ingest/scheduler.py ingest/db.py tests/ingest/test_scheduler.py tests/ingest/test_scheduler_contract.py
All checks passed!

git diff --cached --check
Exit 0 before the code commit.
```

Coverage includes due/timezone/microsecond boundaries, persistent 1h/4h/12h retries and reset, reopened databases, repeated interruptions, a subprocess exiting abruptly without cleanup, independently visible pre-run markers, source/group isolation, client reuse, injectable loop/sleep, lock collisions/canonical aliases/release, inactive/blocked handling, invalid later groups rejected before any earlier group runs, import and actual module help with socket audit hooks, defaults against the real registry, malformed runner outcomes, setup-failure group identity, once exit codes, and fatal persistence errors.

Recorded World Bank integration used actual `operations.run_source` and registered `run_with_refetch`, with original committed JSON/CSV fixtures supplied through injected HTTP. It verified healthy groups, retried only the failed sibling, retained one verifier instance/configuration, and compared all held/served observations and dated legacy rows before and after later simulated HTTP failures. This is offline recorded-response evidence, not fresh publisher acceptance.

Migration checks exercised fresh STRICT schema, populated 0009 upgrade, preserved observations/settings/runs/audit records/served view, idempotent reopen, active foreign-key enforcement and integrity checks. Injected FK-violating migration statements rolled back both new schema and version record, including on a populated database; corrected files then upgraded successfully.

## GitNexus and scope checks

Indexing used `gitnexus analyze --skip-agents-md --name prumo-pipeline` throughout. Before additive Db work, `gitnexus impact Db -r prumo-pipeline` reported MEDIUM risk, 8 direct dependants and no attributed affected processes. Edited inherited test symbols reported LOW risk, no dependants. `run_source` was not modified.

Before the code commit:

```text
gitnexus detect-changes -r prumo-pipeline --scope staged
Changes: 5 files, 236 symbols
Affected processes: 11
Risk level: high
```

The aggregate HIGH result was surfaced before committing. The staged files were exactly the scheduler, additive Db changes/migration and scheduler tests. Graph attribution includes coarse/unmodified-symbol attribution (`close`) and unrelated frontend `observe` name matches; it was not treated as proof of an untouched runtime path. Actual focused execution and diff inspection supplied the additional evidence. Indexer parser warnings for existing empty modules and some unrelated source/test files remain a graph limitation.

Before/after `git hash-object` values matched for protected files and preserved orchestration/cadence/registry:

```text
AGENTS.md              bdf2f55999e6bc8d60d1c594fe85a42fcdc1be36
CLAUDE.md              b0d3b29f6221af4d8a3e9a6b821be02b8be183a6
ingest/operations.py    634c9125d0b979bc314af146bfd275ea3a41aa69
ingest/cadence.py       946be659de335f9cdb1c3148df83f0e9c6b14b93
registry/core.yaml      a0890a198ffa275ed5e8c38d6703c53351381ca9
```

The code commit's actual file list was read back using `git diff-tree --no-commit-id --name-only -r HEAD`. This report is committed separately after its own staged change check.

## Operational limits and remaining gates

The scheduler is serial and fixed-delay, not wall-clock aligned: slow group work delays later groups and adds to the interval between pass starts. Polling adds delay to retry eligibility. Existing HTTP per-request timeouts and bounded verification attempts are retained; there is no new whole-group deadline, watchdog or hard memory guarantee. A hung source can stall the serial pass. No health endpoint or idle-success heartbeat was added; logs and process supervision are minimal operational signals, not proof of freshness.

The lock is advisory and requires a filesystem with reliable flock semantics. It coordinates scheduler CLI instances sharing the same canonical DB path, not arbitrary embedded tick/serve calls, other CLI/manual writers, hard-link aliases or distributed hosts. Embedded callers must provide exclusive ownership themselves. An abruptly terminated attempt has durable state but cannot emit a terminal JSON line. A crash after source verification but before finishing scheduler state can produce a conservative retry rather than false freshness.

Registry changes require restart; changing a group's series membership changes its key and makes it initially due. Existing external CLI/manual runs do not postpone scheduler refresh. Scheduler-only setup failures without dataset_run records are visible in its state/logs; existing status projection was deliberately not expanded. Existing identical-payload verified short-circuit/sampling limitations remain unchanged.

REN/FRED/OECD technical verification does not authorize serving; licence gates remain intact. DGEG ingestion remains blocked. No new catch-up window, precision conversion, locale fallback, parser change, licence grant, data deletion, alert or backup was introduced.

The controller still owns independent spec/quality reviews, whole-suite acceptance, packaging/deployment integration, secure credential provisioning, production installation/catch-up, public maintenance verification and the required 24-hour observation. None of those gates is claimed complete here. Task 19 and final Project 1 closure remain outside this slice.

## Scoped files

- `ingest/scheduler.py`
- `ingest/db.py`
- `ingest/migrations/0010_scheduler_state.sql`
- `tests/ingest/test_scheduler.py` (inherited tests retained with described corrections)
- `tests/ingest/test_scheduler_contract.py`
- `docs/superpowers/handoff/reports/task-18-scheduler-implementation.md`
