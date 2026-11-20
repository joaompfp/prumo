# Notebook time transformations - real-copy browser acceptance

- Result: **FAIL**
- Generated: 2026-11-20T16:52:58.290270+00:00
- Base: `http://127.0.0.1:8197`
- Proxy: `http://127.0.0.1:45229/dados`
- Database: `/home/joao/.hermes/cache/scratch/prumo-time-transformations/acceptance.sqlite3`
- HEAD: `ea01c8039a0cf023b38cd88656dc1f75221cf234`
- Asset manifest: `ca5e58ac2bd7a647c5d0cf85044f5b7bb739ee507df5b33a739695e596ad2aa8` (489 bytes)
- Bundle: `d1bd4b27a97fc8b0195442c7cb50cfd2e1309a5943ce0158a920539936b2107c` (509616 bytes), declared match=True

## Actual counts

- Pages loaded: 127
- Matrix cells: 110 (2605 assertions), failed cells: 32
- Functional checks: 223 (223 assertions), failures: 4
- Screenshots: 9
- Database tables fingerprinted: 23, rows hashed: 777854
- Table fingerprints equal before/after: True
- Integrity check: ['ok']
- Foreign key violations: 0
- Matrix plot heights: min 264 px, plot top 365.765625 to 629.40625 px
- Matrix horizontal overflow maximum: 0 px
- Matrix fonts: readout min 25.245 px, ticks min 18.15 px, base control min 25.245 px

## Cases

| Case | State | Payload | Periods | Matrix cells | Failed cells |
| --- | --- | --- | --- | --- | --- |
| mixed_ihpc_worldbank | ready | v2/calendar | 121 | 10 | 4 |
| mixed_ihpc_eurostat | ready | v2/calendar | 121 | 10 | 4 |
| annual_ihpc_eurostat | ready | v1/comparison | 11 | 10 | 4 |
| base100_gdp_pt_es | ready | v1/comparison | 11 | 10 | 10 |
| base100_six_gdp | ready | v1/group | 11 | 10 | 10 |
| pp_ihpc_unemployment | ready | v1/comparison | 11 | 10 | 0 |
| wrong_base | unavailable | - | - | 10 | 0 |
| rate_base100 | unavailable | - | - | 10 | 0 |
| interval_mix | unavailable | - | - | 10 | 0 |
| empty_group | empty | - | - | 10 | 0 |
| off | off | - | - | 10 | 0 |

## Blockers

- Calendar x-axis labels do not cover the plotted history (6 ticks spanning 304 of 3652 days, last tick 2017 for 2016-2026).
- Canvas y-axis unit text is clipped or merged at the top edge in 32 matrix cells (base100 pair and six sides at all widths; mixed and annual charts at 320 and 390).

## Failure details

- `annual_ihpc_eurostat`: 4 failed cells at widths [320, 390] on ['direct', 'proxy']; ["axis title layout={'canvas_width': 284, 'left_unit_width': 15.854568481445312, 'runs': [[0, 37], [45, 72], [79, 159]], 'first_start': 0, 'first_width': 38}", "axis title layout={'canvas_width': 354, 'left_unit_width': 15.854568481445312, 'runs': [[47, 93], [101, 215]], 'first_start': 47, 'first_width': 47}"]
- `base100_gdp_pt_es`: 10 failed cells at widths [320, 390, 768, 1440, 1920] on ['direct', 'proxy']; ["axis title layout={'canvas_width': 1122, 'left_unit_width': 203.7157440185547, 'runs': [[0, 63], [70, 165]], 'first_start': 0, 'first_width': 64}", "axis title layout={'canvas_width': 284, 'left_unit_width': 203.7157440185547, 'runs': [[0, 76]], 'first_start': 0, 'first_width': 77}", "axis title layout={'canvas_width': 284, 'left_unit_width': 203.7157440185547, 'runs': [[1, 72]], 'first_start': 1, 'first_width': 72}", "axis title layout={'canvas_width': 354, 'left_unit_width': 203.7157440185547, 'runs': [[0, 80]], 'first_start': 0, 'first_width': 81}", "axis title layout={'canvas_width': 731, 'left_unit_width': 203.7157440185547, 'runs': [[0, 20], [27, 122]], 'first_start': 0, 'first_width': 21}"]
- `base100_six_gdp`: 10 failed cells at widths [320, 390, 768, 1440, 1920] on ['direct', 'proxy']; ["axis title layout={'canvas_width': 1122, 'left_unit_width': 203.7157440185547, 'runs': [[0, 63], [70, 165]], 'first_start': 0, 'first_width': 64}", "axis title layout={'canvas_width': 284, 'left_unit_width': 203.7157440185547, 'runs': [[1, 72]], 'first_start': 1, 'first_width': 72}", "axis title layout={'canvas_width': 354, 'left_unit_width': 203.7157440185547, 'runs': [[0, 80]], 'first_start': 0, 'first_width': 81}", "axis title layout={'canvas_width': 731, 'left_unit_width': 203.7157440185547, 'runs': [[0, 20], [27, 122]], 'first_start': 0, 'first_width': 21}", "axis title layout={'canvas_width': 731, 'left_unit_width': 203.7157440185547, 'runs': [[0, 23], [30, 125]], 'first_start': 0, 'first_width': 24}"]
- `mixed_ihpc_eurostat`: 4 failed cells at widths [320, 390] on ['direct', 'proxy']; ["axis title layout={'canvas_width': 284, 'left_unit_width': 15.854568481445312, 'runs': [[0, 37], [45, 72], [79, 159]], 'first_start': 0, 'first_width': 38}", "axis title layout={'canvas_width': 354, 'left_unit_width': 15.854568481445312, 'runs': [[47, 93], [101, 215]], 'first_start': 47, 'first_width': 47}"]
- `mixed_ihpc_worldbank`: 4 failed cells at widths [320, 390] on ['direct', 'proxy']; ["axis title layout={'canvas_width': 284, 'left_unit_width': 15.854568481445312, 'runs': [[18, 79], [86, 115], [123, 159]], 'first_start': 18, 'first_width': 62}", "axis title layout={'canvas_width': 354, 'left_unit_width': 15.854568481445312, 'runs': [[56, 135], [142, 171], [179, 216]], 'first_start': 56, 'first_width': 80}"]
- `mixed_wb:x_axis_coverage`: {"ticks": 6, "span_days": 304.0, "domain_days": 3652.0, "span_ratio": 0.083, "first_tick": "2016", "last_tick": "2017", "first_period": "01/10/2016", "last_period": "01/10/2026"}
- `mixed_euro:x_axis_coverage`: {"ticks": 6, "span_days": 304.0, "domain_days": 3652.0, "span_ratio": 0.083, "first_tick": "2016", "last_tick": "2017", "first_period": "01/10/2016", "last_period": "01/10/2026"}
- `mixed_touch:x_axis_coverage`: {"ticks": 6, "span_days": 304.0, "domain_days": 3652.0, "span_ratio": 0.083, "first_tick": "2016", "last_tick": "2017", "first_period": "01/10/2016", "last_period": "01/10/2026"}
- `fallback:nojs`: [{"svg_x_axis": {"span": 50.900000000000006, "years": ["2016", "2016", "2017", "2017", "2017", "2017"]}}]

## Screenshots

- `pib-per-capita-mixed-1440.png`
- `pib-per-capita-mixed-390.png`
- `annual-hicp-gdp-1440.png`
- `annual-hicp-gdp-390.png`
- `base100-gdp-pt-es-1440.png`
- `base100-gdp-pt-es-390.png`
- `pp-hicp-unemployment-1440.png`
- `pp-hicp-unemployment-390.png`
- `base100-six-sides-1440.png`

## Observations

- {"kind": "touch_tooltip", "point": 120, "visible_immediately": true, "hidden_after_ms": null}
- {"kind": "touch_tooltip", "point": 0, "visible_immediately": true, "hidden_after_ms": 200}

## Limits

- Shared edge, Authelia and production host configuration were not exercised locally.
- Human screen-reader acceptance remains a separate manual gate.
- The visual clipping review is recorded in visual-review.md.
