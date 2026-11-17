# Task 2 specification review

Verdict: PASS

Scope: `abfc92d..d1df017`, country comparison commits `96f1c18` and `d613556`, report `d1df017`.
Read-only review. No implementation, full suite or browser run. The pinned chart bundle typography
failure named in the Task 2 report is a separate assigned correction and is not re-reviewed here.

## Verified

- Catalogue scope: exactly three groups in reading order, each over the fixed ordered countries
  PT, ES, FR, DE, IT. Slug, family, dataset, frequency, unit and native dimensions match
  `registry/core.yaml` for all fifteen selected series.
- Native pins: electricity is `nrg_pc_204:freq=S,siec=E7000,nrg_cons=KWH2500-4999,unit=KWH,tax=I_TAX,currency=EUR`; GDP is `nama_10_pc:freq=A,unit=CP_EUR_HAB,na_item=B1GQ`; debt is
  `gov_10dd_edpt1:freq=A,unit=PC_GDP,sector=S13,na_item=GD`.
- Eligibility: all fifteen sides are active, primary, redistributable and served from verified
  fetched observations in the supplied production snapshot. `public_series` enforces active and
  redistribution, `public_series_values` returns fetched rows only, and `_check_side` enforces
  role, geography, family, indicator key, dataset, native dimensions and non-empty values.
  Withheld, withdrawn, legacy-only, cross-check, inactive, dimensional and unit mismatches hide
  the whole group; no country is silently dropped.
- Shared axis: the read model intersects the five served period sets, filters to finite tokens on
  every side, and passes the exact intersection to the shared group model. There is no
  interpolation, carry-forward, resampling, rebasing or token rounding. Non-numeric common
  periods are excluded and counted separately.
- Published data on the supplied snapshot: electricity 37 common periods (2008-S1 to 2026-S1),
  GDP 31 (1995 to 2025), debt 31 (1995 to 2025). Each page has five summary values, five chart
  series on one axis, five legend entries and one table row per drawn period. GDP 2025 carries
  the provisional flag on all five sides; provenance is resolved at 2025, not at a newer
  unpaired value. Electricity 2026-S1 and debt 2025 are the last common periods.
- Exact tokens and statuses: summary and table use the stored tokens through `format_value`
  (`0,2367`, `28 560`, `89,2`); the table renders `provisório` and the historical Italian GDP
  `quebra de série` flag. The table is newest first and complete for the drawn periods.
- Routes and publication: `/comparar/paises/{slug}` is ordered before `/comparar/{slug}`; the
  index lists all three groups after the pair list; unknown slug is 404; malformed catalogue
  text or country list is a logged 503. Direct and `/dados` prefixes carry links, CSS and chart
  assets correctly. The index is script-free; successful chart pages receive the chart CSP;
  fallback SVG, table and provenance work without a payload.
- Read-only behavior: page and index use one `read_db_readonly` transaction. The supplied
  database hash was unchanged after page and index reads. No SQL or write path exists in
  `app/country_comparisons.py`.
- Caveats: the electricity copy states the semester band average with taxes and explicitly
  excludes a live tariff, estimated bill and affordability measure; GDP states current euros,
  excludes household income, real growth and purchasing-power adjustment; debt states gross
  consolidated stock as a share of GDP and excludes the annual deficit and net debt.
- `pytest tests/app/test_country_comparisons.py tests/presentation/test_country_catalog.py`
  passes 36 tests. `tests/app/test_comparisons.py tests/app/test_routes.py` passes 77 tests.
  Changed Python files pass `ruff check`.

## Non-blocking observations

- The alignment count treats a period as "missing" for a country only when every other country
  publishes it. When two countries share a gap, neither is named as missing, although the other
  three are counted as having a dropped period. The test at
  `tests/app/test_country_comparisons.py:280` pins this "behind versus extra" model; it still
  shows the gap through the dropped counts, but it is narrower than a literal per-country count
  of every absent period.
- The dropped-period sentence says "sem par nos outros países". A dropped period can still be
  shared by two to four countries: France and Germany both publish 1991-1994, and Portugal,
  Spain and France share 2007-S2. The counts and the common span are correct, but the wording
  reads as if no other country publishes those periods.
- The Italian GDP 2010 value carries the source `break` flag and the table shows
  `quebra de série`, while the chart line remains continuous (`chart.breaks == ()`). The spec
  only requires temporal gaps to break the line, so this is not a breach; a future series-break
  marker would make the chart match the status flag.
- `country_comparison` rejects missing, blank and structurally malformed fields, but it does not
  reject a native dimension value containing the native-code separators (`,` or `=`) or a
  non-finite multiplier. Such an authored error is treated as a data mismatch and returns 404
  instead of the catalogue-fault 503. This is an edge case in an otherwise fail-closed validator.
- The index intro says "Três leituras" and the page heading says "Os cinco países". Both match
  the fixed scope; they would need adjusting if the authored group or country count changed.
