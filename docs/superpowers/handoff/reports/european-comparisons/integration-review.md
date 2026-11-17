# Final integration review: European country comparisons

Verdict: PASS

Scope: read-only review at `b1fca40`. Runtime source is unchanged from `0902617`; `b1fca40`
adds only the Task 2 review documents. No code, HANDOFF, roadmap, catalogue, CMS, merge, push
or deploy change was made by this review.

## Cross-task contracts

- Task 1 to Task 2 boundary holds. `app/reads.py:prepare_group_chart` calls
  `chart_model.group_model`, then `interactive.build_payload`, and returns the existing
  `PreparedChart`. `app/country_comparisons.py` consumes that one prepared model for the SVG,
  table and payload. There is no second scale, tick set or value formatter.
- Group payloads are `kind="group"` with one `axes` entry and explicit `axis: 0` on every
  series. The adapter rejects a group without exactly one axis and rejects more than two axes.
- Pair compatibility is pinned, not assumed. `tests/app/test_chart_engine.py` compares the pair
  SVG bytes with `cmp_dual.svg` and the complete payload, including key order and nested values.
  Pair CSS rules and the `a`/`b` model aliases are unchanged. The focused suite passed 17 chart
  engine tests.
- The compiled bundle hash is `debf2758f06efd3ec451bc4972d5bfc38c66e954f85bb352cdb3c3fc957b4e1d`,
  matching `static/js/prumo-charts.manifest.json` and the independent typography pin.

## Discoverability and route

- `/comparar` is in the shared site navigation (`app/main.py:43`). Its index renders the country
  section after the pair list, with one link per available group to
  `/comparar/paises/<slug>`.
- `/comparar/paises/{slug}` is registered before `/comparar/{slug}`, so `paises` is not swallowed
  as a pair slug. Unknown country slugs return 404 on both the direct and `/dados` prefixes.
- Hidden groups disappear from the index. The index itself remains script free; a country page
  gets the chart script only when a successful payload exists, with the server SVG as fallback.
- Tests cover index order, five links, mount prefixes, route order, unknown slug, no script on
  the index, and script/policy on chart pages.

## Snapshot, eligibility and exact values

- Every request uses one `_read` call into `read_db_readonly`, so the index and page see one
  read-only snapshot. `app/country_comparisons.py` has no SQL, cache or write path. It reads
  `public_series`, `public_series_values` and `public_provenance_at` directly.
- `public_series` enforces active status and source redistribution; `public_series_values`
  returns fetched served rows only. `_check_side` adds the expected series id, primary role,
  geography, indicator key, family, dataset, exact native dimensions except `geo`, and matching
  source, unit, frequency, seasonal adjustment, multiplier and base year. Any failed side hides
  the whole group.
- Read-only probe against
  `/home/joao/.hermes/cache/scratch/prumo-eu-comparisons/production-copy.sqlite3` resolved all
  three groups. Common periods were 37 for electricity (2008-S1 to 2026-S1), 31 for GDP
  (1995 to 2025) and 31 for public debt (1995 to 2025).
- Exact production tokens and flags survived: electricity `0,2367`, `0,2509`, `0,2485`,
  `0,3618`, `0,3142`; GDP `28 560`, `34 240`, `43 350`, `54 240`, `38 430`, all five
  `provisional`; debt `89,2`, `100,5`, `115,7`, `62,8`, `136,7`.
- GDP provenance is the 2025 run, not a newer unpaired period. The dedicated test adds a 2026
  value and proves the page still shows 2025 and the older run.
- Alignment text uses the raw period sets, not a cache: it names only periods every other
  country publishes, names dropped periods separately with the "at least one other country"
  explanation, and pluralises from the number of periods (`Fica` for one, `Ficam` for more).
  Tests cover one country with multiple dropped periods and countries sharing a gap.

## CMS, packaging and latest corrections

- No diff under `ingest/`, `registry/`, `backoffice/` or CMS modules. Existing CMS composed
  charts therefore keep the same read and write boundaries. The country page test hashes the
  database before and after index, page and 404 requests and proves no write.
- `Dockerfile` copies `app/`, `static/`, `presentation/` and `registry/`, so the new service,
  template, catalogue and bundle are packaged. The new source and test files are tracked.
- The narrow corrections are present: the summary grid uses
  `repeat(auto-fit, minmax(min(13rem, 100%), 1fr))` in `static/css/prumo.css`, and the typography
  guard now pins the rebuilt bundle rather than the previous bundle.
- `git diff --check 02df1b1 b1fca40` is clean.

## Verification run

```text
.venv-ci/bin/python -m pytest tests/app/test_chart_engine.py \
  tests/app/test_country_comparisons.py tests/app/test_country_layout.py \
  tests/presentation/test_country_catalog.py tests/test_typography.py -q
75 passed, 1 warning in 135.36s
```

The full controller suite was not duplicated. The browser acceptance was not re-run; its
receipt remains in the untracked `browser-accepted` workspace folder, and earlier harness
folders remain historical. Human screen-reader review remains separate.

No important integration defect found.
