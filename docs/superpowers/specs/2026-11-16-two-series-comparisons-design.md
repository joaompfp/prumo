# Prumo — Two-series comparisons (project 4, extension) — Design

Date: 2026-11-16 · Status: written after the owner asked, on 2026-11-16, for "uma secção em que se plotam dois indicadores no mesmo gráfico, para analisar efeitos relacionados", with "indicadores apropriados" chosen by the planner. The owner then asked for the editorial composition first; that shipped the same day. This spec is the comparison half of that request.

## 1. Intent, and what it is not

A section of the public site where a named pair of indicators is drawn on one chart, so a reader can see two series move through the same period. Four things it deliberately is not:

- not a picker over the catalogue. Most of the base is one indicator across many countries; two-of-anything would turn spurious correlations into pages carrying the site's authority.
- not a data edit, not a derived series, not a migration.
- not a free choice of scale mode at request time.
- not a place where a withheld source becomes visible. The REN MIBEL price stays withheld inside a comparison exactly as it is outside one.

## 2. State this design builds on (measured on production, 2026-11-16 13:00 UTC)

Served, `kind = 'fetched'`, redistributable: eredes 3 series / 65,343 values; worldbank 930 / 45,915; eurostat 328 / 45,193; ine 41 / 12,034; bportugal 10 / 4,318. FRED, OECD and REN are served 0 and never plotted.

Common periods, measured with the intersection query in `references/comparison-charts.md`:

| pair | series | common | span |
|---|---|---|---|
| inflation / unemployment | `ine.hicp_yoy.PT` + `ine.unemployment_monthly.PT` | 344 | 1998-02 … 2026-09 |
| euribor / inflation | `bportugal.euribor_3m.EA` + `ine.hicp_yoy.PT` | 359 | 1996-12 … 2026-10 |
| credit / rate | `bportugal.euribor_12m.EA` + `bportugal.credit_housing.PT` | 393 | 1994-01 … 2026-09 |

Both series of every pair are monthly and every one of them carries values. Units: `%` and `%` for the first two, `%` against `MEUR` for the third. Geographies: `PT`+`PT`, `EA`+`PT`, `EA`+`PT`.

Not included, and why: the E-REDES production components (`eredes.production_market.PT` against `eredes.production_special.PT`, 21,781 common 15-minute intervals, and the two are an exact decomposition - `total = market + special` in 21,781 of 21,781 rows, no negatives). Fifteen-minute density is too much for one chart and turning it into weeks is an aggregation method the site does not have yet; a comparison page that silently resamples would be the first place on the site where a plotted number is not a number the publisher printed. It is the natural fourth pair, with its own decision.

## 3. Decisions

### D1. Pairs are curated in the catalogue, never selected at request time

`presentation/catalog/pt.py` gains `COMPARISONS`: an ordered mapping from slug to a frozen record `{series_a, series_b, title, subtitle, mechanism, scale, caption_note}`. The route is `/comparar/{slug}`; an unknown slug is 404. There is no query parameter that names a series. Adding a pair is a catalogue entry plus the evidence row in this spec.

`en.py` carries the same keys with empty tables, as every other catalogue does, so an accidental English render fails cleanly.

### D2. Scale is a property of the pair

`scale` is `one_axis` or `dual_axis`, written in the catalogue:

- `one_axis` requires both series to share the same unit token, and requires that both are rates of the same kind (a rate of change against a rate, or two levels). A level and a year-on-year rate may share the `%` token and still never share an axis. The unit half is asserted against the served data by a test; the "same kind" half is a curation rule checked at review, because the data layer stores a unit code and nothing that says what kind of thing the number is, and inventing that metadata for three pairs would be a field nobody else reads.
- `dual_axis` is allowed only for a curated pair, is labelled on both sides, and its caption states that the two magnitudes are not comparable and that the chart shows direction, not size. The pair's `scale` decides the chart mode; the unit comparison is only the chart's fallback when no mode is given.

Pairs 1 and 2 are `one_axis`; pair 3 is `dual_axis`.

### D3. Only common periods are drawn, and the dropped ones are stated

The page plots the intersection of the two served period sets. Each series' own span and the number of periods it contributes that the other lacks are printed as the alignment statement ("393 períodos comuns entre 1994-01 e 2026-09; 169 períodos do crédito e 1 da Euribor ficam fora"). No interpolation, no carry-forward, no resampling.

The table behind the chart renders the same rows the chart draws, so a reader can always check the drawing.

### D4. Exact tokens, both provenances, one page

Values reach the page as the stored `value_text` through `format_value`; the axis is the only rounded thing. Each series keeps its own provenance block - publisher, attribution, receipt date, run id, payload hash, verification date and whether that value was sampled - and a link to its series page. The page states the mechanism in one sentence a reader could check, and never claims causation.

### D5. No schema change, no new SQL in `app/`

The read path is composed from methods that already exist: `public_series`, `public_series_values`, `public_provenance`. `reads.py` aligns the two lists in Python; `app/` keeps zero SQL. No migration, no new view, no write path.

Consequence: the release is code-only in the existing `prumo` container - `bash -lic 'dc-web-up prumo'` - and rollback is the previous commit plus the same command. The worker and the backoffice are not restarted.

### D6. The navigation gains one item, and the golden capture is re-taken once

`NAV` gains `("/comparar", "Comparações")` after Energia. That changes `base.html`, so **every page's HTML changes**, including the home rendered from the code list. `tests/app/golden/home_before_editorial.html` is a byte-identical capture from the deployed commit `7e563b2` and its docstring says it is never refreshed.

It is refreshed here, once, and the reason is auditable: the new capture `tests/app/golden/home_code_list.html` is rendered from a detached worktree of the *implementation* commit with no composition published, and the commit shows the two golden files differing in exactly the navigation line. The test keeps doing its job afterwards - any unintended change to the home with no composition still fails the byte comparison. A reviewer must check that the diff between the two golden files is only the nav item.

### D7. Fifteen-minute series and derived keys are out of scope

No aggregation and no calculated series on a comparison page in v1. Both are separate decisions: aggregation invents a number, and a calculated series on a comparison page would need the caveat machinery to fit in a caption.

## 4. Pages

### `/comparar` — index

One `<h1>`, one introductory sentence from the catalogue, then one block per pair: title, the mechanism sentence, the span and the number of common periods, and a link. No values on the index: it is a table of contents, not a dashboard.

### `/comparar/{slug}` — a pair

1. Breadcrumb: Início / Comparações / title.
2. `<h1>` and subtitle; a meta line naming both series, their units, their frequency and their geographies (`Área do euro` against `Portugal` must be visible, not implied).
3. The chart: two lines, distinct CSS classes, legend naming both, `aria-label` stating both series and both units; the accessible name is the page title plus both series titles.
4. Table fallback in `<details>`: period, value A with unit, value B with unit.
5. The alignment statement and the caption note.
6. Two provenance blocks, side by side, one per series, each linking to its series page.

## 5. Chart

New function in `app/charts.py`:

```python
two_series_chart(points, *, frequency, title, labels, unit_a, unit_b=None, dual=None,
                 width=WIDTH, height=HEIGHT) -> Markup
```

`points` are dicts with `period`, `a` and `b` (the stored tokens), already aligned by the read layer.

- `dual` is the pair's `scale`: `True` forces two axes even when both units read the same; `None` falls back to comparing `unit_a` and `unit_b`.
- `unit_b` set → dual axis: left ticks from series A, right ticks from series B, gridlines from the left axis only, each side labelled with its unit. The two independent scales are never mixed into one tick set.
- Both lines are `path.chart-line` with an additional class (`chart-line-a`, `chart-line-b`) so colour comes from CSS, never from a `style` attribute.
- Each point carries a `<title>` naming its series, period, exact value and unit.
- Legend is markup outside the SVG, so it reflows at 390 px.
- Empty when either series has no numeric point.
- Last-value labels: one per line, offset so they do not overlap when the two lines end close together; if they would collide, the second is dropped and the legend carries the value instead. Never two labels stacked on top of each other.

## 6. Read layer

`app/reads.py`:

```python
@dataclass(frozen=True)
class ComparisonSummary:  # index block
    slug, title, mechanism, span_text, common_text
@dataclass(frozen=True)
class ComparisonSeries:
    title, source_title, unit_text, frequency_text, geography_text, latest_text, provenance, url
@dataclass(frozen=True)
class ComparisonPage:
    slug, title, subtitle, mechanism, chart_points, table_rows, alignment_text,
    caption_note, a: ComparisonSeries, b: ComparisonSeries, scale, chart_title
```

- `comparisons_index(db)` returns one summary per catalogue pair, reading only what the summary needs (span and common count need both value lists; the index is three pairs, so six list reads per request - measured, see §9).
- `comparison_page(db, slug)` returns `None` for an unknown slug or for a pair whose series is not published (a series that lost its licence disappears with 404, not with a half-drawn chart).
- The alignment counts are computed from the two lists, never from a stored number.

## 7. Tests

Route and read tests (synthetic DB from `tests/app/conftest.py`, extended with a second unit and a second geography):

1. `/comparar` answers 200 and lists exactly the catalogue's pairs, in order.
2. Each pair answers 200; the page contains both series' exact stored tokens and both publishers.
3. Unknown slug → 404. A pair whose B series is withdrawn from the served view → 404, not a one-line chart.
4. Both mount prefixes: links and assets carry `/dados` when `X-Forwarded-Prefix` says so.
5. Unusable database → 503 page, and `MissingText` → 503 with a log line.
6. No `<script>`, no `style=`, CSP header present, `Vary: X-Forwarded-Prefix` present.
7. Alignment: common count and dropped counts match a hand-built fixture where A has two extra periods and B one.
8. One-axis vs dual-axis: a catalogue test asserts `scale == 'one_axis'` implies equal unit tokens and both rate-or-level of the same kind; `dual_axis` implies different units and a caption note.
9. Catalogue completeness: every pair's two series resolve `series_title`, `source_title`, `unit_text`, `frequency_text` and `geography_text`; no pair names a withheld source; no slug repeats a title.
10. Chart unit tests: two paths rendered; one tick set in one-axis mode; two labelled axes in dual mode; empty state when one series has no numeric point; accessible name contains both series titles.
11. Header/nav: every page carries the Comparações link exactly once.

## 8. Proof on a copy of production

Read-only copy under `/home/joao/.hermes/cache/scratch/prumo-compare/`:

- all three pages answer 200 and contain the exact stored tokens for the first and last common period;
- the drawn point count equals the measured intersection (344 / 359 / 393);
- latency for `/comparar` and each pair, n=30 after warm-up, median and p95;
- the index is under 100 ms;
- the home with no composition is byte-identical to the new golden;
- grep the rendered HTML for dotted ids, `must confirm|pending|UNVERIFIED`, `<script>` and `style=`: zero hits.

## 9. Deploy

Code-only release in the existing `prumo` container, by owner authorization: merge to `main`, fast-forward the f0nix checkout, `bash -lic 'dc-web-up prumo'`. No migration, no worker or backoffice restart, database untouched. Rollback: previous commit and the same command.

## 10. Open decision for the owner

D2's `dual_axis` for the credit pair. The alternative is dropping that pair and shipping two same-unit pairs. The planner's default is to ship it, labelled on both sides, because the mechanism it shows - what a household pays against how much the country owes - is the one the owner named when he asked for "efeitos relacionados". If the two independent scales are unacceptable, the pair goes and nothing else changes.

## 11. Implementation notes (what changed while building, and why)

Three defects were found in visual QA against the production copy, after the code passed its own tests. All three are fixed in the same commit; each one is a thing a test would not have caught.

1. **The dual axis clipped its own labels.** With the single-axis right margin of 20 px the tick "150" rendered as "15" and the unit "milhões de euros" as "mi", which left the right axis reading 15 / 10 / 50 / 0 - non-monotonic and meaningless. A dual-axis chart now uses `RIGHT_DUAL = 104` and the unit label is anchored to the viewBox edge (text-anchor end at `width - 4`) so a long unit grows leftwards instead of past the border.
2. **The meta line repeated the geography.** `series_title` already ends with the region ("Taxa Euribor a 12 meses — Área do euro"), so appending `geography_text` printed "— Área do euro — Área do euro". The meta line is now title · frequency · unit, and the geography reaches the reader once, through the title. `ComparisonSeries` therefore carries no `geography_text`.
3. **Pair 3's title did not match its axis order.** It was "Crédito à habitação e taxa" while the rate is series A and the left axis; a reader meeting the legend sees the rate first. The title is now "Taxa e crédito à habitação".

One deliberate re-capture: `tests/app/golden/home_code_list.html` (see D6). The previous file, `home_before_editorial.html`, stays in the tree; `diff` between them is exactly one navigation anchor (plus the whitespace line the nav loop emits around it).

The independent review found five more, all closed in the fix commit:

4. **The table was capped at 60 rows** while the chart drew 344/359/393, which broke D3's promise that a reader can check any drawn point. Comparisons now render every plotted period; `TABLE_CAP` stays for series pages, where the table is a sample of a longer history and says so.
5. **Provenance described the series' newest value, not the value on the page.** `_comparison_side` used `public_provenance`, which is `ORDER BY period DESC LIMIT 1`, so a pair whose last common period was older than either series' newest cited the wrong run. The new `Db.public_provenance_at(series_id, period)` reads the record for exactly the period shown, and the block now carries the archived file hash and the "this value was / was not one of the sampled items" sentence, as the series page does.
6. **A common period with a non-numeric token was counted as plotted.** The chart silently dropped it while the page still called it the last common period. Alignment now keeps only periods where both tokens parse as finite numbers, and the note states how many common periods a publisher left without a number.
7. **A missing catalogue key answered 500.** `comparison_pair` now validates the seven keys and raises `MissingText`, which the app already maps to 503 with a log line; an unknown slug is still a 404.
8. **Two smaller ones from the same review:** `_year_indices` could raise `StopIteration` on an annual series missing a boundary year, and a one-period pair drew an invisible one-command path (it now gets a dot per line). Both fixed.


