# PROVISIONAL — owner review pending

# INE series: mapping notes and series not active (active: false)

Generated during Task 10 (INE adapter). An INE series is mapped to an indicator (`varcd`) and a full
dimension key (`native_code` = `<varcd>:Dim2=<code>,Dim3=<code>,...`, every dimension except the period
pinned; format in `ingest/sources/ine.py`) only when the mapping is established by (a) the legacy collector
code (`collectors/ine.py`, `scripts/collectors/cae-v4-backfill.py`, `scripts/collectors/collect_stale_data.py`,
`scripts/backfill_missing.py`) or the legacy rows' own metadata (`source_id`, `detail`) and (b) agreement
with the legacy values fetched live on 2026-11-11 (≥ 95% for every active series; the rest are INE
revisions since the legacy fetch or the rebasing rounding noted below). Units, ids and roles not changed.
Discontinued check (last value before 2024): none — every active series has values in 2025-2026.

| | count |
|---|---|
| INE series in registry (38 legacy + 4 added by Ruling Y) | 42 |
| active | 41 |
| inactive | 1 |

## Not active

| series | reason |
|---|---|
| `ine.ipi_seasonal_cae.PT` | unit conflict + duplicate: registry unit `%`, but the legacy values (13 rows, 'Indústrias transformadoras', varcd 0011889) are the base-2021 index of CAE section C, i.e. the same INE series as active `ine.ipi_seasonal_cae_C.PT` (`0011889:Dim2=PT,Dim3=C`). |

## Mapping notes for active series (owner review)

| series | native_code | note |
|---|---|---|
| `ine.hicp_yoy.PT` | `0014655:Dim2=PT,Dim3=T` | legacy varcd 0000110 (HICP y/y, base 2015) NO LONGER EXISTS ("O código do indicador não existe"). Successor = INE's base-2025 HICP y/y by COICOP, total. 305/312 legacy months equal; the 7 others differ by exactly 0.1 pp (rebasing rounding: 2000-05, 2003-11, 2005-05, 2009-04, 2015-05, 2021-08, 2023-01). |
| `ine.ipc_yoy.PT`, `ine.ipc_yoy.Continente` | `0014647:Dim2=PT,Dim3=T`, `0014647:Dim2=1,Dim3=T` | legacy varcd 0002386 (CPI y/y, base 2012) NO LONGER EXISTS. Successor = base-2025 CPI y/y by geography and COICOP, total; Dim2 `1` = Continente. 13/13 legacy months equal for each (legacy rows region 'Portugal'/'Continente'). History back to 1949-01. |
| `ine.exports_monthly.PT`, `ine.imports_monthly.PT` | `0001400:Dim2=MUNDO,Dim3=T`, `0001397:Dim2=MUNDO,Dim3=T` | Dim2 = destination/origin `MUNDO` (world), Dim3 = all goods (CGCE `T`), as in the legacy backfill scripts. LEGACY DATA PROBLEM: legacy rows 2005-01..2024-12 hold MILLION euro (3844.565243) under unit `EUR`; 2025 rows hold euro. INE publishes euro (`Euro (€)`, 3844565243). After scaling, 240/252 equal (the rest are 2025 revisions). Task 10 fix round 1 (finding I3) quarantines those 480 legacy rows as `suspect_unit_scale` in `ingest/legacy_import.py` (never rescaled, never served); live fetches carry euro. |
| `ine.ipi_yoy_cae.PT` | `0011897:Dim2=PT,Dim3=C` | legacy `get_ipi_yoy()` default `cae="manufacturing"` → Dim3=C. 229/240 equal. |
| `ine.conf_manufacturing.PT` | `0001188:Dim2=PT` | 312/312 equal. INE unit `Percentagem (%)` (balance of extreme answers). |
| `ine.ipi_seasonal_cae_<X>.PT` (31) | `0011889:Dim2=PT,Dim3=<X>` | `<X>` from the legacy indicator name / detail `sector`. ≥95% equal each (all but recent months; INE revises seasonally adjusted figures every month). FINDING: `_35` ≡ `_D` and `_38` ≡ `_E` in all 261 months (in INE's IPI, section D contains only division 35 and section E only division 38): distinct INE cells, so both kept active; the owner may want one of each pair. |
| `ine.unemployment_monthly.PT` (new, Ruling Y) | `0007983:Dim2=PT,Dim3=T` | Taxa de desemprego (ajustada de sazonalidade, %), 16-74, sexo HM, monthly from 1998-02. The latest month carries INE's sign `&` "Dado provisório" (→ provisional). `indicator_key unemployment_rate.PT.M`: INE primary, `oecd.unemp_m.PT` now cross_check (overlaps.md). |
| `ine.population.PT` (new) | `0006031:Dim2=PT,Dim3=T,Dim4=T,Dim5=T` | População residente (N.º), annual estimates (reference 31 December), PT, HM, all ages, all birthplaces; 2008-2025. Chosen over the NUTS-2024 series (from 2021 only) and NUTS-2013 (to 2023). Key source-qualified: World Bank `population` is a different concept (mid-year), not merged. |
| `ine.live_births.PT` (new) | `0001346:Dim2=PT,Dim3=T` | Nados-vivos (N.º), HM, mother's residence Portugal; 1970-2025. |
| `ine.deaths.PT` (new) | `0005605:Dim2=PT,Dim3=T,Dim4=T` | Óbitos (N.º), residence Portugal (Dim2 also has `T` = total incl. abroad/unknown; `PT` chosen), HM, all ages; 1995-2025. Chosen over the NUTS-2024 series (from 2021 only). |

Ruling Y candidates left out: none of the requested three was unclear. Unemployment by INE quarterly
(0010704, 2011-Q1..2024-Q4, stopped) not added.
