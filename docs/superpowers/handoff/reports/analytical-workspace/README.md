# Notebook analytical workspace prototype

Status: implemented and verified on `pipeline-rebuild`; not merged or installed. Runtime candidate: `050d69e`. Owner visual acceptance and human screen-reader acceptance remain open. The rest of the analytical-workspace roadmap is not implemented by this prototype.

Authority: [workspace roadmap](../../../plans/2026-11-19-analytical-workspace-roadmap.md), owner request after the design council. Installed baseline code is `b7f4d09` / runtime `7baa127`. No production service, source data, CMS document, migration, authentication or shared-edge configuration was changed.

## Delivered

The notebook has a compact heading, add/configure actions beside the analytical surface, last-common-period caption, a fluid height-aware chart, source/unit/retrieval metadata immediately after the plot, settings after the figure and search before the cards. Each card identifies its actual chart role and keeps its own latest period distinct from the common plotted period. Native fragments return to the work area and targeting the settings content opens the native disclosure.

The twelve-card versus six-chart-series contract, ordered address references, explicit empty/off states, unavailable references, ten-year default, native-scale/frequency rules and deliberate dual axes are unchanged. There is no aggregation, rebase, silent series selection, new request API or statistical-domain change. Local ECharts asset is unchanged; SVG, full table, no-JavaScript, blocked-bundle and print remain available. The shared chart macro's optional caller adds notebook metadata without changing default callers' output.

## Matched real-data measurements

Fresh online SQLite backup taken through a read-only source URI, with the backup API, from f0nix into an isolated 218,361,856-byte development copy. The baseline and candidate servers read the SAME copy. Local Chromium 1248, fonts ready, CSS-pixel viewport, neutral captures at `scrollY=0`.

| Viewport | Baseline canvas | Candidate canvas | Baseline top | Candidate top |
|---|---|---|---|---|
| 390x844 | 354x264 | 354x264 | 1444.67 | 573.41 |
| 1440x1000 | 1176x454.36 | 1179.69x455.78 | 917.77 | 326.66 |
| 1920x1080 | 1176x454.36 | 1386.72x535.77 | 917.77 | 330.66 |
| 3774x1870 | 1176x454.36 | 2400x927.27 | 917.77 | 330.66 |

The complete two-series plot fits the first viewport at the laptop/desktop sizes and at 390x844. Body stays 28.05px; measured navigation/search/readout role sizes match baseline. A six-side chart can require scrolling; names and selection are never hidden to satisfy a first-view quota. The height-aware width cap is a prototype design choice, not a measured optimum for every monitor.

[Desktop 1920](assets/notebook-1920.png), [laptop 1440](assets/notebook-1440.png), [mobile 390](assets/notebook-390.png), [wide 3774](assets/notebook-3774.png), [print PDF](assets/notebook-print.pdf).

## Verification and exact scopes

- Prerequisite refactor `fad24e5`: 11 deterministic response/header equivalence cases reported by implementer; controller repeated the 50 existing notebook tests, all passed.
- Controller full offline suite on `87584b3`: 2,855 passed, seven live tests deselected, three isolated module-preserving partitions; raw logs, JUnit, full node manifest and summary archived.
- Controller full offline suite on `0a0730e`: 2,856 passed, seven live tests deselected, same exhaustive partition method. Summary completed at 13:59:21 UTC, before the later accessible-name edit at 14:03:16. This is NOT a fresh full-suite run on `050d69e`.
- After the accessible-name and short-action-label changes, controller affected suite: 126 passed on the final runtime. The same 126 passed from detached clean committed checkout `050d69e`, with `app.notebook`, `app.notebook_chart` and `presentation.notebook` imports verified to come from that checkout. Ruff is clean.
- Final main browser acceptance: 285 passed checks on the final runtime, both root and `/dados`, widths 320/390/768/899/900/901/1024/1440/1920/2560/3774. Includes common-period/source order, mobile selector widths, unchanged plot top when settings open, complete table, exact keyboard values, native add/window/off/empty flows, print, no JS and blocked bundle. Actual bundle digest matched the pinned manifest; no page/CSP errors or off-origin requests.
- Supplementary browser acceptance: 47 passed checks, including six real monthly percentage series at 320/390/768/1440/3774, exact first/interior/last painted pointer and touch selection, vertical touch scrolling, 720px reflow equivalent to 200 percent on a 1440px viewport, matched baseline type and identical payload/SVG/table hashes on four viewports.
- Final total: 332 browser checks. Every one of the copy's 23 table row fingerprints is unchanged; quick check passed and zero FK violations.
- Independent specification and quality reviews passed after repairs; see [review dispositions](reviews.md). No hosted CI or installed behavior is claimed for this branch.

The 720px check proves the layout-reflow case, not a complete manual browser-zoom or assistive-technology session. Raw population manifests and JUnit XML include deliberately hostile typography test identifiers, so they are archived losslessly as `.json.gz`/`.xml.gz`; their raw hashes remain in the receipt manifest. The packaging typography check caught this before delivery; the application's copy rule and original receipts were not weakened or rewritten. Chromium/native fragment opening is verified; Firefox/Safari and human screen-reader acceptance are not claimed. The owner's visual acceptance is the next product checkpoint before generalizing the composition.

## Review corrections retained

The initial candidate made the mobile plot too short to fit a viewport and reordered the caption below a long readout. Both were rejected and corrected. It also exposed an off-to-empty form transition, empty evidence in undrawable states, a chart range nested in the settings form and caveats lost in print. Corrections preserve the actual statistical payload.

The next round found a mobile grid cascade bug and a fragment that reached closed settings without opening them. The grid now fits full labels and the fragment targets content inside the disclosure. Final quality review caught an accessible name that omitted visible text; the name now starts with `Configurar` and has route/browser regressions. Shortening the visible add action to `Acrescentar` lets both actions share a mobile row without changing font size; the accessible label remains `Acrescentar séries`.

Preliminary browser receipts are retained under `diagnostics/`, not represented as final acceptance. One earlier helper collected green checks while merely recording `settings_shortcut_opens=false`; the corrected gate now requires true. Intermediate screenshots could retain scroll from native control interaction; accepted captures explicitly reset and assert `scrollY=0`. Do not reuse those earlier crops as first-view evidence.

## Reproduction

Use a fresh isolated database copy under the approved scratch directory. The included `dev_server.py` wrapper mounts the same public ASGI app at `/` and `/dados`; no proxy/authentication service is needed for this read-only local proof. The application must use the candidate source tree, with `PRUMO_DB_PATH` pointing at that copy. For matched comparison, run baseline `b7f4d09` separately on port 8128 against the same copy.

```bash
PRUMO_DB_PATH=/home/joao/.hermes/cache/scratch/prumo-workspace-qa/acceptance.sqlite3 \
PYTHONPATH="$PWD" .venv-ci/bin/python -m uvicorn dev_server:app \
  --app-dir docs/superpowers/handoff/reports/analytical-workspace \
  --host 127.0.0.1 --port 8129

PRUMO_QA_URL=http://127.0.0.1:8129 \
PRUMO_QA_DB=/home/joao/.hermes/cache/scratch/prumo-workspace-qa/acceptance.sqlite3 \
PRUMO_QA_OUT=/home/joao/.hermes/cache/scratch/prumo-workspace-qa/browser-new \
.venv-ci/bin/python docs/superpowers/handoff/reports/analytical-workspace/browser_acceptance.py

PRUMO_QA_OUT=/home/joao/.hermes/cache/scratch/prumo-workspace-qa/supplementary-new \
.venv-ci/bin/python docs/superpowers/handoff/reports/analytical-workspace/supplementary_acceptance.py

PRUMO_GATE_OUT=/home/joao/.hermes/cache/scratch/prumo-workspace-qa/full-gate-new \
.venv-ci/bin/python docs/superpowers/handoff/reports/notebook-navigation/full_gate.py
```

The browser helper refuses a non-localhost acceptance origin and a database outside the approved scratch root. Its current default is localhost8129; the supplementary helper expects candidate8129/baseline8128. All referenced receipts and screenshots are archived here rather than depending on scratch survival. `receipts/manifest.json` records file hashes; raw full-suite logs are lossless gzip with raw digests.

## Follow-up and release boundary

Keep B's structured point readout/consolidated key, the remaining analytical routes, C's global navigation/home entry, multiseries CMS authoring, dated analysis and approved AI drafts separate. Existing source rights, DGEG technical blockers and worker observation remain open in the main handoff, without a fresh audit claim here.

Current notebook metadata and the existing legend repeat series names; structured consolidation is phase B. The wide notebook and the old 1240px header have different edges; global-shell alignment is phase C. This prototype does not rewrite the CMS homepage or the shared header.

A later authorized UI installation needs public web and the Admin static-preview consumer tested and updated together; there is no migration or worker restart in this candidate. Follow current `docs/data/operations.md` and mount-safe build/rollback procedure. Do not treat implementation permission as installation permission.
