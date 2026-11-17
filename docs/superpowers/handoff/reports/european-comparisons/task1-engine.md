# Task 1: shared multi-series preparation and rendering

## Outcome

The comparison engine now has one ordered, bounded series/value representation that both the SVG
renderer and the interactive payload loop over. Existing pair output and CMS behavior are
unchanged, including the reviewed SVG captures, and a new bounded three-to-six series factory
uses the same domains, ticks, calendar positions and gap helper.

Code commits:

- `dc6a43e` `refactor: represent comparison charts as ordered series values`
- `e63692e` `feat: add bounded country group charts on the shared engine`

No goldens were refreshed. No changes were made to `app/reads.py`, `app/main.py`, catalogues,
CMS files, registry, schema or data.

## RED and GREEN receipts

Baseline pair pinning, before the refactor:

```text
.venv-ci/bin/python -m pytest tests/app/test_chart_engine.py -q
2 passed
```

The two baseline tests pin the reviewed `cmp_dual.svg` bytes and the exact dual-axis payload
shape. They were green before the refactor by design, because they capture existing behavior.

Refactor commit, focused suite:

```text
.venv-ci/bin/python -m pytest tests/app/test_chart_model.py tests/app/test_interactive.py tests/app/test_comparisons.py tests/app/test_chart_engine.py -q
67 passed, 1 warning in 46.63s
```

A detached `a3445e8` worktree rendered the same canonical dual pair, and `cmp` reported the
combined SVG plus normalized payload byte-identical to the current engine.

Extension RED receipt, produced by running the finished group test file against the
refactor-only commit in a detached worktree:

```text
.venv-ci/bin/python -m pytest tests/app/test_chart_engine.py -q
collected 0 items / 1 error
ImportError: cannot import name 'group_chart' from 'app.charts'
```

Extension GREEN, same focused command after `group_model`, the renderer wrapper, adapter, styles
and bundle were added:

```text
.venv-ci/bin/python -m pytest tests/app/test_chart_model.py tests/app/test_interactive.py tests/app/test_comparisons.py tests/app/test_chart_engine.py -q
82 passed, 1 warning in 45.20s
```

Related chart and CMS regression pass:

```text
.venv-ci/bin/python -m pytest tests/app/test_charts.py tests/app/test_chart_layout.py tests/app/test_chart_interaction.py tests/app/test_legibility_review.py tests/app/test_cms_reads.py tests/app/test_cms_home.py -q
59 passed, 1 warning in 77.14s
```

Lint and JavaScript syntax:

```text
.venv-ci/bin/python -m ruff check app/chart_model.py app/charts.py app/interactive.py tests/app/test_chart_engine.py tests/app/test_interactive.py
All checks passed!

node --check tools/charts/src/adapter.js
exit 0
```

The full controller suite was not run here, as instructed.

## Stable API

### Group factory

```python
def group_model(
    points: list[dict],
    *,
    frequency: str,
    title: str,
    labels: tuple[str, ...],
    unit: str = "",
    width: int = WIDTH,
    height: int = HEIGHT,
) -> ComparisonModel | None
```

`points` is ordered oldest first. Each row is:

```python
{"period": "2024-S1", "values": ["0.2315", "0.2100", "0.2500"]}
```

`values` holds the exact stored publisher tokens in `labels` order. Labels must be three to six
unique, non-empty strings. A row whose values length differs from the label count, a row without
a period, a count outside 3 to 6, duplicate labels, blank labels or non-text tokens raise
`ValueError` because they are authored-definition faults. A row with any missing, non-finite or
`None` value is dropped whole, never one country alone. If no row remains, the factory returns
`None`. Periods are kept in caller order; gaps are detected by the existing
`expected_step`/`break_indices` helpers.

The returned `ComparisonModel` has:

- `kind == "group"`, `dual is False`, `ticks_b == ()`, one shared axis from `lo_a` to `hi_a`
- `labels`, `unit_a == unit_b == unit`, and `units` repeated in label order
- `styles == ("g0", ...)` with `g0` first
- `points[*].values`, an ordered tuple of `SeriesValue(number, value_text, value_display, y)`
- exact `value_text` tokens and `format_value` display strings
- `marks` with collision-free last-value labels for groups
- `breaks`, `x_ticks`, `last_x`, `last_anchor` and `last_dx` from the pair engine

Renderer wrapper:

```python
def group_chart(
    points: list[dict],
    *,
    frequency: str,
    title: str,
    labels: tuple[str, ...],
    unit: str = "",
    width: int = WIDTH,
    height: int = HEIGHT,
) -> Markup
```

### Pair compatibility

`comparison_model` keeps its exact signature and output. Pair consumers retain:

- `point.a` and `point.b` properties over `point.values`
- `ComparisonValue` and `ComparisonPoint` aliases
- `model.unit_a`, `model.unit_b`, `model.ticks_a`, `model.ticks_b`, `model.lo_a`, `model.hi_a`,
  `model.lo_b`, `model.hi_b`, `model.interval_a`, `model.interval_b`, `model.labels` and
  `model.marks`
- existing `a`/`b` ink and red styles and dual-axis geometry

The generic `_comparison_model` is internal. `ComparisonModel.styles` is the only new public
model field; `ComparisonModel.units` is a property.

Pair SVG and payload bytes are guarded by `tests/app/test_chart_engine.py`; the pair payload
assertion includes top-level key order and exact nested values. Pair marks also keep their
reviewed selection rule: A always, B only when the two points are at least 30 units apart.

### Interactive payload

Pair and line payload fields are unchanged. A group payload adds the existing `style` field with
`g0` to `g5` and an explicit `axis: 0` on every series entry. It still carries exactly one item
in `axes`, `y` and `display` rows of length N, and `breaks` indices that address existing points.
The adapter rejects more than two axes, rejects a `group` payload without exactly one axis, and
falls back to ink for an unknown style.

## Styles and assets

Group style keys are `g0` to `g5`. `g0` is Carmim via `var(--accent)`. The remaining styles use
`--chart-series-2` to `--chart-series-6` with distinct dash arrays in both SVG CSS and the ECharts
adapter:

| Style | Colour | Dash |
|---|---|---|
| g0 | Carmim | solid |
| g1 | blue | 6 3 |
| g2 | amber | 2 3 |
| g3 | green | 8 3 2 3 |
| g4 | purple | 12 4 |
| g5 | teal | 1 4 |

Pair `chart-line-a`, `chart-line-b`, `swatch-a` and `swatch-b` rules are byte-identical to the
previous CSS.

Pinned bundle rebuild:

```text
node tools/charts/build.mjs
built static/js/prumo-charts.min.js: 506595 bytes, debf2758f06e, gzip 173122
```

Manifest `sha256` is `debf2758f06efd3ec451bc4972d5bfc38c66e954f85bb352cdb3c3fc957b4e1d`, matching
the committed asset. ECharts 6.1.0, ZRender 6.1.0, tslib 2.3.0 and esbuild 0.25.12 are unchanged.
Licence texts under `static/js/licenses/` were copied by the pinned build and are content-identical.

## Test coverage added

`tests/app/test_chart_engine.py` adds:

- pair SVG byte equality against `cmp_dual.svg`; pair payload exact shape and key order
- N = 3, 5 and 6 group models and SVG counts
- invalid counts 0, 1, 2 and 7
- missing values, wrong row length, missing period, duplicate labels, blank labels
- exact stored tokens and display strings across model, SVG and payload
- dropped-period gaps, two-point gaps and single-point centring
- five identical last values producing one visible last label
- hostile labels escaped in SVG and retained inertly in the payload
- one explicit axis and N dimensions in the group payload
- CSS and adapter style/axis contract strings

## Pending risks

- Task 2 must call `group_model` or `group_chart` and add the route, template and Jinja global.
  This task deliberately did not touch `app/main.py` or `app/reads.py`.
- The factory drops invalid rows but does not return per-country dropped counts. Task 2 must
  compute and present those counts from its aligned read model before calling the factory.
- Group labels are passed through as authored short labels. Task 2 owns catalogue wording and
  country ordering.
- Browser visual acceptance of the five-country legend, canvas styles and tooltips is Task 3.
  This task verifies the payload contract, adapter source, CSS rules and JS syntax only.
- `ComparisonModel.units` uses `len(labels) == 2` to preserve pair units. A future two-series
  group is intentionally outside this factory's 3 to 6 bound.
- Pair last-label collision behavior is unchanged from the reviewed implementation, including its
  existing edge cases. Group labels use the stricter text-box collision test.
