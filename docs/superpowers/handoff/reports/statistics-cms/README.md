# Statistics CMS implementation evidence

Code revision: 7c54047 on pipeline-rebuild. Baseline: c9a2e5f, schema0018. Implementation authorized by the owner; merge/deployment not performed. The feature specification is [statistics CMS design](../../../specs/2026-11-16-statistics-cms-design.md); the execution plan is [statistics CMS](../../../plans/2026-11-16-statistics-cms.md).

## Delivered scope

Admin prefix/access boundary and versioned edge templates; local pinned ECharts on detail/comparison charts with SVG summaries and fallback; typed page/chart documents and immutable revisions with CAS/audit; labelled page/chart editor; preview, publish/unpublish, restore and duplicate; public /paginas and /graficos routes with section discovery and read-time eligibility. AI and dated snapshots remain future scope.

The public Admin route is only prepared. No live Authelia/Traefik rule, credential or container changed. The current deployed web remains the earlier punctuation release. The first real owner login/publication and the actual edge asset transfer cannot be claimed from these tests.

## Verification status

The controller's authoritative full offline suite on runtime revision 7c54047 completed: 2580 passed, 7 deselected, 3 warnings in 1230.31 s. The versioned receipt is test-result.json, including the full JUnit hash and its durable original path `/home/joao/prumo-operations/cms-20261117/full-suite.xml`. The original machine-generated XML contains parameter identifiers with forbidden-character test inputs, so it is preserved unchanged outside the authored repository rather than rewritten or granted a typography exception. No runtime code changed after the run started; later changes are prose, source-labelled evidence and operator documentation, with focused typography/Admin checks rerun. The controller separately ran the real-browser chart interaction suite (7 passed), the Admin/typography checks (85 passed), the CMS/route/service checks and full-scope ruff (clean). Independent reviews approved the implemented scopes and final integration after the fixes listed below. Documentation follow-ups do not change the runtime tree.

## Production-copy proof

The online SQLite backup is 217,403,392 bytes. On that copy, migration 0019 applied in 0.537739 s, integrity_check returned ok and foreign_key_check returned no rows. All 18 protected-table fingerprints matched before/after the service workflow and again after browser operations. This includes 542,822 observation rows and 34,219 quarantine rows, but preservation is established by row fingerprints, not counts alone. Source metadata, series, verification/evidence, derived tables, scheduler state and pre-existing editorial tables are included.

The controller exercised create/publish chart, create/publish page, save a private changed draft while published text remained unchanged, restore to a new draft, republish and duplicate. Browser QA then used the actual labelled forms to create a separate trial page with text/card/chart, save, preview, publish and restore an old revision while leaving the live revision unchanged. These are isolated trial publications, not production content.

Receipts: database-acceptance.json; reproduction setup: acceptance_setup.py. The script uses the environment's explicit scratch copy paths; it refuses to overwrite an acceptance database. Its input is a read-only backup, not a versioned database fixture. Use the existing online-backup procedure to supply a fresh copy. Never point it at production for writing.

## Browser proof and review corrections

browser-initial.json retains the initial failures instead of rewriting the earlier QA as a pass. The mobile selection report originally compared canvas fractions; investigation established that the plotted domain had been squeezed by ECharts6 outer-bound handling, while a separate axis-only pixel conversion produced NaN and disabled the native readout path. The correction uses cartesian conversion, reachable endpoints, tap-release selection and axis-name alignment into the margin.

browser-corrections.json records painted first/interior/last and padding selection at 320/390/768/1440, exact readout strings, keyboard Home/Arrow/End, mobile touch and complete tooltips. Footer links wrap and the mobile range spans the control area. Disabled/blocked JS and print preserve SVG; the named accessible SVG is retained while canvas is hidden from assistive technology. Automated AX-tree inspection found one named image and one labelled range. No human screen-reader pass was performed.

ECharts richText could not wrap long exact-value tooltip rows. The narrowly amended implementation returns DOM nodes built only with createElement/textContent, never HTML strings. Independent browser security probes rendered closing tags/event attributes as literal text with zero injected elements, no CSP violations and no external requests. CSP did not gain unsafe-inline/eval or network permissions. The amendment is recorded explicitly in the interactive-chart design.

The CMS preview is intentionally static and labelled so. It uses the same prepared data/rendering, a public data-link base and an Admin asset base. It does not execute chart JavaScript. mobile.png shows the corrected public chart on the real-data copy; editor.png shows the earlier browser editor acceptance, before the static-preview wording correction. Screenshots are not representations of production.

## Independent review dispositions

| Scope | Finding | Correction | Accepted gate |
|---|---|---|---|
| Admin/ECharts specification | Canvas overlay included the legend; missing Admin link; YAML-secret alphabet; observed-step gap heuristic | 2e66d3b | Scoped specification pass, then separate quality approval |
| CMS storage specification | REPLACE bypassed append-only triggers | 0a2293d, recursive_triggers on before writes; REPLACE regression on all three tables/both openers | Specification pass |
| CMS storage quality | Restricted handle could disable foreign_keys/CHECK enforcement | 70f1e45, deny pragma assignments except read-only metadata introspection | Separate quality approval |
| CMS application specification | General pages undiscoverable; missing series links/coverage; nested chart eligibility; stale duplicate copied a newer draft | fd3d9f7 | Scoped specification pass |
| CMS application quality | Base displayed with derived unit; ignored day printed over monthly chart; integer overflow; abbreviated diff detection; preview links | a63e2ea | Scoped quality approval |
| Mobile browser | Endpoint/tap failures, clipped tooltip, narrow controls and footer overflow | 6e72132 | Real-browser regression and independent security/spec amendment review |
| Admin first-click flow | Owner-subject rule plus deny could block anonymous before login | 7c54047 | Exact-scope two_factor challenge, application retains verified owner allowlist; final integration approved |

The Auth-template rule tests and app identity tests are not a live Authelia rule-engine result. The file-provider environment template has been substituted/parsed in tests, not installed with a real credential. These are explicit release acceptance checks.

## Matched-copy measurements

metrics-before.json and metrics-after.json were generated with bench.py against detached c9a2e5f on the0018 copy and current7c54047 on the0019 copy. Twenty requests per route after warmup, same host and source-table content; TestClient includes ASGI/render overhead. Concurrent background tests and both benchmarks mean p95 is an observed measurement, not an isolated CPU guarantee.

The largest non-interval population is 934 observations (INE IPC PT and Continente); both were included. Comparison credit HTML increased 180,767 to 222,408 bytes; the 934-point detail reached 170,111 bytes, under the provisional 250,000-byte target for these measured cases. No point, digit or fallback was removed to meet a budget. This is not a claim of exhaustive maximum HTML size over all possible authored 12-block CMS pages.

CMS page median 60.30 ms/p95 69.56; CMS chart 59.30/65.34. The existing E-REDES detail measured 89.47/94.90 after versus 97.51/120.60 before. Home median 113.99 versus 107.21; its after p95 was 161.86 ms, above the 150 ms target in this concurrent run. No script is added to the home. Do not claim every latency percentile is below150 ms.

The compiled engine+adapter is 505,823 raw bytes and 172,843 local gzip bytes per its manifest. It is pinned and reproducible; production transfer encoding/bytes are unmeasured because it is not installed. Choices generation on the copy returned 1,308 eligible primary series in 1.97 s. Repeated native selectors can make a large editor document heavy; record that as a later usability optimization rather than silently limiting eligible data.

## Remaining gates

Separately authorized merge/release including schema0019, worker/web/backoffice and shared edge; safe encrypted credential provisioning on the correct two hosts; real anonymous challenge, owner publication and non-owner/direct-port refusal; actual edge compression; human screen-reader acceptance. Data-source rights, DGEG reconciliation, lag classification, SIGBUS monitoring and the real elapsed worker observation are not closed by this CMS work.
