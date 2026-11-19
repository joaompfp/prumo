# Notebook workspace review dispositions

Controller record, 2026-11-19. This file summarizes the actual independent findings and their integration; it is not a new user study. Reviewers were isolated subagents reporting the same observed `deepseek-v4.1-flash` model. Different perspectives are not claimed as model diversity.

## Specification

Initial review of `6de464a`: REQUEST_CHANGES.

| Finding | Correction | Verification |
|---|---|---|
| Mobile override collapsed a 264px canvas to 137px and crowded y labels | Remove min-height override; preserve the mobile floor | CSS regression; real 354x264 canvas and painted-point checks |
| Mobile CSS put common-period/source caption after legend and readout | Remove visual reorder; common-period figcaption before plot, source metadata directly after it | Real DOM, geometry and print checks |
| Updating an off chart silently changed it to explicit empty | Mode-aware hidden `grafico`, separate deliberate activation | Native form submission and route regressions for off/empty/all |
| Undrawable states showed empty table/provenance disclosures | Evidence requires an actual prepared chart | Ready/off/empty/unavailable route tests |
| Range Enter submitted settings because figure was inside form | Figure/range outside the authoritative settings form | Browser Enter does not navigate; DOM form association regression |
| Moved caveats disappeared in print | Visible caveat outside print-hidden help | Print-media and source/caveat visibility checks |

Repair `87584b3` passed all six scoped requirements. Re-review found the remaining same-specificity mobile select grid rule was overridden by a later two-column rule. Controller fixed the winning global rule to use intrinsic fit with a bounded minimum, added a regression and measured full mobile select widths. Controller also fixed a real shortcut failure by targeting content inside the native settings disclosure. Final scoped specification verdict on `0a0730e`: PASS.

The initial refactor was independently separate from behavior. The controller reran all 50 existing notebook tests before feature implementation; the full suite subsequently passed on the feature/fix candidates.

## Quality and visual review

Review after specification PASS: REQUEST_CHANGES for one blocking accessibility issue. The Configurar link's accessible name omitted its visible text. Corrected in `e944a1d`; route regression and role-based browser locator now require the visible label in the name. Scoped independent re-review of the exact one-line fix: APPROVED. This does not stand in for human assistive-technology acceptance.

Other observations were non-blocking: repeated short empty/off clauses, metadata separators on wrapped lines, duplicate names in source metadata and old legend, and different wide-layout edges between the working surface and global masthead. They are documented rather than misrepresented as data defects. Key/readout consolidation belongs to B; the shared shell belongs to C.

The reviewer correctly rejected an intermediate mobile crop as first-view proof because it retained scroll from an earlier native interaction. Controller corrected the helper to reset and assert scroll zero, then shortened only the visible add action to fit the two mobile actions on one row. There was no reduction of body/control type, data domain or canvas floor. The full accessible add label stays intact. Final independent image inspection confirmed the complete 390x844 plot and its time-axis labels fit the actual first viewport.

## Controller integration

Final runtime `050d69e`; later edits in this report directory are evidence/documentation only. Final working-tree and clean committed-checkout focused tests: 126 passed. Earlier authoritative full suite on `0a0730e`: 2,856 passed; later accessible-name/action-copy changes are explicitly covered by the final focused/browser gates, not called a third full-suite run.

Final browser receipts: 285 main plus 47 supplementary checks, same real-data copy, both mount shapes, exact unchanged statistical payload/SVG/table against baseline and all 23 table fingerprints unchanged. No off-origin requests or application/CSP errors. The original rejected states remain distinguishable in diagnostics; only final scroll-zero images are under assets/.

Owner visual acceptance, human screen-reader testing and installation remain pending. No next roadmap phase was silently implemented or installed during this checkpoint.
