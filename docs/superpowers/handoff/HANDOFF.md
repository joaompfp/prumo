# HANDOFF — Prumo base data pipeline (read this first)

Written 2026-11-11 at a usage-limit checkpoint so another agent can resume with no memory of the session.

## What this is
Rebuild of Prumo's data layer: a new `ingest/` package (raw → validated → served, SQLite, independent 100%-match verification).
- Spec (authority): `docs/superpowers/specs/2026-11-10-base-data-pipeline-design.md`
- Plan (19 tasks): `docs/superpowers/plans/2026-11-10-base-data-pipeline.md`
- Full decision log with every **Ruling** (A–U), review findings and deferred minors: `docs/superpowers/handoff/progress-ledger.md` — READ IT; rulings bind later tasks.
- Per-task briefs and implementer reports (RED/GREEN evidence, interfaces): `docs/superpowers/handoff/reports/`
- Execution method chosen by the owner: **subagent-driven** (`superpowers:subagent-driven-development`): fresh implementer per task + task review (spec + quality) + scoped re-review fix loop (max 5 rounds) + final whole-branch review. Resume with that skill; its ledger path is `.superpowers/sdd/2026-11-10-base-data-pipeline/progress.md` inside the worktree (git-ignored). If missing, restore it: `mkdir -p .superpowers/sdd/2026-11-10-base-data-pipeline && cp docs/superpowers/handoff/progress-ledger.md .superpowers/sdd/2026-11-10-base-data-pipeline/progress.md` and the `task-N-brief.md` files from `reports/`.

## Where the work lives
- Prumo repo (`joaompfp/prumo`), branch **`pipeline-rebuild`** (never merge to `main` without the owner). Worktree: `~/projects/prumo-pipeline` on f3nix. `git tag legacy-ui-final` = old UI.
- Tests: `~/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -q` (venv: python3.12 + pytest, pydantic>=2, pyyaml, requests, fastapi, uvicorn, httpx). **Do not install duckdb on f3nix: it crashes (Illegal instruction).**
- Deploy host is **f0nix** (`ssh f0nix`); Prumo container `prumo` (maintenance page) on Tailscale `100.118.19.6:8088`; public `cae.joao.date` + `joao.date/dados` via an f3nix Traefik file rule (`router-prumo-f0nix.yml` in the infra repo). Infra repo `~/docker` (f3nix branch `f3nix`; f0nix branch `f0nix`, commit 63b0af1+). Deploy with `bash -lic "dc-web-up prumo"` on f0nix; never raw docker compose/run. Traefik needs a restart to reload file rules (`bash -lic 'dc-core restart traefik'`).
- Legacy data export (CSV, from the old DuckDB, produced on f0nix): `~/projects/_legacy_export/indicators.csv` (246,162 rows). If lost: on f0nix `docker exec prumo python -c "import duckdb;c=duckdb.connect('/data/cae-data.duckdb',read_only=True);c.execute(\"COPY (SELECT source,indicator,region,period,value,unit,category,detail,fetched_at,source_id FROM indicators ORDER BY source,indicator,region,period) TO '/tmp/legacy-indicators.csv' (HEADER, DELIMITER ',')\")"`, then `docker cp` + `scp`.

## Status (2026-11-11)
| Task | State |
|---|---|
| 1 maintenance page + legacy UI removal + deploy | complete, deployed |
| 2 SQLite schema/Db | complete |
| 3 models + registry | complete |
| 4 raw store | complete |
| 5 validators | complete |
| 6 pipeline core + http client | complete |
| 7 verification framework (+ independence guard) | complete (4 fix rounds) |
| 8 legacy import + registry proposal | complete (commits ..8dbf715): provisional `registry/core.yaml` (1,774 series / 1,751 keys), overlaps.md, deferred-tail.md, unclassified.md, licences-todo.md; legacy import re-verified after Task 10 scale fix (164,345 imported, 6,522 missing_unit + 6 non_numeric + 480 suspect_unit_scale quarantined, 74,809 not_in_registry, 0 served) |
| 9 Eurostat adapter + verifier | complete (..954a89e): 329 active series (live-parsed OK), 368 inactive with reasons in registry/unmapped-eurostat.md |
| 10 INE adapter + verifier | complete through 16ee533; fix round 1 passed independent spec and quality reviews; controller live smoke verified 1,399 served / 24 of 24 sampled matches (isolated test DB, not deployment) |
| 11 Banco de Portugal adapter + verifier | complete through 550ad90; independent spec and quality reviews plus scoped fix re-review PASS; all 10 active series exercised live, 4,318 served / 78 missing-value quarantines / 24 of 24 sampled matches in isolated test DB |
| 12 REN (+ DGEG/ERSE if core) | PARTIAL: REN + licence-gate complete through 7f58a21; 182 live observations verified /50 of50 sampled matches /served=0 (restrictive licence). DGEG safe disposition complete through fd54d98 with independent gates:17inactive entries, reasons/evidence preserved. DGEG ingestion remains BLOCKED (no new adapter). ERSE has zero core series. |
| 13 World Bank | BLOCKED on full independent live gate. Implemented through27bec72; independent code spec/quality approved.982entries,52PPP conflicts inactive,930active/18codes. Full930-series fetch45915observations succeeds but CSVexport timeout prevents verification,served0; healthy516-series subset verified only as diagnostic. Not complete. |
| 14-16 source adapters | not started: FRED, OECD, E-REDES/dadosgov |
| 17 CLI/status/replay + delete old collectors | not started |
| 18 scheduler service + compose + deploy | not started |
| 19 docs + final audit pack | not started |
| Final whole-branch review (most capable model) → `superpowers:finishing-a-development-branch` | not started |

Last full controller test run after World Bank implementation: `.venv-ci/bin/python -m pytest tests -q` ->909passed,5live deselected,1warning(159.58s); Ruff all9touchedPython paths clean. WorldBank independent code spec/quality gates passed, but full live gate BLOCKED: controller reproduced930populated/45915written/15465nullquarantines/CSVReadTimeout/0served with bounded real run. Controller separately re-read516-series healthy-subset DB:25853served,516samplematches,all516exact stored evidence envelopes recovered offline. Subset is not all-source completion. See reports/task-13-controller-review.md. DGEG safe disposition passed both gates but ingestion remains blocked; legacy import unchanged. `.venv-ci/bin/ruff` touched paths clean. Final REN live smoke -> verified, all 14 active series over 13 completed months (2025-10..2026-10), 182 written / 0 quarantines / 50 of 50 sampled matches / 0 served with the real restrictive licence (42.56 s); status-bearing evidence recovered offline. Independent spec and quality reviews plus scoped fix re-reviews passed; reports/task-12-ren-*.md. Previous BPstat smoke: 4,318 served / 78 missing-value quarantines / 24 of 24 matches. INE: 1,399 served / 1 quarantine / 24 of 24 matches. All live runs used isolated scratch DBs, no pipeline deployment.

## Obligations carried into EVERY adapter task (9–16) — from rulings I, J, N, O, Q, R, S
1. Adapter = `ingest/sources/<name>.py` (implements `Source`, `fetch` returns an Iterable of `RawResponse`; `parse` returns `dict[series_id, list[RawRow]]` with `RawRow.response_index` pointing at the response each row came from) + independent verifier `ingest/verifiers/<name>.py`. Verifier uses a DIFFERENT endpoint/format than the collector, shares NO helper module with the parser, and passes the static allowlist in `register_verifier` (only `from ingest.http|models|rawstore|sources|verifiers import <allowlisted names>` + stdlib allowlist).
2. Hand numbers over as the publisher's TOKEN `str` (`json.loads(parse_float=str, parse_int=str)` or equivalent) — never floats. Declare `decimal` per series in the registry.
3. Verifier returns `ItemResult(series_id, period, observed_text, evidence_url, ...)` with required identity fields and observed_unit/observed_flag when exposed (report absent surfaces honestly). Archive every publisher response used to extract compared fields, including metadata, not only values (Ruling AC). BPstat uses the versioned `bportugal-portal-evidence` v1 JSON envelope with exact response bytes in base64, URLs and HTTP statuses.
4. Each adapter's tests MUST call `ingest.verifiers.independence.assert_verifier_independent(...)` (subprocess guard: blocks `ingest.sources.*`, checks loaded module names AND file origins) and include parse tests with recorded real fixtures (≤200 KB) cross-checked by hand against the publisher site, an HTML-error-page test, and flag-mapping tests (provisional/estimated/revised/break/normal in `ingest/flags.py` — create it in the first adapter task).
5. If a source has NO independent channel, do not invent one: list it in `registry/unverifiable.md`, mark `not served`, report to the owner (spec §6b).
6. Check API keys/rate limits from f0nix (secrets in SOPS `secrets/web.enc.env`; no FRED key is present there — Ruling F: report NEEDS_CONTEXT, secrets are the owner's).

## Owner decisions that must not be re-litigated
Public site = "Em manutenção" until the UI revamp (project 4). No Telegram/push alerts, no backups. Base data only (derived/AI later). Primary source = closest to origin (Portuguese institution for Portuguese data). 100% sampled verification, any mismatch → whole dataset re-fetched with a fresh sample, nothing served until verified. Revision history starts at the first ingestion date. Fallback policy when primary is down is deliberately undecided (decide from measured events). Registry is provisional; surface `registry/overlaps.md`, `registry/deferred-tail.md`, `registry/licences-todo.md` to the owner at the end.

## Known deferred minors (details in ledger)
Per-task minors are listed in `progress-ledger.md`. Notable: T17 must delete `scripts/audit_nightly.py` + the entrypoint cron block and clean `ci.yml`/`pytest.ini`/`tests/README.md`/`tests/conftest.py`; T17 CLI status must list stale `pending-verification` runs; `verify_run` itself accepts an unregistered verifier (only `run_with_refetch` enforces registration) so CLIs must call `run_with_refetch`; HEAD requests to the maintenance page return 405 (uptime probes).

## Next step (resume here)
1. Tasks 10 and 11 are complete, including their independent reviews and fix-round re-reviews. Do not re-dispatch their completed briefs.
2. REN Phase A and DGEG safe disposition passed independent gates; do not redispatch. DGEG ingestion stays BLOCKED (17inactive/no adapter) pending unit/representation/vintage/channel reconciliation. Task13 WorldBank code is implemented and independently approved through27bec72; do NOT repeat implementation. Read reports/task-13-controller-review.md, spec/quality review and implementer report. Remaining gate: successful all930-active-source independent live verification. CSVexport was intermittently unavailable; first do a small bounded availability probe, not hours of retries. Do not call516healthy-subset result full completion, inactivate series for an outage, bypass independence, relax precision or silently switch channel. Re-run full live acceptance only after channel availability; if still blocked, report it and preserve status. Tasks14FRED(no keyinSOPS:NEEDS_CONTEXTifneeded),15OECD,16E-REDES/dadosgov remain not started. One implementer at a time.
3. Task 17 (CLI/status/replay + delete old collectors; must register EurostatVerifier, INEVerifier, BPortugalVerifier and RenVerifier plus later completed source verifiers via register_verifier; explicitly report blocked DGEG even with all entries inactive; use run_with_refetch, per-source timeouts and SourceSpec.verifiable; list stale pending runs; ignore inactive series), 18 (scheduler + compose + f0nix deploy), 19 (docs), final whole-branch review on the most capable model, then `superpowers:finishing-a-development-branch` (merge to main is the owner's call).

## Method (how each task was run — keep doing the same)
Subagent-driven: dispatch a fresh implementer with a complete brief and binding rulings, then a read-only specification reviewer and a separate quality reviewer with concrete probes. Fix loops are bounded to five rounds, with scoped independent re-reviews. Record findings in the controller-owned ledger and mirror it to `.superpowers/sdd/2026-11-10-base-data-pipeline/progress.md`; commit and push scoped verified work on pipeline-rebuild only. Review packages can use `git diff <BASE_SHA>..<HEAD>`; the old Claude plugin script and model names are historical, not runtime requirements. Adapt dispatch to the active tool schema; actual agents in the INE/BPstat continuation reported kimi-k3. Never fabricate Claude coauthor/session trailers. Never fix code in the controller, run implementers concurrently, merge to main, or deploy early. Use `command cp -f` for ledger mirroring.

## Registry note (important)
`registry/core.yaml` is now AUTHORITATIVE: Task 9 added hand-derived `native_code`/`url` for Eurostat series (and later adapters add theirs). Do NOT re-run `propose_registry` over it (it would wipe them). Inactive series are explained in `registry/unmapped-eurostat.md` (and later `unmapped-<source>.md`). Verifiers are registered by the Task 17 CLI via `register_verifier(<Source>Verifier())`.

## OWNER DECISIONS PENDING
1. (RESOLVED by review: INE has an independent channel — bddXplorer HTML with Referer; see Task 10 fix round.)
2. Eurostat unit labels are inconsistent for the same code (see ledger Task 9).
3. Licences UNVERIFIED for OECD, DGEG, FRED; REN terms checked but restrictive and unresolved (`registry/licences-todo.md`). INE licence verified (CC BY 4.0).
4. INE `value_text`: keep INE's `valor` token (drops trailing zeros: '2' where INE publishes '2,0'; 169/2472 cells) with a numeric verifier [default, Ruling AB], or switch to the published `ind_string` with `decimal: ','` (would quarantine the legacy INE import).
5. REN terms restrict reuse (clauses 2/3.2): internally verified but redistribution_ok=false and served=0 under migration0005. No consent or legal exception established; owner resolution required before serving.
6. DGEG current core has native unit/concept, percent-storage/display, publication-vintage and exact-channel coverage blockers. No new DGEG adapter/ingestion yet. Preserve original registry definitions until explicit reconciliation; safe inactive/blocked disposition is not completed ingestion. Reuse grant for the energy workbook remains unconfirmed.

## Deployed state / environment notes (2026-11-11)
- f0nix runs container `prumo` = the Task 1 maintenance page (prumo repo checkout at `~/docker/stacks/web/images/prumo` on f0nix is on branch `pipeline-rebuild` at the Task 1 commit `031eb3b`; infra repo `~/docker` branch `f0nix`, commits 00c9596 + 63b0af1). The `ingest/` package is NOT deployed yet (Task 18). After Task 18 the f0nix checkout must be updated (`git fetch && git checkout pipeline-rebuild && git pull`) before `bash -lic "dc-web-up prumo-ingest"`.
- Unrelated pre-existing dirt in the infra repos (f0nix: `stacks/office/compose.yml`, untracked `feynman/`, `ifc-viewer/`, `compose.yml.bak-*`; f3nix: nested-repo pointer `stacks/web/images/prumo`) is NOT part of this work — do not commit it blindly.
- f3nix infra repo (branch f3nix): commit 538e66d moved Prumo routing to f0nix (`router-prumo-f0nix.yml`, force-added; Traefik needs a restart to reload file rules).
- Worktree `~/projects/prumo-pipeline` (branch `pipeline-rebuild`, pushed to origin) is the working copy; the original clone `~/docker/stacks/web/images/prumo` is on `main` — do not merge to main without the owner. Continuation probes and isolated live DBs live under `/home/joao/.hermes/cache/scratch/` and expire; committed fixtures, reports and this handoff are the durable record. Legacy Claude scratch paths are historical and are not required to resume.
