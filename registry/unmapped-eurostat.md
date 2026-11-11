# PROVISIONAL — owner review pending

# Eurostat series not mapped (active: false)

Generated during Task 9 (Eurostat adapter). Every Eurostat series in `core.yaml` was mapped to a dataset and a
full dimension key (`native_code`) only when the mapping is established by (a) the legacy collector code or the
legacy rows' own metadata (`source_id` / `detail`) and (b) agreement with the legacy values: at least 75% of the
series' legacy points equal the live Eurostat value within max(1% of the value, 3 units of its last decimal)
(the rest are publisher revisions since the legacy fetch, Feb-Apr 2026). Alternatives (other seasonal
adjustment, other bands/units) were checked and score far lower. Series failing either test are `active: false`
and listed here. Nothing was guessed; units/ids/roles were not changed.

| | count |
|---|---|
| Eurostat series in registry | 697 |
| active (mapped) | 598 |
| inactive: unit conflicts | 35 |
| inactive: dataset/filters not established | 64 |

## Unit conflicts

The registry unit contradicts what Eurostat publishes for the series the legacy values come from.

- **eurostat.gdp_per_capita_pps.DE, eurostat.gdp_per_capita_pps.ES, eurostat.gdp_per_capita_pps.EU27_2020, eurostat.gdp_per_capita_pps.FR, eurostat.gdp_per_capita_pps.PL, eurostat.gdp_per_capita_pps.PT** — legacy values are PPS per inhabitant (nama_10_pc CP_PPS_EU27_2020_HAB, e.g. DE 2000 = 23000), not an index EU27=100 (that is PC_EU27_2020_HAB_MPPS_CP).

- **eurostat.price_level_index.AT, eurostat.price_level_index.BE, eurostat.price_level_index.BG, eurostat.price_level_index.CY, eurostat.price_level_index.CZ, eurostat.price_level_index.DE, eurostat.price_level_index.DK, eurostat.price_level_index.EE, eurostat.price_level_index.ES, eurostat.price_level_index.EU27, eurostat.price_level_index.FI, eurostat.price_level_index.FR, eurostat.price_level_index.GR, eurostat.price_level_index.HR, eurostat.price_level_index.HU, eurostat.price_level_index.IE, eurostat.price_level_index.IT, eurostat.price_level_index.LT, eurostat.price_level_index.LU, eurostat.price_level_index.LV, eurostat.price_level_index.MT, eurostat.price_level_index.NL, eurostat.price_level_index.PL, eurostat.price_level_index.PT, eurostat.price_level_index.RO, eurostat.price_level_index.SE, eurostat.price_level_index.SI, eurostat.price_level_index.SK** — legacy values are prc_ppp_ind PLI_EU28 (GDP), i.e. EU28=100 (728/728 exact), not EU27=100 (PLI_EU27_2020: 0 exact).

- **eurostat.gdp_quarterly.EU27_2020** — series is nama_10_gdp CLV10_MEUR B1GQ (chain-linked volumes, reference year 2010, million euro; annual although the id says quarterly); the registry unit 'EUR million' reads as current prices.

## Dataset/filters not established

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
