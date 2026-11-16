# Prumo - Two-series comparisons - Implementation plan

Spec: `docs/superpowers/specs/2026-11-16-two-series-comparisons-design.md`. Branch `pipeline-rebuild`. No migration, no schema change, no write path.

## Part 1 - catalogue

`presentation/catalog/pt.py`: `COMPARISONS` (ordered, three pairs) and `COMPARISONS_INTRO`; `en.py` the same names as empty tables. Each pair: `series_a`, `series_b`, `title`, `subtitle`, `mechanism`, `scale`, `caption_note`.

Acceptance: a registry-free catalogue test asserts every pair names two series, that `scale == 'one_axis'` implies equal unit tokens, that `dual_axis` implies different unit tokens and a non-empty `caption_note`, that no slug is repeated and no title collides with another pair.

## Part 2 - read layer

`app/reads.py`: `ComparisonSummary`, `ComparisonSeries`, `ComparisonPage`; `comparisons_index(db, lang)` and `comparison_page(db, slug, lang)`. Composition only from `public_series`, `public_series_values` and `public_provenance_at` (the period shown, not the series' newest); alignment computed in Python; `None` for an unknown slug or an unpublished series.

Acceptance: alignment counts on a fixture where A has one period B lacks and B has one A lacks; `None` when either series is withheld or has no served value; no new SQL in `app/`.

## Part 3 - chart

`app/charts.py`: `two_series_chart(points, *, frequency, title, labels, unit_a, unit_b=None, ...)`. One axis when `unit_b is None`; dual axis otherwise, gridlines from the left only, both sides labelled. Legend outside the SVG. Empty paragraph when nothing numeric.

Acceptance: two `<path>` elements with `chart-line-a`/`chart-line-b`; one tick set in one-axis mode, two labelled axes in dual mode; `<title>` per point carries the exact token; accessible name names both series and units.

## Part 4 - surface

`app/main.py`: nav item `("/comparar", "Comparações")`, routes `/comparar` and `/comparar/{slug}`. Templates `compare_index.html`, `compare.html`. CSS for legend, the two line colours, axis labels and the two provenance columns.

Acceptance: 200 for the index and each pair, 404 unknown slug, 503 unusable database, links carry the mount prefix, no `<script>`, no `style=`, CSP and `Vary` present; the home with no composition is byte-identical to a re-taken golden whose only difference from the 2026-11-16 capture is the nav item.

## Part 5 - gates

Full suite `.venv-ci/bin/python -m pytest -q`, `ruff check app/ ingest/ presentation/ tests/`, independent review, proof on a read-only copy of production (three pages, point counts 344/359/393, latency, token grep). Report; deploy only on the owner's word.
