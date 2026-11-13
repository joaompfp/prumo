# Prumo documentation map

The current system is the SQLite base-data pipeline and maintenance-only web app.
Task 18 is deployed on f0nix; its real 24-hour observation and final project acceptance
remain open. The [handoff](docs/superpowers/handoff/HANDOFF.md) owns progress and gates.
Historical dashboard documents below are retained references, not current instructions.

## Current entrypoints

| Document | Purpose |
|---|---|
| [README](README.md) | Runtime overview, local setup, supported interfaces and test commands |
| [Methodology](docs/data/methodology.md) | Data stages, native values, vintages, flags and sampled verification |
| [Source catalogue](docs/data/sources.md) | Generated registry metadata, primary identifiers and reviewed independent channels |
| [Operations](docs/data/operations.md) | Actual f0nix services/paths, status, manual-write safety and open observation |
| [Manual refresh](docs/data/manual-refresh.md) | Original World Bank/E-REDES bundles, offline import semantics and return codes |
| [Agent context](CLAUDE.md) | Agent instructions; human-prefix refresh awaits protected-file approval, with generated graph text retained |
| [Local development constraints](AGENTS.md) | Repository instructions |

For source or adapter work, read the methodology and registry decisions before changing
code. For a production update, use operations and its linked manual instead of the old
collector commands. The web health endpoint does not report source freshness.

## Registry and decisions

| Path | Authority |
|---|---|
| [Core registry](registry/core.yaml) | Source metadata, licence eligibility, series identity, primary/cross-check role and active state |
| [Licence review](registry/licences-todo.md) | Unresolved redistribution grants, separate from technical verification |
| [Unverifiable definitions](registry/unverifiable.md) | Current DGEG block and boundaries of that finding |
| [DGEG mapping findings](registry/unmapped-dgeg.md) | Per-series blockers and resumption criteria |
| [Overlaps](registry/overlaps.md) | Provisional primary-source assignments for owner review |
| [Deferred tail](registry/deferred-tail.md) | Indicators outside the current core |
| [Design](docs/superpowers/specs/2026-11-10-base-data-pipeline-design.md) | Project 1 intent and original design; later ledger rulings supersede historical assumptions |
| [Implementation plan](docs/superpowers/plans/2026-11-10-base-data-pipeline.md) | Task scope, not proof of operational acceptance |
| [Decision ledger](docs/superpowers/handoff/progress-ledger.md) | Binding rulings and review history; controller-owned |
| [Task 18 release checkpoint](docs/superpowers/handoff/reports/task-18-controller-review.md) | Real deployment evidence, distinct from final observation acceptance |
| [Task 19 brief](docs/superpowers/handoff/reports/task-19-brief.md) | Dated intermediate source checkpoint and documentation ownership |

## Code navigation

- `ingest/db.py` and `ingest/migrations/`: all SQL access and schema evolution.
- `ingest/sources/` and `ingest/verifiers/`: separate collector and independent-channel implementations.
- `ingest/validate.py`, `ingest/models.py`, `ingest/flags.py`: validation, periods, exact
  text/Decimal handling and reviewed flag mappings.
- `ingest/operations.py`, `ingest/cli.py`: grouping and operator command semantics.
- `ingest/scheduler.py`, `ingest/cadence.py`: deployed serial worker and shared refresh policy.
- `app/main.py`: maintenance GET routes, static mount and `/healthz`.
- `tests/ingest/`, `tests/test_maintenance.py`, `tests/test_docker_contract.py`: offline
  regression coverage and image/runbook contracts.

## Historical references

These documents describe earlier designs, scope or dashboard behavior. They do not
supersede the current registry, methodology, operations or handoff.

- [Older documentation index](docs/README.md) and [source notes](SOURCES.md).
- [Earlier normalization policy](docs/data/NORMALIZATION.md) and
  [indicator audit](docs/data/painel-indicators-audit.md).
- [Legacy deployment runbook](docs/operations/MIGRATION_RUNBOOK.md).
- [Design guide](docs/design-guide.md) and [design resources](docs/design/README.md).
- Retained collector code, scripts, seeds and
  [historical audit evidence](docs/superpowers/handoff/reports/).

The removed UI is recoverable at the Git tag `legacy-ui-final`. Retention is deliberate;
a historical link does not assert that its old commands or imports still work.
