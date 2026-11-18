# European comparisons: acceptance evidence

This is the pre-release acceptance record. The combined candidate is now installed;
see [final installation](../legibility-release/installed.md) for the actual current images,
release gates and recovery points. Earlier not-installed statements below describe this
report's own checkpoint.

## Delivered scope

Runtime `0902617` (with review documentation at `b1fca40`) adds three curated five-country comparisons using existing verified Eurostat series. The ordered countries are Portugal, Spain, France, Germany and Italy. Electricity uses actual household retail EUR/kWh with all taxes included for annual consumption 2 500 to 4 999 kWh, not an energy price index. The other comparisons are GDP per inhabitant at current euro prices and general-government gross consolidated debt as percentage of GDP.

No migration, registry/source/ingestion change, CMS document mutation, authentication change, merge or installation occurred. The earlier typography/Caderno candidate remains on this same branch. Existing CMS chart documents remain single-series/pairs; these country groups are a curated public surface, not a newly exposed N-series editor.

## Code and independent reviews

Task 1 first refactored pair preparation into ordered values (`dc6a43e`) while preserving pair SVG and normalized payload bytes. Task 1 then added the bounded shared-axis group engine and rebuilt local chart asset (`e63692e`). Task 2 added the validated country read service (`96f1c18`) and public page/index integration (`d613556`).

Specification and quality gates for both tasks are APPROVED. The final integration review also returned PASS against the actual frozen runtime and narrow corrections. See `task1-spec-review.md`, `task1-quality-review.md`, `task2-spec-review.md`, `task2-quality-review.md` and `integration-review.md`. These are scoped reviews, not the controller full-suite receipt.

The reviewed byte-identical chart bundle is 506 595 bytes, SHA-256 `debf2758f06efd3ec451bc4972d5bfc38c66e954f85bb352cdb3c3fc957b4e1d`. Its 173 122-byte gzip figure is a local compression measurement, not installed transfer evidence. The pinned typography exception was reconciled with the independently reproduced bundle rather than weakening the guard or editing upstream localisation strings.

## Production-copy proof

A consistent online SQLite backup was made from the live database through a read-only source URI, then copied to local scratch. Snapshot `production-copy.sqlite3` was 217 755 648 bytes at collection; quick_check ok and zero foreign-key violations. The snapshot preserves all original data. Development servers bind to localhost and never point at production.

The independently reconciled served coverage is:

| Group | Common finite periods | Span | Table rows |
|---|---|---|---|
| Electricity | 37 | 2008-S1 to 2026-S1 | 37 |
| GDP per inhabitant | 31 | 1995 to 2025 | 31 |
| General-government debt | 31 | 1995 to 2025 | 31 |

All fifteen selected registry series are active primary series with redistribution allowed and fetched verified values. No new collection is claimed. Each chart, exact table, latest-country summary and per-country provenance uses the same common-period snapshot. Provisional GDP statuses remain visible. The captured HTML bodies contain the full rendered data/provenance, archived losslessly under `receipts/`; `http-and-timings.json` pins their uncompressed hashes, headers and statuses.

`browser-accepted/acceptance.json` records 410 passed checks, zero runtime errors/warnings and zero off-origin requests. It includes before/after row counts and exact fingerprints for all 23 tables, including the CMS: every fingerprint is identical. The code is read-only; no publication trial was required or run.

## Browser scope

Real installed Chromium, actual local compiled bundle, local Lato/Schola fonts and the production snapshot:

- 320, 390, 768 and 1440px, direct and `/dados` mount shapes;
- five ordered series, one axis, distinct patterns/colours, Carmim Portugal;
- same count of plotted periods and complete table rows;
- exact first/second/last keyboard readouts for every group at every width/prefix;
- first/interior/last pointer tooltips with all five exact country strings, and actual touch release on the electricity group;
- named SVG/complete table with JavaScript disabled and bundle blocked, restored SVG on print;
- SVG label containment, no whole-page overflow, five complete provenance records, prior pair routes, discovery links, script-free index and404 responses;
- actual served bundle digest equal to the versioned manifest.

The screenshots in `browser-accepted/` were inspected through vision. The summary minimum-track bug at320px was fixed without reducing type or precision. Table scrolling is local to the labelled complete-table region. Human screen-reader acceptance remains a separate unmet manual gate; no such acceptance is claimed.

## Initial failures and their disposition

The unmodified earlier JSON receipts remain alongside the accepted receipt. They record actual unsuccessful probes, not passing product checks:

| Receipt folder | Result and disposition |
|---|---|
| `browser` | Wrong harness selector for the existing legend class. Corrected to `.legend > li`; no application change. |
| `browser-second` | Playwright string-based polling triggered the strict CSP eval refusal. Replaced polling with locator assertions; CSP unchanged. |
| `browser-third`, `browser-fourth` | Series-colour extrema supplied incorrect plot limits, selecting the previous period. Coordinates now come from actual painted grid edges; exact first/interior/last assertions remain. |
| `browser-fifth` | The tooltip probe did not yet observe the complete expected update. A locator assertion now waits for the exact full tooltip; endpoints remain within the drawn symbol by one pixel. |
| `browser-sixth` | Real320px overflow: a 13rem minimum grid track exceeded the available width. Runtime `0902617` clamps it to100percent; a source regression and the complete browser rerun pass. |
| `browser-final` | All interaction checks passed, but navigating intentional404 pages correctly emitted console resource errors. Those deliberate HTTP checks now use the request client separately; no global console suppression was added. |

Raw publisher/statistical values were never rounded or rewritten to satisfy a probe. Screenshot crops of adjacent page sections and tooltip occlusion while a control is active are not treated as missing data. Duplicate intermediate PNGs are local working captures, not part of the versioned accepted screenshot inventory.

## Reproduction

Use a consistent read-only-source online backup under the approved scratch directory, never a direct copy of a live WAL main file. Set `PRUMO_QA_DB` to that isolated copy. The browser script deliberately pins the accepted coverage above; a future publisher update requires a new independently reconciled acceptance scope, not changing this historical receipt.

From the repository root, using the same flags exercised for this acceptance server:

```bash
PRUMO_QA_DB=/absolute/scratch/production-copy.sqlite3 \
  .venv-ci/bin/python -m uvicorn qa_server:app \
  --app-dir docs/superpowers/handoff/reports/european-comparisons \
  --host 127.0.0.1 --port 8099 --workers 1
PRUMO_QA_DB=/absolute/scratch/production-copy.sqlite3 \
  PRUMO_QA_OUT=/absolute/new-evidence-directory \
  .venv-ci/bin/python docs/superpowers/handoff/reports/european-comparisons/browser_acceptance.py
```

Choose an unused output directory to retain earlier evidence. The helper `capture_pages.py` refuses to overwrite existing raw HTML captures. Timings in `receipts/http-and-timings.json` are n=20 per route after warmup, with the full suite running concurrently. They are local development timings, not a production SLA or a zero-concurrency benchmark. Public index median/p95 was 56.6/64.9 ms; group pages median 150.7 to 157.3 ms, p95 168.8 to 189.5 ms.

## Final gates

Controller authoritative offline suite: 2 774 passed, 7 network tests deselected, 3 warnings in 1 507.85 seconds. It launched at b1fca40 with runtime 0902617 and no application, dependency, configuration, asset or test changes during the run. Later changes are documentation/evidence only. Exact raw output is archived losslessly in `receipts/full-suite-b1fca40.log.gz`; `final-gates.json` pins the uncompressed SHA-256 and scope. Ruff across app/ingest/presentation/backoffice/tests and JavaScript syntax checks are clean.

Detached clean committed checkout 32146a5: actual module origins point into the detached tree; the index and all country routes return 200 against the production snapshot; the compiled asset matches its manifest. The affected engine, country, pair, presentation, layout, interactive and typography suite passed 124 tests with one dependency warning in 199.45 seconds. This is committed-tree packaging evidence, not another full-suite claim. Runtime/tests match the authoritative full run byte-for-byte.

The localhost development server was stopped after acceptance. Production remains the installed Carmim/Tabler baseline; no URLs for the new country groups are claimed live. The owner roadmap and technical handoff distinguish the completed branch candidate from pending merge/installation. A release of this combined branch affects web/backoffice only and requires owner approval; no migration, worker or edge change is needed.
