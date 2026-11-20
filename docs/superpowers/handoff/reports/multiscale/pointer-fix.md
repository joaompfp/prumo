# Pointer tooltip fix: final plotted point

## Symptom

On the real grouped-six chart at 390px and 1440px, moving the pointer from the middle of the
plot to the extreme last plotted x updated `.chart-readout` and the range to the final period,
but `.chart-tooltip` could still show the previous period. Pointer hover at the first plotted
edge could also leave the tooltip hidden.

## Cause

`locate(event)` chose the correct union row and called `show(point, false)`. That updated
`activePoint`, the range and the readout, but `show()` only dispatched `showTip` when `announce`
was true (keyboard and range input). Native ECharts axis hover does not always invoke the
formatter or keep the tooltip visible at the extreme symbols, so the visible tooltip could stay
on the prior row even though the adapter state had advanced.

## Fix

`tools/charts/src/adapter.js` now explicitly syncs the visible tooltip after a non-touch
`pointermove` or `pointerdown` locate:

- `locate` returns the chosen row and still updates the readout without touching aria-live.
- `syncTip` defers one `showTip` to a zero-delay task, after native pointer handling has run.
  This is needed at the plot edges, where native hover hides the tooltip again after the row is
  rendered. A burst of moves coalesces into the latest point.
- `showTip` remains the shared pixel-based endpoint clamp already used by keyboard and touch.
- `updateAxisPointer` ignores events while the explicit showTip action runs, preventing a
  feedback loop that could rewrite the chosen row.
- `pointerleave` cancels a pending sync and hides the tooltip. Touch movement stays inert and
  touch release keeps its exact `locate` plus `showTip` path.
- Pointer movement still does not write `.chart-live`; only keyboard and range input announce.

## Regression

`tests/app/test_group_interaction.py` now renders six periods and a responsive shell, then
checks pointer positions at the first, middle and last drawn x at 390px and 1440px. At each
position it asserts the selected range row and the exact text of every `.chart-tip-line`, not
only the readout.

Before the fix this test failed at the last point on both widths: the range selected row 5
while the tooltip still listed the row 4 period and values. It also failed at the first point
because no tooltip became visible. After the fix all positions pass.

## Verification

- `tests/app/test_group_interaction.py`: 6 passed.
- `tests/app/test_chart_interaction.py tests/app/test_calendar_interaction.py
  tests/app/test_group_interaction.py`: 22 passed.
- `tests/test_typography.py`: 18 passed with the rebuilt bundle hash.
- Real server at `127.0.0.1:18137`, grouped-six URL, 390px and 1440px: first, middle and last
  pointer positions all selected the expected row and showed the exact tooltip rows.
- Rebuilding `static/js/prumo-charts.min.js` twice produced the same SHA-256:
  `2330b172258ffed4ffd88bc7abe1d4e98f4a6d06f1a37292148770f1dac12157`.

## Files

- `tools/charts/src/adapter.js`
- `static/js/prumo-charts.min.js`
- `static/js/prumo-charts.manifest.json`
- `static/js/prumo-charts.NOTICE.txt`
- `tests/app/test_group_interaction.py`
- `tests/test_typography.py`
