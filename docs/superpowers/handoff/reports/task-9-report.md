# Task 9 report — Eurostat adapter + independent verifier

Status: DONE. Commits on `pipeline-rebuild`: 38848e6 (flags), f467b5d (registry mapping),
bb778dc (adapter + fixtures), 3ad6e49 (verifier + guard fix), b72315c (live test), plus this report.
Tests: `pytest tests/ingest -q` → 481 passed, 1 deselected (the live test).

## What was built (signatures)

- `ingest/flags.py` (shared by all adapters)
  - `FLAGS = ('normal','provisional','estimated','revised','break')` (weakest → strongest)
  - `PRECEDENCE = ('break','provisional','estimated','revised','normal')`
  - `EUROSTAT_VALUE_FLAGS: dict[str,str]`, `EUROSTAT_NO_VALUE_MARKERS = {':','c','z'}`
  - `map_eurostat_flag(code: str | None, *, value_present: bool = True) -> str | None`
    — returns a FLAGS member when a value is present ('normal' for None/blank), None when
    `value_present=False` (after checking every code is known); unknown code → ValueError;
    a no-value marker on a value → ValueError.
- `ingest/sources/eurostat.py`
  - `BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"`
  - `parse_native_code(code: str | None) -> tuple[str, tuple[tuple[str, str], ...]]`
  - `class EurostatSource: name = 'eurostat'; expected_format = 'json'`
    - `fetch(specs, http) -> Iterator[RawResponse]` — one GET per (dataset, non-geo key) group,
      params = pinned dims + `geo=[...]` (repeated), no time filter (full history).
    - `parse(specs, responses) -> dict[str, list[RawRow]]` — `response_index` = group index.
- `ingest/verifiers/eurostat.py`
  - `SDMX_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"`
  - `class EurostatVerifier: source_name = 'eurostat'; check(items: list[BlindItem], http) -> list[ItemResult]`
  - Imports only `csv`, `io`, `ingest.http.{Http, HttpResult}`, `ingest.verifiers.{BlindItem, ItemResult}`.
  - Registration is the caller's job (`register_verifier` is not in the verifier allowlist) → Task 17 CLI must call `register_verifier(EurostatVerifier())`.
- `ingest/verifiers/independence.py`: one-line fix — the verifier module itself is no longer
  reported as a "non-shared ingest module" (every real verifier lives in `ingest/verifiers/`, so
  the guard failed the first real adapter). RED test `test_verifier_inside_the_ingest_package_passes`
  + a control test that a second ingest module is still rejected.
- Tests: `tests/ingest/test_flags.py` (46), `test_source_eurostat.py` (36), `test_verifier_eurostat.py`
  (16), `test_live_eurostat.py` (1, `@pytest.mark.live`), helpers `eurostat_fixtures.py`
  (`FixtureHttp` serves recorded bodies by exact URL) and `eurostat_verifier_entry.py` (subprocess
  entry). Fixtures `tests/ingest/fixtures/eurostat/` (all ≤ 55 KB; MANIFEST.json lists series + URLs):
  monthly `sts_inpr_m` (with 'i' flags), annual `nama_10_pc` (p and b flags), quarterly
  `namq_10_gdp`, semester `nrg_pc_204`, each as JSON-stat + SDMX TSV; real error bodies
  (404 JSON error object, 404 "Not Found" text, SDMX XML fault) + the 413 async error object
  observed live this session.
- `pytest.ini`: marker `live` registered; addopts `-m "not live"` (CLI `-m live` overrides).

## native_code format (registry contract for Eurostat)

`<dataset>:<dim>=<code>,<dim>=<code>,...` — every dimension except `time` pinned to exactly one
code, in the dataset's own order (JSON-stat `id` order = SDMX key order), `geo` included, e.g.
`une_rt_m:freq=M,s_adj=SA,age=TOTAL,unit=PC_ACT,sex=T,geo=PT`. One native_code = one Eurostat
series; the source turns it into query params, the verifier into the SDMX key `M.SA.TOTAL.PC_ACT.T.PT`.
`url` = `https://ec.europa.eu/eurostat/databrowser/view/<dataset>/default/table?lang=en`.

## Registry: 697 Eurostat series → 598 active, 99 inactive after round 0 (round 1 below: 329 active)

Mapping rule: dataset + filters taken from the legacy collector code (collectors/eurostat.py,
scripts/backfill_*.py, scripts/collectors/*.py) or the legacy rows' own `source_id`/`detail`, AND
confirmed against the live API: ≥ 75% of the series' legacy points equal the live value within
max(1%, 3 units of the last decimal); the rest are revisions since Feb–Apr 2026. Alternatives
(CA/NSA, other bands, other units) were scored and are far lower (e.g. IPI SCA 5307/5540 vs CA 565).
Legacy geographies `EU27`/`GR` map to Eurostat `EU27_2020`/`EL` (geography field unchanged).
- 35 unit conflicts: `gdp_per_capita_pps` ×6 (values are PPS/inhabitant, registry says index
  EU27=100), `price_level_index` ×28 (values are PLI_EU28 = EU28=100, registry says EU27=100),
  `gdp_quarterly.EU27_2020` (CLV10_MEUR chain-linked volumes, annual; registry 'EUR million').
- 64 not established: `current_account_pct_gdp` ×27 (no collector code for the quarterly rows;
  best candidate agrees 47%), `employment_rate` ×28 (legacy collector left `indic_em` unpinned: the
  data is the ACTIVITY rate, 433/458 exact — owner decision whether to map to EMP_LFS),
  per-series failures: cci/consumer_confidence HR, PL, MT (×6; HR/PL legacy values unrelated to
  today's series), `STS_INPR_M_C.SK` (57%), `electricity_price_household.EL/.EU27_2020` (their
  legacy rows are band TOT_KWH, not DC — see the electricity note in unmapped-eurostat.md).
Unit pairings of the active set (label ↔ code): I15/I21/index_2021/'Index (2015=100)'/index_2015 ↔
I15/I21; balance, 'balance %' ↔ BAL; EUR/kWh ↔ KWH + currency=EUR; 'EUR per capita' ↔ CP_EUR_HAB;
'% GDP' ↔ PC_GDP; '%' ↔ PC_ACT; M_EUR_2010 ↔ CLV10_MEUR; I10_2010/index_2010=100 ↔ I10;
'index 2020=100' ↔ I20.
Note: native_codes are hand-curated now; re-running `ingest/propose_registry.py` would drop them.

## Flag mapping (Eurostat → shared vocabulary)

| code | meaning | flag |
|---|---|---|
| (none) | — | normal |
| b | break in time series | break |
| d | definition differs | break |
| p | provisional | provisional |
| e | estimated | estimated |
| s | Eurostat estimate (pre-2023) | estimated |
| f | forecast | estimated |
| u | low reliability | estimated |
| n | not significant | estimated |
| i | value imputed by Eurostat (label from the payload's `extension.status.label`) | estimated |
| r | revised (pre-2023) | revised |
| `:` c z | not available / confidential / not applicable | only on missing values → row value None (quarantined non_numeric); on a value → ValueError |
| anything else | — | ValueError (dataset fails validation) |

Combined codes → strongest by PRECEDENCE (break > provisional > estimated > revised > normal).

## TDD evidence
- flags: RED = collection error (ModuleNotFoundError ingest.flags); GREEN 45 → 46 after adding 'i'.
- source: RED = collection error with `ingest/sources/eurostat.py` moved aside; GREEN 36 passed.
  (The first version was 62 s because YAML loading was uncached; now ~2.6 s.)
- verifier: RED = collection error with the module moved aside; first GREEN attempt 7 failures
  (fixture router too strict for sampled geo subsets, wrong column name in test, token context)
  then 1 failure that was a real guard bug (verifier module counted as non-shared) → RED test in
  test_independence.py → fix → 16 + 10 passed.

## Live test (run once, f3nix, 2026-11-11)
```
pytest tests/ingest/test_live_eurostat.py -m live -s
final state: verified  run_id=1  written=474  quarantined=0
verification of run 1: sample 50, passed=True, mismatches=0
  eurostat.STS_INPR_M_C.PT: 321 observations 2000-01..2026-09
  eurostat.gdp_quarterly.EU27: 127 observations 1995-Q1..2026-Q3
  eurostat.gov_debt_pct_gdp.EU27_2020: 26 observations 2000..2025
1 passed in 7.27s
```
Verified on the first attempt (no refetch), sample 50, 0 mismatches.

## Independence evidence
- Channel: collector = Statistics API 1.0 JSON-stat (query params, flattened cube); verifier =
  SDMX 2.1 REST data API, `format=TSV` (dotted key with '+', one row per series, value and flags
  in one cell). Different endpoint, query language, format and parser.
- `register_verifier` static allowlist passes (`test_verifier_registers_and_passes_allowlist`);
  no shared ingest module with the parser (the parser's `ingest.flags` is not imported).
- `assert_verifier_independent("ingest.verifiers.eurostat", "tests.ingest.eurostat_verifier_entry:run",
  source_name="eurostat", blocked_prefixes=("collectors", "ingest.flags"))` passes: the verifier
  runs on blinded items with `ingest.sources.*` AND `ingest.flags` blocked and asserts 7 values/flags.
- Deliberate duplication (commented): native_code parsing and the flag table exist in both modules;
  divergence fails verification loudly rather than both sides sharing a mistake.
- Tamper tests through the real pipeline: changed value → `value differs`, removed 'p' → `flag differs`;
  both runs end `failed-verification`, nothing served.

## Decisions that matter for adapters 10–16 (concerns)
1. Every fetched observation carries a FLAGS member, `'normal'` stored explicitly (so the verifier
   compares a flag on every item). Adapters 10–16 should do the same.
2. Vocabulary is closed (5 values) and lossy: d→break, u/n/f/i/s→estimated. Owner may want
   "low reliability"/"forecast" kept separately later.
3. `unit_raw` is None and `observed_unit` is None for Eurostat: the unit is a code pinned in the key;
   the label↔code pairing was checked once at mapping time. Reviewers asked for units "read from
   evidence" (Ruling O note) — here the evidence only proves the cell is in the pinned unit code.
4. Requests split per (dataset, non-geo key) rather than one per dataset: a whole dataset query
   hits Eurostat's HTTP 413 "ASYNCHRONOUS_RESPONSE" (observed live).
5. Cells with a status but no value become value-None rows → quarantined `non_numeric`; this records
   withheld values but adds quarantine noise (e.g. confidential cells).
6. Guard fix in `independence.py` (verifier module exempt from the non-shared check) — small change
   to Task 7 code, test-covered.
7. Verifier fetches full history per group (no period bounds) so evidence is one stable document;
   larger evidence files for long monthly series (~25 KB for 4 geos).
8. GitNexus impact tools were not available in this session (no MCP); the only edit to existing
   code is the one-line guard change above (callers: adapter tests only).

## Fix round 1 (review: C1, I1, I2, I3, M1, M3, M5, M6)

Commits: b06aee6 (C1), c5f5e39 (I1+I2), 9f277bf (I3), 3e201ca (M1/M3/M5/M6), plus this report.

### C1 — confidentiality status (Ruling X)
Real payloads carry `'|C'` (confidential) and `'|N'` (not for publication). `ingest/flags.py` now has
`EUROSTAT_CONFIDENTIALITY = {'C': 'confidential', 'N': 'not for publication'}` and
`split_eurostat_status(status) -> (flags, confidentiality | None)`: the status is split on `|`; a reviewed
confidentiality code makes the cell value None (quarantined `non_numeric`, one per cell) and its flag part is
ignored (still checked to be known); an unknown confidentiality code raises. The verifier mirrors it
(duplicated on purpose): the TSV renders the cell as `': @C'` → `observed_text=None`. Such a cell is never
sampled (sampling draws only from written observations) — `test_confidential_cells_are_never_sampled` runs
the real pipeline on the fixture (62 quarantined, every written observation verified).
New real fixtures: `confidential_c_sts_inpr_m` (STS_INPR_M_C.IE, 60 `|C` cells) and
`confidential_n_sts_inpr_m` (metals.PT C24_C25 I21, 2 `|N` cells).

Probe (`probe_full.py` logic without the monkeypatch, live, all 598 then-active series, 33 requests):
- before: `PARSE RAISES: unknown Eurostat flag code(s) ['C', '|'] in '|C'`
- after: `empty series: 0`, `rejections: non_numeric 964`, `flags: normal 82871, estimated 21988,
  provisional 6156, break 142`; 195 series with last value before 2025 (sts_inpr_m/I15 168, sts_copr_m/I15 27)
- after round 1 (329 active, 20 requests, live): `empty series: 0`, `non_numeric 62`, `flags: normal 42142,
  estimated 1778, provisional 1461, break 110`, latest year 2025: 203 series, 2026: 126; none before 2025.

### I1 — discontinued (Ruling W)
Rule (mechanical, from the live fetch): an active series whose last period with a value is before 2024 is
discontinued. All 195 are base-2015 (I15) indices of sts_inpr_m (168) / sts_copr_m (27), superseded by
Eurostat's 2021=100 rebase. For each, the same key with `unit=I21` was fetched live: 180 have I21 values to
2026; 15 have no I21 values for that geo (listed as 'no values'); 16 have a successor series in the
registry. Last-value years: 2023 ×178, 2020 ×10, 2022 ×2, 2013 ×2, 2009 ×2, 2004 ×1. Section 'Discontinued /
rebased (last value year)' in registry/unmapped-eurostat.md. Nothing else deactivated on this ground.
(The reviewer's sibling condition "an active sibling with a newer base" holds for only 16 of the 195 because
the registry has few I21 series; I used Eurostat's own I21 key as the sibling and report the registry one.)

### I2 — duplicates: exactly one active series per native_code
Re-derived from the legacy code:
- `labour_productivity_hour` ×28 → inactive, not established: scripts/backfill_full.py defines it as NOMINAL
  (NLPR, EUR_HW, 'EUR/hour'), contradicting the registry unit I10_2010 and its own values (= real RLPR_HW I10).
- `unit_labour_cost` ×28 → inactive, not established: legacy code uses na_item 'NULC' + unit I15 (neither
  per hour nor per person), values identical to `unit_labour_cost_hour`.
- the others → `duplicate of <kept id>`; kept = the id whose legacy code defines that exact key
  (collect_stale_data.py / collectors/eurostat.py), else the primary / the family with most geos.

| kept family | inactive families | groups | Eurostat key |
|---|---|---|---|
| STS_INPR_M_C | ipi_manufacturing | 1 | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C,s_adj=SCA,unit=I21` |
| STS_INPR_M_C29C30 | transport_eq | 1 | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21` |
| cci | consumer_confidence | 5 | `ei_bsco_m:freq=M,indic=BS-CSMCI,s_adj=SA,unit=BAL` |
| chemicals_pharma | STS_INPR_M_C20C21 | 1 | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21` |
| hicp | hicp | 1 | `prc_hicp_midx:freq=M,unit=I15,coicop=CP00` |
| ipi | STS_INPR_M_BD, total_industry | 1 | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=B-D,s_adj=SCA,unit=I21` |
| labour_productivity_hour_real | labour_productivity_per_hour | 6 | `nama_10_lp_ulc:freq=A,unit=I10,na_item=RLPR_HW` |
| manufacturing | STS_INPR_M_C | 1 | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C,s_adj=SCA,unit=I21` |
| — | labour_productivity_hour | 28 | `nama_10_lp_ulc:freq=A,unit=I10,na_item=RLPR_HW` |
| — | unit_labour_cost | 28 | `nama_10_lp_ulc:freq=A,unit=I10,na_item=NULC_HW` |

`test_active_native_codes_are_unique` (RED on the pre-fix registry: 74 duplicate codes). No active
cross_check is the same Eurostat series as its primary (the remaining Eurostat cross_checks are cross-checks
of INE primaries).

### Counts now (697 Eurostat series)
active 329; inactive 368 = discontinued 195 + duplicate 18 + unit conflict 35 + not established 120
(current_account 27, employment_rate 28, labour_productivity_hour 28, unit_labour_cost 28, per-series 9).
Discontinued and duplicate series keep their native_code/url in the registry (for the record);
the others have none.

### I3 — unit label ↔ code
`tests/ingest/test_registry_eurostat_units.py`: reviewed table of 10 (unit code[, currency]) → allowed
labels; asserts every active series' code is paired with an allowed label, every label in use is in the
table and no code in the table is stale. A mislabel in a registry copy is caught
(`gdp_per_capita_eur.AT CP_EUR_HAB '% GDP'`). Finding for the owner (registry not edited): one code, several
labels — I21: 'I21' / 'index_2021'; I15: 'I15' / 'Index (2015=100)' / 'index_2015'; BAL: 'balance' /
'balance %'; I10: 'I10_2010' / 'index_2010=100'.

### Hardening
- M1: `independence.py` exempts only `ingest.verifiers.<x>` (not the package, not the guard): RED 3 failures
  (`ingest.flags`, `ingest.db`, `ingest.pipeline` passed as "verifier"), GREEN after `_own_module`.
- M3: JSON-stat `value`/`status` arrays must cover the cube (empty status array allowed), object keys must be
  flat indices inside it; 7 cases raise.
- M5: verifier TSV: two rows for one series key with different cells raise (identical copies tolerated).
- M6: `propose(..., force=False)` raises FileExistsError if `out_dir/core.yaml` contains `native_code:`.
  Note: propose's own output also contains native_code (legacy codes), so re-running it into the same
  directory now needs force=True.

### Live test (re-run, 2026-11-11)
```
final state: verified  run_id=1  written=474  quarantined=0
verification of run 1: sample 50, passed=True, mismatches=0
  eurostat.gdp_quarterly.EU27: 127 observations 1995-Q1..2026-Q3
  eurostat.gov_debt_pct_gdp.EU27_2020: 26 observations 2000..2025
  eurostat.manufacturing.PT: 321 observations 2000-01..2026-09
```
(live series switched from STS_INPR_M_C.PT, now a duplicate of manufacturing.PT — same Eurostat key.)

### Test run
```
.venv-ci/bin/python -m pytest tests/ingest -q
================= 525 passed, 1 deselected in 72.85s (0:01:12) =================
```
