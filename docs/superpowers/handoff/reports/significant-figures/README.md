# Four-significant-figure presentation

The owner corrected the fixed two-decimal policy: normal statistical readings should show at most four significant figures, with decimal places determined by magnitude. The existing shared localization boundary was retained. No storage, formula, geometry, CSV, source collection, CMS composition, schema, authentication or shared-edge change belongs to this correction.

## Contract

`app.formatting.format_value` rounds Decimal text with HALF_UP and Portuguese separators. It preserves integer place-value zeros, removes redundant fractional zeros and never rounds a tiny nonzero value to zero. Compact scientific notation covers extreme magnitudes. Counts, identifiers, dates and original-value evidence remain exact. `format_axis` shares the significant-figure rule, with compact scientific text for small ticks. Public routes, authored CMS charts and static previews consume the same preparation.

Examples: `2.35673648910157` -> `2,357`; `80.7926829268293` -> `80,79`; `0.0123456` -> `0,01235`; `12345` -> `12 350`. Full policy: [numeric display](../../../../data/numeric-display.md).

## Verification before release

Specification review initially found stale evidence assertions. These were corrected without changing any original-token checks, and the scoped independent specification re-review passed. Independent quality review approved the formatter after decimal/context/scale edge probes; its untracked-golden warning is covered by explicit staging and committed-checkout acceptance.

Controller final focused gate passed 248 tests covering display/evidence, chart/calendar, annual analysis, typography and backoffice boundaries. The additional legibility-assets gate passed seven tests. Ruff passed on app, ingest, presentation, backoffice and tests. The initial broader 1,016-test run had 1,009 passes and seven failures, all stale display/golden expectations, before those expectations were corrected. That earlier run is not represented as an all-green full suite. A fresh exact-release hosted suite remains the release gate.

The old dual-axis SVG capture is preserved byte-for-byte in `tests/app/golden/charts/pre_significant_figures/cmp_dual.svg`. Its successor changes only three tick texts; a new XML assertion pins every element, attribute, tail and every other text, proving unchanged geometry.

Real archived-production-copy browser acceptance passed 130 checks across eight reported-example/viewport cases, plus home, catalogue, Caderno, published authored comparisons, calculated detail, methodology and no-JavaScript fallback. The entire isolated database file stayed byte-identical. No application errors, external requests or warnings occurred. The new browser helper is [browser_check.py](browser_check.py); local receipt and captures were collected under `/home/joao/.hermes/cache/scratch/prumo-significant-20261125/browser-local` and are archived with the release evidence.

This acceptance verifies the display policy, not human screen-reader use. The final clean committed checkout passed 255 affected tests and broader ruff. Exact-release CI and installed behavior are recorded separately in [installed.md](installed.md); the hosted suite passed 3,364 tests and the installed browser gate passed 255 checks. Earlier failures retain their original scope rather than substituting for this fresh release evidence.
