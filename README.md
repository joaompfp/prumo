# Prumo

Prumo is rebuilding its base-data layer for Portuguese, European and world statistics.
The Python `ingest/` pipeline stores publisher responses and validated observations in
SQLite, with independent sampled verification and licence-gated queryability.

The maintenance web app and ingestion worker are already deployed on f0nix. The public
sites, `https://cae.joao.date/` and `https://joao.date/dados/`, remain in "Em manutenção"
until the later UI revamp. The retired dashboard is recoverable at the Git tag
`legacy-ui-final`; its chart sections and data API are not current interfaces.

Task 18's real 24-hour observation remains open. Deployment does not close that gate
or constitute final owner acceptance of Project 1. See the [current handoff](docs/superpowers/handoff/HANDOFF.md)
and [operations](docs/data/operations.md) for the dated checkpoint and remaining gates.

## Documentation

- [Documentation map](DOCS_MAP.md): current entrypoints and historical references.
- [Methodology](docs/data/methodology.md): raw, validated and served stages, precision,
  vintages, flags and the limits of sampled verification.
- [Source catalogue](docs/data/sources.md): registry-generated licences, attribution,
  primary-series identifiers and reviewed independent channels.
- [Operations](docs/data/operations.md): deployed f0nix paths, status, worker ownership,
  manual-write procedure and observation acceptance.
- [Manual refresh](docs/data/manual-refresh.md): original-response capture and offline
  bundle rules for World Bank and E-REDES.
- [Handoff](docs/superpowers/handoff/HANDOFF.md): controller-owned decisions and review status.

## Local setup

Terminology: HTTP means Hypertext Transfer Protocol; API means application programming
interface; JSON means JavaScript Object Notation; CLI means command-line interface;
SQL means Structured Query Language. Publisher identities are in the source catalogue.

Python 3.12 is the deployed image baseline. From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m ingest --help
.venv/bin/python -m ingest run --help
.venv/bin/python -m ingest capture --help
.venv/bin/python -m ingest.scheduler --help
```

Help does not fetch sources or open the data store. A local maintenance app needs no
populated database:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080
```

GET `/healthz` returns `{"status":"ok"}`. Other non-static GET paths return the
maintenance page, including old `/api/*` paths and `/docs`; there is no public data API
or interactive API documentation. `/static` serves only the maintenance page's favicon
(the legacy UI assets are recoverable at the `legacy-ui-final` tag). Health reports
web-process availability, not ingestion freshness. HEAD on `/`, `/healthz` and the
maintenance routes returns 200, for uptime probes.

## Runtime layout

| Path | Responsibility |
|---|---|
| `ingest/sources/` | Publisher-specific fetching and parsing |
| `ingest/verifiers/` | Independently parsed publisher channels |
| `ingest/pipeline.py`, `ingest/verify.py` | Raw capture, validation and sampled verification |
| `ingest/db.py`, `ingest/migrations/` | SQL access and versioned SQLite schema |
| `ingest/cli.py`, `ingest/operations.py` | Command-line interface and dataset-group policy |
| `ingest/scheduler.py`, `ingest/cadence.py` | Serial refresh, persisted retry state and cadence |
| `registry/core.yaml` | Authoritative source and series definitions, including inactive entries |
| `app/main.py`, `static/` | Maintenance-only HTTP app and its favicon |
| `deploy/prumo-ingest.yml` | Worker definition installed in the f0nix infrastructure stack |
| `tests/ingest/` | Offline pipeline, adapter, verifier and CLI tests; opt-in live tests |

Retained `collectors/`, scripts, seeds and archived documentation are historical or
unresolved integrations, not the deployed ingestion entrypoint. The runtime image has
no DuckDB dependency. Do not regenerate `registry/core.yaml` from a legacy proposal or
remove retained data to make the documentation look current.

## Commands and paths

`python -m ingest` provides `docs`, `run`, `capture`, `status`, `verify`,
`import-legacy` and `replay`. `python -m ingest docs` renders the source catalogue
to stdout without network or database access; `python -m ingest --registry PATH docs`
selects a custom registry. The catalogue is generated, not edited by hand. Consult
subcommand help before a write. `run --dry-run` still performs real
network fetching in an isolated temporary database. `replay` is a fresh re-fetch, not
reconstruction of missing historical vintages. Bundle imports are offline but write
the selected destination database.

Production uses `/data/prumo.sqlite3` and `/data/raw`, shared by `prumo` and
`prumo-ingest` on f0nix. The worker reads `PRUMO_DB_PATH`; the ingestion CLI's database
override is still `PRUMO_DB`. Both support `PRUMO_RAW_DIR`. For operator CLI commands,
pass global `--db` and `--raw-dir` explicitly before the subcommand, as shown in
[operations](docs/data/operations.md). Local experiments must use separate paths.

A registry licence grant and successful verification are separate requirements. FRED,
OECD and REN remain legally withheld; DGEG remains inactive and not verifiable under
its current definitions. [Licence decisions](registry/licences-todo.md) and
[unverifiable definitions](registry/unverifiable.md) retain the unresolved cases.

## Tests and lint

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check app/ ingest/
```

Ruff is a development/CI tool, installed separately from `requirements.txt`. Default
pytest configuration deselects live tests; invoking live collection requires explicit
scope. For documentation-only changes, use focused link, shell syntax, help and
relevant contract checks rather than repeating the controller's full suite.

Deployment and independent manual writes require separate owner authorization. Use
the f0nix `dc-web-*` aliases and the [operations runbook](docs/data/operations.md);
never start a second writer alongside the scheduler. No push alerts or automatic
backups are part of this pipeline.
