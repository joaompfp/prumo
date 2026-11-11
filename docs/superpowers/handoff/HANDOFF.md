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
| 8 legacy import + registry proposal | complete (commits ..8dbf715): provisional `registry/core.yaml` (1,774 series / 1,751 keys), overlaps.md, deferred-tail.md, unclassified.md, licences-todo.md; legacy import verified on the real export (164,825 imported, 6,522 missing_unit + 6 non_numeric quarantined, 74,809 not_in_registry, 0 served) |
| 9 Eurostat adapter + verifier | complete (..954a89e): 329 active series (live-parsed OK), 368 inactive with reasons in registry/unmapped-eurostat.md |
| 10 INE adapter | implemented (..2b8198a); review ❌: CRITICAL — INE DOES have an independent channel (bddXplorer HTML table with a `Referer` header) so the verifier must be built; + 3 Important. **Fix round 1 NOT yet dispatched: ready-to-dispatch instructions in `docs/superpowers/handoff/task-10-fix-round-1.md`** |
| 11–16 source adapters | not started (Eurostat, INE, Banco de Portugal, REN(+DGEG/ERSE), World Bank, FRED, OECD, E-REDES/dadosgov) |
| 17 CLI/status/replay + delete old collectors | not started |
| 18 scheduler service + compose + deploy | not started |
| 19 docs + final audit pack | not started |
| Final whole-branch review (most capable model) → `superpowers:finishing-a-development-branch` | not started |

Last full test run: `pytest tests/ingest -q` → 604 passed (2 live deselected).

## Obligations carried into EVERY adapter task (9–16) — from rulings I, J, N, O, Q, R, S
1. Adapter = `ingest/sources/<name>.py` (implements `Source`, `fetch` returns an Iterable of `RawResponse`; `parse` returns `dict[series_id, list[RawRow]]` with `RawRow.response_index` pointing at the response each row came from) + independent verifier `ingest/verifiers/<name>.py`. Verifier uses a DIFFERENT endpoint/format than the collector, shares NO helper module with the parser, and passes the static allowlist in `register_verifier` (only `from ingest.http|models|rawstore|sources|verifiers import <allowlisted names>` + stdlib allowlist).
2. Hand numbers over as the publisher's TOKEN `str` (`json.loads(parse_float=str, parse_int=str)` or equivalent) — never floats. Declare `decimal` per series in the registry.
3. Verifier returns `ItemResult(series_id, period, observed_text, evidence_url, ...)` with series_id/period REQUIRED, `observed_unit`/`observed_flag` whenever the channel exposes them (say in the report if not), and `evidence` bytes so the evidence is kept in the raw store.
4. Each adapter's tests MUST call `ingest.verifiers.independence.assert_verifier_independent(...)` (subprocess guard: blocks `ingest.sources.*`, checks loaded module names AND file origins) and include parse tests with recorded real fixtures (≤200 KB) cross-checked by hand against the publisher site, an HTML-error-page test, and flag-mapping tests (provisional/estimated/revised/break/normal in `ingest/flags.py` — create it in the first adapter task).
5. If a source has NO independent channel, do not invent one: list it in `registry/unverifiable.md`, mark `not served`, report to the owner (spec §6b).
6. Check API keys/rate limits from f0nix (secrets in SOPS `secrets/web.enc.env`; no FRED key is present there — Ruling F: report NEEDS_CONTEXT, secrets are the owner's).

## Owner decisions that must not be re-litigated
Public site = "Em manutenção" until the UI revamp (project 4). No Telegram/push alerts, no backups. Base data only (derived/AI later). Primary source = closest to origin (Portuguese institution for Portuguese data). 100% sampled verification, any mismatch → whole dataset re-fetched with a fresh sample, nothing served until verified. Revision history starts at the first ingestion date. Fallback policy when primary is down is deliberately undecided (decide from measured events). Registry is provisional; surface `registry/overlaps.md`, `registry/deferred-tail.md`, `registry/licences-todo.md` to the owner at the end.

## Known deferred minors (details in ledger)
Per-task minors are listed in `progress-ledger.md`. Notable: T17 must delete `scripts/audit_nightly.py` + the entrypoint cron block and clean `ci.yml`/`pytest.ini`/`tests/README.md`/`tests/conftest.py`; T17 CLI status must list stale `pending-verification` runs; `verify_run` itself accepts an unregistered verifier (only `run_with_refetch` enforces registration) so CLIs must call `run_with_refetch`; HEAD requests to the maintenance page return 405 (uptime probes).

## Next step (resume here)
1. Dispatch Task 10 fix round 1 from `docs/superpowers/handoff/task-10-fix-round-1.md` (fresh implementer; the earlier agents' ids are gone), then a scoped re-review.
2. Task 11 Banco de Portugal (BPstat; add units — legacy had none → 0 core series today), then 12 REN(+DGEG/ERSE), 13 World Bank, 14 FRED (no key in SOPS: NEEDS_CONTEXT to owner), 15 OECD, 16 E-REDES/dadosgov (only if the registry marks core). Use `adapter-dispatch-template.md` for each dispatch.
3. Task 17 (CLI/status/replay + delete old collectors; must register verifiers: `register_verifier(EurostatVerifier())` etc.; per-source timeouts; list stale pending runs; ignore inactive series; machine-readable unverifiable marker), 18 (scheduler + compose + f0nix deploy), 19 (docs), final whole-branch review on the most capable model, then `superpowers:finishing-a-development-branch` (merge to main is the owner's call).

## Method (how each task was run — keep doing the same)
Subagent-driven: (a) dispatch an implementer (opus for adapters/judgement tasks, sonnet for mechanical) with the task brief + rulings, told to commit as it goes; (b) generate the review package: `bash ~/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.0/skills/subagent-driven-development/scripts/review-package docs/superpowers/plans/2026-11-10-base-data-pipeline.md <BASE_SHA> HEAD`; (c) dispatch an ADVERSARIAL reviewer (opus for adapters/verification; sonnet for small tasks) that probes live/with scratch scripts; (d) fix loop ≤5 rounds with scoped re-reviews of each fix diff; (e) record every finding/ruling in `.superpowers/sdd/2026-11-10-base-data-pipeline/progress.md` and copy it to `docs/superpowers/handoff/progress-ledger.md` + commit + push after each step. Never fix findings in the controller session; never run implementers in parallel. Use `command cp -f` (the shell aliases `cp -i`).

## Registry note (important)
`registry/core.yaml` is now AUTHORITATIVE: Task 9 added hand-derived `native_code`/`url` for Eurostat series (and later adapters add theirs). Do NOT re-run `propose_registry` over it (it would wipe them). Inactive series are explained in `registry/unmapped-eurostat.md` (and later `unmapped-<source>.md`). Verifiers are registered by the Task 17 CLI via `register_verifier(<Source>Verifier())`.

## OWNER DECISIONS PENDING
1. (RESOLVED by review: INE has an independent channel — bddXplorer HTML with Referer; see Task 10 fix round.)
2. Eurostat unit labels are inconsistent for the same code (see ledger Task 9).
3. Licences UNVERIFIED for OECD, REN, DGEG, FRED (`registry/licences-todo.md`); INE licence verified (CC BY 4.0).
4. INE `value_text`: keep INE's `valor` token (drops trailing zeros: '2' where INE publishes '2,0'; 169/2472 cells) with a numeric verifier [default, Ruling AB], or switch to the published `ind_string` with `decimal: ','` (would quarantine the legacy INE import).

## Deployed state / environment notes (2026-11-11)
- f0nix runs container `prumo` = the Task 1 maintenance page (prumo repo checkout at `~/docker/stacks/web/images/prumo` on f0nix is on branch `pipeline-rebuild` at the Task 1 commit `031eb3b`; infra repo `~/docker` branch `f0nix`, commits 00c9596 + 63b0af1). The `ingest/` package is NOT deployed yet (Task 18). After Task 18 the f0nix checkout must be updated (`git fetch && git checkout pipeline-rebuild && git pull`) before `bash -lic "dc-web-up prumo-ingest"`.
- Unrelated pre-existing dirt in the infra repos (f0nix: `stacks/office/compose.yml`, untracked `feynman/`, `ifc-viewer/`, `compose.yml.bak-*`; f3nix: nested-repo pointer `stacks/web/images/prumo`) is NOT part of this work — do not commit it blindly.
- f3nix infra repo (branch f3nix): commit 538e66d moved Prumo routing to f0nix (`router-prumo-f0nix.yml`, force-added; Traefik needs a restart to reload file rules).
- Worktree `~/projects/prumo-pipeline` (branch `pipeline-rebuild`, pushed to origin) is the working copy; the original clone `~/docker/stacks/web/images/prumo` is on `main` — do not merge to main without the owner. Local temp files (probe scripts) live under `/tmp/claude-1000/...` and may disappear; everything needed is in this folder.
