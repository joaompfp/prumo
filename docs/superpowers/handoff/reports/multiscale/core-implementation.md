# Multiscale core chart contract

Slice: explicit per-series axis membership for prepared chart models, SVG, interactive payload and
the local ECharts adapter. Baseline `68f6799`. The notebook read service, comparison routes,
templates, catalogue and shared handoff were not edited.

## Contract

`ComparisonModel` gains two authoritative per-series fields:

- `units: tuple[str, ...]`: the display unit for each series, in label order.
- `axes: tuple[int, ...]`: the axis membership for each series, one of `0` (left) or `1` (right).
- `axis_labels: tuple[str, ...]`: `("Eixo esquerdo"/"Eixo direito")` per series when dual,
  otherwise empty strings. Renderers and later template work read this one property instead of
  inferring membership from position, colour or unit text.

`CalendarModel` gains `axes: tuple[int, ...]`, `axis_labels` and `CalendarSeries.axis`.

Axis domains, ticks, intervals and y geometry are computed from every series assigned to that
axis. A later series with the domain extreme therefore expands its own axis. No value is
rescaled, interpolated, dropped or transformed. Rows still drop whole when any member is missing,
and sparse calendar cells stay `None`.

## Public preparation signatures

```python
chart_model.group_model(
    points, *, frequency, title, labels, unit="", units=None, axes=None,
    width=WIDTH, height=HEIGHT,
) -> ComparisonModel | None

charts.group_chart(
    points, *, frequency, title, labels, unit="", units=None, axes=None,
    width=WIDTH, height=HEIGHT,
) -> Markup

reads.prepare_group_chart(
    points, *, frequency, title, labels, unit="", units=None, axes=None,
    badge="", lang="pt",
) -> PreparedChart[ComparisonModel]

calendar_model.calendar_model(
    histories, *, labels, units, frequencies, title, dual=None, axes=None,
    width=WIDTH, height=HEIGHT,
) -> CalendarModel | None
```

Existing calls remain valid: `unit` still means every series shares that unit, and omitting
`axes` keeps a group on one shared left axis. `calendar_model(dual=True)` with two sides still
means independent left/right axes, including a same-unit pair; `dual=True` with three to six
sides now requires explicit `axes`, and `axes` wins only after agreeing with an explicit `dual`
flag.

Validation raises `ValueError` for authoring faults: wrong axis count, non-integer or boolean
axis values, an index outside `0`/`1`, an all-right assignment with no left member, wrong
per-series unit count, and a dual flag that contradicts the assignments.

## Rendering and payload

- SVG geometry uses `value.y` assembled from `axes[index]`; it never tests series position.
- `ComparisonModel.name` and `CalendarModel.name` enumerate every side. Mixed units are named
  per side, for example `Título: A (milhões de euros), B (%) e C (%)`.
- A grouped or sparse chart with more than two sides on two axes adds a visible
  `legend-axis` label and `data-axis` attribute to every legend item. The old two-series legend
  bytes are unchanged.
- Payload v1 group series carry `"axis": model.axes[index]`; payload v2 calendar series carry
  `"axis": item.axis`. Both expose one `axes` entry per used axis, including every member's
  values in the domain.
- The ECharts adapter uses `entry.axis` when declared. The positional fallback is restricted to
  legacy one-or-two-series line/pair payloads; a grouped payload without an explicit axis is
  rejected. Both validators reject an axis group with no member.

## Verification (actual results)

Focused model, renderer, payload, JS and digest gate:

```bash
.venv-ci/bin/python -m pytest tests/app/test_chart_model.py tests/app/test_chart_engine.py \
  tests/app/test_calendar_model.py tests/app/test_interactive.py \
  tests/app/test_group_interaction.py tests/app/test_calendar_interaction.py \
  tests/test_typography.py -q
```

Result: `123 passed, 1 warning in 51.76s` (the engine file alone also passed `30 passed`).

Application suite without browser-layout modules (the browser interaction modules were run
separately):

```bash
.venv-ci/bin/python -m pytest tests/app -q \
  --ignore=tests/app/test_chart_interaction.py \
  --ignore=tests/app/test_calendar_interaction.py \
  --ignore=tests/app/test_group_interaction.py \
  --ignore=tests/app/test_chart_layout.py \
  --ignore=tests/app/test_country_layout.py \
  --ignore=tests/app/test_legibility_review.py
```

Result: `419 passed, 1 warning in 372.60s`.

Browser adapter probes:

```bash
.venv-ci/bin/python -m pytest tests/app/test_group_interaction.py \
  tests/app/test_calendar_interaction.py tests/app/test_chart_interaction.py -q
```

Result: `4 passed` for the new grouped probe in its own run, and `16 passed` for the calendar
and existing pair interaction modules in `51.56s`.

Backoffice suite:

```bash
.venv-ci/bin/python -m pytest tests/backoffice -q -x
```

Result: `303 passed, 1 warning in 237.77s`.

Lint and bundle rebuild:

```bash
.venv-ci/bin/ruff check app/chart_model.py app/calendar_model.py app/calendar_svg.py \
  app/charts.py app/interactive.py app/reads.py tests/app/test_chart_engine.py \
  tests/app/test_calendar_model.py tests/app/test_group_interaction.py tests/test_typography.py
node tools/charts/build.mjs
```

Result: ruff `All checks passed!`; bundle `510271 bytes, 8e52625d93cd, gzip 174154`, manifest
sha256 `8e52625d93cd42ab367b082eb29d477db83e13d083c1d3185b1b4861b74f198e`.
`tests/test_typography.py` was updated to that exact rebuilt digest.

## Not in this slice

The notebook read service still refuses a dual scale with more than two sides. Wiring explicit
axes into `notebook_chart` and `calendar_notebook`, compatibility validation by unit/multiplier/
base year, curated comparisons and route/template work remain for the controller's next consumer
task.
