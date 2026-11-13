# OECD series mapping notes (Task 15, 2026-11-12)

Scoped to the six active core monthly PT series. Ids, indicator keys, roles, geography,
frequency and units are preserved from the pre-Task-15 registry by owner instruction; only
`native_code`, `url`, `multiplier` and `seasonal_adjustment` were populated from publisher
evidence. Nothing was regenerated; no series was inactivated or replaced.

## native_code grammar (full publisher request identity)

`<agency>,<dataflow>/<key>` - the exact probed request identity on the SDMX data API
(`GET https://sdmx.oecd.org/public/rest/data/<agency>,<dataflow>/<key>`,
`Accept: application/vnd.sdmx.data+json;version=2.0`):

- `agency`: the OECD agency id (`OECD.SDD.STES` for the short-term economic statistics agency,
  `OECD.SDD.TPS` for labour-market statistics).
- `dataflow`: the publisher's `<DSD>@<DF>` token, e.g. `DSD_STES@DF_CLI` - the artifact id pins
  BOTH the data structure definition and the concrete dataflow (never a bare `DF_CLI` stub).
- `key`: the dot-joined pinned dimension codes in keyPosition order (one segment per series
  dimension; `_Z` = "not applicable"). The parse never reorders it; dimension ids differ per
  dataflow (e.g. DF_IALFS_UNE_M orders REF_AREA,MEASURE,UNIT_MEASURE,TRANSFORMATION,ADJUSTMENT,
  SEX,AGE,ACTIVITY,FREQ - NOT the STES order).

`url` is the canonical series request address (no window params - the source's default run is
full history; bounded runs add `startPeriod`/`endPeriod=YYYY-MM` at request time).

Dataflow identities in scope:

| dataflow token | agency | series |
|---|---|---|
| `DSD_STES@DF_CLI` | OECD.SDD.STES | oecd.cli.PT |
| `DSD_STES@DF_BTS` | OECD.SDD.STES | oecd.employment.PT, oecd.order_books.PT, oecd.production.PT, oecd.selling_prices.PT |
| `DSD_LFS@DF_IALFS_UNE_M` | OECD.SDD.TPS | oecd.unemp_m.PT |

## The cli identity trap: BCICP, not LI

`oecd.cli.PT` is **composite business confidence** (`MEASURE=BCICP`, "Composite business
confidence", `ADJUSTMENT=AA` amplitude adjusted, long-term average = 100 - publisher definition
archived as discovery item 20), living in the DF_CLI ("Composite leading indicators") dataflow.
It is NOT the headline composite leading indicator: the dataflow's own DEFAULT annotation is
`MEASURE=LI,ADJUSTMENT=AA,FREQ=M,METHODOLOGY=H` - a `LI` measure exists and a defaulted key
would silently serve it. The legacy name (backfill scripts called it `cli`) is kept as the id;
the semantic correction is documented here and in the registry comment. The registry unit prose
`index (100=trend)` matches the publisher definition quoted in item 20.

## Units / multiplier / adjustment (publisher evidence, archived fixtures)

Registry units are prose; the publisher channels expose codes/labels. Evidence pairing:

| series | UNIT_MEASURE (code / label) | registry unit | UNIT_MULT | ADJUSTMENT |
|---|---|---|---|---|
| oecd.cli.PT | IX / Index (with TRANSFORMATION=IX) | index (100=trend) | 0 | AA Amplitude adjusted |
| oecd.employment.PT | PB / Percentage balance | balance % | 0 | Y Calendar and seasonally adjusted |
| oecd.order_books.PT | PB / Percentage balance | balance % | 0 | Y |
| oecd.production.PT | PB / Percentage balance | balance % | 0 | Y |
| oecd.selling_prices.PT | PB / Percentage balance | balance % | 0 | Y |
| oecd.unemp_m.PT | PT_LF_SUB / Percentage of labour force in the same subgroup | % | 0 | Y |

- `multiplier: 0` records the observed `UNIT_MULT=0` ("Units") in every archived Task 15
  response: no scaling ever; any other multiplier fails closed at parse time.
- `seasonal_adjustment` is set to the publisher's ADJUSTMENT=Y label for BTS/unemployment.
  For `oecd.cli.PT` the field is left unset on purpose: `AA` is AMPLITUDE adjustment, not a
  seasonal adjustment - writing it into a field named `seasonal_adjustment` would mislabel it.
  The AA pin is carried by `native_code` (segment 6) regardless.
- `DECIMALS` (2 on CLI/BTS, 1 on unemployment) is a DISPLAY hint: CLI publishes 4-5-dp tokens
  (`99.83678`). Never round or truncate. No base year is invented (none published in channel).
- `BASE_PER` exists only in the CSV channel and is empty in every fixture row.

## Roles / cross-check

`oecd.unemp_m.PT` stays `cross_check` of `unemployment_rate.PT.M` - INE remains the primary
source (registry indicator pairing unchanged). The other five are `primary` for their
oecd-specific indicator keys.

## Status flags

Only `OBS_STATUS=A` ("Normal value") occurred in all 77 archived observations; the collector
maps `A -> normal`. The full OBS_STATUS codelist could not be enumerated within the discovery
budget (publisher codelist probe answered HTTP 404, discovery item 13), so ANY other code -
referenced or merely listed - fails closed (quarantine + format_change triage), never a
guessed mapping. The verifier (Part B) applies the same policy independently.

## Licence posture (serving gate, unchanged)

`redistribution_ok: false` stands. OECD T&C §3 grants data reuse for any purpose incl.
commercial with attribution + sub-licence acknowledgment propagation, subject to a PER-DATASET
third-party rights caveat (DF_CLI/DF_BTS/DF_IALFS_UNE_M clearance is the owner's outstanding
duty). CC BY 4.0 covers written content since 2024-07-01 only - not a blanket statistical-data
licence. Details: registry/licences-todo.md (oecd row) and discovery items 15-20.
