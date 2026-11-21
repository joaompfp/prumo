# Prumo analytical workspace roadmap

Date: 2026-11-19
Authority: owner request to create an improvements roadmap and begin implementation after the design council. This plan governs the next interface iteration; previous product milestones remain installed history, not unfinished features.

## Owner correction: CMS owns editorial comparisons (2026-11-21)

Phase D is prioritized ahead of further public configuration. Author series selection, axes, time transformations and copy in the authenticated CMS; the public comparison displays only its published revision. The Caderno remains a separate exploratory tool. Real existing comparisons, not installation trials, are converted into editable CMS documents. This owner-authorized content conversion amends the earlier no-live-publication boundary only for that explicit import, preserving authored home, source data, schema, worker and edge. Implementation plan: `2026-11-21-cms-owned-comparisons.md`. Phase D is installed at 2026-11-21 15:33 UTC from runtime/main `a9add13`, with all nine real compositions published as CMS content. Exact-main CI passed 3,183 tests; installed public acceptance passed 348 checks and all nine exact Admin editors were read back. Schema, protected source tables, authored home and immediate worker baseline are unchanged. See `../handoff/reports/cms-comparisons/installed.md`.

## Goal and baseline

Make the public Prumo an effective statistics tool: chart and composition controls first, readable evidence nearby, editorial prose at its appropriate reading width. Keep the CMS for authored content and preserve the existing data pipeline.

Baseline: clean `pipeline-rebuild` and `main` at `b7f4d09`; public code `7baa127`. The council's controlled 1920x1080 notebook capture put the canvas at Y=917.77, 1176x454.36 CSS pixels. Opening settings at 1440 moved it to Y=1786.83. At 3774px wide it still occupied only 1176px. Those are baseline observations, not targets dictated by an agent's proposed layout.

Council authority: `/home/joao/reports/prumo-design-council-2026-11-18-b7f4d09/REPORT.md`, synthesis through line 153. Individual contradictory/retracted recommendations are not requirements. A read-only designer translation confirmed that composition can improve without a SPA or a permanent sidebar.

## Non-negotiable contracts

- Preserve carmim, the approved plumb-bob icon, local Lato/Schola and enlarged functional type. Body stays 28.05px; existing navigation, label, value and control roles cannot shrink to recover space. Compact display headings and remove repeated prose instead.
- Keep twelve notebook cards distinct from at most six chart series. Preserve ordered references, explicit empty/off state, unavailable references, ten-year default, five-year/all options and bounded UTC interval day.
- Do not interpolate, aggregate, rebase, silently remove series or change statistical domains to fill space. Explicit two-axis charts for two series stay supported.
- Keep native GET/HEAD forms, address-based state, read-only one-snapshot preparation, exact publisher strings, same-snapshot payload/table/provenance and both public mount shapes.
- SVG remains on summaries and as no-JavaScript, failed-bundle, accessible and print fallback. Local ECharts may enhance analytical pages under the existing strict CSP; no new external dependency, second data request, account, cookie or tracker.
- No source-data write, migration, worker restart, licence change, proxy/authentication change or live CMS publication belongs to this roadmap's interface phases.
- No literal or encoded em dashes in authored text/code. Original receipts remain untouched.

## Delivery gates

Each slice must have focused automated checks, a real populated browser pass and a scoped independent review. The controller owns full-suite verification and status. Record implementation, automated verification, human acceptance and installation separately.

The first completed notebook candidate is a product/design checkpoint before its layout is generalized. Obtain the owner's visual acceptance; do not claim usability was proven by overflow tests. Release remains separately authorized. Because public templates/CSS are consumed by static Admin previews, a later UI release must test and update both readers without touching ingestion.

## Phase A: notebook workspace prototype

Status: owner accepted the prototype for installation and authorized merge/push/deploy. Runtime `050d69e` is installed from main `913eb2f` on 2026-11-19 at 16:55 UTC; only public web and static-preview Admin were recreated. Phase A is the completed installed scope, not the remainder of this roadmap. Human screen-reader and broader usability acceptance remain separate.

### A0. Isolate presentation boundaries

Extract cohesive settings, search and evidence partials before changing their composition. Preserve baseline responses and form contracts.

Acceptance: deterministic empty/populated/search/off/unavailable notebook HTML and relevant headers unchanged, including `/dados`; existing notebook contracts pass. Commit this refactor separately.

### A1. Put the analytical surface first

Use a notebook-scoped layout hook, compact title/status and a fluid working width independent of prose. Put the chart before explanations/settings, with add/select/window actions near the result. Keep native settings/search discoverable and operable; opening settings must not push the desktop chart away. Start with a single full-width stage, not a sidebar deducted from the old 1240px wrap. Give chart height and width a coherent responsive relationship. Keep content order and keyboard order consistent.

Acceptance: the two-real-series notebook at 1440x1000 and 1920x1080 shows the entire plot and principal actions in the initial viewport; no giant introduction before it. At 3774x1870 the chart gains both width and height relative to baseline. At 390x844 actual chart data and the composition entry are visible in the first view without reducing functional type. A six-series layout may need vertical scrolling, but cannot truncate names or hide selection. Opening settings changes desktop chart top by no more than 8 CSS pixels. No page overflow at 320/390/768/1024/1440/1920/2560/3774 or responsive breakpoint neighbours.

Likely files: `app/templates/notebook.html`, notebook partials, `app/templates/base.html` layout hook, `static/css/prumo.css`. Keep notebook-specific rules scoped rather than append a second global control system.

### A2. Make time and composition state explicit

Label last common chart period separately from each card's own latest value; show whether a card is drawn, excluded from the chosen group, disabled or unavailable. Put source/unit/common period next to the chart and in print. Retain exact values and full evidence below. Search/add, chart submit and removals must preserve other address settings and return to the relevant work area.

Acceptance: the IHPC/unemployment case explains common September values versus a later October card; group/off/empty/unavailable/six-of-twelve states remain honest. Native forms survive no JS. Fragments may change navigation position but must not introduce a new statistical URL parameter. No source-table content changes during the complete isolated workflow.

Likely files: `app/notebook.py`, `presentation/notebook.py`, notebook templates and focused route tests. Shared chart enhancements are optional only when needed for this acceptance; otherwise defer them to B.

### A3. Validate prototype and present checkpoint

Compare real populated before/after first views at laptop, desktop, wide monitor and mobile, including opening settings, adding a third series and changing the window. Probe two axes, six long series names, incompatible periods, no selection, explicit empty/off, no JS, blocked bundle, print, touch and keyboard. Keep charts and tables complete. Verify actual fonts, functional role sizes, focus, CSP/requests and both mounts, plus static CMS preview.

Acceptance: independent specification then quality/design review; controller focused tests, full offline suite and ruff; clean committed-checkout entrypoint/assets/tests; record screenshots and exact measurements. Human screen-reader and visual acceptance remain explicit separate gates. Do not mark the whole roadmap done after this prototype.

## Owner amendment: time alignment and analytical views (2026-11-20)

The owner prioritized mixed-frequency comparison and explicit normalisation before phase B, then authorized commit/push/merge/deployment. The original no-transformation restriction above remains the layout-phase boundary; this amendment permits only the separately reviewed analytical methods in `2026-11-20-notebook-time-transformations.md` and its specification. No source values, schema, worker or authored CMS content change.

Phase T is implemented and reviewed: native A/S/Q/M/D calendar overlay; complete-year annual means/year-end for reviewed families; annual base100 for levels and percentage-point differences for rates; original input/base evidence and exact native periods. Methods are explicit address state, never default hidden aggregation. HICP monthly-rate means are not official annual inflation. Native same-frequency/dense, two-axis and PT15M-day paths remain.

Installed main `7690837` includes corrected captions/methodology; implementation through `b17901f`. Clean committed-checkout gate: 287 passed, imports resolved in that checkout, ruff clean. Real-copy acceptance: 110 matrix cells / 2,605 assertions plus 223 functional checks, both local mount shapes, all 23 table fingerprints preserved. Exact-main CI44789496972 passed: 3,075 passed, 19 skipped, seven live deselected, three warnings. Reader-only activation on f0nix at 2026-11-20 18:15 UTC succeeded: web3ecad22a / Admin6e14cef1 healthy; worker identity/start/image/restarts, schema and CMS fingerprints unchanged. Installed checks: 115 public browser checks on both addresses, 33 state/Admin and ten static-preview checks. Human screen-reader acceptance remains separate. Evidence and rollback: `../handoff/reports/time-transformations/installed.md`.
## Owner amendment: multiseries on two scales (2026-11-20)

Phase U is installed at 2026-11-20 22:33 UTC on authorized runtime/main `3aac922`. Exact-main CI `44828613494` passed (3,114 passed, 25 skipped, seven live deselected); clean checkout 144, installed browser 38 scenarios / 876 assertions, state/Admin 33 and static preview ten passed. Only readers were recreated; schema and CMS fingerprints were preserved. The worker already had one earlier autonomous restart, unchanged during deployment; operational observation remains open. Evidence/recovery: `../handoff/reports/multiscale/installed.md`. The owner requested up to six series grouped on two compatible scales and useful Portugal-focused comparisons. Contract and release gates: `2026-11-20-multiseries-two-scales.md`. Existing two-series independent axes remain; three to six series share axes by raw unit, multiplier and base year. More than two scale groups is refused with guidance; analytical transformations retain their common-axis rule. Native/sparse calendars, full tables, exact values and provenance are preserved. `/comparar` gains reviewed Caderno configurations for interest rates/credit/deposits, public finances and foreign trade. No CMS document, source data or schema change.

## Phase B: shared chart reading and analytical pages

Status: INSTALLED after owner authorization, on f0nix at 2026-11-21 21:36 UTC, main/runtime release `5346447` (implementation `4d6b4c6`). Only web and static-preview Admin were recreated. Exact-main hosted CI `44951525399` passed 3,193 tests, with 29 skipped and seven live deselected; fresh clean-checkout gate 84 tests, installed public acceptance 1,392 assertions in 104 cases, Admin editors/preview 54, state/access 33 and static home preview ten passed. Schema/CMS and the complete worker baseline are unchanged. Development reviews and the isolated real-copy CMS workflow retain their documented scope. Evidence/recovery: `../handoff/reports/analytical-reading/installed.md`. Human screen-reader acceptance remains separate. Pending worker-safety commits through `68609ef` on `pipeline-rebuild` are deliberately excluded.

B1. Replace the long point-readout sentence with structured period/series/value rows while preserving exact strings, keyboard announcements and DOM-only tooltip safety. Make the native range target usable and keep series names/patterns adjacent to the plot. Review any canvas label/gutter adjustment together with SVG, touch coordinates, failed init and print; statistical domains do not change.

B2. Apply the accepted analytical composition to CMS-owned pairs, five-country comparisons and reusable public chart pages through `cms_chart.html`, plus primary/calculated series detail. Since phase D, the former `compare.html` and `compare_countries.html` templates are no longer routed; do not revive code-curated pages to satisfy this phase. Preserve two axes, calculated caveats, UTC-day selection, complete tables and period-specific provenance. Test long names and five/six sides, not just two short labels.

Acceptance: each route family has a populated first-view comparison, exact point/table tests, no-JS/print proof and measured typography. No blanket CSS change that only fixes the notebook while shrinking or clipping other charts.

## Phase C: discovery and entry into the tool

Status: planned; depends on B's shared surface.

C1. Refine global navigation/search at the enlarged scale, emphasizing Explore, Comparisons and Notebook without another tall presentation block. Keep themes, authored pages, sources, methodology and Admin discoverable. Validate expanded rightmost menus and current labels at breakpoint neighbours.

C2. Make homepage/search/theme results effective starting points: visible data, obvious add-to-notebook actions and compact wayfinding. Preserve the authored CMS home and all sections. Preview layout changes on a copy; any new text/order/content publication requires an explicit editorial decision, not a hidden initializer or CSS release.

Acceptance: search to series to notebook and add/change/share journeys are usable on desktop/mobile. Record real task outcomes, not merely passing geometry counts. Human visual acceptance precedes installation.

## Phase D: authoring analytical content

Status: INSTALLED by the owner-corrected CMS scope on 2026-11-21. See `2026-11-21-cms-owned-comparisons.md` and `../handoff/reports/cms-comparisons/installed.md`; remaining dated analysis and AI work belongs to phase E.

Extend the current one/two-series CMS chart contract to explicit comparable groups of at most six. Reuse notebook/model eligibility; add editor validation, reusable references and full revision/audit lifecycle. Assess whether a migration is needed from the actual schema before assigning a number. Existing documents must round-trip unchanged. No arbitrary transformations.

Acceptance: create, preview, publish, edit, stale-form refusal, unpublish and restore a multi-series chart/page on an isolated production copy; verify public/private boundaries and protected data fingerprints. Separate release approval for any migration.

## Phase E: dated analysis and assisted writing

Status: future product work after the analytical/editorial workflow is accepted.

E1. Specify dated analyses versus continuously updating pages. Preserve the actual inputs/vintages used by a published analysis and flag commentary whose referenced data have changed.

E2. Recover useful legacy AI prompts as an optional editor action that generates an editable draft from selected exact values, periods, sources and caveats. Calculations remain in the verified calculation layer. Record generation inputs/version and require deliberate human publication. No live visitor generation or automatic publication.

Acceptance: independently reviewed designs before implementation, explicit rights/input boundaries, audit and rejection/edit/publication tests. No speculative hooks in the layout work.

## Separate operational register

Carry forward source rights for REN/FRED/OECD, DGEG technical blockers, old-period classification, operational audited actions, worker SIGBUS/elapsed observation and human accessibility acceptance. This roadmap does not assert a fresh production audit or close those items. Use current handoff/runbooks for evidence; do not mix ingestion changes into UI commits.

## Progress ledger

| Slice | State | Evidence / next gate |
|---|---|---|
| A0 | Verified | Refactor `fad24e5`; 11 deterministic equivalence cases and controller repeat of all 50 existing notebook tests |
| A1-A2 | Installed after owner release approval | Main `913eb2f`, runtime `050d69e`, f0nix 2026-11-19 16:55 UTC. Fluid plot-first notebook, native settings after figure, nearby add/configure actions, honest chart/card states and common-period/source labels |
| A3 | Automated gates and authorized installation complete; human screen-reader open | Earlier full local suite: 2,856 on `0a0730e`; final development 126 committed-tree and 332 browser checks retain their scope. Exact-main hosted CI 44569621926 passed before activation: 2,847 passed, nine skipped, seven live deselected. Fresh release gate: 100 focused committed-tree tests, 459 installed public browser checks, 33 state/Admin and ten preview checks. Worker, schema and CMS fingerprints unchanged. Installation approval does not replace human screen-reader/usability acceptance |
| B | Installed after owner authorization | Main/runtime `5346447`, f0nix 2026-11-21 21:36 UTC. Exact-main CI 3,193 passed; 84 fresh committed-tree tests; 1,392 installed public assertions, 54 Admin editors/preview, 33 state/access and ten home-preview checks. Only readers replaced; schema/CMS/worker unchanged. Human screen-reader gate remains open. Evidence: `../handoff/reports/analytical-reading/installed.md` |
| C | Planned | Discovery and entry, preserving the CMS-owned homepage and published content |
| D | Installed | Nine real editable CMS comparisons, runtime `a9add13`; see owner correction above |
| E | Future | Dated analysis and approved AI drafts need their own design/product acceptance |

Development evidence, exact test scopes and neutral desktop/mobile captures: `../handoff/reports/analytical-workspace/README.md`. Installed acceptance, images, recovery and checker correction: `../handoff/reports/analytical-workspace-release/installed.md`. The settings form now contains window/scale/group/day AFTER the plot; the nearby Configurar action opens it natively. A1's near-result control requirement is implemented as this single path rather than duplicated forms. Later point-readout consolidation and global masthead alignment stay in B/C.

Canonical implementation roadmap: this file. User-facing project index: `/home/joao/vaults/projects/prumo/roadmap-e-implementacao.md`. Controller resume state: `../handoff/HANDOFF.md`.
