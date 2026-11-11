# Task 8 report: legacy import and registry proposal

Status: **DONE_WITH_CONCERNS**. Commits: `4d0b4b6` (legacy_import + tests), `3bec761` (controller WIP checkpoint of propose_registry + tests, written by this task), `d0d2bc5` (generated registry files + core-registry test), `261d99c` (report), `864d054` (fix round 1: Ruling V missing_unit, truthful gaps and reasons), plus this report update.

## Summary numbers (real export, 246,162 rows)

### Rows per source, in / out of core

| source | in core | out of core | core series |
|---|---|---|---|
| EUROSTAT | 100,450 | 56,862 | 697 |
| WORLDBANK | 46,348 | 6,270 | 982 |
| FRED | 9,868 | 277 | 20 |
| INE | 9,216 | 653 | 38 |
| REN | 2,714 | 0 | 14 |
| OECD | 2,291 | 0 | 6 |
| DGEG | 466 | 6,759 | 17 |
| BPORTUGAL | 0 | 3,471 | 0 |
| ERSE | 0 | 517 | 0 |
| **total** | **171,353** | **74,809** | **1,774** |

"In core" means the row's series is in the registry. 6,522 of those rows are then quarantined as `missing_unit` (see below).

- Registry: 1,774 series, 1,751 indicator_keys (one primary each), 23 cross_checks. Themes: economy 1,441, demography 270, energy 63.
- Overlaps: 20 indicator_keys with more than one series (23 cross-checks), 0 flagged LARGE (relative gap above 2%) after fix round 1. The earlier 6 were artefacts of unitless rows, see the fix section.
- Left out: 429 deferred series (DGEG long tail 179, World Bank non-core themes 250), 282 unclassified series (several units 178, several period formats 41, no unit 30, no parseable period 28, legacy data problem 3, quarterly stored as months 2).

### `import_legacy` against the real export (temp SQLite in the scratchpad, deleted afterwards)

| outcome | rows |
|---|---|
| imported (`legacy-unverified`) | 164,825 |
| quarantined `missing_unit` (blank legacy unit, Ruling V): Eurostat 1,819, FRED 3,779, INE 864, World Bank 60 | 6,522 |
| quarantined `non_numeric` (DOUBLE text in scientific notation, e.g. `5.22e-05`, all World Bank) | 6 |
| quarantined `bad_period` | 0 |
| quarantined `unit_mismatch` | 0 |
| skipped `not_in_registry` | 74,809 |
| **total** | **246,162** |

- Second run: `n_imported=0`, `{not_in_registry: 74809}` only, still 164,825 observations, 6,528 quarantine rows and 7 dataset_runs. Idempotent.
- 7 synthetic runs (`legacy:<source>`), all `verified`. `served_observation` = 0 rows (`legacy_served` = '0').
- The "11.2k nulls" in the spec are null **units**. No value is empty. Under Ruling V a blank unit is never given the registry unit: the row is quarantined as `missing_unit`. Series with no unit at all are left out of core. Every unitless row range is listed in `unclassified.md`, in the section "Legacy rows quarantined: unit missing".
- `bad_period` is 0 because the only unparseable periods (`2022-00`, Eurostat `earn_ses_pub2s`) belong to series with no parseable period, and those are unclassified. INE free-text periods (`Setembro de 2025`) normalize to `YYYY-MM`.
- Runtime is about 23 s for proposal + import together.

## What was built

- `ingest/legacy_import.py`
  - `import_legacy(db: Db, csv_path: Path, registry: list[SeriesSpec] | None = None) -> LegacyImportReport(n_imported: int, n_quarantined_by_reason: dict[str, int])`. With `None` it loads `registry/core.yaml`. It calls `sync_registry`, reads the CSV with stdlib `csv`, and validates each row with `ingest.validate.validate` using the series `decimal` and unit. All writes happen in one transaction.
  - `legacy_series_id(source, indicator, region)` gives `"<source lower>.<indicator>.<geography>"`. `legacy_geography` handles the aliases `Portugal` to `PT` and `GLOBAL` to `WORLD`, and maps every FRED row to `WORLD` (all FRED rows are global IMF commodity prices filed under PT, GLOBAL or WORLD).
  - `fetched_at_utc` reads naive timestamps as UTC. `fetched_at` is stored as ISO-8601 Z, and `value_text` is stored verbatim.
  - Report semantics: the report counts what this call wrote. `not_in_registry` is a skip and is counted on every call.
  - Dedupe is done in code: an observation is skipped if `(series_id, period, value_text, fetched_at)` already exists in the run, and a quarantine row is skipped if `(series_id, raw_period, raw_value, reason)` already exists. When two legacy rows map to the same (series, period), for example after a region alias merge, both are kept as vintages in fetched_at order, so the later fetch gets the higher id and the served view would pick it.
- `ingest/db.py` gains `legacy_run`, `legacy_observation_keys`, `quarantine_keys` and `write_legacy_observations`. No other module imports sqlite3, and duckdb is imported nowhere.
- `ingest/propose_registry.py`, `propose(csv_path: Path, out_dir: Path) -> None`, writes `core.proposed.yaml`, an identical `core.yaml`, `overlaps.md`, `deferred-tail.md`, `unclassified.md` and `licences-todo.md`. Every judgement call is in explicit tables:
  - `THEMES`/`THEME_PREFIXES` set the theme.
  - `NON_CORE_THEMES` lists health, education and digital indicators, which are deferred.
  - `DGEG_CORE` keeps the 17 national headline energy indicators. The rest of DGEG is deferred.
  - `CONCEPTS` defines cross-source equivalences. Without an entry, the concept is source-qualified (for example `worldbank_population`), so indicators that merely share a legacy name never merge.
  - `LEGACY_DATA_PROBLEMS` lists series that are left out after inspection.
  - `PT_GEOS`/`EUROPE` plus a source rank per geography class decide the primary.
  - `LICENCES`/`LICENCE_TODO` hold the licence data.
  - `indicator_key` is `<concept>.<geography>.<frequency>`. Frequency is inferred per row with `normalize_period`, trying A, S, Q, M, D in that order.
  - Gaps are computed with `Decimal` on the latest legacy vintage. No float arithmetic is done on values.
- Generated files in `registry/`. Both YAML files start with `# PROVISIONAL — owner review pending`.

## Registry decisions

| decision | why |
|---|---|
| Primary for PT geography: INE > BPORTUGAL > REN > DGEG > ERSE > Eurostat > OECD > WB > FRED | spec §5 |
| Primary for European geography: Eurostat first; world: WB > OECD > FRED | spec §5 |
| Tie within one source: most rows, then most periods, then id | deterministic |
| Units kept exactly as the data labels them (`% PIB`, `% GDP`, `I21`, `index_2021=100`) | Ruling T |
| No unit in data, or several units, or several period formats: series left out (`unclassified.md`) | Ruling T; no invented units |
| Monthly-format series whose months are only 01/04/07/10: left out as "quarterly stored as months" (INE `gdp_yoy`, INE `unemployment`) | otherwise registered with the wrong frequency |
| World Bank `gov_debt_pct_gdp_wb` NOT a cross-check of Eurostat `gov_debt_pct_gdp` | WB code GC.DOD.TOTL.GD.ZS is central-government debt; gaps up to 23% |
| `LEGACY_DATA_PROBLEMS`: Eurostat `unemployment_m` (labelled PC_ACT, values are thousands of persons), INE `emp_industry_cae` (labelled %, values are an index), FRED `commodity_cotton` (cotton / 100, derived) | found by inspection and overlap gaps |
| FRED `commodity_X` vs `X` kept as cross_check pairs (identical values) | legacy duplicates; the owner can drop them |
| Eurostat geographies kept as they appear (`EL` and `GR`, `EU27` and `EU27_2020`); WB keeps all 54 countries as "world basics" | Ruling T |
| ERSE entirely out: annual and monthly tariff periods are mixed in every series | no single frequency |
| Licences confirmed: Eurostat CC BY 4.0 (https://ec.europa.eu/eurostat/web/main/help/copyright-notice; the URL in the ruling returns 404), World Bank CC BY 4.0 (datacatalog page checked). All others: `UNVERIFIED — builder must confirm before serving`, `redistribution_ok: false`, listed in `licences-todo.md` (INE page under maintenance; OECD page returned 403; BdP, REN, DGEG, FRED/IMF not read) | no invented licences |

## RED / GREEN evidence

RED for legacy_import (tests written first):
```
ERROR tests/ingest/test_legacy_import.py
E   ModuleNotFoundError: No module named 'ingest.legacy_import'
```
GREEN: `tests/ingest/test_legacy_import.py ..... 5 passed in 1.15s`

RED for propose_registry (module moved aside):
```
ERROR tests/ingest/test_propose_registry.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```
RED for the DGEG core theme (found on the real data, test added first):
```
E   AssertionError: assert {'eurostat.un...tion.MZ', ...} == {'dgeg.energy...mp_m.PT', ...}
================== 1 failed, 3 passed, 1 deselected in 0.24s ===================
```
RED for the committed registry test before generation:
```
E   FileNotFoundError: ... registry/core.proposed.yaml
========================= 1 failed, 11 passed in 0.59s =========================
```
Final:
```
tests/ingest/test_legacy_import.py::test_null_value_and_unit_quarantined PASSED
tests/ingest/test_legacy_import.py::test_ine_free_text_period_normalized_or_quarantined PASSED
tests/ingest/test_legacy_import.py::test_legacy_rows_not_in_served_view PASSED
tests/ingest/test_legacy_import.py::test_import_is_idempotent PASSED
tests/ingest/test_legacy_import.py::test_same_period_from_two_fetches_kept_as_vintages PASSED
tests/ingest/test_propose_registry.py::test_proposal_has_one_primary_per_indicator_key PASSED
tests/ingest/test_propose_registry.py::test_proposal_prefers_portuguese_institution PASSED
tests/ingest/test_propose_registry.py::test_proposal_leaves_out_tail_mixed_units_and_unknowns PASSED
tests/ingest/test_propose_registry.py::test_proposal_licences_not_invented PASSED
tests/ingest/test_propose_registry.py::test_real_export_proposal_and_import PASSED   (slow, skipif no export; asserts 246162 rows accounted, 0 served)
pytest tests/ingest -q  ->  376 passed in 56.81s
```

## Files changed

- `ingest/legacy_import.py` (new)
- `ingest/propose_registry.py` (new)
- `ingest/db.py` (4 legacy methods)
- `tests/ingest/test_legacy_import.py`, `tests/ingest/test_propose_registry.py`, `tests/ingest/legacy_csv.py` (new; the brief named a single test file, and it is split in two)
- `tests/ingest/test_registry.py`: the skeleton test is replaced by `test_core_registry_loads_and_syncs`
- `registry/core.proposed.yaml`, `registry/core.yaml`, `registry/overlaps.md`, `registry/deferred-tail.md`, `registry/unclassified.md`, `registry/licences-todo.md`

## Concerns / open questions for the owner and for Tasks 9–16

1. **Banco de Portugal has zero core series.** The legacy data has no unit for any BPstat series, and I did not invent units. Task 11 must add euribor, yields, credit, deposits and EUR/USD to the registry with units from BPstat metadata. Similar gaps: Eurostat `gdp_quarterly`, `hicp`, `ipi_total`, `ipi_manufacturing` (several units, rebasing across vintages); INE `gdp_yoy` and `unemployment` (quarterly stored as months); World Bank PT-only `gdp`, `inflation` and others (no unit). See `unclassified.md`.
2. **No core series is servable yet except Eurostat and World Bank.** INE, OECD, REN, DGEG and FRED are `UNVERIFIED` with `redistribution_ok: false` until a person confirms their terms (`licences-todo.md`).
3. **Superseded by fix round 1 (Ruling V).** Unitless legacy rows are now quarantined as `missing_unit` and never imported (6,522 rows; ranges in `unclassified.md`).
4. **Superseded by fix round 1.** The "8–12% INE vs Eurostat IPI gap" was not a disagreement between sources. It came from unitless Eurostat rows (2000–2017), which are an older base-year vintage and had been labelled I21. Over explicit-I21 periods (2018 on), INE and Eurostat agree within 0.7% (`ipi_total`: 0.69%, `ipi_manufacturing`: 0.06–0.67%, `ipi_c22`: 0.09%, `ipi_c28`: 0.47%). `seasonal_adjustment` is still left empty everywhere.
8. **Owner note (F4).** Six tiny World Bank values written in scientific notation (for example `5.22e-05`) are quarantined as `non_numeric` by design. They are DOUBLE text from the old store, not publisher tokens. The World Bank adapter will re-fetch them.
5. **PT unemployment primary is OECD** (`unemployment_rate.PT.M`), because INE's legacy series is quarterly and Eurostat's PT monthly series has several units. Task 10 (INE) should add the INE monthly series as primary.
6. **Naive legacy `fetched_at` values are assumed to be UTC.**
7. The CLAUDE.md GitNexus impact and detect_changes steps were not run, because no GitNexus tools were available in this session.

## Fix round 1 (review F1, F2, F4; Ruling V)

| finding | fix |
|---|---|
| F1: blank legacy units were imported under the registry unit, which invents a unit | `legacy_import`: an otherwise-valid row whose CSV unit is blank is quarantined as `missing_unit`. This is a legacy-only reason, local to `legacy_import.py`; `validate()` and the live pipeline are unchanged. A non-empty unit that differs from the registry unit is still `unit_mismatch`. Identical quarantined rows from two legacy fetches are each written (the quarantine table has no fetched_at), so all 246,162 rows are accounted for. Re-runs still write nothing. |
| F1 in proposal | `overlaps.md` gaps and row counts use only rows with an explicit unit, and the file says why. The `unclassified.md` section is now "Legacy rows quarantined: unit missing": per series, the count and period range of unitless rows, covering both core series (rows quarantined) and series with no unit at all (not core, for example BdP). Tie-breaks use explicit-row counts. |
| F2: `_why` claimed "Portuguese institution" for Eurostat-vs-Eurostat ties | `_why` states the rule that actually decided: the PT, Eurostat or world rule only when the primary really is that kind of source; otherwise "closest to origin by source rank: X ahead of Y". For same-source names it says "tie broken by row count (n vs m)", or "by period count, then series id (equal row counts)" when the counts are equal. |
| F4 | owner note added as concern 8 |

Effect: large gaps went from 6 to 0. The FRED primaries of three pairs moved to the `commodity_*` names because the unitless copies no longer count. The registry still has 1,774 series and 1,751 keys with one primary each, loads, and syncs into a fresh DB (1,774 series).

Tests:
- RED: `test_null_value_and_unit_quarantined`, `test_empty_unit_row_never_takes_the_registry_unit`, `test_overlap_gap_uses_only_rows_with_an_explicit_unit`, `test_series_without_any_explicit_unit_not_core_and_listed` and `test_why_is_truthful` failed (5 failed, 8 passed) before the fix.
- `test_identical_quarantined_rows_from_two_fetches_both_counted` was written together with its fix. The bug it pins was found by the real-export total check, which first summed to 246,108.

```
$ .venv-ci/bin/python -m pytest tests/ingest -q
============================= 381 passed in 57.01s =============================
```
