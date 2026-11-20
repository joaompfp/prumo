# Multiseries charts on two scales and Portuguese comparisons

Owner authorizes implementation, commit, push, merge and production deployment. Baseline is main/pipeline-rebuild `68f6799`, with runtime `7690837`. This is an extension of the analytical-workspace roadmap after phase T.

## Acceptance contract

The Caderno retains twelve cards and at most six plotted series. Choosing two axes no longer implies exactly two series: series sharing a compatible native scale use the same axis. Compatibility includes unit, multiplier and base year, not merely a translated label. For three to six series, two distinct compatible groups map in stable first-appearance order to left and right. A selection requiring more than two groups is refused with actionable guidance and all cards retained. A single compatible group uses the common-scale setting; do not silently split or flatten deliberate axis choices. Existing two-series dual-axis links preserve their independent-axis semantics.

Axis membership is authoritative in the prepared model and is consumed identically by SVG geometry, ECharts payload, legend/readout and complete table. Axis domains include every member of that group. No renderer infers membership from series position, colour or unit text. Native sparse calendars, annual harmonisation and the bounded interval path retain their current data contracts. Approved base100 and percentage-point transforms keep their one-axis requirement. Raw values, missing cells, calculation evidence, publisher geography, licence/withdrawal gates and same-snapshot provenance remain intact.

Populate a discoverable Portugal-focused comparison section with several useful three-to-six-series configurations supported by currently eligible served data. Use actual source concepts, periods and units; describe euro-area rates accurately and avoid causal claims. Prefer reusable Caderno configurations and a clear edit/open-in-Caderno action over a second analytical calculation path. Keep existing pair/country routes intact. This release does not require a data migration or silently overwrite authored CMS documents.

## Delivery sequence

1. Refactor pure chart axis allocation into an explicit per-series contract; preserve existing pair/group output where the behavior is unchanged. Extend dense and sparse geometry, payload and local interactive adapter, with focused regression tests.
2. Integrate compatibility validation, actionable copy, axis membership and grouped scales into the notebook read service. Populate curated Portuguese comparisons, making each discoverable and editable in the Caderno. Exercise routes with eligible, withdrawn, empty, mixed-frequency, annual and over-scale selections.
3. Independent specification review, then quality review with correction loops. Controller runs the full offline suite and browser acceptance against an online backup of real production data. Inspect 320/390/768/1440/wide layouts, both mounts, exact point inspection, six series, SVG/no-JS/print, CSP and static Admin preview. Retain human screen-reader acceptance as an open manual gate.
4. Verify committed-tree completeness and exact-main hosted CI, merge/push, prebuild without changing bind-mounted live files, then deploy only public web and Admin static-preview consumer using existing f0nix aliases. Pin rollback images and verify actual new images, URLs, logs, protected schema/CMS fingerprints and unchanged worker identity. No shared-edge/authentication changes.
5. Update HANDOFF, operations receipt and the owner roadmap at `/home/joao/vaults/projects/prumo/roadmap-e-implementacao.md` with the installed outcome, exact evidence scope and public links.

## Evidence location

Implementation, review and installed receipts belong in `docs/superpowers/handoff/reports/multiscale/`. Use the runtime scratch directory only for isolated database copies and temporary servers. Never alter original statistical evidence to satisfy authored-text checks. Authored text/code contains no em dashes.
