# Notebook time transformations - real-copy browser acceptance

- Result: **FAIL**
- Generated: 2026-11-20T17:28:55.951106+00:00
- Base: `http://127.0.0.1:8197`
- Proxy: `http://127.0.0.1:44651/dados`
- Database: `/home/joao/.hermes/cache/scratch/prumo-time-transformations/acceptance.sqlite3`
- HEAD: `bb4b0261048cfdef7d9cc1818a602fe13e82e91a`
- Asset manifest: `cdad76dba58f2b2122d17200a081b589e3f484a01a8efe5af947cfa7775d0697` (489 bytes)
- Bundle: `b7a4f50dbb09ad926d071d0264e2f16de19606807e96e418b407e3dcac4377b8` (509974 bytes), declared match=True

## Actual counts

- Pages loaded: 113
- Matrix cells: 110 (2605 assertions), failed cells: 0
- Functional checks: 98 (98 assertions), failures: 0
- Screenshots: 0
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


## Observations

- None.

## Limits

- Shared edge, Authelia and production host configuration were not exercised locally.
- Human screen-reader acceptance remains a separate manual gate.
- The visual clipping review is recorded in visual-review.md.
