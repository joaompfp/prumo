# Prumo — Base Data Pipeline (ingestion + sanitization) — Design

Date: 2026-11-10 · Status: draft for approval · Project 1 of 4 (see "Sequence")

## 1. Intent and why

Prumo is a Portuguese/European/world statistics dashboard read by professionals and the public.
Its single promise is **trust**: every number on screen is a number an institution published,
traceable to that publisher, never silently stale, never silently altered. The owner must be able
to survive an audit by professional statisticians.

Today the data is frozen at 2026-04-06: the nightly collector never ran in the container
(`entrypoint.sh` relies on `crond`, absent from `python:3.12-slim`). The store (a single DuckDB
file) has no constraints worth the name: ~11k of 246k rows lack a value or unit, INE periods are
free text ("Setembro de 2025") while other sources use `2026-02`, and nothing records what a
source originally sent or how a value changed over time.

This project replaces ingestion and the system of record. It is the foundation for everything else.

## 2. Sequence (four projects, brainstormed one at a time)

1. **Base data pipeline** — this document.
2. Backoffice (review of flags, source health, indicator registry) — *owner's guess: needed, not yet designed*.
3. Derived layer (YoY, comparisons, scores, AI commentary) — separate dataset built on top of base data.
4. UI revamp — must later expose a per-figure provenance view ("where does this come from").

## 3. Goals

- G1. Every stored value links to: publisher, dataset/series ID, source URL, the exact raw payload
  received, retrieval time.
- G2. Nothing invented: no interpolation, gap-filling, unit conversion or rounding unless explicitly
  declared in the registry; values keep the publisher's precision.
- G3. Keep official observation metadata: status flags (provisional / estimated / revised / break in
  series), unit and multiplier, seasonal adjustment, base year, frequency.
- G4. Vintages: a revised value never overwrites history. We can answer "what did we show on date X,
  and why did it change".
- G5. Two dates per value: reference period (what it measures) and release/retrieval date (when known).
- G6. Bad data is rejected at the door by constraints and validators; failures never overwrite good
  data and are visible as "last verified on date X". Staleness is stated, never hidden.
- G7. Reproducible: re-running the pipeline from the stored raw files yields the same database.
- G8. Licence and attribution recorded per source and shown wherever its data is shown.
- G9. Catch up the missing months (2026-04 → now) first. Sources serve their *current* vintage, so the
  catch-up is a live re-fetch: the first raw payloads (and therefore real vintage history) begin on the
  day it runs. It still gives months of observations per indicator to tune collectors and validators
  against real formats; fetch failures, format changes and cross-source disagreements are measured
  from then on, and revisions are measured going forward as the pipeline runs daily. Revisions that
  happened during the gap cannot be reconstructed and the documentation says so.

## 4. Scope of indicators

Core set only: **economics, demography, energy** for **Portugal and Europe**, plus **basic world
statistics where widely available**. The other ~400-indicator tail (e.g. DGEG's 180 fuel series by
type/region) is deferred until the pipeline has proven itself. The first task of the build is to
produce the registry of the core set (theme, geography, primary source, frequency) from the existing
data for the owner to review once.

## 5. Source-of-truth rule

Each indicator has exactly one **primary source**: the most reputable, closest to the origin.
Portuguese data prefers a Portuguese institution (INE, Banco de Portugal, REN, DGEG, ERSE); EU-wide
data prefers Eurostat; world data World Bank / OECD / FRED as appropriate. Other sources publishing
the same indicator are **cross-checks only** — never displayed in place of the primary. A large
primary-vs-cross-check gap raises a flag for human review; it is never auto-corrected.

**Deliberately undecided:** behaviour when the primary is down or publishes a doubtful revision
(show last-verified-stale vs. labelled fallback). The pipeline must log every fetch failure,
revision and cross-source disagreement as a structured event so the policy is decided later from
counts measured during the replay (G9).

## 6. Architecture

Three stages, strictly separated (separation of concerns):

1. **Raw** — each fetch saves the payload unmodified, content-hashed, on disk beside the DB, with a
   manifest row (source, URL/params, time, hash, HTTP status).
2. **Validated** — per-source parser turns a raw payload into standard observations; validators
   (schema, unit, period, range, duplicate, flag) accept or reject. Rejections are recorded with reason.
3. **Served** — only validated observations, as the current vintage plus full history. The app reads
   only this stage.

**System of record:** SQLite (strict tables, WAL, real constraints, one inspectable file). DuckDB may
read it for analysis and for the later derived layer. **Language:** Python stays (SDMX/JSON-stat
clients, Pydantic validation); no rewrite. **Scheduler:** a small purpose-built runner plus a run log;
no Airflow/Dagster/Prefect. **Engine portability:** all access through one data-access module;
schema in versioned, portable SQL migrations, so moving to Postgres later means rewriting one module.

Runs on f0nix (container `prumo`, Tailscale `100.118.19.6:8088`; public via f3nix Traefik file rule
for `cae.joao.date` and `joao.date/dados`). Local Ollama on f0nix is the only AI backend;
`claude-max-proxy` is retired and all Claude/Anthropic code, env vars and scripts are to be removed.

## 7. Non-goals and anti-goals

Non-goals (this project): preserving the current UI/API, derived numbers, AI commentary, UI redesign, backoffice UI, backups
(owner: "forget about backups, we're revamping anyway"), the fallback policy (§5).
Anti-goals — failure even if it technically works: a wrong number on screen; a number correct but
late; any number that cannot be traced and defended to an auditor.

## 8. Existing system facts (for the builder)

- Repo `joaompfp/prumo`, FastAPI app under `app/`, collectors under `collectors/` (bportugal, dadosgov,
  dgeg_fuel_api, eredes, eurostat, fred, habitacao, ine, oecd, ren, worldbank), orchestration in
  `scripts/collect_scheduled.py`, nightly audit `scripts/audit_nightly.py`.
- Current table `indicators(source, indicator, region, period, value, unit, category, detail,
  fetched_at, source_id)` plus `collection_log`, `fetch_log`, `meta`. 246k rows, 9 sources:
  EUROSTAT 157k, WORLDBANK 53k, FRED 10k, INE 10k, DGEG 7k, BPORTUGAL 3.5k, REN 2.7k, OECD 2.3k, ERSE 0.5k.
  Latest data 2026-04-06; 0 duplicate keys; ~11.2k null value/unit.
- Deployment: f0nix compose `stacks/web/compose/prumo.yml` (committed). Data dir
  `stacks/web/appdata/prumo` (119 MB; stale backups deliberately not copied).
- Dead code to remove in the sanitize phase: `app/services/claude_client.py` Claude paths
  (`search_web`, Claude call), `CAE_ANTHROPIC_TOKEN` handling in `interpret.py`, `scripts/ai/*haiku*`,
  `painel_card_links.py` dependency on it, stale `CLAUDE.md`/`SETUP_NOTES.md` (still say `dc-jarbas`/`cae-dashboard`).

## 9. Decided by the owner (as stated)

- Trust = provenance from known, reputable institutional sources.
- Base data first; calculations and commentary come later as a separate derived dataset.
- Prefer the most reputable source closest to the origin (Portuguese institution for Portuguese data).
- Fallback policy deferred until measured.
- Core scope as in §4. Stack open to change; SQLite first, other engine "when needed".
- Audience: professionals and the public. Must be bullet-proof and audit-proof.
- Catch-up replay (Apr→Nov) is used to tune ingestion over months of real data.

## 10. Left to the builder

Table layout and naming; the standard observation model and flag vocabulary (SDMX concepts are a
sensible reference); validator set and thresholds; runner design and schedule per source release
calendar; how the app's read path migrates; test strategy (the replay corpus is the regression set);
order of source migration; how to expose provenance to the future UI.

## 11. Builder's own calls (to be confirmed by the owner)

Owner accepted that revision history starts on the first ingestion date, which is recorded. Settled after the builder check; these are the planner's calls, not the owner's words:

1. **Legacy rows.** The 246k existing rows are imported once as a vintage tagged `legacy-unverified`
   (original `fetched_at` kept, no raw payload). Core-set series are then re-fetched; the fresh,
   fully-traced vintage supersedes the legacy one. Legacy rows are never presented as verified.
2. **Public site during the rebuild (owner decision).** `cae.joao.date` and `joao.date/dados` serve a
   placeholder page "Em manutenção" until the UI revamp (project 4). The current UI and its API response
   shapes are not preserved: no compatibility layer, no legacy-labelled pages. Rows with null
   value/unit are never served: quarantined with a reason, re-fetched where the source has them.
   "Done" = core set ingested, validated and queryable from the new store.
3. **Registry.** The builder proposes primary-source assignments; the owner reviews once. The pipeline
   proceeds on the provisional assignments. A non-Portuguese source may be primary when no Portuguese
   institution publishes the series (follows the "closest to origin" rule). ERSE is in scope if it
   falls under energy.
4. **Licences.** The registry records licence name, URL and attribution text per source, researched
   by the builder. Any source whose terms restrict redistribution is reported to the owner before
   being served. Displaying attribution is project 4.
5. **Operations.** f0nix has ~87 GB free; raw files are kept compressed for the core set with no
   retention limit for now. The builder verifies API keys (SOPS `web.enc.env`) and rate limits work
   from f0nix before the replay and throttles it. Fetch cadence follows each source's release calendar.
6. **Visibility until the backoffice exists.** Run log and events live in the DB; a CLI status report
   shows last-verified dates, failures and flags. Pushing alerts to Telegram follows the existing
   `[SILENT]`-unless-real-issue pattern and is added only after the owner agrees. `audit_nightly.py`
   is replaced by pipeline checks and deleted once superseded.
7. **AI.** All Claude/Anthropic code is removed. Existing AI features (interpretation, headlines,
   painel analysis) are switched off with the old UI; their replacement belongs to the derived layer.
8. **Cross-check thresholds.** Chosen per indicator type and tuned from measured disagreement;
   starting values are the builder's.
