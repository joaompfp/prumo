# Task 22 report: final-review part C fixes (C-I1, C-I2, C-I3, C-M6, C-M7, C-M8, C-M9)

Branch `pipeline-rebuild`, base a57d818. Commits:

| commit | scope |
|---|---|
| e6ad1c7 | C-M6: loader rejects active series sharing a native_code within a source |
| e69de45 | C-I1: read-only `python -m ingest lag` data-time check (`ingest/data_lag.py`) |
| 9bfe630 | C-I1: `eurostat.hicp.EU27_2020` inactive, evidence in `registry/unmapped-eurostat.md` |
| dd66ed7 | C-I2: one geography code / one unit label per unit code, legacy-import safe |
| 183c93f | C-I3: `seasonal_adjustment` from Eurostat `s_adj` pins and INE indicator names |
| 7c5c9d8 | docs: regenerated `docs/data/sources.md`; `lag` paragraph in `docs/data/operations.md` |

Nothing was pushed or deployed. f0nix and the production DB were not touched. AGENTS.md and
CLAUDE.md were left unstaged, as found. `registry/core.proposed.yaml` mirrors every
`core.yaml` change, because tests pin the two files as equal (see M7).

## What changed

### C-M6: unique active native_code per source
- `ingest/registry.py:_validate` raises `ValueError("active series share a native_code within a
  source: ...")` when two active series of one source pin the same code. Inactive pairs and
  cross-source equality are allowed.
- Tests: `test_registry_rejects_two_active_series_with_one_native_code` (RED, then GREEN) and
  `test_registry_allows_shared_native_code_when_inactive_or_cross_source`.
- Side effect found by the suite: `propose_registry` copied each legacy collector code into
  `native_code`. Those codes are often dataset-level (e.g. `ei_bsco_m` shared by 25 series), so a
  fresh proposal from the real export no longer loaded. The proposer now drops a code that several
  proposed series of one source share, because such a code names a dataset, not a series. Only the
  never-rerun proposer output changes. `test_real_export_proposal_and_import` passes again, with
  its 246,162-row total unchanged.

### C-I1: frozen HICP, plus a wider staleness rule
**Deactivation.** `eurostat.hicp.EU27_2020` is now `active: false`, with its definition unchanged.
Live evidence from 2026-11-14:
- `prc_hicp_midx` ends at 2025-12 for the I15, I05 and I96 units, `updated` 2026-02-06.
- The Eurostat TOC now titles it "HICP - monthly data (index) (1996-2025)" under
  "HICP - ECOICOP ver.1". The whole ver.1 family ends at 2025-12.
- The TOC entries for the other 9 datasets behind active Eurostat series all have 2026 updates and
  current data ends.

The evidence is recorded under "Frozen dataset: prc_hicp_midx" in `registry/unmapped-eurostat.md`.
That section also lists the successor candidates as an OWNER DECISION; none were mapped. One
candidate is `prc_hicp_minr` (ECOICOP ver.2, to 2026-10). It has units I25 and I15, and its
`I15`/`TOTAL` 2025-11 and 2025-12 values equal the frozen series. The classification and the
dimension (`coicop18`) differ, so it would be a new series id. Counts are now 328 active / 369
inactive Eurostat series and 1,344 active overall.

**Staleness rule.** Ruling W only caught series with a last value before 2024 and a newer-base
sibling. The new rule is `ingest/data_lag.py` (pure) plus `Db.latest_fetched_periods()` plus the
CLI command `python -m ingest lag`:
- It compares the newest FETCHED period of every active series with today. Legacy rows are
  ignored. All run states count, because a period the publisher gave us is data-time evidence.
- Allowance in whole periods (`MAX_LAG`): A 3, S 3, Q 4, M 6, D 30, PT15M 7.
- It prints `LAGGING ...` and `NO-FETCHED-DATA ...`, and exits 1 if anything lags.
- A hit means "investigate". The command never deactivates anything.
- The thresholds are documented in the module docstring and in `docs/data/operations.md`.
- The deployed image does not have the command until an authorized rebuild.
- Tests: `tests/ingest/test_data_lag.py`, 19 tests covering period arithmetic, the frozen-HICP
  shape, exclusion of legacy rows, and the CLI exit codes.

**Run against the repo registry.** I could not use the production DB, so I built an isolated
scratch DB. A scratch script ran `pipeline.run_dataset` (fetch, parse, validate, write; no
verification) live from f3nix for every active group of every source.
- On the pre-change registry: 50 lagging, including `eurostat.hicp.EU27_2020` (2025-12, lag 11).
- On the new registry: 49 lagging, and 53 without fetched data. Those 53 are not covered:
  - INE (41): the API answered 429 to f3nix all afternoon.
  - FRED (12): there is no key on f3nix (`.fred_api_key` was removed) and the public table timed
    out from f3nix.

  Run `python -m ingest lag` read-only on f0nix after a rebuild to cover them.

None of the 49 is a frozen dataset. Each publisher dataset is live, so I deactivated nothing and
list all of them as owner decisions (below).

### C-I2: canonical geography and unit labels
**How labels are compared.** I traced every comparison before changing anything:
- Eurostat and World Bank adapters hand over `unit_raw=None`, and their verifiers report
  `observed_unit=None`. Fetched rows, verification and the identical-payload short-circuit are
  therefore label-blind. The short-circuit fingerprints response bytes, not the registry.
- Replay re-reads each item with its stored `verification_spec`, so archived items are unaffected.
- Geography is not used by the Eurostat adapter or verifier.
- The only place a label meets data is the legacy CSV import: `validate()` requires the legacy
  unit text to equal `spec.unit`.

The registry labels were each series' legacy spelling, so relabelling alone would have turned the
legacy rows of those series into `unit_mismatch`.

**What changed:**
- **Geography.** Every Eurostat series with a native_code now has `geography` equal to its pinned
  `geo`. That follows the Eurostat convention, which was already dominant (`EL` ×25 vs `GR` ×2,
  `EU27_2020` ×26 vs `EU27` ×9). Nine series changed, 7 of them active.
- **Series ids and indicator_keys are NOT changed.** They keep `.GR` / `.EU27`, because they are
  identity keys used by the legacy id mapping, stored rows and the one-primary-per-key rule.
  Leftovers:
  - `eurostat.price_level_index.GR` and `.EU27` are inactive and have no native_code, so they have
    no pinned geo; the EU27 composition behind them is unestablished.
  - The ids above still carry the legacy suffix.
- **Units: one label per Eurostat unit code and per World Bank indicator,** keeping the dominant
  spelling. 23 series changed, 9 of them active (`eurostat.ipi_total.EU27` and the 8 WB EU/GR
  birth, death, life-expectancy and population series):
  - Eurostat: I21 → `I21`, I10 → `I10_2010`, BAL → `balance`, I15 → `I15`.
  - World Bank: SP.POP.TOTL → `hab.`, SP.DYN.CBRT.IN / SP.DYN.CDRT.IN → `/1000`,
    SP.DYN.LE00.IN → `anos`.
- **Safety.** `ingest/legacy_import.LEGACY_UNIT_SPELLINGS` maps each of the 23 relabelled series
  to its former label. The import accepts that one label for that one series as the same unit;
  nothing is converted.
- **Not relabelled.** The inactive PPP conflict labels (`USD (2017 PPC)` / `USD (2017)`) are kept
  as evidence. An existing test pins them "preserved, not edited".

**Tests:** `tests/ingest/test_task22_labels.py` (8 tests). They cover:
- `geography == pinned geo`, and one label per code.
- Ids and indicator_keys are unchanged.
- A DB built and legacy-imported under the OLD registry re-syncs to the new labels. That re-sync
  produces no `series_deactivated` events and keeps the same active count. Re-importing the same
  CSV under the new labels then writes 0 rows and 0 quarantines.
- A fresh import accepts the former spellings.
- A former spelling is refused for any other series.

Two of these tests fail without the alias (checked). The reviewed unit tables in
`test_registry_eurostat_units.py` and `test_registry_worldbank_units.py` now allow exactly one
label per code.

**Real-data proof:** a full import of the real legacy CSV under the pre- and post-relabel
registries gives identical results:
- 161,263 imported, the same 11,036 quarantine rows by reason, and the same 44,487 served rows.
- A repeat import writes 0 in both cases.

### C-I3: seasonal_adjustment
The field vocabulary follows the existing short codes (FRED's `NSA`). OECD's publisher prose is
verifier-bound and untouched.
- **Eurostat:** the `s_adj` code pinned in native_code, on 304 series (98 active: 52 `SA`, 46
  `SCA`). It stays None where the dataset has no `s_adj` dimension: `gov_10dd_edpt1`,
  `lc_lci_r2_a`, `nama_10_lp_ulc`, `nama_10_pc`, `nrg_pc_204` and `prc_hicp_midx`. A new test
  derives the expected value from native_code.
- **INE**, from the indicator names in the committed, sha-pinned fixtures (a test re-reads them):
  - `SCA` for the 30 active `ipi_seasonal_cae_*` series (0011889, "ajustado de efeitos de
    calendário e de sazonalidade").
  - `SA` for `ine.unemployment_monthly.PT` (0007983, "Ajustada de sazonalidade").
- **Left None (ambiguous or not confirmable):**
  - INE `ipi_yoy_cae.PT` (0011897). An uncommitted metadata read from 2026-11-11 names it
    "Índice de produção industrial - bruto", which would be `NSA`. INE returned 429 today and
    there is no committed fixture, so it is not set.
  - INE `conf_manufacturing` (0001188), `hicp_yoy`, `ipc_yoy` ×2, `exports/imports_monthly`,
    `population`, `live_births` and `deaths`: their names state no adjustment.
  - `oecd.cli.PT` (see M9).
- None of these sources' adapters or verifiers read the field. Replay uses stored specs.

### C-M7 / C-M8 / C-M9: reported, not changed
- **M7.** The `# PROVISIONAL — owner review pending` header stays. HANDOFF's owner decisions say
  "Registry is provisional", and no sign-off is recorded. `core.proposed.yaml` is byte-identical
  but still referenced: `test_registry.py:26` and `test_registry_dgeg_disposition.py:109` pin
  equality, and `propose_registry.py` writes it. It is kept, mirrored, and not deleted.
- **M8.** Unfilled attribution placeholders; I invented no text:
  - `ine.attribution`: "Fonte: Instituto Nacional de Estatística, IP – Portugal (identificação da
    informação estatística referida, período de referência da informação)". This is INE's
    prescribed template, also pinned by `test_core_ine_attribution_is_the_authoritative_portuguese_wording`.
  - `oecd.attribution`: "Source: OECD (year), (dataset name), sdmx.oecd.org (accessed on
    YYYY-MM-DD)".
  - The other sources have complete strings.
- **M9.** `oecd.cli.PT` was NOT renamed or reworded:
  - A rename changes the series id.
  - The unit wording is bound to verification. The OECD verifier maps publisher `UNIT_MEASURE=IX`
    to exactly `index (100=trend)` (`ingest/verifiers/oecd.py:109`). `replay_check` re-derives
    `observed_unit` from archived evidence and requires it to equal the stored claim, so changing
    the map would make every archived OECD cli verification item fail replay.
  - The wording is also the Task 15-reviewed paraphrase of the publisher definition ("amplitude
    adjusted index, long-term average = 100", discovery item 20).
  - Its `seasonal_adjustment` stays None, because the verifier asserts `ADJUSTMENT=AA` → None.

## Tests
- Targeted runs while iterating (registry, sources, verifiers, legacy import, CLI, docgen,
  task17/20): all green.
- Ruff: `.venv-ci/bin/ruff check ingest tests/ingest` is clean.
- Full suite, `.venv-ci/bin/python -m pytest tests/ingest -m "not live" -q`: **1500 passed, 7 deselected (live), 2 warnings in 460 s** (at 7c5c9d8).

## OWNER DECISIONS
1. **HICP successor** for the EU aggregate. Options: `prc_hicp_minr` I15 or I25 `TOTAL` (a new
   series id, ECOICOP ver.2), `prc_hicp_fpd`, or an INE/BdP source. Nothing is mapped.
2. **Lagging active series** (`lag` on live data 2026-11-14; publisher datasets are live, so
   nothing was deactivated):
   - `eurostat.cci.EE`: `ei_bsco_m` has EE values to 2026-04. The periods 2026-05..10 exist
     with no values, while the dataset was updated 2026-10-29.
   - `worldbank.gini` ×18 (latest 2014-2022). Survey-based and sparse by nature: AO, CA, CN, CV,
     DE, EG, GB, GW, HU, JP, KR, MY, MZ, NG, NL, ST, TL, ZA.
   - `worldbank.gov_debt_pct_gdp_wb` ×18 (GC.DOD.TOTL.GD.ZS; latest 1990-2018): CL, CY, CZ, DE,
     DK, EG, FI, ID, IN, IT, LU, LV, MT, NL, NO, PL, PT, SI. The indicator itself reaches 2024
     for other countries.
   - `worldbank.rnd_pct_gdp` ×9 (latest 2011-2022): AO, CL, CV, ID, IN, MY, MZ, NG, ZA.
   - `worldbank.exports_pct_gdp.NG`, `imports_pct_gdp.NG` and `trade_balance_pct_gdp.NG`: the
     World Bank currently publishes only 1960 for Nigeria (API `lastupdated` 2026-11-11).
   - Choices: keep with the lag visible, deactivate per series with this evidence, or tune
     `MAX_LAG` per indicator.
   - Not checked: INE ×41 and FRED ×12 (see C-I1). Run `lag` on f0nix after a rebuild.
3. `ine.ipi_yoy_cae.PT` `seasonal_adjustment`: set `NSA` ("bruto") once INE metadata is
   re-confirmed or a fixture is archived.
4. `oecd.cli.PT` id and unit prose (M9): a rename means a new series id plus a replay-aware
   verifier map change.
5. Registry `PROVISIONAL` header and `core.proposed.yaml` (M7): drop or regenerate after owner
   sign-off. Attribution templates for INE and OECD (M8): render per series or store filled
   forms.
6. HANDOFF pending item 2 ("Eurostat unit labels are inconsistent for the same code") is resolved
   by C-I2. The controller may close it.
