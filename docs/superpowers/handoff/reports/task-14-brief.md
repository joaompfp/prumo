# Task 14 - FRED implementation and independent verification brief

Base: pipeline-rebuild at 38aad8c, clean at intake. Owner explicitly authorized Task14 while Task13 World Bank fresh-network gate remains OPEN. Do not work on Task13, main, deployment or scheduler. Controller baseline: `.venv-ci/bin/python -m pytest tests -q` -> 929 passed, 5 live deselected, 1 warning, 162.96s.

## Authority and scope

Task14 in the approved base-data-pipeline plan: FRED source adapter, genuinely independent verifier, original fixtures <=200KB each, exact publisher value tokens, flag/error/tamper/registration/subprocess-independence tests and live full-registry acceptance. Design spec6b requires exact Decimal matches and stored evidence, including units/metadata. All SQL remains in Db/migrations. No shared parser/verifier helpers. Implementers own code, tests and task report, not shared handoff/ledger. Controller handles independent spec review, separate quality review, fixes and final gates. Truthful commits only; obsolete Claude trailers are not required.

Read local AGENTS.md, prumo-data-pipeline skill, relevant contracts and tests before editing. New source boundaries come first; do not widen core interfaces without approval. Current GitNexus worktree alias prumo-pipeline was refreshed at38aad8c. impact import_legacy LOW/0 direct; legacy_geography LOW/2 direct,4 total (proposal flow). Neither needs modification for this task. New modules have no pre-existing callers. Run detect-changes before every scoped commit.

## Original evidence, already collected (no further network during implementation)

Directory `/home/joao/.hermes/cache/scratch/prumo-t14-preflight/`:
- manifest.json: exact original API metadata, full API observations, fredgraph CSV and series pages, timestamps, HTTP statuses, hashes, secret-free URLs. All54responses200.
- api-meta-<CODE>.body, api-full-<CODE>.body, csv-<CODE>.body, html-<CODE>.body.
- table-manifest.json and table-<CODE>.body: original server-rendered `https://fred.stlouisfed.org/data/<CODE>` HTML. Each about94KB, all12responses200.
- table-comparison.json: all12series independently parsed by controller: each417 numeric API values exactly equals417 HTML table values;144 '.' API missing cells preceding1992. API metadata's range1992-01..2026-09 is nonmissing range; observation endpoint starts1980 with144missings. Preserve '.' as missing/non_numeric quarantine, never fill or truncate them.
- summary.json: metadata and whole-history CSV mismatch diagnostic. CSV is REJECTED as verifier: nonzero exact Decimal differences on10/12series (examples70.51 vs70.51000000000001). No tolerance or rounding. A genuine independent HTML table channel DOES work; use that channel instead. Not a cosmetic API encoding switch.
- alternative-manifest.json includes explicit current-vintage API and table .txt redirects. `/data/CODE.txt` now returns same HTML, NOT a plain text file.
- f0nix-probes.json: production-egress API metadata and CSV both HTTP200 using owner's existing legacy key. No secret persisted on f0nix, no auth failure. API and CSV also healthy locally. Controller will perform post-implementation fresh full pipeline through production egress.
- registry-discovery.md: read-only discovery; controller independently confirmed all6 twin joins. Its count '13 IMF' is wrong: there are12 distinct IMF codes plusEIA/BLS. Do not copy this error.
- fred-terms.body: authentic FRED API terms, third-party rights not granted. IMF terms unavailable; do NOT claim permission. FRED remains redistribution_ok=false. No emails/requests to data owner.

All artifacts must remain exact publisher bytes. Copy relevant originals to tests/ingest/fixtures/fred/ and status/timestamp/hash manifest; durable evidence for blocked steel/gas and licensing can live under reports/evidence/task-14-fred/. Never archive .fred_api_key, no invented statuses, never rebuild publisher originals from parsed data. Explain redaction of api_key from public URL records. Keep each fixture <=200KB. Do not copy controller scratch scripts as production code.

## Registry disposition (binding for this task)

All20old FRED entries are currently active, unitUSD. Preserve registry ids, indicator_keys, roles and geography, except explicit active/native metadata below. No derived values, new concepts or new series.

Active12 unique IMF globals (same concepts, precise publisher units; copy exact unit labels from original metadata and HTML):
- fred.aluminum.WORLD -> PALUMUSDM, U.S. Dollars per Metric Ton
- fred.brent_oil.WORLD -> POILBREUSDM, U.S. Dollars per Barrel
- fred.coffee.WORLD -> PCOFFOTMUSDM, U.S. Cents per Pound
- fred.copper.WORLD -> PCOPPUSDM, U.S. Dollars per Metric Ton
- fred.corn.WORLD -> PMAIZMTUSDM, U.S. Dollars per Metric Ton
- fred.cotton.WORLD -> PCOTTINDUSDM, U.S. Cents per Pound
- fred.wheat.WORLD -> PWHEAMTUSDM, U.S. Dollars per Metric Ton
- fred.commodity_iron_ore.WORLD -> PIORECRUSDM, U.S. Dollars per Metric Ton
- fred.commodity_nickel.WORLD -> PNICKUSDM, U.S. Dollars per Metric Ton
- fred.commodity_soybean.WORLD -> PSOYBUSDM, U.S. Dollars per Metric Ton
- fred.commodity_sugar.WORLD -> PSUGAISAUSDM, U.S. Cents per Pound
- fred.commodity_zinc.WORLD -> PZINCUSDM, U.S. Dollars per Metric Ton
All M, decimal '.', multiplier null, base_year null, seasonal_adjustment NSA, geographyWORLD, canonical series URL. This is metadata correction for fresh publisher data, NOT permission to convert or relabel legacy values. Old bareUSD legacy rows for corrected entries must be rejected by existing unit_mismatch validation; test this safeguard rather than changing importer or attaching new units to old rows.

Inactive8, preserve their original conceptual definitions and metadata fields unless an exact established native code is being documented:
- fred.iron_ore.WORLD, fred.nickel.WORLD, fred.soybean.WORLD, fred.sugar.WORLD, fred.zinc.WORLD: exact same-source twins of existing commodity_* PRIMARY (133/277/277/179/277 identical legacy periods respectively), not independent cross-checks. Fill the missing primary code; retain primary roles. Mark coded crosschecks inactive, no primary swap.
- fred.commodity_steel.WORLD: exact313-period subset duplicate ofWPU101, additionally wrong USD/WORLD price concept. Keep inactive and explain.
- fred.steel.WORLD: WPU101 is US BLS Index1982=100, not WORLD steel price inUSD. Inactivate, no substitution or conversion.
- fred.natural_gas.WORLD: MHHNGSP is US HenryHub USD perMillionBTU, not a global benchmark matching currentWORLD definition. Inactivate, no new US indicator in this task.
Make active fields explicit for all20. Explain each inactive entry in registry/unmapped-fred.md and preserve original API/page evidence forWPU101/MHHNGSP. Legacy commodity_cotton orphan is0.01x coded cotton; keep not-in-registry, never map it to PCOTTINDUSDM. Do not regenerate registry or touch other sources.

Source licence: accurate restricted/permission-unconfirmed FRED/IMF terms and attribution for active IMF set; redistribution_ok=false, verifiable=true. API accessibility is not redistribution consent. Public-domain EIA/BLS facts can be documented but do not clear the IMF source. Keep registry/licences-todo.md accurate.

## Collector contract (Part A)

Create ingest/sources/fred.py, tests/ingest/test_source_fred.py and fixture helpers as needed. Class FredSource.name='fred', constructor api_key explicit or envFRED_API_KEY, fail clearly when missing. DO NOT read legacy .fred_api_key inside production module; controller supplies it only for tests/live. No credential in repr/logs/raw URL/params/events or committed fixtures. api_key only in the outgoing request. FRED requires key in query. Remove secret from returned final URLs and params; sanitize raised network/API errors without exposing underlying request URL or response excerpts. Reject a response containing the credential before yielding, rather than modifying original body. Add secret-sentinel regression tests for success URLs, failures and persisted pipeline artifacts. Do not change core HTTP contract to do this.

GET api.stlouisfed.org/fred/series (metadata) and /series/observations (JSON observations) per unique series, using limit100000, unitslin, output_type1, sort/order native; do not aggregate frequency or transform values. Follow declared pagination ifcount/limit requires, checking offsets/completeness/duplicate dates/realtime identity; no cross-series drift. fetch must yield RawResponses incrementally so partial evidence is retained on later failure. parse uses archived response URL/params identity plus required metadata, no external HTTP/DB. Metadata must assert id, actual unit/frequency/NSA against spec; reject unknown shape/status/value primitive, duplicated keys/dates, invalid month-first dates, unknown extra observation status fields, and period/identity drift. Publisher value is a JSON STRING here, unlike REN/WorldBank JSON numbers: preserve actual string token byte content, '.' ->None; never float conversion. Missingcells quarantine downstream. status_flag normal with honest declaration that no per-observation status surface exists; unknown non-empty fields failclosed. RawRow.response_index must refer to the observation response, while metadata responses also remain archived. Keep last_updated as metadata, not fabricated per-observation release dates.

Part A ends after collector/registry/fixtures tests and scoped commits. Do not implement verifier in parallel. Full verification gates come after Part B.

## Independent verifier contract (Part B)

Create ingest/verifiers/fred.py class FredVerifier.source_name='fred'. GET public server-rendered https://fred.stlouisfed.org/data/<CODE>, once per unique series/check() call. Different endpoint family, transport (HTML vs API JSON) and independent HTMLParser; no source module/helper imports. Avoid regex matching unrelated page numbers. Parse the metadata table (Series ID, Title, Source, Release, Seasonal Adjustment, Frequency, Units, DateRange...) and the data-table-observations table. Validate unique identity/unit/M/NSA and valid month-first dates, duplicate row/period/table metadata rejection, complete declared range, unknown shapes/columns, missing value marker. Read full token from the cells, no rounding. HTML table contains exact full-precision tokens, not the rounded5-digit series landing-page display. ItemResult identity required, observed_unit actual metadata, observed_flag=None because the table has no per-observation status. Evidence envelope fred-table-evidence v1 (or similarly explicit) with exact complete HTML bytes, final URL and actual HTTP status; one response contains both values and metadata, offline recoverable. No metadata API in verifier, no expected values visible.

Tests: >=5 named exact observations crosschecked against original HTML and API; malformed/HTML error pages for collector and wrong table errors for verifier; status-surface failclosed; metadata/dimension/date/duplicate/type/truncation guards; normalregistration and assert_verifier_independent subprocess running real fixture checks; genuine tamper mismatch through verify_run or run_with_refetch; one failed-verification must stayunserved, priorverified history unaffected; normal full12 recorded pipeline with null quarantines + licencefalse/served0 + stored evidence replay/offline full bodies/units. Mutation fixtures must be labeled as tests, never genuine evidence. Create live test, deselected by default, using all12active registry series and bounded retries/sample. Registered verifier only; do not mutate private registry in accepted controller run. Live/final gates belong to controller.

## Acceptance/reports

Use .venv-ci/bin/python / .venv-ci/bin/ruff; never DuckDB. Scratchisolated DBs under /home/joao/.hermes/cache/scratch. TDD RED/GREEN, scoped atomic commits, no staging unrelated paths. Report actual test output/remaining blockers, changedpaths/commits, fixture origins and rejected CSV evidence. No fake Claude authorship. Do not mark wholeTask14complete before independent specPASS, separate qualityAPPROVED and controllerfresh full12live/evidence/regression gates. Source remains legally withheld, not technically unverifiable. T17 registers FredVerifier and handles FRED_API_KEY provisioning; Task18 productionSOPS key needs configuration, not assumed from localfile. No deploy/mainmerge/push by child. No Task15 in this dispatch.
