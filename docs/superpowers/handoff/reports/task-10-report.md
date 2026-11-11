# Task 10 report — INE adapter (verifier STOPPED: no independent channel)

Status: DONE_WITH_CONCERNS. Adapter, flags mapping, registry, fixtures and tests done; the verifier part
was STOPPED per the brief/spec §6b because INE exposes a single machine-readable data channel. INE series
are collected but NOT SERVED until the owner decides (registry/unverifiable.md).
Commits on `pipeline-rebuild`: 02205b5 (period labels + flags), e42b8d6 (registry), 445dad4 (adapter +
fixtures + tests), 22148da (live test), + this report.
Tests: `pytest tests/ingest -q` → 604 passed, 2 deselected (the two live tests).

## Key finding — INE has ONE machine-readable data channel
Probed live 2026-11-11 (f3nix, UA `prumo-ingest/1.0`, ≤1 req/s):
| channel | result |
|---|---|
| `json_indicador/pindica.jsp?op=2` | the data API (collector) |
| `pindica.jsp?op=1` | latest value repeated for every period (0001188: '-5.2' for every month 1990..2026) — unusable |
| `pindicaMeta.jsp` | metadata only |
| `xml_indic.jsp?opc=1/2/3` | catalogue (metadata + links to the same JSON API) |
| INE API v2 doc page | lists exactly three APIs: Catalog, Database, Metadata |
| HVD DCAT-AP catalogue `catalogo_hvd_json.jsp` | all 50 distributions = the same `pindica.jsp?op=2` |
| indicator page `xurl/indx/<varcd>` → `bddXplorer04.jsp` (the "indicator page export" in the plan) | browser-only app; plain HTTP client gets an empty body; not pursued (would need browser emulation) |
| short-term indicators / HVD statistics | Power BI embeds |
| web search | no public INE SDMX/CSV bulk endpoint |
Eurostat republishes some INE-produced series (HICP, IPI, demography) — a cross-check of the same
publisher's figures, not independence (brief), so not built. → `registry/unverifiable.md` (options a/b/c
for the owner); no `ingest/verifiers/ine.py`; `get_verifier('ine')` raises, `run_with_refetch` refuses INE,
`run_dataset` runs end `pending-verification`, `served_observation` stays empty (tested).
Not built because of the STOP: test_verifier_detects_tampered_value, test_verifier_registers_and_passes_allowlist,
test_subprocess_independence (assert_verifier_independent) — they need a verifier.

## Licence (redistribution_ok 0 → 1)
INE "Terms and conditions of use" — https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_cont_inst&INST=3585857
(read 2026-11-11): "The statistical data made available on this website is free of charge and can be used
and reused by the users in accordance with the Creative Commons CC BY Attribuition 4.0 license provided that
the source is acknowledged, as follows: Source: Instituto Nacional de Estatística – Portugal (Statistics
Portugal) (identification of the statistical information mentioned; reference period of the information)"
… "Should the user modify the original data, it must be explicitly mentioned." (The HVD pages also state
CC BY 4.0.) Registry `ine`: licence `CC BY 4.0`, that URL, attribution `Source: Instituto Nacional de
Estatística – Portugal (Statistics Portugal)`, `redistribution_ok: true`; licences-todo.md updated. The old
URL (`ine_condicoes_utilizacao`) still answers "em manutenção". Note: `ingest/propose_registry.py` still
has INE as UNVERIFIED in code (propose must not be re-run over core.yaml anyway).

## What was built
- `ingest/flags.py`: `INE_VALUE_SIGNS = {'&': ('provisional','Dado provisório')}`,
  `INE_NO_VALUE_SIGNS = {'x': 'Dado não disponível', '-': 'Dado nulo ou não aplicável'}`,
  `map_ine_flag(sign, description, *, value_present=True) -> str | None` — sign must come with its exact
  reviewed description; value sign without value, no-value sign on a value, missing value without sign,
  unknown sign → ValueError.
- `ingest/models.py::normalize_period`: quarterly regex now accepts INE's '1.º Trimestre de 2011'
  (live label of 0010704; was rejected). Only widens accepted input (callers: validate, legacy import).
- `ingest/sources/ine.py`: `BASE_URL`, `PAGE_URL`, `parse_native_code(code) -> (varcd, (("Dim2",c),...))`,
  `INESource(name='ine', expected_format='json')`; `fetch` = one GET per (varcd, dim names) group:
  `op=2&varcd=..&lang=PT&Dim1=T&DimN=<sorted comma-joined codes>`; `parse` → rows keyed by series id,
  `response_index` = group index, period label as-is, value = INE `valor` token (JSON string), flag via
  map_ine_flag, `unit_raw` None. Raises on: markup, non-JSON, not a 1-record list, `Sucesso` without
  `Verdadeiro`/with `Falso`, other `IndicadorCod`, duplicate JSON keys (period labels), duplicate cells,
  cell dimensions ≠ native_code dims, `UltimoPref` missing from `Dados` (truncation guard), bare JSON
  numbers where strings are expected, `valor` vs `ind_string` disagreement, unknown signs.
- native_code format: `<7-digit varcd>:Dim2=<code>,Dim3=<code>,...` — every dimension but Dim1 (period)
  pinned, in order, no gaps; payload field of Dim2 is `geocod`, DimN is `dim_N`. url =
  `https://www.ine.pt/xurl/indx/<varcd>`.
- Tests: `test_flags.py` (+11 INE), `test_models.py` (+5 labels), `test_source_ine.py` (55: fixture rows,
  label normalisation, status flags, no-value cells, tokens, response_index, fetch params, native_code
  parse/reject, `test_registry_native_codes_complete`, `test_active_native_codes_are_unique`, 23 malformed
  payloads, duplicate keys, `test_parse_html_error_page_raises` (real INE HTML error), real INE error
  objects (unknown varcd, bad Dim code), pipeline run on fixtures → pending-verification + 0 served,
  `test_ine_is_unverifiable_and_not_served`), `test_registry_ine_units.py` (3), `test_live_ine.py` (live).
- Fixtures `tests/ingest/fixtures/ine/` (8 real sets ≤145 KB + 3 real error bodies, MANIFEST.json).

## Decisions (documented in docstrings) — concerns for adapters 11–16 / T17-18
1. Token = `valor` ('.' decimal), not `ind_string` (published rendering, ',' decimal, spaces, sign
   appended). `valor` DROPS TRAILING ZEROS ('2' for published '2,0'; '2.4' for '2,40'). Using
   `ind_string` would require `decimal: ','` and would re-quarantine the whole legacy INE import (legacy
   values are '.'), so `ind_string` is only a consistency check. Owner may want the published precision.
2. INE is slow: 17–45 s per request; trade (0001397/0001400, Dim1=T) 170–236 s. The full INE scope
   takes ~10 min. The T17/T18 RequestsHttp for INE needs `timeout` ≥ 300 s (default 30 s would fail every
   INE run); the registry has no per-source timeout field (smallest choice: none added; flagged).
3. One request per varcd group with comma-joined codes (INE validates every code: one bad code fails the
   whole request with 'Código(s) em Dim2 não válido(s)' — fails loudly, no partial data).
4. INE series are collected but not served (no verifier). T17 status will show INE runs as stale
   `pending-verification`; it should cite registry/unverifiable.md.
5. Registry: series kept `active: true` (collected for revision history) although not served; an owner
   who prefers not to collect at all should set them inactive.

## Registry (registry/core.yaml + core.proposed.yaml, identical bodies)
38 legacy INE series → 37 active + 1 inactive; + 4 new (Ruling Y) → 42 INE series, 41 active, unique
native codes. Details and per-series notes in `registry/unmapped-ine.md`. Highlights:
- legacy HICP 0000110 and CPI 0002386 NO LONGER EXIST → base-2025 successors 0014655 / 0014647
  (HICP 305/312 legacy months equal, 7 differ by 0.1 pp rebasing rounding; CPI PT and Continente 13/13).
- `ine.ipi_seasonal_cae.PT` inactive: unit '%' but values are the CAE-C index (= `ine.ipi_seasonal_cae_C.PT`).
- trade: LEGACY DATA PROBLEM — legacy rows 2005–2024 are MILLION EUR under unit 'EUR' (2025 rows EUR);
  INE publishes EUR; 240/252 equal after scaling. Task 8 imported them as EUR (legacy-unverified).
- IPI ≥95% equal each (rest = recent revisions); `_35` ≡ `_D` and `_38` ≡ `_E` in all 261 months
  (INE's D/E contain only those divisions) — both kept (distinct INE cells); owner may drop one per pair.
- Ruling Y: `ine.unemployment_monthly.PT` (`0007983:Dim2=PT,Dim3=T`, SA, 16–74, '%') is now primary of
  `unemployment_rate.PT.M`; `oecd.unemp_m.PT` → cross_check (overlaps.md row: 336 common months, 186
  equal, max gap 3.45% flagged — OECD 15–74/older vintage). Demography (theme demography, unit 'N.º' =
  INE 'Número (N.º)', source-qualified keys): `ine.population.PT` (`0006031:Dim2=PT,Dim3=T,Dim4=T,Dim5=T`,
  31 Dec estimates 2008–2025), `ine.live_births.PT` (`0001346:Dim2=PT,Dim3=T`, 1970–2025),
  `ine.deaths.PT` (`0005605:Dim2=PT,Dim3=T,Dim4=T`, 1995–2025). Nothing requested was left out.
- Unit labels ↔ INE `UnidadeMedida`: '%' ↔ Percentagem (%); 'EUR' ↔ Euro (€); 'index_2021=100' ↔
  Não aplicável (-) + "Base 2021" in the name; 'N.º' ↔ Número (N.º).

## Full-scope live probe (all 41 active + candidates, via INESource + RequestsHttp, 2026-11-11)
11 requests, ~10 min. All HTTP 200; parse raised nothing; validate:
- series with no data: 0; exceptions: 0
- flags: normal 12030, provisional 1 (`&` on unemployment 2026-09)
- signs observed: `&` 'Dado provisório' (with value), `x` 'Dado não disponível' (no value; 9 cells in
  our series: latest IPI months of divisions 08,10,14,24,25,26×2,31,32), `-` 'Dado nulo ou não aplicável'
  (HICP COICOP sub-indices, not in our series). No other sign in 0014655/0014647 full cubes (~1.1M cells).
- quarantine: non_numeric 9 (the `x` cells), nothing else
- period labels: monthly '<Mês> de AAAA' (all 12 month names), annual 'AAAA'; quarterly
  '<n>.º Trimestre de AAAA' only in 0010704 (not registered) — normalize_period fixed for it
- timings: 0001188 30 s, 0001346 4 s, 0001397 170 s, 0001400 236 s, 0005605 3 s, 0006031 2 s,
  0007983 23 s, 0011889 (31 codes, 1.7 MB) 18 s, 0011897 15 s, 0014647 75 s, 0014655 25 s.

## Fixtures hand-checked via a third channel (Eurostat SDMX 2.1 SDMX-CSV, 2026-11-11)
demo_gind A.LBIRTH.PT 2024 = 84642 ✓; A.DEATH.PT 2024 = 118396 ✓; A.JAN.PT 2025 = 11387222 = INE 2024 ✓;
prc_hicp_manr M.RCH_A.CP00.PT 2025-10 = 2.0 (INE valor '2', ind_string '2,0') ✓, 2025-12 = 2.4 ✓;
sts_inpr_m M.PRD.C.SCA.I21.PT 2026-09 = 96.6 (INE 96.57, Eurostat rounds) ✓. (HICP 2023-01: Eurostat
8.6 vs INE base-2025 8.7 — the rebasing difference noted above.) Unemployment, confidence and trade have
no third channel with the same definition: fixture-only.

## Live test (run once, f3nix, 2026-11-11)
```
pytest tests/ingest/test_live_ine.py -m live -s
final state: pending-verification  run_id=1  written=1139  quarantined=0  served=0
  ine.conf_manufacturing.PT: 478 observations 1987-01..2026-10 (provisional: 0)
  ine.ipi_seasonal_cae_C.PT: 261 observations 2005-01..2026-09 (provisional: 0)
  ine.live_births.PT: 56 observations 1970..2025 (provisional: 0)
  ine.unemployment_monthly.PT: 344 observations 1998-02..2026-09 (provisional: 1)
1 passed in 85.95s
```

## TDD evidence
- periods: RED 2 failed ('1.º Trimestre de 2011', '4.º Trimestre de 2024') → GREEN 71.
- flags: RED collection error (no map_ine_flag) → GREEN 76.
- adapter: first run 53/54 — a bare JSON number as `valor` was accepted → `_JsonNumber` marker → 55/55.
- GitNexus MCP tools were not available in this session; edits to existing code: normalize_period regex
  (widening), flags.py (append-only).
