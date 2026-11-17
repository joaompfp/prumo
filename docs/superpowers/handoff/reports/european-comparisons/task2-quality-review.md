# Task 2 quality and integration review

Verdict: APPROVED

Scope: `abfc92d..d1df017`, country comparison commits `96f1c18`, `d613556` and report
`d1df017`, on the approved Task 1 shared chart engine. Read-only source review. No runtime,
HANDOFF, roadmap or catalogue changes were made; this report is the only file added by this
review.

## Evidence

### Eligibility and same snapshot

- The route reads through `_read` (`app/main.py:83`) into `read_db_readonly`, which wraps the
  whole callback in one deferred read transaction (`ingest/db.py:2339`). `country_comparisons.page`
  and `country_comparisons.index` therefore see one snapshot for `public_series`,
  `public_series_values` and `public_provenance_at`.
- `_check_side` (`app/country_comparisons.py:148-194`) requires the expected series id,
  `role == "primary"`, matching geography, expected indicator key and family, a parseable
  `dataset:dimensions` native code, `geo` equal to the country, and every other pinned dimension
  exactly equal to the catalogue. `public_series` enforces active status and source
  redistribution; `public_series_values` returns fetched served rows only.
- `_published_group` (`app/country_comparisons.py:197-237`) also requires all five sides to agree
  on source, unit, frequency, seasonal adjustment, multiplier and base year, and hides the whole
  group if any side is missing or mismatched.
- Regression coverage passes for withheld source, inactive side, withdrawn run, legacy-only
  values, cross-check role, native dimension drift, unit drift and family drift in
  `tests/app/test_country_comparisons.py`. The supplied production snapshot has all fifteen
  selected series active, primary, redistributable and served.

### Dimensions, counts and alignment

Independent SQL recomputation against
`/home/joao/.hermes/cache/scratch/prumo-eu-comparisons/production-copy.sqlite3` matches the read
model exactly:

| Group | Served periods PT/ES/FR/DE/IT | Common finite periods | Span | Table rows | Chart points |
|---|---|---|---|---|---|
| eletricidade-domestica | 38/38/38/39/37 | 37 | 2008-S1 to 2026-S1 | 37 | 37 |
| pib-por-habitante | 31/31/51/35/31 | 31 | 1995 to 2025 | 31 | 31 |
| divida-publica | 31/31/31/31/31 | 31 | 1995 to 2025 | 31 | 31 |

- The electricity catalogue pins `nrg_pc_204:freq=S,siec=E7000,nrg_cons=KWH2500-4999,unit=KWH,tax=I_TAX,currency=EUR`. GDP pins `nama_10_pc:freq=A,unit=CP_EUR_HAB,na_item=B1GQ`. Debt pins `gov_10dd_edpt1:freq=A,unit=PC_GDP,sector=S13,na_item=GD`. All five registry identities per group match these dimensions except `geo` (`tests/presentation/test_country_catalog.py`).
- The index and page use the same intersection. Periods are intersected before finite filtering; common periods with a nonnumeric token are removed and counted once, never interpolated or carried forward.
- The electricity recomputed missing counts are `[0,0,0,0,1]` and dropped counts `[1,1,1,2,0]`, matching the shown alignment text. GDP dropped counts are `[0,0,20,4,0]`; debt has no gaps.
- Five countries appear on every page: five summary entries, five chart series on one axis, five legend entries, and five table columns. The index shows the country list, span and common count without preparing a chart.

### Exact values, status and provenance

- Summary and table use the stored token through `format_value`; the production electricity page shows `0,2367`, `0,2509`, `0,2485`, `0,3618`, `0,3142`. GDP shows `28 560`, `34 240`, `43 350`, `54 240`, `38 430`; debt shows `89,2`, `100,5`, `115,7`, `62,8`, `136,7`. No rounding or conversion is introduced.
- GDP 2025 carries the source `provisional` flag on all five sides and renders `provisório` in the summary and table. `normal` maps to an empty status text, so ordinary cells stay clean.
- Provenance is resolved with `public_provenance_at` at the last finite common period actually drawn (`app/country_comparisons.py:290-306`, `app/country_comparisons.py:321-325`). For every production side, the displayed `run_id` matched the `dataset_run_id` of the served row at that period. The dedicated test adds a newer unpaired 2026 GDP value and proves the page still reports 2025 and the older run.
- `tests/app/test_country_comparisons.py` also pins the exact four-decimal token, the provisional flag in summary and table, the full newest-first table, the shared axis and the payload values.

### Routes, templates and preserved pair/CMS behaviour

- `/comparar/paises/{slug}` is registered before `/comparar/{slug}` (`app/main.py:246-263`). Unknown slugs return 404 on direct and `/dados` prefixes; malformed catalogue text or a malformed country list raises `MissingText` and returns the logged 503 on both the page and `/comparar`.
- The index remains script-free and the chart pages receive the chart CSP only when a payload exists. The SVG fallback, table and provenance render without a payload. Mount-prefixed links and assets are covered.
- Pair comparison and CMS behaviour are unchanged: `app/chart_model.py`, `app/charts.py`, `app/interactive.py`, `ingest/` and `registry/` have no diff in this range. Production pair pages and `/paginas` return 200; pair, CMS, route and chart-engine tests pass.

### Read-only and boundaries

- `app/country_comparisons.py` contains no SQL, `execute` call or write path. `tests/backoffice/test_boundaries.py` passes.
- A before/after SHA-256 of the production snapshot was identical after reading the index, all three country pages and the unknown slug: `f6bf13164687f6a4...`.
- The page uses the shared `prepare_group_chart` wrapper (`app/reads.py:353-368`), which calls the Task 1 `group_model` and `interactive.build_payload`. No separate scale, tick, geometry or value formatter was introduced.

## Tests run

- `.venv-ci/bin/python -m pytest tests/app/test_country_comparisons.py tests/presentation/test_country_catalog.py -q`: 36 passed.
- `.venv-ci/bin/python -m pytest tests/app/test_comparisons.py tests/app/test_cms_reads.py tests/app/test_cms_home.py -q`: 67 passed.
- `.venv-ci/bin/python -m pytest tests/backoffice/test_boundaries.py tests/app/test_routes.py -q`: 51 passed.
- `.venv-ci/bin/python -m pytest tests/app/test_chart_engine.py tests/app/test_interactive.py -q`: 36 passed.
- `.venv-ci/bin/python -m ruff check` over every changed Python file: passed.
- Production snapshot through `TestClient`: index 200 with three country links, three pair links and no script; each country page 200 with five lines, one axis, five legend entries and 37/31/31 table rows; unknown slug 404. Pair pages and `/paginas` returned 200.

The known `tests/test_typography.py` pinned-bundle hash failure was not run or reclassified; per the task it is a controller packaging correction for the previous bundle, not a source defect in this range.

## Non-blocking observations

- The phrase `sem par nos outros países` is too strong when two or more countries share a dropped period. Production electricity has PT, ES and FR sharing 2007-S2, and GDP has FR and DE sharing 1991-1994. The counts and spans are correct; the controller is already handling the wording change to "em falta em pelo menos outro país".
- `missing` names a country as behind only when every other country publishes the period. When two countries share a gap, neither is named in that sentence, although the other three show a dropped count. This is pinned by `tests/app/test_country_comparisons.py:280` and is narrower than a literal per-country absence count; the dropped counts still expose the gap.
- `Os cinco países` and `Três leituras` are hardcoded to the fixed five-country, three-group scope. They are correct now and would need updating if the authored counts changed.
- **Nit:** `alignment_text` selects `Fica` from the number of countries with gaps, not the number of periods. A single country with two or more dropped periods reads `Fica de fora 2 períodos de ...`. No current production page hits this (electricity has four countries with gaps and GDP two), but it is reproducible with one country holding multiple extra periods.
- `_native_parts` is slightly more permissive than `ingest/sources/eurostat.parse_native_code`: it accepts `=` or `:` inside a dimension value and does not reject `time`. An authored fault of that shape would surface as a data mismatch (404) rather than a catalogue fault (503). It has no effect on the pinned production catalogue.
- `_periods_text`, `_common_text` and `_join_labels` duplicate small private text helpers already present in `app/reads.py` and `app/chart_model.py`. Value formatting, scale, ticks and SQL boundaries are shared; consolidating the pluralisation helpers is optional cleanup, not a correctness risk.
