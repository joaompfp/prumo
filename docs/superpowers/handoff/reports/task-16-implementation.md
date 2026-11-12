# Task 16 implementation report: native E-REDES national-production pipeline (PT15M)

Branch `pipeline-rebuild`, base 03639ee. Implementer: sole code implementer per
`task-16-brief.md`. Scope delivered: the national production dataset
`energia-produzida-total-nacional` with its three native fields (dgm/pre/total), native
quarter-hour UTC timestamps, an OpenDataSoft JSON collector with explicit windows, and an
independent same-portal `/exports/csv` verifier with a versioned offline-replayable evidence
envelope. dadosgov untouched (its code preserved; no live CKAN API exists — discovery §4).
No "April baseline" invented (discovery proved no stored E-REDES rows exist anywhere).

## Commits (all task-owned paths only; controller docs/discovery evidence untouched)

| commit | content |
|---|---|
| `ec62566` | feat(ingest): native PT15M frequency — `models.normalize_period` single canonical UTC spelling + NEW migration `0006_pt15m.sql` (series CHECK rebuild + observation triggers; served view re-created verbatim, licence gate intact) + `_migrate` FK toggle/FK-check; TDD |
| `a611a9a` | feat(registry): eredes source block + `eredes.production_{market,special,total}.PT` (PT15M, energy, PT, kWh, primary, keys `eredes_production_*.PT.PT15M`, native_code `<dataset>:<field>`, schedule 1d, throttle ≤1 rps) in core.yaml **and mirrored core.proposed.yaml**; genuine fixtures + MANIFEST; registry/metadata tests |
| `5a220e5` | feat(ingest): `EredesSource` adapter (`ingest/sources/eredes.py`) + `eredes_fixtures.py` + `test_source_eredes.py` |
| `5bd312d` | feat(ingest): `EredesVerifier` (`ingest/verifiers/eredes.py`, `eredes-csv-evidence` v1) + verifier fixtures/entry + `test_verifier_eredes.py` |

## Slice 1 — native-period contract (separate commit, per brief)

- `ingest/models.py`: `Frequency` gains `"PT15M"`; `normalize_period` accepts only
  `YYYY-MM-DDTHH:MM:SS+00:00` (ASCII digits, real Gregorian date/hour, minute 00/15/30/45,
  seconds 00), re-emits canonical (folded input uppercased 'T'). Everything else rejected
  ('Z', offsets, spaces, fractional seconds, non-dates, Arabic-Indic digits). A/S/Q/M/D
  behavior unchanged (existing suites pass).
- `ingest/migrations/0006_pt15m.sql`: rebuilds `series` with the extended CHECK and replaces
  both observation triggers with a PT15M arm (exact-length GLOB + strftime round-trip +
  explicit hour/minute/second bounds — strftime alone normalizes `24:00`). Applied migration
  files untouched; no writable_schema.
- `ingest/db.py::_migrate`: migrations now run with `PRAGMA foreign_keys` temporarily OFF
  outside the per-file transaction (a RENAME with FK ON silently rewrites child REFERENCES —
  empirically verified: child clause became `REFERENCES "series_v5"`), then
  `PRAGMA foreign_key_check` is asserted before FK is re-enabled. Failure mid-migration rolls
  back as before.
- Tests (`tests/ingest/test_migration_pt15m.py`, `test_models.py`): populated-0005 upgrade
  preserves observations (fetched + legacy), raw_fetch provenance, verification rows, settings;
  served view + licence gate intact (blocked source serves nothing, CC-BY source serves);
  FK enforcement verified post-rebuild; repeated open idempotent; bad spellings rejected on
  insert AND update triggers; A-series enforcement unchanged.

GitNexus (controller-refreshed index @ 03639ee): pre-existing brief analysis of
`normalize_period` accepted (CRITICAL), plus `open_db` LOW(0), `_migrate` LOW(1), `Frequency`
LOW(0), `SeriesSpec`/`Observation` HIGH(42 — registry/verification consumers; no structural
change, additive literal only). `detect-changes` run before each commit: slice-1 diff maps to
`normalize_period`/`_migrate` only (plus the known retired-JS false positives); slices 3/4 add
only new symbols (no existing-symbol impact).

## Slice 2 — genuine bounded fixtures (network budget respected)

Probe on 2026-11-12 from f3nix egress: **3 of 8 requests, 1.543 s of 60 s, 10 s timeout each,
0 retries**, each body ≤ 17 KB (cap 200 KB). Archived unmodified under
`tests/ingest/fixtures/eredes/` with `MANIFEST.json` (request URLs+params, final URLs, HTTP
200s, fetch timestamps, sha256 per body: metadata `396af188…`, window_json `5b5baba6…`,
window_csv `78bbea1b…`). Window: one complete UTC day, 2026-11-10 (96 records; total_count ==
results length — complete in one 100-record page, no truncation). The same window was fetched
on both channels; **all 288 value tokens are byte-identical** between JSON and CSV (recorded
in MANIFEST note). Discovery's probe-truncated catalog/CSV were NOT used as fixtures.

## Slice 3 — collector contract (source constructor, for T17)

`EredesSource(from_ts: str | None = None, to_ts: str | None = None, *, today: date | None = None)`

- Explicit mode: both bounds are canonical UTC **day starts** (`YYYY-MM-DDT00:00:00+00:00`),
  `from < to`; one page set per (dataset, UTC day). T17 catch-up `from 2026-04-01` works with
  no month dropping (one request per day, ~96 records each) and bounded memory (generator).
- Default mode (daily refresh): the last **3 complete UTC days** (today partial/never
  requested). Schedule from registry `1d`, portal throttle ≤1 rps via the shared Http client.
- No silent caps: windows are one day (96 ≤ 100/page); pagination asserts constant
  `total_count` across pages, contiguous offsets, `count == total_count`; a window denser
  than the 10000 offset cap raises instead of truncating at 100/10000.
- Every response is archived evidence (dataset metadata first, then pages; fetch yields as it
  goes), `RawRow.response_index` points at the records page; parse derives windows from the
  **validated original request params** (where/order_by/limit).
- Tokens: tagged JSON numbers only (quoted numbers rejected), exact publisher strings incl.
  `.0`/float tails; negative `dgm` is native and preserved; no flag surface → `flag_raw=None`;
  record key set exact; `dia/mes/ano/date/time` echo columns must equal `datahora`; strict
  ascending unique timestamps within the requested day; metadata asserted (dataset_id,
  datahora datetime, dgm/pre/total double + exact labels — the kWh unit evidence, CC BY 4.0 +
  licence URL, publisher E-REDES). Drift fails closed (format_change/failed-*), never guessed.

## Slice 4 — independent verifier

- Channel: same-portal OpenDataSoft **exports/csv** (`lang=pt&timezone=UTC&where=<day span>`)
  — different endpoint AND format from the collector; plus the dataset metadata response for
  the unit labels (`Market (kWh)` → observed_unit `kWh`).
- One CSV + one metadata response per check() call (cached); periods string-matched to the
  CSV's own canonical `datahora` tokens; missing row → `observed_text=None` (mismatch, not
  invention); header/echo/duplicate/containment/spelling drift fail closed; non-2xx raises;
  no status surface on either channel → `observed_flag=None` honestly.
- Evidence per item: versioned `eredes-csv-evidence` v1 JSON envelope (schema+version,
  `responses`: `[csv, metadata]` each with final URL, actual HTTP status, base64 body);
  `verify_run` stores it in the raw store; `replay_item` re-decides offline. No
  parser/helper import from the collector (constants duplicated on purpose); registration AST
  + `assert_verifier_independent` subprocess guard (entry
  `tests/ingest/eredes_verifier_entry:run`) both pass.

## Test evidence (actual commands run on this branch)

- `.venv-ci/bin/python -m pytest tests/ingest -q` (whole ingest area; `-x` + test_pipeline
  re-run separately): **1231 passed** (241 s + 11 s), including all 44 + 22 new E-REDES tests,
  the 102 PT15M/migration tests, and every existing source/verifier suite.
- `.venv-ci/bin/ruff check <all touched files>`: clean (E/F/W/I per ruff.toml; repo files are
  not `ruff format`-normalized — pre-existing style preserved).
- Full 4-min controller suite not re-run beyond this (budget); nothing outside `ingest/`,
  `registry/`, `tests/` was touched.

Named exact genuine samples asserted ≥5 across fields/times (e.g. market 2026-11-10T00:00Z
`925741.0`, special 00:15Z `523992.0`, total 06:30Z `1340285.0`, total 23:30Z `1551219.0`,
market 23:45Z `1097652.0`), quoted-number/noncanonical-date/duplicate/missing-page rejection,
HTML-200 on both channels, DST-adjacent canonical spellings (2026-03-29/2026-10-25, UTC
unaffected), registration+subprocess independence, tamper detection through `verify_run`
(value and unit-label), offline archive recovery + replay, a verified run served (288 rows,
CC BY 4.0, vs REN's licence-gated zero), and the `run_with_refetch` registered path.

## Integration notes for T17

- Instantiate `EredesSource()` for the daily default (last 3 complete UTC days ≈ 288 rows/series
  worst case) or `EredesSource(from_ts="2026-04-01T00:00:00+00:00", to_ts=...)` for catch-up —
  one metadata + one page-set per UTC day (~230 requests for April→November at 1 rps throttle).
- Register `EredesVerifier()` via `register_verifier` before `run_with_refetch`; keep
  verification sample `size` modest (one CSV request covers the whole sampled day span).
- The scheduler must pass each series' registry set together (one dataset, three series share
  every fetch — single request serves dgm/pre/total).
- Legacy collector `collectors/eredes.py` (OpenDataSoft 8-dataset client, structurally incapable
  of storing) is untouched, per "no old collector deletion"; scheduler migration is T17's.

## Known limits / controller gates

- Values are energy per 15-min interval in kWh per the publisher's own labels; no local
  summation of fields, no equating with REN transmission concepts.
- Only dataset `energia-produzida-total-nacional` reviewed/admitted; the other live national
  datasets (consumo, injetada) are explicit future scope, as are the four unverified legacy
  dataset IDs (discovery §3/§5).
- Task 16 acceptance stays controller-owned (independent spec review, quality review, live
  gate). Nothing merged/pushed/deployed; dadosgov preserved with no invented replacement.

Task 16 tracked status: **not marked closed by this implementer.**
