# Task 2 report: curated country comparison pages

Date: 2026-11-17
Branch: pipeline-rebuild
Scope: implementation and tests only. No push, merge or deployment.

## Outcome

Three curated country comparison pages are implemented on the approved multi-series engine:

- `/comparar/paises/eletricidade-domestica`
- `/comparar/paises/pib-por-habitante`
- `/comparar/paises/divida-publica`

Each page fixes the ordered countries Portugal, Spain, France, Germany and Italy, one shared
axis, short geography labels, exact stored tokens, status flags in the summary and complete
table, and per-country provenance at the last common period drawn. `/comparar` now lists a
country section after the existing pair list. Unknown slugs return 404; incomplete or malformed
authored definitions raise MissingText and render the logged generic 503.

## Read model and APIs

New `app/country_comparisons.py`:

- `page(db, slug, *, lang="pt") -> CountryComparisonPage | None`
- `index(db, *, lang="pt") -> CountryComparisonIndex`
- `alignment_text(points, missing, dropped, unparsed, labels, frequency) -> str`
- Frozen dataclasses: `CountrySide`, `CountryValueCell`, `CountryTableRow`,
  `CountryComparisonPage`, `CountryComparisonSummary`, `CountryComparisonIndex`.

New thin preparation wrapper in `app/reads.py`:

- `prepare_group_chart(points, *, frequency, title, labels, unit="", badge="", lang="pt")`

It calls `chart_model.group_model` and `interactive.build_payload` through the existing
`PreparedChart` boundary. No engine, adapter, bundle or manifest changes.

Presentation additions:

- `presentation.COUNTRY_COMPARISONS_TITLE`
- `presentation.COUNTRY_COMPARISONS_INTRO`
- `presentation.COUNTRY_COMPARISONS_COUNTRIES`
- `presentation.COUNTRY_COMPARISONS`
- `country_comparisons(lang)`, `country_comparison(lang, slug)`,
  `country_comparison_countries(lang)`, `country_comparisons_title(lang)`,
  `country_comparisons_intro(lang)`.
- The English catalogue has explicit empty country tables so a non-Portuguese render refuses
  with MissingText rather than AttributeError.

## Catalogue contract

Each group pins:

- family, source, dataset, stored frequency and unit;
- exact native dimensions except `geo` (for electricity: `freq=S`, `siec=E7000`,
  `nrg_cons=KWH2500-4999`, `unit=KWH`, `tax=I_TAX`, `currency=EUR`);
- seasonal adjustment, multiplier and base year;
- reviewed title, subtitle, mechanism, caption, definition note and notebook action.

The read model requires, on every side:

- an active, primary, redistributable series with fetched served values;
- the expected series id, geography and indicator key;
- the same family, source, unit, frequency, seasonal adjustment, multiplier and base year;
- exactly the pinned native dataset and dimensions, with only `geo` varying.

Any missing, withheld, withdrawn, legacy-only, cross-check or mismatched side hides the whole
group. The index omits hidden groups; the page returns 404. It never draws fewer than five lines.

The common period intersection is exact. Periods every other country publishes but one country
does not are counted per country; periods a country has without a shared partner are counted
separately; common periods with a nonnumeric token are counted once. There is no interpolation,
carry-forward, resampling, rebasing or rounding of stored tokens.

## Routes, templates and assets

- `app/main.py`: `/comparar` now reads the pair index and country index in one read-only
  transaction; `/comparar/paises/{slug}` is registered before `/comparar/{slug}`.
- `app/templates/compare_countries.html`: summary, generic chart shell fallback, complete table
  with a labelled horizontal scroller, per-country provenance and notebook link carrying all
  five series.
- `app/templates/compare_index.html`: country section, hidden when no group is available.
- `static/css/prumo.css`: scoped country-link, summary, table and provenance rules. Carmim
  remains the first group style. No new JavaScript framework.

Links and assets use the existing validated mount helper and work on direct and `/dados`
prefixes. The local chart bundle is loaded only when a successful chart payload exists; the
index is script-free.

## Verification

Production snapshot used read-only:
`/home/joao/.hermes/cache/scratch/prumo-eu-comparisons/production-copy.sqlite3`.

- All 15 selected series are active, primary, redistributable and have fetched served values.
- Registry identities and native dimensions match the catalogue for all 15.
- `eletricidade-domestica`: 37 common periods, 2008-S1 to 2026-S1, 37 table rows; 5 lines;
  one axis; 5 legend labels; 5 summary values.
- `pib-por-habitante`: 31 common periods, 1995 to 2025, 31 table rows; the current five values
  carry the provisional flag; provenance is the run behind 2025, not any newer period.
- `divida-publica`: 31 common periods, 1995 to 2025, 31 table rows; all five cover the same
  periods.
- All three pages returned 200 on direct and `/dados` prefixes; unknown slug returned 404.
- The database file hash was unchanged after the page and index reads.

Tests run:

- `tests/app/test_country_comparisons.py tests/presentation/test_country_catalog.py`:
  36 passed.
- `tests/app/test_country_comparisons.py tests/presentation/test_country_catalog.py
  tests/app/test_comparisons.py tests/app/test_chart_engine.py tests/app/test_interactive.py
  tests/app/test_routes.py tests/backoffice/test_boundaries.py`: 153 passed.
- CMS and shared readers:
  `tests/app/test_cms_home.py tests/app/test_home_composition.py tests/app/test_notebook.py
  tests/app/test_reads.py tests/app/test_charts.py tests/app/test_chart_layout.py
  tests/backoffice/test_cms_routes.py tests/backoffice/test_cms_service.py`: 121 passed.
- `ruff check` over every changed Python file: passed.

Known pre-existing failure, not caused by this task: `tests/test_typography.py` pins the vendored
chart bundle SHA-256 to `cc980ca1...`, while the bundle committed at `abfc92d` hashes to
`debf2758...`. The same mismatch exists at `abfc92d` before these changes. The bundle was not
touched.

## Commits

- `96f1c18` feat: add curated country comparison read model
- `d613556` feat: publish curated country comparison pages
- This report is committed separately.

No push, merge, deployment or production write was performed.
