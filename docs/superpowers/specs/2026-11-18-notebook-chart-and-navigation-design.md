# Notebook chart and public navigation

Status: implementation authorized by the owner's request; release remains separate.
Baseline: pipeline-rebuild/main 24a3dc7, running runtime 42c581f. No migration or ingestion work.

## Requested outcome

The reader can plot the selected Caderno series on one chart, and the public site has coherent app-like navigation with aligned search controls. Preserve Carmim, paper/charcoal, the approved plumb-bob, local Lato/Schola and the enlarged reading scale. Improve hierarchy and layout, not decorative motion or a SPA rewrite.

## Navigation contract

Extract public navigation preparation and header markup before changing layout. Desktop: a masthead with brand on the left and a single aligned search control on the right; a separate destination rail anchored to the same content edges. Group themes under a labelled native disclosure rather than equal-weight links for every topic. Keep Início, Comparações, Caderno and Páginas discoverable, with Fontes and Metodologia as supporting destinations. Exact page links receive aria-current; nested routes receive honest section context, never a falsely current home link. Compact layout uses an in-flow native menu, no overlay or focus trap. Search stays one aligned input/button control, including at 320px. Preserve semantic landmarks, skip link, large text, real focus outlines and labelled actions. No new runtime JavaScript required for navigation. Do not load Tabler's administrative stylesheet on public pages.

## Caderno chart contract

Retain the ordered, bounded twelve-card notebook and its stateless public GET/HEAD link. The user explicitly authorizes reader-configured charts here, superseding the earlier cards-only restriction. No account, cookie, local storage, write route or new data fetch API.

The page adds an Evolution together panel before the cards. It offers an explicit chart subset (up to six selected notebook series) and shared or dual axes. Default: all selected series if there are at most six, on a shared axis. Never silently choose a largest group, omit an incompatible side or truncate an over-limit group. When the selection cannot be drawn, keep every eligible card, explain the specific readable reason and leave the configuration controls available. An empty notebook remains a simple search/empty state. A one-series notebook may render a single-series chart.

Use bounded optional repeated g parameters for an explicit chart subset, escala=comum|dupla, janela=max|5a|10a and an optional ISO UTC day for interval histories. Validate parameters before opening the database; malformed references, excess parameters and references outside the notebook are invalid addresses. Distinguish implicit all from an explicit group. Preserve chart settings through search, add, remove and canonical links; prune a removed reference without accidentally selecting all other series. The clean share link omits only the transient search term. No automatic persistence outside the address.

Every chart side must remain public-eligible (active, primary, redistributable, verified fetched values). A previously explicitly selected side losing eligibility makes that entire chart unavailable, while eligible cards remain. Missing catalogue text follows the logged generic 503 policy. Never reveal identifiers or internal rejection codes as reader copy.

All sides have the same native periodicity. Shared axes additionally require matching native unit, multiplier and index base; independently labelled series retain their geography, adjustment and definition. Dual axes require exactly two series and a deliberate choice, with both units visible. Do not normalize, rebase, interpolate, resample, invent zero values or imply causality. Explain that comparing curves alone does not establish a relationship. More than two distinct unit scales cannot be drawn.

Non-interval values use the existing bounded window semantics and native calendar coordinates. Interval histories are bounded to one common selected UTC day using existing day/range reads; never load unbounded interval history or invent aggregation. If interval support cannot meet this contract, retain an explicit unavailable state rather than a misleading graph.

Intersect finite values for every side, preserve exact source tokens and flags, report excluded periods and show every plotted period in the table. Summary and provenance belong to the last common finite period, not each series' newest value. Same-snapshot server preparation drives SVG, local ECharts payload, keyboard/pointer/touch readout and complete table. Reuse existing chart preparation, style and provenance contracts. No second request for chart data. Public notebook gets the narrowly allowed script policy only when it has a valid payload; empty/incompatible/errors remain script-free and noindex.

## Composition and boundaries

Separate address parsing, chart preparation, HTTP handling and markup. SQL stays in ingest/db.py. Reuse the authoritative card template and chart shell. Place chart controls, canonical link and clear action near the current selection, with cards still readable. Keep search results usable as stacked labelled records on narrow screens. Avoid a large fixed header; no sticky element may obscure focus/content at narrow widths. Keep print, no-JavaScript and blocked-bundle SVG/table alternatives.

## Acceptance and delivery

Record the initial independent design critique, scoped failing/passing tests and independent specification then quality reviews. Verify the actual page with a fresh online read-only production backup, including both mount shapes and 320/390/768/1024/1440 widths plus breakpoint neighbours. Check native menu/search keyboard, current destinations, asset bytes/fonts, chart exact first/interior/last pointer/touch/keyboard values, dual axes, incompatible groups, complete table, no-JavaScript/blocked bundle/print, CSP, no external requests and whole-copy fingerprints. Human screen-reader acceptance stays separate.

Controller owns the final full suite and lint gate on frozen runtime files, plus a detached committed-tree focused gate. Update HANDOFF, reader guide and /home/joao/vaults/projects/prumo/roadmap-e-implementacao.md. Commit and push only the reviewed branch. No merge/deploy, production content write, migration, worker restart, shared-edge change or AI phase is included without a release instruction.

## Binding review resolutions

- All notebook responses remain noindex, including successful charts. Empty/incompatible/error responses do not enable scripts.
- Add grafico=off as explicit empty chart state. With grafico=on and no g values the submitted subset is empty, not implicit all; ordinary old addresses with neither parameter still mean all. Preserve the addressed s selection and explicit g references in chart-page canonical/search/add links when eligibility changes. Prune g only for deliberate card removal, never for rights/availability loss. Removing the final explicit g sets grafico=off, never implicit all. Keep a clear distinction between addressed and eligible selections; existing unavailable-card copy remains.
- Default window is rolling ten years (janela=10a maps to existing 10y, 5a to 5y, max to max). Old addresses remain valid but now default to this bounded chart window. Windows are explicitly shown and shareable, anchored to the newest shared data period, not the server date. Exact complete table and SVG are never silently truncated. Measure max-history six-series size and preserve a documented measured budget exception if it exceeds 250 kB; prefer a collapsed complete table rather than hiding data.
- Intervals: choose the newest shared available UTC day with at least two common finite points. An explicit valid day without common values gives a chart-unavailable explanation without substitution; a one-common-point explicit day may use a visible marker. Bound each range read to that day. A malformed ISO day is an invalid address.
- Retain a deliberate dual-axis mode when add/remove leaves a different group size; explain that exactly two sides are needed and offer the shared-scale setting. Seven to twelve implicit sides show a choose-up-to-six state plus controls; no automatic group selection.
- Prepare N-way finite intersection and exclusion counts before model construction, including calendar-unparseable values. A legend uses the series title and adds publisher (then unit/adjustment) only when needed to disambiguate; full source/definition metadata remains in a disclosure. If labels still collide, return a readable unavailable state rather than a public500. Validate the primary role for each side through the existing eligibility rule.
- At320px a single joined search control may use an icon-only submit with its visible icon and accessible name Procurar; desktop keeps icon plus text. This explicitly replaces the earlier stacked-search decision while preserving the input and button font scale, minimum hit target and visible input label. Never assume a230px input minimum at this width.
- Current theme remains visible in the disclosure summary (e.g. Economia). Exact route links use aria-current=page; parent/current-section elements use an explicit visual/context label without claiming the parent is the current page. Active routes must work with both X-Forwarded-Prefix and a real root_path mount.
- Update intentional route/no-script assertions and parse hidden s inputs within their respective forms. Preserve old home goldens as historical captures; compare unchanged CMS/fallback content below the new shared chrome instead of regenerating them blindly. Hide notebook chart controls and management toolbar in print.

## Implementation slices

1. Refactor navigation contract/header; refactor notebook settings and chart preparation seams without changing existing data behavior.
2. Implement responsive public shell and explicit chart composition in disjoint owned files, with focused regression tests.
3. Controller integrates styles, exercises real browser/data-copy flows, fixes review findings and records final evidence.
4. Freeze runtime, run controller full suite, committed-tree check, update handoff/roadmap and publish branch.
