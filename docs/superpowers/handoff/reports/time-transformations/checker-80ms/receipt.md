# Notebook time transformations - real-copy browser acceptance

- Result: **FAIL**
- Generated: 2026-11-20T17:23:42.094878+00:00
- Base: `http://127.0.0.1:8197`
- Proxy: `http://127.0.0.1:35411/dados`
- Database: `/home/joao/.hermes/cache/scratch/prumo-time-transformations/acceptance.sqlite3`
- HEAD: `bb4b0261048cfdef7d9cc1818a602fe13e82e91a`
- Asset manifest: `cdad76dba58f2b2122d17200a081b589e3f484a01a8efe5af947cfa7775d0697` (489 bytes)
- Bundle: `b7a4f50dbb09ad926d071d0264e2f16de19606807e96e418b407e3dcac4377b8` (509974 bytes), declared match=True

## Actual counts

- Pages loaded: 136
- Matrix cells: 110 (2605 assertions), failed cells: 0
- Functional checks: 223 (223 assertions), failures: 1
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
| mixed_ihpc_worldbank | ready | v2/calendar | 121 | 10 | 0 |
| mixed_ihpc_eurostat | ready | v2/calendar | 121 | 10 | 0 |
| annual_ihpc_eurostat | ready | v1/comparison | 11 | 10 | 0 |
| base100_gdp_pt_es | ready | v1/comparison | 11 | 10 | 0 |
| base100_six_gdp | ready | v1/group | 11 | 10 | 0 |
| pp_ihpc_unemployment | ready | v1/comparison | 11 | 10 | 0 |
| wrong_base | unavailable | - | - | 10 | 0 |
| rate_base100 | unavailable | - | - | 10 | 0 |
| interval_mix | unavailable | - | - | 10 | 0 |
| empty_group | empty | - | - | 10 | 0 |
| off | off | - | - | 10 | 0 |

## Blockers

- None.

## Failure details

- `mixed_touch:keyboard_tooltips`: [{"key": "End", "point": 120, "readout": "01/10/2026 - Taxa de variação homóloga do IHPC - Portugal - outubro de 2026: 3,9 %; PIB per capita - Portugal - sem observação nesta posição temporal", "aria": "01/10/2026", "tip": "01/11/2016 Taxa de variação homóloga do IHPC - Portugal - novembro de 2016: 0,5 % PIB per capita - Portugal - sem observação nesta posição temporal"}]

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
