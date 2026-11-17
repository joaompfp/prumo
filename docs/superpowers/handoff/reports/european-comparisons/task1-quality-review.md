# Task 1 quality review: shared chart engine

Verdict: APPROVED

Scope: `a3445e8..12cfbfa`, quality pass after spec PASS. No implementation changes were made.

## Evidence

- Pair output remains byte-identical. `tests/app/test_chart_engine.py:31` compares the full dual-axis SVG against `tests/app/golden/charts/cmp_dual.svg`, and `:38` proves plot plus legend concatenation is byte-equal. The payload shape and key order are pinned at `tests/app/test_chart_engine.py:44-86`.
- The shared factory at `app/chart_model.py:425-509` keeps one domain, tick, ordinal, position and break path for both SVG and payload. Group rows are validated at `app/chart_model.py:542-595`; wrong series counts, duplicate or blank labels, malformed row shapes and non-text tokens raise before any geometry is built.
- One shared axis is enforced end to end. `group_model` passes `dual=False`; `app/interactive.py:69-80` emits one axis and explicit `axis: 0` for every group series; `tools/charts/src/adapter.js:33-35` rejects more than two axes and rejects a group with anything other than one axis.
- Exact tokens and displays are preserved. `SeriesValue` stores the authored token and `format_value` display; `app/charts.py:148-162` and `app/interactive.py:104-107` both read the same tuple. `tests/app/test_chart_engine.py:203-230` checks tokens, displays, payload rows and SVG titles.
- Colour and pattern parity holds for the new styles. CSS at `static/css/prumo.css:543-575` defines `g0` through `g5`; `tools/charts/src/adapter.js:143-151` uses the same colours and dash arrays (`g1` 6/3, `g2` 2/3, `g3` 8/3/2/3, `g4` 12/4, `g5` 1/4). `g0` is Carmim through `--accent` in both places.
- Escaping and finite guards hold. Labels and units are escaped in SVG at `app/charts.py:148-162`; hostile labels are covered at `tests/app/test_chart_engine.py:233-247`. `decimal_or_none` rejects NaN and Infinity, and `_finite` declines browser enhancement for any non-finite value.
- Non-finite or missing group values drop the whole period, never one country. `tests/app/test_chart_engine.py:169-181` asserts the dropped semester and absent period both become line breaks.
- Last-value label suppression at `app/chart_model.py:477-493` is collision based for groups and preserves the reviewed pair rule exactly. `tests/app/test_chart_engine.py:195-201` covers identical values.
- No new external request, CSP relaxation or runtime data access was introduced. The adapter change is a local style map and axis selection.

## Tests

Command: `/home/joao/.local/bin/pytest tests/app/test_chart_engine.py tests/app/test_interactive.py -q`

Result: `36 passed in 19.25s` on Python 3.12.3, pytest 9.2.0. That is 17 engine tests plus 19 interactive tests, including the committed bundle fingerprint test.

## Non-blocking observations

- `static/css/prumo.css` `.swatch-g1` approximates the 6/3 line dash with a 6px on, 4px off gradient. This matches the existing pair-b legend approximation and does not affect SVG or canvas stroke parity.
- `tools/charts/src/adapter.js:208` falls back to the ink style for an unknown style key. Styles come from the engine constants, so this is a defensive default rather than an exposed input path.
- `_label_series` has a single-label branch that group validation makes unreachable. Harmless dead branch.
