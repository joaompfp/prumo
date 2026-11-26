# Prumo: interactive charts on comparison and detail pages

Date: 2026-11-16
Status: implementation authorized within the statistics CMS cycle; implemented on the development branch, not deployed. Final acceptance gates are recorded in the current handoff.

## Responsive inspection amendment (2026-11-26)

The owner prefers an unobstructed mobile plot and the existing floating desktop effect. Narrow viewports below 600 CSS pixels or a coarse primary pointer use the existing persistent readout immediately below the plot, full width, before the native range. Each swatch stays beside its own title and the value below that title. Do not duplicate the tooltip as a second below-plot box. Fine hovering pointers at wider viewports retain the safe DOM tooltip. On hybrid devices an actual touch or pen switches to inline inspection; a mouse restores eligible desktop hover. Responsive changes preserve the inspected period and remove stale overlays.

A tap selects an actual observed point and retains the prepared reader values; a vertical drag scrolls without changing the selected row. Keyboard and the labelled native range remain available, without adding public composition settings to published CMS comparisons. No numerical precision, geometry, alignment, source token, CSV, schema, CMS document, security policy or fallback changes belong to this presentation fix. Static Admin preview stays non-executable; no-JavaScript and print still use SVG. This supersedes only the earlier requirement for a floating mobile tooltip.

## Implementation amendment (2026-11-17)

The mobile verification found that ECharts 6.1.0 richText tooltips cannot wrap the complete exact value strings. The implemented formatter therefore returns DOM nodes constructed exclusively with createElement/textContent, never HTML strings. This is a narrow amendment to the richText-only/no-HTML-tooltip wording below, supported by an independent browser security review: hostile titles remained literal text, no injected element executed, and the existing strict CSP stayed unchanged, with no unsafe-inline, unsafe-eval, remote origin or connect-src permission. The formatter must always return a node; a future HTML-string formatter is outside this amendment. This is a presentation correction, not a change to source tokens, coordinate domains or statistical methods.

Cartesian pixel conversion and touch-release handling were corrected from real mobile tests; right-axis names grow into their available margin instead of shrinking the data region. Controls and footer links wrap on narrow screens. SVG remains accessible, script-free fallback and print output. The separate CMS preview is intentionally static and identifies itself as such, while public analytical pages retain interactive inspection.
Baseline: `3cb9d51` on `pipeline-rebuild` and `main`.

## Objective

Add point inspection with Apache ECharts where the reader studies a chart: the existing comparison pages and individual series pages. Keep server-generated SVG (Scalable Vector Graphics) for cards, lists and small summaries. The owner described the desired interaction as reading a point while moving over the chart, and explicitly distinguished that use from the small SVG summaries.

A reader can move the pointer, tap a period, or use a keyboard control to read the period and the exact displayed value of each plotted series. Comparisons inspect both lines at the same common period. This does not add or edit data, select new comparison pairs, or configure pages in the backoffice.

This spec replaces only D8's blanket no-JavaScript/no-third-party-library rule in `2026-11-15-public-ui-design.md`, and the equivalent no-script checks in the comparison spec, for the detail surfaces below. Local-only assets, privacy, primary/verified/licensed reads, exact values, provenance, and the server-rendered fallback remain binding. The existing historical specs are not rewritten as if this were the original design.

## Scope

| Surface | Rendering after successful enhancement |
|---|---|
| `/comparar/{slug}` | ECharts for the existing curated pair; the approved dual axis for `credito-e-taxa` stays |
| `/series/{id}` | ECharts for the selected server-side window; includes E-REDES for one selected UTC day |
| `/calculadas/{key}` | ECharts for the calculated series; its calculated badge, formula, inputs and caveats stay |
| Home, theme lists, search, `/comparar` index, other summaries | Current HTML and SVG; no script or chart payload added |
| Errors, CSV exports, backoffice | Unchanged |

No new routes, JSON endpoints, SQL statements or database methods, migrations, write paths, services, remote assets, cookies or analytics. The narrow UTC-day correction below may reread existing metadata once; it does not contact the publisher. No free pairing, smoothing, interpolation, aggregation, rebasing, data sampling, legend toggling, toolbox, zoom or cross-day loading. Existing window links and the UTC day form remain GET navigation. A later need for additional interactions gets its own scope; no unused modules are bundled now.

## Measured feasibility

The old UI loaded ECharts 5.5.0 from jsDelivr (`legacy-ui-final:templates/dashboard.html:46`). It is not a locally vendored asset to restore, and its API-based adapter is not reusable unchanged.

An isolated probe fetched official ECharts 6.1.0 and built only `LineChart`, `GridComponent`, `TooltipComponent` and `CanvasRenderer` with esbuild 0.25.12. It did not modify Prumo's dependency files or running services.

| Asset | Minified bytes | Local gzip bytes |
|---|---|---|
| Full ECharts 6.1.0 distribution | 1,121,883 | 368,202 |
| Line/grid/tooltip/canvas proof engine | 501,845 | 170,575 |

The smaller build is an engine probe, not the finished Prumo adapter. Gzip figures are local compression measurements, not proof that production serves compressed responses. The final bundle must stay at or below 650,000 raw bytes and 220,000 gzip bytes, include the adapter, and record its actual transfer size separately.

Chromium at 1440 px accepted pointer inspection and at 390 px accepted an interior touch point. Both displayed the supplied exact decimal strings on two axes, with no console errors/warnings, CSP (Content Security Policy) violations, external requests or horizontal overflow. Canvas plus `tooltip.renderMode='richText'` worked with `style-src 'self'` and without `unsafe-inline` or `unsafe-eval`.

This is synthetic feasibility evidence, not production-data, accessibility, fallback or performance acceptance. An initial tap exactly on the mobile plot's first boundary did not open the tooltip; changing to an interior point established basic touch operation, not edge-target correctness. First/last-period touch targets and scroll behaviour are explicit release tests.

Current uncompressed public HTML spot checks were 123,013 bytes for the IPC detail, 55,817 for IHPC, 183,945 for the dual-axis comparison and 162,190 for Euribor/inflation. These are candidates, not an exhaustive largest-page baseline. Base/calculated history and common-period comparisons have no artificial point cap; their measured population and largest-page budget must be established on the current production copy before implementation. E-REDES remains one UTC day. Never drop points to meet an asset or HTML budget.

Evidence and reproducible source: `../handoff/reports/echarts-feasibility/README.md`.

## Architecture and boundaries

### Shared chart preparation before adding behaviour

Refactor the existing chart preparation into a small pure Python module before adding the interactive renderer. It owns finite-point selection, calendar x positions, comparison breaks, numeric domains/ticks and the association between coordinates and exact reader strings. Preserve current SVG output during this refactor. Do not copy the domain, alignment or precision rules into a second JavaScript implementation.

`app/reads.py` still composes page data from `Db` methods on the existing read-only transaction. `app/charts.py` renders SVG from the prepared chart; one payload serializer exposes only what the browser renderer needs. Templates own structure; the local JavaScript adapter owns chart lifecycle and interaction. SQL remains in `ingest/db.py`, and this feature needs no new query.

The payload comes from the same page result and the same database snapshot as the fallback and its table. Do not request data again after page load. Emit a versioned JSON (JavaScript Object Notation) data block using Jinja's `tojson`, read with `textContent` and `JSON.parse`; never construct JSON by concatenation or inject catalogue text through `innerHTML`.

The compact model carries an accessible chart name, per-series reader title/unit/source label, scale mode, x coordinates, explicit break positions, axis bounds and per-point period/value display strings. Arrays may remove repeated metadata. Raw internal series ids, derived keys, licence notes and stored vocabulary codes are not presentation fields. Finite drawing coordinates are numbers; reported values are server-formatted strings. If safe numeric coordinates cannot be produced, decline enhancement and keep the SVG rather than throwing away data or failing the page.

### Progressive enhancement

Keep the server SVG and existing content visible by default. A single deferred, local, content-fingerprinted bundle initialises a separate chart container. Only after successful `setOption` does the adapter add a CSS class that swaps visual display to the canvas. A missing bundle, malformed payload, unsupported API or renderer failure leaves the SVG and table usable. Dispose a partial chart and disconnect observers on failure.

Do not remove the fallback from the document. Use print CSS to show SVG and hide canvas/interaction controls. Keep one accessible chart description: the server SVG retains its accessible name even when visually hidden; the canvas is `aria-hidden`. On success keep the SVG in flow at `opacity:0; pointer-events:none` and absolutely position the canvas over that same wrapper. Never use `display:none`, `visibility:hidden` or `aria-hidden` on the screen-reader SVG. Print CSS restores opacity and hides the canvas. Avoid duplicate accessible figures and do not append a unit to a calculated title that already states it.

The in-flow SVG sets the wrapper height before and after enhancement; reserve the control/readout row in the initial server layout as well, so subsequent content does not move when controls become active. A `ResizeObserver` resizes the chart; no polling timer or global chart registry. Read the current CSS colour/font tokens instead of reviving the legacy palette. In the feature commit, make comparison A solid ink and B dashed red in both renderers and their legend; this is an explicit presentation change after, not during, the SVG-preserving refactor. Preserve the caption. Set `animation:false` for deterministic fixed-data rendering.

### Exact point inspection and keyboard access

The tooltip names the Portuguese period and each series' exact display string with its unit. The two axes and values stay distinct. Calculated data remain identified as calculated by Prumo. No tooltip, end label or readout formats a value back from a JavaScript number; `3.90` must display as `3,90`, not `3,9`. Axis ticks alone may be rounded. Do not expose the axis pointer's approximate numeric-coordinate label as a data value.

Add an enhancement-only native range control labelled from the presentation catalogue, with one step per drawable period and `aria-valuetext` set to its readable period. Arrow keys and Home/End select the previous/next/first/last period. A persistent text readout uses the same point selection as pointer/touch and contains the exact value(s). On focus and keyboard changes it announces through a polite live region; ordinary pointer movement must not flood assistive technology announcements. The range is absent or hidden until enhancement succeeds, so there is no dead focus stop without JavaScript. An empty chart has no control; a one-point chart has a visible point and a static readout without a useless slider.

This covers every loaded chart point, including older points outside a series page's existing 60-row table. Do not describe that table as complete: its current limit and note remain. Comparison and calculated tables retain all plotted rows. The E-REDES table retains all intervals of the selected day. CSV remains the complete downloadable source history.

### Time, gaps and scale

Use proportional numeric calendar coordinates matching the current SVG rather than category spacing that compresses missing periods. Comparison observations remain the intersection where both values are finite, exactly as today; do not expand the pair to the union or inspect an unpaired period. Insert null gap sentinels in the draw stream at the prepared break positions, with `connectNulls:false`. A sentinel has no reported value and is never a slider step, tooltip row or table row. Base/derived series explicitly use `connectNulls:true`, retaining their current connection across missing observations. No invented zero, interpolated value or carried-forward observation may enter either renderer or the readout.

The Python model owns each y-axis minimum, maximum and uniform tick interval. The payload carries those fields for both axes when dual; the adapter sets ECharts `min`, `max` and `interval` rather than accepting its automatic scale. Assert the rendered bounds and tick positions against the prepared model. Only formatting of axis tick labels is approximate; domain/tick choice is not recomputed in the browser.

Scale mode comes from the curated comparison definition, never from comparing unit labels or a browser parameter. The two percentage pairs have one axis; `credito-e-taxa` has two, visibly labelled on both sides, with independent numeric bounds and no common-zero emphasis. Keep the warning about magnitudes and causation. Give a single point a visible symbol.

E-REDES remains at most one selected UTC (Coordinated Universal Time) day, normally up to 96 intervals. Readout periods and x labels use UTC regardless of the browser timezone; ticks show hours, not repeated dates. Both renderers must name the actual selected day. The latest-series headline remains explicitly the latest-series figure, not a claim about an older selected day. The current `series_page` silently chooses another day if the requested day is absent from cached metadata (`app/reads.py:295-305`). Correct that narrow case by calling the existing `Db.public_day_counts` once on the same read-only handle and using the returned rows without a publisher fetch or new SQL statement. If an explicitly requested day is still absent, return 404; an omitted day retains the current default. Existing database failures retain the normal 503 handling, with no new retry/timeout policy. Include this extra metadata-read cost in the newly-available-day timing case. This intentional invalid-day correction is separate from renderer work; it is not permission to refactor unrelated caches.

### Scripts, security and distribution

Only successful HTML detail responses that embed a chart payload receive `script-src 'self'; script-src-attr 'none'` in their existing CSP. Other pages keep the current no-script policy. Set one effective policy, not two conflicting headers. Do not decide this from a path prefix that also matches CSV or error responses.

Keep `default-src 'none'; style-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`. No inline executable scripts, event attributes, `unsafe-inline`, `unsafe-eval`, remote loader, `connect-src` permission or HTML tooltip. Retain `nosniff`, validated `X-Forwarded-Prefix` and `Vary`. The inert data block is escaped even for catalogue text containing `</script>`, quotes, ampersands and rich-text delimiters.

Build source and an exact npm lockfile belong in a dedicated tooling directory, not the Python runtime. Commit the generated chart bundle, its hash, ECharts/ZRender/tslib licences and notices, and the documented reproducible command. The existing Dockerfile copies `static/`; production needs neither Node nor npm, and no request may fetch library code from a CDN. ECharts is pinned at 6.1.0 for this design; upgrades require a rebuilt asset and fresh checks.

All script and stylesheet URLs use the validated mount base, supporting both `cae.joao.date` and `joao.date/dados`. No scripts are inserted globally into the base template's output: an empty script block on other pages must preserve their rendered bytes and home golden.

## Verification and acceptance

Use the existing `.venv-ci` Python environment. Application tests: `.venv-ci/bin/python -m pytest tests/app -q`. Final gate: `.venv-ci/bin/python -m pytest tests -q`. Lint: `.venv-ci/bin/ruff check app/ ingest/ presentation/ tests/`. Browser probes use a Python environment with Playwright and an installed Chromium; `.venv-ci` currently has no Playwright. The feasibility README records the exact build and probe commands already exercised. Implementers add and verify the final adapter build/test command when its tooling exists.

| Acceptance | Required proof |
|---|---|
| Shared preparation | Refactor-only tests and unchanged SVG snapshots before new interaction code; later domain/tick parity and solid/dashed legend parity in both renderers |
| Route scope | Local bundle/payload only on eligible detail responses; no scripts on home, lists, index, errors, exports or backoffice |
| Same values | JSON, SVG and readout share drawable periods; comparison/calculated tables contain the identical period set; series table subset is labelled |
| Precision and safe text | Trailing zeros, negative and grouped values, hostile catalogue titles, null/nonfinite values and empty/single-point cases |
| Scale and gaps | Both one-axis pairs, approved dual-axis pair, nonconsecutive periods and proportional x spacing; no smoothing/sampling |
| Pointer, touch and keyboard | First/interior/last drawable common point, one-point chart, both comparison values together, no gap-sentinel inspection, Arrow/Home/End, no keyboard trap or pointer announcement flood; accessibility-tree check plus a real screen-reader pass, or report that acceptance gate as unmet |
| UTC day | Old/current/newly available days, warm cache, no silent day substitution, hour ticks, both renderers consistent in Lisbon and non-European browser timezones |
| Fallback and print | JavaScript disabled, bundle blocked, invalid data and partial init failure retain SVG/table; enhanced accessibility tree still has one named chart; following-block offset is unchanged after enhancement; print selects SVG |
| Browser security | No console errors/warnings, CSP violations, off-origin requests or executable text injection; check real interactions, not only a successful load |
| Responsive | 320, 390, 768 and 1440 px: no clipping or overflow, readable right-axis unit, vertical touch scroll works |
| Budgets | Final engine+adapter bytes and actual transfer encoding; unchanged summary bytes/assets; measure the largest detail population before adding payloads and after. The existing 250,000-byte HTML target is provisional until that baseline; a miss requires an explicit budget decision, never truncation, lost precision or removed fallback |
| Server time | Same-copy before/after median and p95; preserve the existing 150 ms standard-page target; report existing E-REDES deviations and allow no more than 10% regression on its measured baseline |
| Existing contracts | CSV bytes, provenance, licence gates, primary/verified filtering, existing 404/503 cases, prefix handling, GET/HEAD-only and read-only database behaviour unchanged; explicit invalid UTC day gains the documented 404 correction |

Run visual QA on a current read-only production copy before freezing the tree for the full suite. The isolated renderer probe does not substitute for those checks. An independent specification review and a separate code-quality review must pass, with scoped fix/re-review rounds, before declaring implementation ready.

## Implementation order and release boundary

First refactor and test common chart preparation without behaviour changes. Then add the pinned local build, payload escaping and scoped CSP, followed by the comparison adapter and point controls. Reuse that adapter for base/calculated detail and the UTC day chart. Finish with no-JavaScript/print/failure checks, real-data browser QA, performance measurements, the full suite and independent reviews.

This is a web-only release with no migration or data write. Merge/push to `main` and installation require the owner's explicit release instruction after the gates pass. Installation uses the existing `bash -lic 'dc-web-up prumo'` on f0nix, without restarting worker/backoffice. The authoritative procedure and rollback recording remain `docs/data/operations.md`; this spec does not authorise running it. Reverting to the previous approved code and rebuilding the web container removes the enhancement without a database restore.
