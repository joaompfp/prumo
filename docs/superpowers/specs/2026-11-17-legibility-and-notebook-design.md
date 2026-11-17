# Legibility and indicator notebook

Status: implementation authorized by the owner's request for a design-agent refinement, a minimum 50% type increase and a useful surprise feature. Release remains subject to the existing release scope and gates. Baseline: 6f851d4, installed public/Admin runtime 14f845e. No schema, ingestion, authentication or edge change.

## Goal

Make Prumo comfortable to read and operate on desktop and mobile without losing its editorial character. Add a useful personal reading tool without accounts, cookies, statistical transformations or a second data system.

## Design decision

The requested independent designer inspected the live public pages and an isolated production-copy Admin. Its measured baseline receipts are retained with this work. Adopt local licensed Lato for text, controls and numbers, and TeX Gyre Schola for display headings. Keep the approved carmim, paper, charcoal and plumb-bob geometry. Use tabular lining figures for values. Reserve uppercase for short status text. The owner delegated the design and surprise choice, so another approval dialogue is not required for implementation.

Increase every functional text role by at least 1.5x its baseline computed size at the same viewport, including navigation, table cells, labels and chart readouts. The designer's suggested smaller exceptions for public table cells/navigation are NOT accepted because they would miss the owner's explicit minimum. Recompose the layout rather than shrinking text to recover density. Public base body: 17px to 25.5px; Admin body: 14px to 21px. Verify 320/390/768/1024/1440 widths. Baseline mobile shrinkage is removed. Public cards use 3/2/1 columns and predictable content slots, long exact number tokens remain intact. Public and Admin navigation use accessible native disclosures on narrow screens. Keep controls understandable with missing fonts/JavaScript.

Charts retain exact publisher strings and existing geometry/data contracts. Increase real canvas labels and tooltips, and make SVG fallback labels readable at narrow widths without hiding its accessible image. Preserve print fallback, point selection and explicit dual axes. Avoid clipping and add bounded table scrolling where the full-size data cannot fit. Local font-src self is permitted, but script/CSP policies otherwise remain unchanged.

## New feature: Caderno de indicadores

A server-rendered, GET/HEAD-only notebook holds up to twelve primary eligible series. Selection lives in the address (repeated query parameters), not a cookie, account, browser storage or database. Anyone with the address can open it; do not describe it as private or as a historical snapshot. It always shows current served values and explicitly names that behavior.

The notebook reuses the authoritative card preparation and current eligibility checks on the same read-only database snapshot. Cards preserve exact values, units, periods, source, fetch date, flags and SVG summaries. No new calculations, free-pair charts, source fetching or schema changes. Search reuses the existing public search semantics and excludes ineligible/withdrawn/legacy-only rows. Search, add, remove, clear and empty/limit/unavailable states work without JavaScript. Validate syntax and selection bounds before database work; deduplicate ordered IDs, reject malformed/over-limit requests rather than silently truncating. Revalidate selected IDs without the stale catalogue cache. Unknown or newly ineligible selections are omitted with a clear count, without exposing IDs or internal reason codes. Missing built-in catalogue text remains a logged 503, not fabricated copy.

Discoverability: a header/footer notebook entry, a single-series start action and a comparison start action. Notebook links carry the selection, respect both mounted public prefixes, and do not carry arbitrary hosts. A canonical selection-only link omits a transient search query so the reader can bookmark/copy a clean address. Mark notebook responses noindex, follow and set the corresponding response header. No extra script or external request is needed. Existing public pages/CSV retain their strict read-only and script-free contracts.

## Boundaries and implementation slices

1. Typeface assets/licences and presentation tokens/layout, independent of notebook behavior. Preserve control semantics, CSRF, auditing and unsaved-draft guards. Rebuild the pinned chart asset only when its source changes and record the receipt.
2. Notebook read model/service and routes as separate cohesive modules, using existing Db/reads preparation rather than SQL or a new persistence representation. Page template and tests, then thin integration into application/navigation/detail actions.
3. Real-data browser acceptance, independent specification and quality reviews, authoritative frozen-tree suite, documentation and handoff/roadmap update.

Parallel implementers have disjoint ownership. The controller owns integration, public base/header integration, production operations and the authoritative full suite. No AGENTS.md or CLAUDE.md changes. No source rights changes or AI commentary are included.

## Acceptance

Record computed old/new type sizes for representative role populations, requiring every matched functional role to reach 1.5x. Validate loaded local fonts and all advertised assets, native mobile navigation, populated editor and cards, no page overflow, exact number tokens, visible keyboard focus/AA contrast in light/dark Admin, missing-font/no-JS/print behavior and no new console/CSP/off-origin errors. Human screen-reader acceptance remains a separate explicit gate.

Exercise notebook add/search/remove/clear/share reopen, deduplication, bounds, hostile values, inactive/withheld/cross-check/legacy-only/withdrawn selections, immediate eligibility changes and both prefixes. Unit/route tests must pin source data fingerprints and GET/HEAD-only behavior. Compare protected data/CMS/schema fingerprints around the complete isolated browser workflow. Production installation, if authorized, affects only prumo and prumo-backoffice; the worker and shared edge must remain untouched.
