# Notebook time transformations - real-copy browser acceptance

- Result: **PASS**
- Generated: 2026-11-20T18:01:56.272881+00:00
- Base: `http://127.0.0.1:8197`
- Proxy: `http://127.0.0.1:44901/dados`
- Database: `/home/joao/.hermes/cache/scratch/prumo-time-transformations/acceptance.sqlite3`
- HEAD: `b17901f0220f508aa246e419530dfaecd663652f`
- Asset manifest: `4c273da8a26251fc0a4e69e9a4618450a57e26aeb333f5613d4ce746a273e9de` (489 bytes)
- Bundle: `5ec098d90cb667f8f2486828a18274861e52a782a48319d457c0baf6e8eaec4b` (510109 bytes), declared match=True

## Actual counts

- Pages loaded: 136
- Matrix cells: 110 (2605 assertions), failed cells: 0
- Functional checks: 223 (223 assertions), failures: 0
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
- {"kind": "touch_tooltip", "point": 0, "visible_immediately": true, "hidden_after_ms": 225}

## Limits

- Shared edge, Authelia and production host configuration were not exercised locally.
- Human screen-reader acceptance remains a separate manual gate.
- The visual clipping review is recorded in visual-review.md.
