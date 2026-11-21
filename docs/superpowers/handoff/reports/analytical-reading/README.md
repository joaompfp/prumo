# Shared analytical reading: phase B

## Delivery boundary

Implemented candidate on `feature/analytical-reading`, runtime `4d6b4c6`, based on installed main `34ed8c0`. Not merged or installed. The separate `pipeline-rebuild` branch contained three unpushed worker-safety commits through `68609ef` before this work; none is included here. Source data, CMS schema, existing live publications, authentication and shared edge are outside this change.

Comparisons remain CMS documents. The backoffice selects series, axes, windows, transformations and editorial text; the public page displays the published revision. The Caderno remains separate exploration. No new custom comparison or implicit publication was introduced.

## Implementation

- A shared inspected-point view feeds the tooltip, structured DOM readout and polite keyboard announcement. Each row keeps its exact server-formatted value/unit, native period where applicable and explicit missing state. Hidden compatibility separators preserve the previous `textContent` contract without forcing a long visible sentence.
- Pointer movement stays silent; the separate polite region owns keyboard announcements. The persistent output explicitly disables its implicit live announcement. The native range target is at least 48px high, preserving the functional reading scale.
- Primary and calculated detail pages, reusable CMS charts and CMS-owned comparisons share the plot-first analytical width. Formula, caveats, source links, full available table and period-specific provenance are retained below the plot. Native series-window/day actions are grouped after the figure with a nearby fragment shortcut that opens their disclosure even without JavaScript.
- Print restores SVG and exposes evidence tables and editorial notes. A narrow calculated-badge wrapping fix prevents a min-content grid from overflowing a 320px screen. No statistical domain or publisher precision changed.
- All assets are local. The exact compiled bundle hash is `951c0f155f53a2b1278fc304d98e37f0aa5b8e84468803111b8806d9832a21ea`; 511,675 bytes and 174,583 bytes local gzip. These are build measurements, not installed network-transfer claims.

## Verification

Authoritative full-suite result: pending final collection. No result from the interrupted earlier run is counted as a complete suite. The final run freezes runtime `4d6b4c6`, uses the existing interpreter and two isolated pytest workers; pytest-xdist/execnet were installed only under scratch, not as an application/runtime dependency.

Focused controller runs passed 125 tests after initial integration, 83 after the daily-note correction, and 58 after the final mobile-controls adjustment. These are distinct overlapping scopes, not additive test counts. New analytical-page checks cover both prefixes, normal/calculated/reusable/CMS comparison routes, exact rows, native disclosures without JavaScript, 320/390/1440 geometry, print and SVG.

The final populated browser workflow passed 1,219 assertions across 128 route/viewport/mount combinations, plus an additional 22 native-day/asset assertions. `browser/result.json` and `browser/native-controls.json` contain the complete enumerated populations. Tested routes cover a primary monthly series, 15-minute E-REDES day, calculated series, reusable calculated CMS chart, pair, grouped two-axis comparison, five-country comparison and sparse-frequency Caderno. Widths are 320, 390, 760, 761, 900, 901, 1440 and 1920 on both mount shapes.

The actual labelled Admin workflow edited a real comparison on the isolated production copy, saved privately, confirmed the public revision stayed unchanged, read a static private preview with script execution refused, published, read back the public title and restored the original composition. The 20 protected non-CMS tables, schema and authored homepage have identical fingerprints before/after. Production was not used for trial publication.

The auxiliary check used the native daily selector, with and without JavaScript, submitted an alternate available day, verified the GET address/prefix and fetched the exact compiled asset linked by each public prefix. No application/CSP errors or external requests occurred in the successful integrated matrix. Source files and historical receipts remain untouched.

## First views and neutral captures

All screenshots are captured after local fonts load, with `scrollY=0` and tooltips explicitly hidden by actual pointer entry/leave, except the separately labelled inspector capture. Values retain the source's legitimate differing decimal lengths.

| Page and viewport | Plot top | Plot bottom |
|---|---|---|
| Monthly series, 390x844 | 508.94 | 772.94 |
| E-REDES daily series, 390x844 | 547.20 | 811.20 |
| Grouped two-axis CMS comparison, 390x844 | 534.91 | 798.91 |
| Monthly/daily series, 1440x1000 | 434.94 | 890.72 |
| Grouped two-axis CMS comparison, 1440x1000 | 425.92 | 881.70 |

Captures: `browser/series-390.png`, `browser/series-1440.png`, `browser/dual-390.png`, `browser/dual-1440.png`, `browser/countries-390.png`, `browser/countries-1440.png` and `browser/structured-inspector-1440.png`.

## Reviews and retained findings

Independent specification and quality reviews approved the implementation. The spec reviewer initially classified old `compare.html`/`compare_countries.html` files as missing live coverage. Actual route inspection proved both are dead templates after phase D: pairs, countries, reusable charts and previews render `cms_chart.html`. The plan now names the reachable CMS renderer; no code-curated route was revived. A bounded independent re-review approved that disposition and the final mobile-control delta.

Controller browser testing found and fixed three real issues before runtime freeze: editorial notes hidden in print, a calculated badge overflowing a narrow grid and interval prose pushing the plot just below the desktop fold. Later neutral capture checks found a probe problem: a keyboard tooltip could remain visible because the pointer had never entered the offscreen canvas. The harness now scrolls to the actual canvas, enters its edge, leaves and asserts hidden tooltips before returning to the top. Earlier screenshot interpretations of absent legends or source precision were not used to modify data.

Human screen-reader acceptance and the owner's visual acceptance of this candidate remain open. Browser checks do not establish a human assistive-technology pass or complete print pagination on every physical printer.

## Reproduction and later installation

Use an isolated online SQLite backup containing the installed real CMS comparisons, never a bare copy of a live WAL database. `qa_server.py` refuses a database outside the approved scratch root. Start it from this exact checkout with `PRUMO_QA_DB` set to that copy, then run:

```sh
/home/joao/projects/prumo-pipeline/.venv-ci/bin/python docs/superpowers/handoff/reports/analytical-reading/browser_check.py --origin http://127.0.0.1:46247 --db /absolute/scratch/copy.sqlite3
/home/joao/projects/prumo-pipeline/.venv-ci/bin/python docs/superpowers/handoff/reports/analytical-reading/extra_check.py --origin http://127.0.0.1:46247
```

A later authorized release affects web and the static-preview backoffice consumer only. There is no migration, content initialization or ingestion restart. Follow the existing mount-safe build/recreation runbook, preserve CMS/schema fingerprints and pin the currently running reader images for rollback. Do not implicitly include the pending worker-safety branch. No deployment or fresh hosted-CI result is claimed here.
