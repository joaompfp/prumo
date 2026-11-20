# Notebook time alignment and analytical transformations

Date: 2026-11-20
Status: implementation and release authorized by the owner
Baseline: b6c9b42, installed runtime 050d69e

## Goal and scope

Allow the notebook to compare selected indicators with different publication frequencies, and offer explicit annual harmonisation and scale transformations. The owner's example is monthly Portuguese HICP year-on-year versus annual GDP per inhabitant. Preserve the approved plot-first layout, large type, carmim, exact original tokens, twelve cards/six chart sides and deliberate two axes. The owner authorized commit, push, merge and deployment; do not ask for release approval again within this schema-unchanged web/Admin scope.

No ingestion, source-data, worker, schema, CMS content, licence or shared-edge change. Existing pair/country/detail routes retain their statistical contracts and v1 payload. New computations are ephemeral analytical views, never publisher observations or worker-verified derived series. They must be labelled calculated, reproducible and independently checked before rendering.

## Native time alignment

Same-frequency original selections retain the existing common-period renderer and exact response contract apart from the new controls. Mixed A/S/Q/M/D selections use a new sparse calendar model, not a widened nullable dense model. Map native periods to their start day on a Gregorian calendar, merge cells starting on the same day, and retain each cell's native period and frequency. Explain that this position is a display convention, not a publication or measurement date. No interpolation, carry-forward, upsampling, invented monthly GDP, annual step/hold, aggregation or zero substitution.

A series line connects its own consecutive native observations even when other series have intervening points. Break only for a missing native period; missing cells from another frequency do not break a complete annual line. Mark actual observations. Do not fabricate common values at a cursor position. Tooltip, keyboard readout and full table name the original period of each present cell, or explicitly say no observation at this calendar position. Latest provenance and card chart-role labels use each side's own last plotted native period, not a fictitious common one.

PT15M remains restricted to the existing single UTC day and cannot be mixed or transformed. No silently dropped chosen side. A side without a finite drawable value in the selected window makes the whole chart unavailable with a useful reason, while cards remain.

Mixed windows use the latest finite observation start across the union, rolling back five/ten calendar years; max uses all finite histories. Filter on real calendar coordinates, never lexicographic comparisons between annual and monthly tokens. A derived annual view windows on its latest common complete year. Different native period bases remain explicitly identified, including a warning against reading annual and quarterly totals as directly equivalent.

## Annual harmonisation

Address `frequencia=original|anual`, default original. Annual data stays native. Subannual annualisation is allowed only through reviewed indicator-family policies, never inferred from a unit alone. Initial policies: arithmetic mean of monthly HICP year-on-year, unemployment rate and Euribor; end-of-year December observation for monthly housing/consumer credit and deposits; arithmetic mean of monthly IPI levels. Other native A series remain available unchanged. Unknown subannual concepts, daily, semester prices and PT15M are refused with a reader-facing explanation rather than a guessed method.

The mean of twelve monthly year-on-year inflation rates is NOT the official annual inflation rate. Label it verbatim as a calculated annual mean of monthly year-on-year rates, and say it is not the official annual inflation. Likewise, monthly unemployment mean is unweighted, not the official annual estimate. Native annual series are not labelled calculated when no transformation is applied.

Require all twelve finite canonical months for means and end-of-year policies; a missing, invalid, non-finite or duplicate input prevents that annual value. Incomplete years are omitted with explicit per-series counts; no partial-year means, annualisation or replacement. A native break status excludes that year's computed value. End-year output retains December's exact token but remains identified as a calculated view with the complete-year prerequisite.

## Scale and base

Address `transformacao=original|base100|pp`, default original; `base=YYYY` optional. Transformations in this release require annual frequency, providing a single unambiguous base year for all selected sides. Invalid/repeated parameters fail as a generic 404 before opening the database. A valid but statistically unsupported choice is a 200 unavailable chart with explanation and unchanged cards.

Base 100 is only for reviewed level families, including GDP per inhabitant/current levels, price levels, population and credit/deposit/IPI levels; reject percentages, rates, balances, growth and unknown concepts. Require every base value strictly positive. Formula: 100 * value / base. Negative subsequent levels remain mathematical results but are not coerced or hidden. All sides use the same common year and one common index axis; the caller must select common scale rather than silently replacing a requested dual axis.

P.p. is only for reviewed percentage-rate families (HICP year-on-year, unemployment and Euribor). Formula: rate - base_rate. A zero or negative base is valid. The resulting axis is points percentage, not percent change. Mixed rates/levels and unknown concepts are refused.

An explicit base must exist in every eligible annual history, even if outside the display window. Otherwise use the first common complete year within the chosen window, with that auto-base stated next to the chart. Never silently substitute an invalid explicit base. Preserve base/frequency/transform settings in search/add/remove/off/empty/native form/share flows.

## Calculation and evidence

Pure domain module outside HTTP/persistence performs calendar parsing, reviewed method selection, annual grouping and transformations. Immutable inputs carry original series/period/token/status references. Decimal calculation uses a local fixed precision; independently recompute every calculated output with Fraction and compare the declared quantized result. Non-terminating results are half-even to six decimal places, with rounding explicitly disclosed. Original values are never reformatted from floats and are never rounded or stored differently. Geometry alone uses float.

Every calculated point retains every source input plus the base inputs if transformed. Provide a complete disclosure with the formula/method, original input periods, exact values, flags and links to each source series. Last-point and base evidence must resolve to each actual input period/run, not pretend a January or annual output was publisher-verified. Preserve original series CSV exports without adding transformed values to them. No transformed CSV is advertised in this release.

## Rendering and interaction

Add a sibling calendar chart model and payload v2 for sparse observations; keep dense models/payload v1 byte-compatible. Share pure axis/domain/tick primitives and render SVG from the same model as ECharts. The v2 adapter accepts finite or null cells, independent per-series gap boundaries and explicit per-cell native period labels. A null cell is not zero and is not an inspectable observation. One union row is one keyboard position; tooltip/readout must show missing positions explicitly. Two native sides can use deliberate dual axes with correct units/order. Up to six compatible or base100/pp sides share one axis.

Use safe DOM text nodes for exact readouts/tooltips, local pinned rebuilt bundle, unchanged strict CSP, full accessible SVG/no-JS/failed-bundle/print alternatives and complete tables. In transformed views show calculated badge/method/base and link to originals in print as well as interactive mode. Do not shrink typography or move the plot behind settings.

## Acceptance and release

Refactor boundaries first and preserve existing dense goldens. Unit tests include canonical dates/leap days, annual/monthly/quarter/semester collisions, native gaps, duplicate/nonfinite values, complete/incomplete years, known/unknown policies, zero/negative base, independent Fraction disagreement and explicit/automatic base. Route tests cover all query validation and state-preservation paths, same-snapshot eligibility, withdrawn/withheld originals and protected-data fingerprints.

Browser acceptance on a real production copy covers the owner's mixed pair, annual calculated pair, compatible base100 and pp examples, six sides, deliberate dual axes, wrong choices, no-JS/blocked/print, pointer/touch/keyboard exact values, missing cells, complete tables, mobile and both mount prefixes. Independent spec review precedes quality review. Controller owns full offline suite, clean committed-checkout and exact-main CI gates.

Release uses existing f0nix aliases, mount-safe detached prebuild, pinned rollback images and readback of actual installed image/health/content. Only public web and the Admin static-preview consumer change; capture and prove unchanged worker identity/restarts, schema/migrations and authored CMS fingerprints. No live CMS publication. Update handoff, operations and owner roadmap with installed scope and remaining human accessibility gates.
