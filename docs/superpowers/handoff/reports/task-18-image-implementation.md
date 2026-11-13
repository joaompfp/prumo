# Task 18B image, compose and runbook implementation

## Scope

Implemented only the image/deployment-contract slice in
`/home/joao/projects/prumo-pipeline` on `pipeline-rebuild`.
No scheduler, cadence, DB, migrations, operations, status, ingestion CLI or scheduler-test
files were edited by this slice. Existing `AGENTS.md`/`CLAUDE.md` dirt and the controller's
briefs were not edited or staged. No shared HANDOFF/ledger changes, nested agents, merge,
push, deployment, live publisher calls, secret provisioning or external configuration
changes were performed.

## Changed files

- `Dockerfile`: package app/static/ingest/registry, including migrations; remove historical
  collector/script/seed copies; use `PRUMO_DB_PATH=/data/prumo.sqlite3` and
  `PRUMO_RAW_DIR=/data/raw`. Preserve the existing uvicorn command, HTTP healthcheck,
  entrypoint, Python base and exposed container port.
- `entrypoint.sh`: only `set -e`, create `/data`, then `exec "$@"`. Remove site.json,
  ideology and DuckDB seeding and obsolete cron prose. Historical repository files remain.
- `.dockerignore`: deny-by-default runtime allowlist, with final nested cache, virtualenv,
  env/credential, database and editor-artifact exclusions. No secret values were introduced.
- `deploy/prumo-ingest.yml`: repository-only worker candidate with a distinct image/build,
  shared persistent data, DNS mount, 512m limit, bounded stdout logging, existing proxy
  network and no public ports/labels. Only `FRED_API_KEY=${FRED_API_KEY:-}` is a source
  secret; inherited HTTP healthcheck explicitly disabled.
- `tests/test_docker_contract.py`: offline input contracts, executable entrypoint
  PID/argument/exit preservation and directory-failure behavior, compose contract and
  runbook shell syntax/authoritative manual-refresh link checks.
- `docs/data/operations.md`: controller prerequisites, bootstrap/import/catch-up,
  status/log/SQLite/raw evidence commands, container handoff for authoritative manual
  bundles, safe worker-stop rollback and an open 24-hour acceptance procedure.
- `docs/superpowers/handoff/reports/task-18-image-implementation.md`: this report.

## RED

Tests were written and executed before production-file changes:

```bash
.venv-ci/bin/python -m pytest tests/test_docker_contract.py \
  --basetemp=/home/joao/.hermes/cache/scratch/prumo-task18-image-red
```

The first test pass exposed an incidental Dockerfile continuation-whitespace issue in the
new test parser. Corrected that parser and repeated RED against unchanged production files:
`7 failed, 2 passed, 3 errors in 0.17s`, exit 1. Failures covered historical image copies/env,
unsafe context, seed behavior, entrypoint execution and missing runbook/candidate. The
unchanged web command/healthcheck and directory-failure short circuit passed. Missing
compose was reported as fixture assertion errors, not skipped coverage.

The test double intercepts only mkdir so entrypoint execution cannot create production
`/data`; pytest scratch paths remain under the mandated scratch directory.

## GREEN

```bash
.venv-ci/bin/python -m pytest tests/test_docker_contract.py tests/test_maintenance.py \
  tests/test_task17_cleanup.py \
  --basetemp=/home/joao/.hermes/cache/scratch/prumo-task18-image-green
.venv-ci/bin/ruff check tests/test_docker_contract.py
/bin/sh -n entrypoint.sh
git diff --check -- Dockerfile entrypoint.sh .dockerignore
```

Actual results: `63 passed, 1 warning in 1.31s`; Ruff `All checks passed!`; shell syntax and
whitespace checks exited successfully. All new Docker contracts passed. Maintenance routes
and retained historical-file/cleanup boundaries passed without app changes. No full suite,
image build or production execution is claimed.

## Interface findings and controller gates

The real `.venv-ci/bin/python -m ingest --help`, `import-legacy --help`, `run --help` and
`status --help` were executed offline before authoring commands:

- `import-legacy` takes a positional CSV; global `--db`/`--raw-dir` precede the subcommand.
- The current CLI DB environment name is `PRUMO_DB`, not the worker contract's
  `PRUMO_DB_PATH`. Operator commands explicitly select `/data/prumo.sqlite3`; this slice
  did not change the other implementer's CLI path.
- The current E-REDES `run --to` is inclusive and rejects today UTC. The brief's desired
  initial window has an exclusive upper bound at the actual UTC day start. The runbook
  derives yesterday UTC for the existing CLI's `--to` to produce precisely that window,
  rather than documenting an invalid command or changing the CLI. Recheck deployed help
  before execution and stop if its contract has changed.
- The controller must install/include the candidate, correct existing web DuckDB paths,
  preserve maintenance web health/port binding, review obsolete AI coupling, provision and
  silently verify the SOPS FRED key, build and execute the actual deployment.
- The SOPS, infra, container, response-evidence and public-site commands are unexecuted
  operator instructions. They require the real f0nix environment. This slice did not read
  or print secrets. Dockerignore tests check the input contract, not a built image/context.
- Manual-refresh.md remains unchanged and authoritative; the new runbook supplies only
  the deployed container handoff. Recorded input keeps original dates and is never called
  fresh solely because import/verification happened now.
- Worker-stop is the safe operational rollback. No destructive schema downgrade or
  unreviewed historical entrypoint restoration is provided.
- Full-suite/build evidence, independent spec/quality reviews, production catch-up and
  the actual 24-hour observation remain controller-owned and open. Known source failures,
  per-indicator World Bank failures, DGEG blocks and REN/FRED/OECD withholding must be
  reported separately, without an all-core-fresh claim.

## Staging and GitNexus

The exact worktree initially reported GitNexus up to date at `aa89fed`. No existing runtime
Python symbols were modified. Impact lookup for the new test fixture
`tests/test_docker_contract.py:instructions` returned target-not-found / UNKNOWN; it was
not present in the pre-existing index. GitNexus text queries also emitted read-only FTS
initialization warnings and returned no image/entrypoint flows; this is a graph limitation,
not evidence that deployment changes have no impact.

Only the listed slice paths were staged. The staged Dockerfile, entrypoint, ignore and
compose diff was inspected, and:

```bash
gitnexus detect-changes -r prumo-pipeline --scope staged
```

returned `No changes detected.` This graph result does not replace the explicit file diff
or focused tests. The complete staged slice, including tests, runbook and report, is
inspected again and the mandated staged detection repeated before the scoped commit.
Commit identity is reported by the final Git output rather than embedded in its own file.
