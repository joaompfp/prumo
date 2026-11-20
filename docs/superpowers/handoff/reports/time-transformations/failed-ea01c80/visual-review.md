# Visual review - notebook time transformations

Method: inspected the rendered PNG screenshots with vision, not only DOM measurements.
The neutral screenshots are at scrollY 0 with the settings disclosure closed.

## Blockers found by visual inspection

### 1. Mixed calendar x-axis labels collapse into 2016-2017

- `pib-per-capita-mixed-1440.png` and `pib-per-capita-mixed-390.png` show only the
  year `2017` on the x-axis, clustered at the left end of a 2016-2026 plot.
- The payload confirms the cause: six ticks whose x positions span 304 of 3652
  days (8.3% of the domain), with tick texts `2016, 2016, 2017, 2017, 2017, 2017`.
- This affects `mixed_ihpc_worldbank`, `mixed_ihpc_eurostat` and the mixed touch
  page. Because the same model feeds the server SVG, the no-JS and print chart
  inherits the bad x-axis coverage.
- Source location: `app/calendar_model.py`, `_x_labels`. After building
  `indices` as row indices, the six-label branch replaces that list with sampled
  positions in the range 0-10 instead of sampling the values in `indices`. The
  result is six labels over the first few months instead of one label per sampled
  year.
- Harness checks: `mixed_wb:x_axis_coverage`, `mixed_euro:x_axis_coverage`,
  `mixed_touch:x_axis_coverage` (span ratio 0.083, last tick 2017).

### 2. Long y-axis unit names are clipped or merged at the top edge

- `base100-gdp-pt-es-1440.png`: the chart unit `índice (base 2015=100)` is drawn
  as `:e (base 2015=100)`; the beginning is cut by the canvas boundary.
- `base100-gdp-pt-es-390.png`: the same label is reduced to `015=100)`.
- `base100-six-sides-1440.png`: the same clipped label appears above the plot.
- `annual-hicp-gdp-390.png`: the right-axis name `euros por habitante` begins as
  `e/€ros por habitante`; the leading glyph is merged with the left `%` title.
- `pib-per-capita-mixed-390.png`: the two titles read as one `% dólares dos EUA`
  line above the plot.
- `annual-320.png` and `mixed-euro-320.png`: at 320 px the right-axis name
  `euros por habitante` starts as `uros por habitante`, clipped by the canvas edge.
- The canvas paints a merged first text run in 32 matrix cells: base100 pair and
  six sides at all five widths, plus mixed and annual charts at 320 and 390, on
  both the direct and mounted-prefix origins.
- Source location: `tools/charts/src/adapter.js`, axis `nameTextStyle.align`.
  Right-aligning the left-axis name makes a long unit extend left beyond the
  canvas. At narrow widths the right-axis title is also placed close enough to
  the left title to merge with it. The server SVG starts the same text at the
  plot edge, so the enhanced canvas and the fallback diverge.
- Harness check: `axis title layout` in the matrix. It reads the painted text runs
  in the top band and compares the first run with the measured left-unit width.
  The affected cells report first runs 21 to 81 px wide against a 16 px `%` title,
  or a run starting at x 0 for the base100 `índice` label.

## Confirmed passing visual checks

- The plot and both y-axis tick sets are fully visible in the first 1440x900 and
  390x900 viewport on the annual, base100 and pp pages.
- The neutral screenshots show the plot before the settings disclosure, with the
  readout and legend below it.
- Annual x-axis labels are `2015`, `2020`, `2025`, spread across the full domain.
- Base100 and pp x-axis labels are also spread across the full domain.
- The six base100 series are distinguishable by color and dash pattern over the
  eleven annual points. The remaining four legend entries fall below the 900 px
  fold, which is ordinary scrolling, not chart clipping.
- Large type is intact: readout 25.245 px, chart ticks 18.15 px, base control
  25.245 px. No page-level horizontal overflow was measured at any of the five
  widths.
- Axis titles on the annual, pp, and mixed-worldbank 1440 charts are complete.

## Touch observation

The touch tap selects the correct union row on release. The tooltip content is
complete immediately after release, but ECharts hides it after the touch
pointerleave; the measured lifetime was 200 ms on the first point and remained
visible through the 400 ms sample on the last point in the final run. The
persistent touch readout remains correct. This is recorded as an observation,
not as one of the two blockers above.
