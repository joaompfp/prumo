# Phase C: discovery and entry into Prumo

Date: 2026-11-25
Base: installed main `1a0bf13`, runtime `3ab1fdc`.
Authority: owner continuation after phase B, under `2026-11-19-analytical-workspace-roadmap.md`, C1-C2. This is implementation authorization, not an installation or editorial-publication decision.

## Installed checkpoint

Owner explicitly authorized merge and installation. Release/main `72fa437` is installed from 2026-11-25 13:37 UTC. Exact hosted CI, read-only public/Admin acceptance, preservation checks and recovery are recorded in `../handoff/reports/discovery-entry/installed.md`. The implementation and release-gate wording below is the approved contract, not an outstanding request for another authorization. No next phase, live CMS edit or worker change was started.

## Delivery contract

Make finding an indicator and opening a useful notebook straightforward, without making the public frontend the editor of authored comparisons. Preserve the CMS homepage, all its blocks and their text/order. Published comparison configuration remains in the authenticated backoffice. Source data, read-only SQLite safety, source rights, schema and worker remain untouched.

Retain carmim, plumb-bob geometry, local Lato/Schola, 28.05px body and the installed functional reading sizes. Use native GET forms and disclosures; discovery summaries remain script-free. Keep exact publisher values and links to provenance on both public mounts and the static Admin preview.

## C0: isolate list preparation

Extract shared search matching, filtering/order/page helpers and common row presentation before changing behavior. Keep search and theme public signatures and data/output contracts. Acceptance: baseline versus refactor model/HTML equivalence and focused route/read tests. Commit independently.

## C1: make navigation task-oriented

Keep a compact native shell, with Explore, Comparisons and Notebook as clear entries. Use the existing search route as the complete indicator catalogue; retain themes, authored pages, sources, methodology and Admin. Show exact/current-location states honestly. Avoid duplicate search controls on task pages. Keep public and static-preview navigation consistent.

Acceptance: all destinations remain discoverable in desktop/mobile; right-edge menus and long active labels fit breakpoint neighbours; labels match accessible names; keyboard and no-JavaScript navigation work without reducing type or displacing the analytical pages unnecessarily.

## C2: build an honest browsable catalogue

Add a paginated search-page contract over the same authoritative served primary catalogue and latest-value readers. Empty search opens the catalogue. Text matching accepts multiple accent-insensitive tokens. Filters cover theme, geography group, source and frequency; parameters survive pagination. Count before pagination, never call the capped row count a total. Keep the existing capped search contract for the notebook unless a separate reviewed change is needed.

Reuse the same result presentation for search and themes, reflowing exact value, period, source and collection date on narrow screens. Show a clear single-series notebook entry; its label must make clear that it opens a notebook for that indicator, not silently accumulates a cross-page saved selection. Use the existing notebook to add more series and share address state. No account, cookie, new persistent selection or public composition editor is introduced.

Acceptance: token search for an indicator and Portugal; truthful counts for over-100 matches; first/last pagination and invalid/empty filters; no silent truncation; bounded query and page handling; responsive exact values; withheld/inactive/withdrawn/legacy-only rows remain excluded.

## C3: connect existing content to exploration

Add a native notebook action to existing CMS indicator cards without changing stored editorial content or the legacy fallback contract. Reuse the actual card renderer rather than introducing an alternative source of latest-value preparation. Preserve availability policies and the complete authored home. Keep other analytical pages and the notebook state contract unchanged.

Acceptance: CMS-home card to notebook works; primary detail to notebook to adding a second indicator to a clean shared URL works without JavaScript. Read back private preview, all nine CMS comparisons and the untouched published content on the isolated copy.

Theme descriptions remain in secondary filter/help content; authored theme readings follow the data. This changes presentation only, not stored CMS order or text. Each discovery response uses fresh catalogue metadata so totals do not lag a withdrawal; the notebook retains its existing bounded search contract.

## Verification and closeout

Controller owns authoritative full offline suite and ruff. Each implementation increment gets focused checks and a separate commit. Independent specification then quality/integration review must pass; new findings get narrow correction and re-review.

Use an online backup from a canonical `mode=ro&readonly_shm=1` source and develop on the isolated scratch copy only. Fingerprint all tables/schema/CMS before and after service/browser workflows. Capture matched baseline/candidate at 320/390/768/1024/1440/1920 and relevant breakpoint neighbours, with fonts loaded and neutral top-of-page screenshots. Exercise actual search/filter/page/open/add/share tasks, both mounts, menus, keyboard, no JS, strict CSP, Admin static preview and unchanged analytical chart reading. Measure type and response times; technical checks do not replace owner visual or human screen-reader acceptance.

Archive exact evidence in `docs/superpowers/handoff/reports/discovery-entry/`; preserve initial failures separately from accepted results. Verify clean committed-checkout imports, routes/assets and affected tests before pushing the feature branch. Update the authoritative roadmap, handoff and `/home/joao/vaults/projects/prumo/roadmap-e-implementacao.md` with implemented versus installed status.

Release gate: owner visual acceptance and explicit merge/installation authorization. A future release affects public web and static-preview Admin only; no worker, migration, CMS publication, shared-edge or authentication change.
