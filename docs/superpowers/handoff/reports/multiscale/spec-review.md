# Multiscale spec review: 68f6799..ecc0e93

Verdict: FAIL. The chart contract passes the scoped probes below, but the curated reader copy does not satisfy the required nominal-versus-real distinction.

## Blocker

1. `presentation/portugal_comparisons.py:101-107` and `:122-127` never state that
   `eurostat.gdp_per_capita_eur.PT` is at current prices, so the published cards do not distinguish
   nominal GDP per capita from a real measure. The only "preços correntes" evidence is internal
   (`docs/superpowers/handoff/reports/multiscale/curation.md:118,153`), which is not reader copy.
   `presentation/portugal_comparisons.py:79-84` also omits that the Euribor and 10-year yield are
   nominal rates. Add explicit "preços correntes (nominal)" and "taxas nominais" wording to those
   caveats.

Secondary copy defect in the same pass: `presentation/portugal_comparisons.py:62-64` calls the
section "séries portuguesas" although the first card contains the euro-area Euribor series. The card
caveat corrects this, but the section intro should not imply every member is Portuguese.

## Scoped probes (actual results)

- 12 cards / 6 plot: built a 12-series database and requested six explicit sides in interleaved
  first-seen order (`%`, `MEUR`, `%`, `MEUR`, `%`, `MEUR`). Result: 12 cards, 6 plotted series, 2
  axes, series memberships `[0, 1, 0, 1, 0, 1]`, 12 group checkboxes with 6 checked.
- `/comparar`: 3 Portugal cards and 3 canonical links with `grafico=on`, every `g`, and
  `escala=dupla`; links work with no prefix and with `/dados`. Setting
  `eurostat.gdp_per_capita_eur.PT` inactive hides both cards that use it and leaves the rates card.
- Registry check: all nine configured ids are `active`, `role=primary`; bportugal, eurostat and
  worldbank have `redistribution_ok=True`; units and frequencies match the three definitions.

## Passing contract points

- Allocation uses the raw `(unit, multiplier, base_year)` signature and first-seen `0`/`1` order;
  one group returns `one_group`, more than two returns `too_many_groups`, common mixed scales return
  `mixed_scale`, and all three refusals preserve cards and settings.
- Two-side dual charts remain independent even with equal units; common selections retain one axis;
  base100 and pp remain common-only.
- Prepared models own axis membership and group-wide domains; SVG legends, payload v1/v2 and the
  adapter consume `axes`/`axis`; sparse calendar cells remain null; the bounded interval path is
  unchanged.
- Tables, side values, SVG titles and provenance use the same prepared snapshot values. No CMS,
  authentication, migration or data-write change is present in the reviewed diff.

## Non-blocking notes for the quality pass

- `app/portugal_comparisons.py:93-97` checks every series against its group signature but does not
  require the two groups' signatures themselves to differ. A future definition with two identical
  groups would advertise a card whose link then refuses as `one_group`. The three current
  definitions have distinct groups.
- `app/calendar_notebook.py:275-283` re-reads `side.row` rather than the annualised output, so the
  check at `:430-435` cannot detect a future method that changes the effective output unit. Current
  reviewed methods preserve the source unit.
- `reads.catalogue` has a 30-second cache, so a just-withdrawn source can remain advertised on
  `/comparar` until the TTL; the link still fails closed. This is existing cache behavior.
