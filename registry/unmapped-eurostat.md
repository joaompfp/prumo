# PROVISIONAL — owner review pending

# Eurostat series not active (active: false)

Generated during Task 9 (Eurostat adapter, review round 1). A Eurostat series is mapped to a dataset and a
full dimension key (`native_code`) only when the mapping is established by (a) the legacy collector code or the
legacy rows' own metadata (`source_id` / `detail`) and (b) agreement with the legacy values: at least 75% of the
series' legacy points equal the live Eurostat value within max(1% of the value, 3 units of its last decimal)
(the rest are publisher revisions since the legacy fetch, Feb-Apr 2026). Alternatives (other seasonal
adjustment, other bands/units) were checked and score far lower. Then: discontinued series and duplicates of
another active series are set inactive (sections below), so every active native_code is unique.
Nothing was guessed; units/ids/roles were not changed.

| | count |
|---|---|
| Eurostat series in registry | 697 |
| active | 328 |
| inactive: discontinued / rebased | 196 (195 rebased I15 + 1 frozen dataset, below) |
| inactive: duplicate of another active series | 18 |
| inactive: unit conflicts | 35 |
| inactive: dataset/filters not established | 120 |

## Unit conflicts

The registry unit contradicts what Eurostat publishes for the series the legacy values come from.

- **eurostat.gdp_per_capita_pps.DE, eurostat.gdp_per_capita_pps.ES, eurostat.gdp_per_capita_pps.EU27_2020, eurostat.gdp_per_capita_pps.FR, eurostat.gdp_per_capita_pps.PL, eurostat.gdp_per_capita_pps.PT** — legacy values are PPS per inhabitant (nama_10_pc CP_PPS_EU27_2020_HAB, e.g. DE 2000 = 23000), not an index EU27=100 (that is PC_EU27_2020_HAB_MPPS_CP).

- **eurostat.price_level_index.AT, eurostat.price_level_index.BE, eurostat.price_level_index.BG, eurostat.price_level_index.CY, eurostat.price_level_index.CZ, eurostat.price_level_index.DE, eurostat.price_level_index.DK, eurostat.price_level_index.EE, eurostat.price_level_index.ES, eurostat.price_level_index.EU27, eurostat.price_level_index.FI, eurostat.price_level_index.FR, eurostat.price_level_index.GR, eurostat.price_level_index.HR, eurostat.price_level_index.HU, eurostat.price_level_index.IE, eurostat.price_level_index.IT, eurostat.price_level_index.LT, eurostat.price_level_index.LU, eurostat.price_level_index.LV, eurostat.price_level_index.MT, eurostat.price_level_index.NL, eurostat.price_level_index.PL, eurostat.price_level_index.PT, eurostat.price_level_index.RO, eurostat.price_level_index.SE, eurostat.price_level_index.SI, eurostat.price_level_index.SK** — legacy values are prc_ppp_ind PLI_EU28 (GDP), i.e. EU28=100 (728/728 exact), not EU27=100 (PLI_EU27_2020: 0 exact).

- **eurostat.gdp_quarterly.EU27_2020** — series is nama_10_gdp CLV10_MEUR B1GQ (chain-linked volumes, reference year 2010, million euro; annual although the id says quarterly); the registry unit 'EUR million' reads as current prices.

## Dataset/filters not established

- **eurostat.labour_productivity_hour.AT, eurostat.labour_productivity_hour.BE, eurostat.labour_productivity_hour.BG, eurostat.labour_productivity_hour.CY, eurostat.labour_productivity_hour.CZ, eurostat.labour_productivity_hour.DE, eurostat.labour_productivity_hour.DK, eurostat.labour_productivity_hour.EE, eurostat.labour_productivity_hour.EL, eurostat.labour_productivity_hour.ES, eurostat.labour_productivity_hour.EU27_2020, eurostat.labour_productivity_hour.FI, eurostat.labour_productivity_hour.FR, eurostat.labour_productivity_hour.HR, eurostat.labour_productivity_hour.HU, eurostat.labour_productivity_hour.IE, eurostat.labour_productivity_hour.IT, eurostat.labour_productivity_hour.LT, eurostat.labour_productivity_hour.LU, eurostat.labour_productivity_hour.LV, eurostat.labour_productivity_hour.MT, eurostat.labour_productivity_hour.NL, eurostat.labour_productivity_hour.PL, eurostat.labour_productivity_hour.PT, eurostat.labour_productivity_hour.RO, eurostat.labour_productivity_hour.SE, eurostat.labour_productivity_hour.SI, eurostat.labour_productivity_hour.SK** — legacy code (scripts/backfill_full.py EUROSTAT_LABOUR_ANNUAL) defines labour_productivity_hour as NOMINAL labour productivity per hour (na_item NLPR, unit EUR_HW, 'EUR/hour'), which contradicts the registry unit I10_2010 and the legacy values (identical to the real series RLPR_HW I10, i.e. labour_productivity_hour_real); a nominal index NLPR_HW I10 is not published.

- **eurostat.unit_labour_cost.AT, eurostat.unit_labour_cost.BE, eurostat.unit_labour_cost.BG, eurostat.unit_labour_cost.CY, eurostat.unit_labour_cost.CZ, eurostat.unit_labour_cost.DE, eurostat.unit_labour_cost.DK, eurostat.unit_labour_cost.EE, eurostat.unit_labour_cost.EL, eurostat.unit_labour_cost.ES, eurostat.unit_labour_cost.EU27_2020, eurostat.unit_labour_cost.FI, eurostat.unit_labour_cost.FR, eurostat.unit_labour_cost.HR, eurostat.unit_labour_cost.HU, eurostat.unit_labour_cost.IE, eurostat.unit_labour_cost.IT, eurostat.unit_labour_cost.LT, eurostat.unit_labour_cost.LU, eurostat.unit_labour_cost.LV, eurostat.unit_labour_cost.MT, eurostat.unit_labour_cost.NL, eurostat.unit_labour_cost.PL, eurostat.unit_labour_cost.PT, eurostat.unit_labour_cost.RO, eurostat.unit_labour_cost.SE, eurostat.unit_labour_cost.SI, eurostat.unit_labour_cost.SK** — legacy code defines unit_labour_cost with na_item 'NULC' and unit I15 (neither per hour nor per person; 'NULC' is not a code of nama_10_lp_ulc) while unit_labour_cost_hour / _person are defined separately; its legacy values are identical to unit_labour_cost_hour (NULC_HW I10), so it is not an established separate series.

- **eurostat.employment_rate.AT, eurostat.employment_rate.BE, eurostat.employment_rate.BG, eurostat.employment_rate.CY, eurostat.employment_rate.CZ, eurostat.employment_rate.DE, eurostat.employment_rate.DK, eurostat.employment_rate.EE, eurostat.employment_rate.EL, eurostat.employment_rate.ES, eurostat.employment_rate.EU27_2020, eurostat.employment_rate.FI, eurostat.employment_rate.FR, eurostat.employment_rate.HR, eurostat.employment_rate.HU, eurostat.employment_rate.IE, eurostat.employment_rate.IT, eurostat.employment_rate.LT, eurostat.employment_rate.LU, eurostat.employment_rate.LV, eurostat.employment_rate.MT, eurostat.employment_rate.NL, eurostat.employment_rate.PL, eurostat.employment_rate.PT, eurostat.employment_rate.RO, eurostat.employment_rate.SE, eurostat.employment_rate.SI, eurostat.employment_rate.SK** — legacy collector (scripts/backfill_full.py) left indic_em unpinned; the legacy values are the ACTIVITY rate (lfsi_emp_a indic_em=ACT: 433/458 exact) not the employment rate (EMP_LFS: 0/458 within 1%). Mapping to EMP_LFS would serve a different series than the registry was built from; owner decision.

- **eurostat.current_account_pct_gdp.AT, eurostat.current_account_pct_gdp.BE, eurostat.current_account_pct_gdp.BG, eurostat.current_account_pct_gdp.CY, eurostat.current_account_pct_gdp.CZ, eurostat.current_account_pct_gdp.DE, eurostat.current_account_pct_gdp.DK, eurostat.current_account_pct_gdp.EE, eurostat.current_account_pct_gdp.EL, eurostat.current_account_pct_gdp.ES, eurostat.current_account_pct_gdp.FI, eurostat.current_account_pct_gdp.FR, eurostat.current_account_pct_gdp.HR, eurostat.current_account_pct_gdp.HU, eurostat.current_account_pct_gdp.IE, eurostat.current_account_pct_gdp.IT, eurostat.current_account_pct_gdp.LT, eurostat.current_account_pct_gdp.LU, eurostat.current_account_pct_gdp.LV, eurostat.current_account_pct_gdp.MT, eurostat.current_account_pct_gdp.NL, eurostat.current_account_pct_gdp.PL, eurostat.current_account_pct_gdp.PT, eurostat.current_account_pct_gdp.RO, eurostat.current_account_pct_gdp.SE, eurostat.current_account_pct_gdp.SI, eurostat.current_account_pct_gdp.SK** — no collector code produced these quarterly rows (scripts/backfill_full.py names tipsbp20, which is annual); best candidate bop_gdp6_q (Q, PC_GDP, NSA, CA, BAL, WRL_REST) agrees with only 290/621 legacy points within 1% (e.g. BG 2020-Q1 8.8 vs 4.5, MT 2020-Q2 14.2 vs 0.0): dataset/filters not established.

### Per series (best candidate fails the agreement test)

| series | candidate native_code | agreement | worst points |
|---|---|---|---|
| eurostat.STS_INPR_M_C.SK | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C,s_adj=SCA,unit=I21,geo=SK` | 114/200 | 2014-12 legacy 109.4 vs 106.3, 2018-09 legacy 107.4 vs 110.4 |
| eurostat.cci.HR | `ei_bsco_m:freq=M,indic=BS-CSMCI,s_adj=SA,unit=BAL,geo=HR` | 0/250 | 2025-04 legacy -14.1 vs -9.5, 2025-05 legacy -13.4 vs -9.1 |
| eurostat.cci.MT | `ei_bsco_m:freq=M,indic=BS-CSMCI,s_adj=SA,unit=BAL,geo=MT` | 181/280 | 2025-06 legacy 0.3 vs -0.7, 2003-01 legacy -7.8 vs -6.9 |
| eurostat.cci.PL | `ei_bsco_m:freq=M,indic=BS-CSMCI,s_adj=SA,unit=BAL,geo=PL` | 0/298 | 2022-06 legacy -13.1 vs -40.9, 2022-03 legacy -12.1 vs -37.7 |
| eurostat.consumer_confidence.HR | `ei_bsco_m:freq=M,indic=BS-CSMCI,s_adj=SA,unit=BAL,geo=HR` | 0/250 | 2025-04 legacy -14.1 vs -9.5, 2025-05 legacy -13.4 vs -9.1 |
| eurostat.consumer_confidence.MT | `ei_bsco_m:freq=M,indic=BS-CSMCI,s_adj=SA,unit=BAL,geo=MT` | 181/280 | 2025-06 legacy 0.3 vs -0.7, 2003-01 legacy -7.8 vs -6.9 |
| eurostat.consumer_confidence.PL | `ei_bsco_m:freq=M,indic=BS-CSMCI,s_adj=SA,unit=BAL,geo=PL` | 0/298 | 2022-06 legacy -13.1 vs -40.9, 2022-03 legacy -12.1 vs -37.7 |
| eurostat.electricity_price_household.EL | `nrg_pc_204:freq=S,siec=E7000,nrg_cons=KWH2500-4999,unit=KWH,tax=I_TAX,currency=EUR,geo=EL` | 0/3 | 2024-S1 legacy 0.2434 vs 0.2218, 2024-S2 legacy 0.2493 vs 0.2311 |
| eurostat.electricity_price_household.EU27_2020 | `nrg_pc_204:freq=S,siec=E7000,nrg_cons=KWH2500-4999,unit=KWH,tax=I_TAX,currency=EUR,geo=EU27_2020` | 0/3 | 2025-S1 legacy 0.2934 vs 0.2879, 2024-S2 legacy 0.2941 vs 0.2887 |

## Discontinued / rebased (last value year)

Rule (mechanical, from a live fetch of every active series on 2026-11-11): the series' last period with a
value is before 2024. All 195 are base-2015 indices (unit I15) of sts_inpr_m / sts_copr_m, which Eurostat
stopped updating when it rebased short-term statistics to 2021=100 (I21). They are not refetched; their
history stays in the legacy import and the raw store. The successor column is the same key with unit=I21
and the registry series that holds it, if any (`—` = none in the registry; the I21 key's newest period is
shown, or 'no values' when Eurostat publishes no I21 data for that geo).

| series | last value year | dataset | successor key (I21) | successor in registry | I21 newest |
|---|---|---|---|---|---|
| eurostat.construction_index.AT | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=AT` | — | 2026-08 |
| eurostat.construction_index.BE | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=BE` | — | 2026-09 |
| eurostat.construction_index.BG | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.construction_index.CZ | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.construction_index.DE | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=DE` | — | 2026-09 |
| eurostat.construction_index.DK | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=DK` | — | 2026-08 |
| eurostat.construction_index.ES | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=ES` | — | 2026-08 |
| eurostat.construction_output.AT | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=AT` | — | 2026-08 |
| eurostat.construction_output.BE | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=BE` | — | 2026-09 |
| eurostat.construction_output.BG | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.construction_output.CZ | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.construction_output.DE | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=DE` | — | 2026-09 |
| eurostat.construction_output.DK | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=DK` | — | 2026-08 |
| eurostat.construction_output.ES | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=ES` | — | 2026-08 |
| eurostat.construction_output.EU27_2020 | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=EU27_2020` | — | 2026-08 |
| eurostat.construction_output.FI | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=FI` | — | 2026-08 |
| eurostat.construction_output.FR | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=FR` | — | 2026-09 |
| eurostat.construction_output.HR | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=HR` | — | 2026-08 |
| eurostat.construction_output.HU | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.construction_output.IT | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=IT` | — | 2026-08 |
| eurostat.construction_output.LU | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=LU` | — | 2026-08 |
| eurostat.construction_output.NL | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.construction_output.PL | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.construction_output.RO | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.construction_output.SE | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=SE` | — | 2026-08 |
| eurostat.construction_output.SI | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=SI` | — | 2026-08 |
| eurostat.construction_output.SK | 2023 | sts_copr_m | `sts_copr_m:freq=M,indic_bt=PRD,nace_r2=F,s_adj=SCA,unit=I21,geo=SK` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.AT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=AT` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_chemicals_pharma.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=CZ` | eurostat.STS_INPR_M_C20C21.CZ | 2026-09 |
| eurostat.ipi_chemicals_pharma.DE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=DE` | eurostat.STS_INPR_M_C20C21.DE | 2026-09 |
| eurostat.ipi_chemicals_pharma.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_chemicals_pharma.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_chemicals_pharma.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.ES | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=ES` | — | 2026-09 |
| eurostat.ipi_chemicals_pharma.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=EU27_2020` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.FR | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=FR` | — | 2026-09 |
| eurostat.ipi_chemicals_pharma.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.IE | 2009 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=IE` | — | 2009-12 |
| eurostat.ipi_chemicals_pharma.IT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=IT` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.LT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=LT` | — | 2025-12 |
| eurostat.ipi_chemicals_pharma.LV | 2013 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=LV` | — | 2013-12 |
| eurostat.ipi_chemicals_pharma.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_chemicals_pharma.PT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=PT` | eurostat.STS_INPR_M_C20C21.PT | 2026-09 |
| eurostat.ipi_chemicals_pharma.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_chemicals_pharma.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C20_C21,s_adj=SCA,unit=I21,geo=SE` | — | 2024-08 |
| eurostat.ipi_electronics.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_electronics.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_electronics.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.ipi_electronics.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_electronics.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_electronics.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_electronics.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_electronics.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_electronics.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_electronics.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_electronics.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_electronics.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C26_C27,s_adj=SCA,unit=I21,geo=SE` | — | 2026-08 |
| eurostat.ipi_food_beverage.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_food_beverage.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_food_beverage.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_food_beverage.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_food_beverage.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_food_beverage.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_food_beverage.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_food_beverage.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_food_beverage.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_food_beverage.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_food_beverage.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C10-C12,s_adj=SCA,unit=I21,geo=SE` | — | 2024-08 |
| eurostat.ipi_machinery.AT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=AT` | — | 2026-08 |
| eurostat.ipi_machinery.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_machinery.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_machinery.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.ipi_machinery.DE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=DE` | — | 2026-09 |
| eurostat.ipi_machinery.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_machinery.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_machinery.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_machinery.ES | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=ES` | — | 2026-09 |
| eurostat.ipi_machinery.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=EU27_2020` | — | 2026-08 |
| eurostat.ipi_machinery.FI | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=FI` | — | 2026-08 |
| eurostat.ipi_machinery.FR | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=FR` | — | 2026-09 |
| eurostat.ipi_machinery.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_machinery.IE | 2009 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=IE` | — | 2009-12 |
| eurostat.ipi_machinery.IT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=IT` | — | 2026-08 |
| eurostat.ipi_machinery.LT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=LT` | — | 2026-09 |
| eurostat.ipi_machinery.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_machinery.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_machinery.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_machinery.PT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=PT` | eurostat.machinery.PT | 2026-09 |
| eurostat.ipi_machinery.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_machinery.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C28,s_adj=SCA,unit=I21,geo=SE` | — | 2026-08 |
| eurostat.ipi_manufacturing.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C,s_adj=SCA,unit=I21,geo=EU27_2020` | eurostat.STS_INPR_M_C.EU27 | 2026-08 |
| eurostat.ipi_metals.AT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=AT` | — | 2026-08 |
| eurostat.ipi_metals.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_metals.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_metals.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.ipi_metals.DE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=DE` | — | 2026-09 |
| eurostat.ipi_metals.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_metals.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_metals.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_metals.ES | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=ES` | — | 2026-09 |
| eurostat.ipi_metals.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=EU27_2020` | — | 2026-08 |
| eurostat.ipi_metals.FI | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=FI` | — | 2026-08 |
| eurostat.ipi_metals.FR | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=FR` | — | 2026-09 |
| eurostat.ipi_metals.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_metals.IE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=IE` | — | 2026-09 |
| eurostat.ipi_metals.IT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=IT` | — | 2026-08 |
| eurostat.ipi_metals.LT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=LT` | — | 2025-12 |
| eurostat.ipi_metals.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_metals.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_metals.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_metals.PT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=PT` | eurostat.metals.PT | 2026-08 |
| eurostat.ipi_metals.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_metals.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C24_C25,s_adj=SCA,unit=I21,geo=SE` | — | 2026-08 |
| eurostat.ipi_nonmetallic.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_nonmetallic.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_nonmetallic.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.ipi_nonmetallic.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_nonmetallic.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_nonmetallic.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_nonmetallic.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=EU27_2020` | — | 2026-08 |
| eurostat.ipi_nonmetallic.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_nonmetallic.IT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=IT` | — | 2026-08 |
| eurostat.ipi_nonmetallic.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_nonmetallic.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_nonmetallic.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_nonmetallic.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_nonmetallic.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C23,s_adj=SCA,unit=I21,geo=SE` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.AT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=AT` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.DE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=DE` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_rubber_plastics.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.ES | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=ES` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=EU27_2020` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.FR | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=FR` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.IE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=IE` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.IT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=IT` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.LT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=LT` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_rubber_plastics.PT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=PT` | eurostat.rubber_plastics.PT | 2026-09 |
| eurostat.ipi_rubber_plastics.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_rubber_plastics.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C22,s_adj=SCA,unit=I21,geo=SE` | — | 2026-08 |
| eurostat.ipi_textiles.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_textiles.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_textiles.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.ipi_textiles.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_textiles.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_textiles.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_textiles.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_textiles.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_textiles.PL | 2022 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=PL` | — | 2022-08 |
| eurostat.ipi_textiles.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_textiles.SE | 2004 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C13-C15,s_adj=SCA,unit=I21,geo=SE` | — | 2004-12 |
| eurostat.ipi_total.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=B-D,s_adj=SCA,unit=I21,geo=EU27_2020` | eurostat.ipi_total.EU27 | 2026-08 |
| eurostat.ipi_transport_eq.AT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=AT` | — | 2026-08 |
| eurostat.ipi_transport_eq.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_transport_eq.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_transport_eq.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=CZ` | eurostat.STS_INPR_M_C29C30.CZ | 2026-09 |
| eurostat.ipi_transport_eq.DE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=DE` | eurostat.STS_INPR_M_C29C30.DE | 2026-09 |
| eurostat.ipi_transport_eq.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_transport_eq.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_transport_eq.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_transport_eq.ES | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=ES` | eurostat.STS_INPR_M_C29C30.ES | 2026-09 |
| eurostat.ipi_transport_eq.EU27_2020 | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=EU27_2020` | eurostat.STS_INPR_M_C29C30.EU27 | 2026-08 |
| eurostat.ipi_transport_eq.FR | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=FR` | eurostat.STS_INPR_M_C29C30.FR | 2026-09 |
| eurostat.ipi_transport_eq.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=HU` | eurostat.STS_INPR_M_C29C30.HU | 2026-08 |
| eurostat.ipi_transport_eq.IE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=IE` | — | 2026-09 |
| eurostat.ipi_transport_eq.IT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=IT` | — | 2026-08 |
| eurostat.ipi_transport_eq.LT | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=LT` | — | 2025-12 |
| eurostat.ipi_transport_eq.LV | 2013 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_transport_eq.NL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=NL` | — | 2026-08 |
| eurostat.ipi_transport_eq.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=PL` | eurostat.STS_INPR_M_C29C30.PL | 2026-09 |
| eurostat.ipi_transport_eq.PT | 2022 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=PT` | eurostat.transport_eq.PT | 2026-09 |
| eurostat.ipi_transport_eq.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_transport_eq.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C29_C30,s_adj=SCA,unit=I21,geo=SE` | — | 2024-08 |
| eurostat.ipi_wood_paper.BE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=BE` | — | 2026-08 |
| eurostat.ipi_wood_paper.BG | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=BG` | — | 2026-09 |
| eurostat.ipi_wood_paper.CZ | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=CZ` | — | 2026-09 |
| eurostat.ipi_wood_paper.DK | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=DK` | — | 2026-09 |
| eurostat.ipi_wood_paper.EE | 2020 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=EE` | — | no values |
| eurostat.ipi_wood_paper.EL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=EL` | — | 2026-08 |
| eurostat.ipi_wood_paper.HU | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=HU` | — | 2026-08 |
| eurostat.ipi_wood_paper.LV | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=LV` | — | 2026-09 |
| eurostat.ipi_wood_paper.PL | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=PL` | — | 2026-09 |
| eurostat.ipi_wood_paper.RO | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=RO` | — | 2026-08 |
| eurostat.ipi_wood_paper.SE | 2023 | sts_inpr_m | `sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C16-C18,s_adj=SCA,unit=I21,geo=SE` | — | 2026-06 |

### Frozen dataset: prc_hicp_midx (Task 22, final review C-I1)

| series | native_code | last period | dataset updated |
|---|---|---|---|
| eurostat.hicp.EU27_2020 | `prc_hicp_midx:freq=M,unit=I15,coicop=CP00,geo=EU27_2020` | 2025-12 | 2026-02-06 |

Evidence (live GETs, 2026-11-14):
- `GET https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_midx?geo=EU27_2020&coicop=CP00&unit=<U>&lastTimePeriod=2`
  for U = I15, I05, I96: newest periods `2025-11`, `2025-12` for every unit (I96 has no values),
  `updated` = `2026-02-06T23:00:00+0100`. I15 values 133.63 / 133.83.
- Eurostat table of contents (`/api/dissemination/catalogue/toc/txt?lang=en`): `prc_hicp_midx` is now titled
  "HICP - monthly data (index) (1996-2025)", filed under the folder "Harmonised index of consumer prices (HICP) -
  ECOICOP ver.1", data end `2025-12`, last update 06.02.2026. The whole ECOICOP ver.1 family
  (`prc_hicp_manr`, `prc_hicp_mmor`, `prc_hicp_mv12r`, `prc_hicp_aind`, `prc_hicp_fp`, ...) carries the same
  "(…-2025)" titles and 2025-12 ends.
- The same TOC lists the other 9 datasets behind active Eurostat series with 2026 updates and current data ends
  (ei_bsco_m 2026-10, une_rt_m 2026-10, sts_inpr_m 2026-09, namq_10_gdp 2026-Q3, nrg_pc_204 2026-S1,
  annual tables 2025), so prc_hicp_midx is the only frozen one.

The series stays in the registry (inactive, definition unchanged); its fetched and legacy history is kept.

**OWNER DECISION: successor mapping (not made here; nothing invented).** Candidates seen live, not mapped:
- `prc_hicp_minr` — "HICP - ECOICOP ver.2 - indices and rates of change, monthly data", data to 2026-10,
  updated 2026-11-04. Dimensions `freq, unit, coicop18, geo, time`; units `I25` (Index, 2025=100), `I15`
  (Index, 2015=100), `RCH_M`, `RCH_A`, `RCH_MV12MAVR`; all-items code `coicop18=TOTAL`. Its `I15`/`TOTAL`/
  `EU27_2020` values for 2025-11 / 2025-12 (133.63 / 133.83) equal the frozen series, but the classification
  (ECOICOP ver.2) and the dimension name differ, so it is a NEW series id, not a relabel.
- `prc_hicp_fpd` (first released data, ECOICOP ver.2, to 2026-10) and `prc_hicp_ainr` (annual).
- Or an INE/BdP source for the EU aggregate, per the "closest to origin" rule (part C review declined to judge).

## Duplicates (same Eurostat series as an active series)

Exactly one active series per native_code. Kept: the id whose legacy collector code defines that exact key
(collectors/eurostat.py, scripts/collectors/collect_stale_data.py) or, between equals, the registry primary /
the family covering the most geographies. See the report's duplicate-group table.

| inactive series | duplicate of |
|---|---|
| eurostat.STS_INPR_M_BD.PT | eurostat.ipi.PT |
| eurostat.STS_INPR_M_C.PT | eurostat.manufacturing.PT |
| eurostat.STS_INPR_M_C20C21.PT | eurostat.chemicals_pharma.PT |
| eurostat.consumer_confidence.BG | eurostat.cci.BG |
| eurostat.consumer_confidence.CY | eurostat.cci.CY |
| eurostat.consumer_confidence.LT | eurostat.cci.LT |
| eurostat.consumer_confidence.LU | eurostat.cci.LU |
| eurostat.consumer_confidence.RO | eurostat.cci.RO |
| eurostat.hicp.EU27 | eurostat.hicp.EU27_2020 |
| eurostat.ipi_manufacturing.EU27 | eurostat.STS_INPR_M_C.EU27 |
| eurostat.labour_productivity_per_hour.DE | eurostat.labour_productivity_hour_real.DE |
| eurostat.labour_productivity_per_hour.ES | eurostat.labour_productivity_hour_real.ES |
| eurostat.labour_productivity_per_hour.EU27_2020 | eurostat.labour_productivity_hour_real.EU27_2020 |
| eurostat.labour_productivity_per_hour.FR | eurostat.labour_productivity_hour_real.FR |
| eurostat.labour_productivity_per_hour.PL | eurostat.labour_productivity_hour_real.PL |
| eurostat.labour_productivity_per_hour.PT | eurostat.labour_productivity_hour_real.PT |
| eurostat.total_industry.PT | eurostat.ipi.PT |
| eurostat.transport_eq.PT | eurostat.STS_INPR_M_C29C30.PT |

## Note on electricity_price_household

The legacy table mixed two Eurostat series under this name: 902 rows from
`scripts/collectors/collect_electricity_prices.py` (nrg_pc_204 band DC `KWH2500-4999`, 884 exact) and 84 rows
(2023-S1..2025-S1, source_id `nrg_pc_204`) from `collectors/eurostat.py::get_electricity_prices`, which used
`nrg_cons=TOT_KWH` (75/84 exact against TOT_KWH, 0/84 against DC). The active series are mapped to band DC
(the bulk of their history); `.EL` and `.EU27_2020` hold only the TOT_KWH rows, so they fail the agreement test
and stay inactive (their DC history is in `.GR` / `.EU27`, which are mapped to geo EL / EU27_2020).

## Registry geography vs Eurostat geo code

Legacy geographies `EU27` and `GR` are mapped to Eurostat `EU27_2020` and `EL` (by value agreement); the
`geography` field itself was not changed.
