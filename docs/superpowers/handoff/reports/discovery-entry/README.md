# Phase C: discovery and entry

## Candidate, not installed

Branch: `feature/discovery-navigation` in `/home/joao/projects/prumo-discovery`.
Installed base: main `1a0bf13`, runtime `3ab1fdc`. Candidate runtime: `cd55507`.
No merge, release, live CMS publication, schema change, worker restart or edge/authentication operation belongs to this delivery. The public frontend continues to present the CMS operator's published comparisons; only the separate Caderno is reader-configured.

The candidate turns the search route into a complete browsable catalogue, adds conjunctive accent-insensitive text search and theme/geography/source/frequency filters, and paginates with real totals rather than silently cutting at 100. Existing notebook search retains its phrase semantics and 100-row cap. Query and filters share one native form, so applying filters includes a newly edited term. Unknown addressed filters remain visibly unavailable, rather than masquerading as the default choice. Discovery totals use fresh metadata within the same read-only snapshot, while values retain the existing fetched/verified serving boundary.

Native navigation groups the catalogue/themes under Explorar, keeps Comparações/Caderno prominent, and retains authored pages, sources, methodology and Admin. Task pages avoid duplicate search fields. Search/theme records show exact values, units, periods, sources and collection dates, with a clear single-series Criar caderno action. Existing CMS card blocks expose that same entry without changing any stored text, block order or publication. Theme descriptions remain available in the filter/help disclosure and authored theme readings follow the data; neither is removed. Legacy fallback cards keep their byte contract.

## Verification

Controller focused gate on the final runtime: 132 tests passed; application/ingest/presentation/backoffice/test ruff passed. Independent C0 review, whole-phase specification review with a scoped correction re-review, quality/integration review and final minor-finding re-review all passed. See `reviews.md` for scope and disposition.

Real-copy browser acceptance: 2,148 assertions and four complete search/series/notebook/add/share journeys, with JavaScript enabled/disabled and both public mount shapes. The populated matrix covers 320/390/600/601/768/820/821/900/901/1024/1100/1101/1440/1920 CSS pixels. Tests include expanded menus, unknown filters, pagination, exact reading of all nine published comparisons, local assets, strict CSP, no off-origin requests, keyboard focus and print. Static Admin homepage preview retains the card action without executable scripts, and its real link opens the notebook. Expanded navigation was also exercised on Demografia, Comparações and Metodologia at every tested width. This is an isolated internal preview, not an owner login through Authelia.

All 23 table fingerprints, schema, integrity result and foreign keys match before and after the read-only workflow. The copy was obtained through online backup and its isolated journal mode was prepared before final acceptance. No source data, CMS content or history was edited by these browser checks.

At 390px, the search's first record begins at Y=444.125; its actual value is visible in the first 844px view. At 1440px, it begins at Y=440.797. The first theme record begins at Y=616.484 and Y=483.188 respectively, with its actual value also in the first view. Body/result values remain 28.05px; navigation remains 26.6475px. Only display headings compact. The rejected first candidate put the search record at Y=1221.406 on mobile and 840.625 on desktop; this early candidate is not the installed baseline.

Local HTTP benchmarks use 20 samples after two warmups, concurrency one, the same production copy and concurrent offline-test load. Median, p95 and response sizes are retained separately for the original and expanded browser passes. The old empty catalogue and phrase search are not equivalent workloads: they served no matching data. These are local HTTP measurements, not installed-edge timings or traffic-capacity claims.

The final frozen-runtime full offline suite passed 3,278 tests, with seven live tests deselected and three warnings, in 1,893.48 seconds on runtime `cd55507`. Runtime/build/test inputs remained unchanged throughout the run. The earlier 3,274-test run preceded later corrections and remains earlier evidence, not the final-tree verdict. `final-gates.json` and the lossless full log archive identify the exact scope. No hosted CI result is claimed for this feature branch. A fresh detached committed checkout at `ca0904c` passed 182 tests covering discovery, navigation, card/CMS home, routes, preview, boundaries and typography. All imported app/persistence paths resolved inside that checkout; a real-copy search and exact local stylesheet readback passed, with broader ruff clean. Later reporting changes do not alter the runtime tested by this gate.

Human visual acceptance, human screen-reader/zoom usability and explicit installation approval remain open. Source rights/DGEG, dated analysis/approved AI and the worker's elapsed operational acceptance remain separate workstreams.

## Evidence and reproduction

Accepted neutral top-of-page captures are in `assets/`; raw receipts are losslessly compressed in `receipts/`, with raw/archive SHA-256 in `manifest.json`. Original failure receipts remain labelled as failures, even where the first harness incorrectly left a true `passed` field after an exception. The failing series-detail journey had not opened the already-existing native Intervalo e ações disclosure; the accepted harness uses that real control.

The browser helper is `browser_check.py`. Run it against baseline and candidate QA servers using the existing `reports/analytical-reading/qa_server.py`, a disposable database under `/home/joao/.hermes/cache/scratch`, and unused local ports. Its `--origin`, `--baseline`, `--db` and new `--output` directory are mandatory. Do not point it at production. It uses the project's read-only opener for fingerprints and never publishes content.

A future authorized code-only release affects `prumo` and `prumo-backoffice`, because the latter consumes the public templates for static preview. Retain the current worker, schema, CMS revisions and shared edge. Follow the existing mount-safe release procedure; this report does not authorize installation.
