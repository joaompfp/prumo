# Prumo: encontrar, reunir e ler indicadores

> For Hermes: use subagent-driven-development for isolated implementation slices, then independent specification and quality review. The owner authorized planning, implementation and a verified production iteration in the current request.

Goal: make finding several indicators and inspecting them together a continuous task, while editorial comparisons remain authored in the CMS.

Architecture: keep the native GET/HEAD public application, address-based Caderno and the existing same-snapshot chart model. Refactor shared presentation boundaries before behavior changes. Reuse the current pinned ECharts engine and catalogue; introduce no external UI/search service, source-data writes, migrations or authentication changes.

Stack: Python/FastAPI/Jinja, SQLite read-only snapshots, local CSS and pinned ECharts, native forms with progressive enhancement only where necessary.

Baseline: main `3b29735`, runtime `63662ba`, verified in the repository and live on 26/11. Evidence input: `/home/joao/reports/prumo-ollama-critique-20261125T210214Z/REPORT.md`. The report contains independent Kimi and DeepSeek critiques and explicit coordinator rejections; rejected rounding/cropping claims do not become requirements.

## Product decisions and alternatives

Keep the current reading scale, local Lato/Schola, carmim and plumb-bob. Prioritize the relationship between plot, selected period and series identity over another visual-library migration. A permanently open sidebar would reduce laptop chart width; a compact adjacent inspector with secondary metadata disclosed is the first prototype. A focus mode is deferred until this composition has been measured.

Preserve the public/editorial boundary. A comparison's series, axes, transformation and title remain configured in authenticated Admin and published through its existing lifecycle. Reader selection belongs only to Caderno and catalogue entry. No arbitrary public configuration is added to authored comparisons.

Retain four significant figures for normal reader strings through the shared formatter; original values, geometry, provenance, calculations and CSV remain exact. Do not fill temporal gaps or add statistical transformations to repair layout.

## Roadmap

| Phase | Outcome | Acceptance | Status |
|---|---|---|---|
| L1. Adjacent inspection | Period control and structured series/value rows immediately follow the canvas; detailed metadata no longer separates them | Published dual/multicountry charts, native mixed-frequency Caderno and detail; pointer/touch/keyboard exactness, no-JS/blocked/print, both mounts, 320/390/768/1440/1920 | Installed 26/11, runtime `17b65de`; verified in installed.md |
| L2. Build a selection from search | Native multi-result selection, explicit current selection, one action to open Caderno; selections survive search/filter/pagination deliberately | Select Portugal/Spain/Germany together, add to existing references, remove a selection, cross pages without loss, no cookies or public writes; twelve-card/six-plot rules remain | Installed 26/11 at 10:26; usability correction release `79c182b` installed at 13:55, native Caderno batch and sticky progressive feedback; reports/selection-ux |
| L3. Discover by subject | Theme vocabulary helps complete catalogue discovery; useful verified empty states, without broadening bounded notebook suggestions accidentally | `energia` offers actual eligible energy series; multi-token/accent/filter/withdrawal/count tests; no invented unavailable destinations | Installed 26/11, runtime `17b65de`; bounded suggestions unchanged |
| L4. CMS-authored data-first entry | Compact homepage opening plus visible published values and comparison entry | Real published content with unit/period/source above the desktop fold, mobile usable, editor can change composition, operator drafts preserved | Planned next; no live CMS edits in L1-L3 |
| L5. Comparable-country discovery | Group comparable concepts and make country choices clearer; related published comparisons | Transparent grouping/ordering, truthful counts/coverage, no hidden definition differences | Planned after selection workflow |
| L6. Focus measurement | Optional analytical focus after measuring the new composition | Separate design and evidence; no global type reduction | Future, not part of this release |
| L7. Dated analysis and AI | Fixed references and editable AI drafts approved by a person | Separate design; no automatic public generation/publication | Future, not part of this release |

Separate open tracks remain rights/DGEG, stale historical periods, operational authoring, historical worker cause/elapsed acceptance and human screen-reader testing. A UI release closes none of those gates.

## Mobile inspection amendment

Installed 26/11 at 21:32 UTC, runtime/main `f6fc106`, exact CI `45897388598`. The owner found that the floating tooltip obscures mobile plots. L1 now has distinct presentation modes: fine hovering desktop retains the safe DOM tooltip, while narrow/coarse and actual touch/pen use the shared persistent period/series/value rows immediately below the plot, before the native range. Stable swatch/title/value slots prevent wrapping from detaching labels. No duplicate tooltip box, reduced reading size, public composition setting or statistical change is introduced. Hybrid input and viewport changes preserve the period; native touch scrolling leaves selection unchanged. This supersedes only L1's universal range-before-readout and floating mobile assumptions. Source metadata remains secondary and available without JavaScript and in print. Implementation and installed browser gates passed; reader observation completed at 21:46:59 UTC with 900.034003 seconds/30 stable samples and the final 36 state/access checks passed again. L4 remains next.

## Selection usability amendment

The owner found the first L2 delivery difficult to use. The revised contract makes batch choice primary in selectable catalogue rows and Caderno quick search, removing the competing per-row one-series action only in that selection context. Query and choices share a native form, including further searches, ordering and removals. A compact sticky tray replaces duplicated pre-result scaffolding. A small local progressive script supplies live feedback and enhanced twelve-item limits while native GET recovery remains usable without it. This supersedes the earlier iteration's script-free choice and its individual-shortcut decision on selectable rows. Chart settings apply to the submitted notebook; pending selection must first be applied. Ordinary link navigation does not autosave a pending form. No editorial CMS/source-data boundary changes.

## Binding review resolutions before implementation

Independent design review identified missing transition details. These decisions supersede ambiguous shorthand in the slices below.

L1 order is canvas, inspector (range followed by selected-period rows), compact visible color/pattern legend, then secondary source/definition metadata in a native `details` with summary `Séries, eixos e fontes`. Each multi-series readout row uses the prepared series style swatch and prepared axis/unit membership; no re-inference from translated unit names. Hide the inspector until enhancement succeeds, so blocked/no-JS has no empty control gap. Keep every fallback source/series link accessible. Force the metadata disclosure open in print, including its native details-content wrapper. Cover `_cms_blocks.html` and static Admin previews as well as `_cms_analysis.html`, notebook, primary and derived consumers. Do not shrink the installed mobile canvas dimensions or functional text. The control remains outside every configuration form. Clarify calendar position versus a monthly/annual observation through row labels, not duplicated latest-date prose.

L2 uses ONE native GET form with id `discovery-form`. Query, filters, result checkboxes, selection tray and pager buttons all belong to that form. Only the query/filter group has the search landmark. All result controls submit together. Search/filter submits reset to page one; previous/next submit a `pagina` value, carrying the current checked set. No link claims to carry unsaved changes. Bounded repeated `ordem` fields retain the previously applied selection order across hidden off-page and visible checkbox fields; they cannot select absent/unchecked references, and new choices append in submission order. Clearing the selection deliberately resets old chart settings.  The individually labelled create-Caderno link remains a distinct one-series shortcut. The shared result partial gets an explicit opt-in selection context; theme pages retain their working single-series entry and have no orphan checkboxes.

| Native transition | Submitted state and result |
|---|---|
| Check results, search again or apply filters | Every checked current result plus selected off-page hidden references; reset page to one |
| Check results, change page | Same selection and query/filters plus requested `pagina`; no lost unsaved checks |
| Uncheck a current result | Its id is absent; do not also emit a hidden input for it |
| Remove a tray item | A named `retirar` submit carries the current form state; validate/remove just that reference, preserving the rest |
| Open the selection | Named `acao=abrir` submit to the discovery route; validate and redirect to canonical Caderno with ordered unique references and compatible preserved settings |
| Enter from Caderno | Link to catalogue carrying addressed `s` and the actual chart settings; deliberately removed plotted members are pruned through the existing chart helper |
| Clear or change query/filter | Use named native form actions where retention is claimed, not anchors that discard unsaved checks |

Discovery accepts at most 48 raw bounded valid series-reference parameters before deduplication, to allow recovery when up to 24 visible results are added to a prior selection. Over that hard ceiling or malformed references give a generic invalid-address response before DB work, with no identifier echo. The discovery recovery model retains all ordered unique references through 48, visibly reports counts above the Caderno limit of twelve and refuses the `abrir` handoff while over limit. No silent truncation. Ordered deduplication removes duplicates explicitly; its notice is separate from the notebook's unchanged strict twelve-raw-parameter parser. A final handoff contains no duplicate `s` fields.

Resolve selected names/eligibility from the same fresh catalogue snapshot without loading histories. The summary says `referências selecionadas`; unavailable entries have a generic reader label, a visible unavailable state and a remove control, never a raw identifier or protected label. Up to twelve unavailable references may be passed to the Caderno's existing explicit skipped-state contract, not silently removed. The compact tray precedes the results and lists selected references with native remove submits inside a review disclosure; it cannot cover result actions on mobile. The displayed count describes the last server response and labels explain that new checks travel on submission. The open action is always available, even on a first visit or a previously over-limit response: the actual submitted set is validated on the server, so checking or unchecking results needs no intermediate refresh. A second clearly named open action follows the results. No JavaScript is needed in this iteration.

Keep the two selection bounds explicit: twelve cards maximum and six drawn series. A seven-to-twelve-reference handoff preserves every card and presents the existing nearby choose-up-to-six state. Existing chart settings survive catalogue round trips; deliberate removals prune only their group entries. L2 owns `app/notebook.py`, `_notebook_search.html` and the top add-link integration in `_notebook_chart.html` too; isolated branches may touch that last file in separate hunks, coordinated during integration.

L3 adds a catalogue-only matching helper using the resolved theme TITLE (for example `Energia`), not its blurb. `reads.search` and its bounded phrase/cap contract remain unchanged. Empty-state suggestions, if implemented, are only already-resolved theme options with eligible counts from the same snapshot; otherwise retain the honest generic recovery text without promising a recommendation system. No new aliases for unavailable concepts.

The original review is retained under `../handoff/reports/analysis-loop/design-review.md`. L6 focus measurement and L7 dated analysis/AI require separate specs; they are not a shared implementation task. Human screen-reader acceptance remains open regardless of automated results.

## Implementation slices

### 1. Shared inspection boundary

Files: `app/templates/_chart.html`, `static/css/chart-inspector.css`; consumers `_cms_analysis.html`, `_notebook_chart.html`, primary/derived chart templates; affected tests under `tests/app/`.

First extract secondary metadata into a named native disclosure while preserving its populated links, units, sources and print/no-JS visibility. Commit a behavior-neutral boundary extraction where applicable. Then put `.chart-controls` immediately after `.chart-scroll` and before the secondary series metadata. The native range and point readout must stay outside configuration forms. Readout rows must identify the series, scale/unit and the actual inspected native period, not a bare list of latest dates. Label complete coverage as `Todo o histórico` where existing copy says `Máximo`.

Write a failing DOM-order test before changing markup. Run focused interaction/layout/typography tests. If the current payload already carries the required labels/styles, consume it rather than adding parallel calculations. Rebuild/hash the chart bundle only if source behavior changes, preserving CSP and vendored-byte guards.

### 2. Native catalogue selection boundary

Files: a small selection contract module if required, `app/reads.py` only for discovery matching, `app/main.py` for bounded request parsing, `app/templates/search.html`, `_series_results.html`, `static/css/discovery.css`, focused discovery/selection tests.

Define ordered bounded series references through the existing notebook parser/URL helper before opening the DB. Keep query/filter state and selection in native GET submissions. Show checkbox labels, a clear selection summary and `Abrir caderno`; retain the individual entry. Search, filters and page navigation must not discard current selection. If JavaScript is unnecessary, do not add a script exception to summaries. Preserve unavailable addressed references honestly and never silently truncate an over-limit request. Reuse twelve-card/six-plot validation; selection is not a CMS publication.

Write red tests for several submitted results, preserving earlier references, unchecking current results, changing page/query and the pre-deduplication bound. Then implement and run discovery/notebook/boundary tests. Prevent nested forms and ensure each control has one valid native form owner.

### 3. Subject matching

Extend only the complete catalogue matching contract with resolved theme vocabulary/approved aliases, using the existing normalization. Preserve bounded notebook suggestion behavior. Write red `energia`, accent, multi-token, filter/count and withheld/withdrawn tests, then implement. Avoid a speculative concept grouping system in this slice.

### 4. Populated acceptance and review

Use an isolated online SQLite copy made through a read-only `readonly_shm=1` source, never copying the live main file alone. Fingerprint before/after. Compare baseline/candidate first views at matching viewports with actual fonts and values. Check real pointer/touch/keyboard endpoints, complete tooltip/readout strings and native periods, table and source access, static Admin preview, no-JavaScript/blocked-bundle/print and off-origin/CSP errors. Capture neutral and active states separately, assert scrollY=0 for first views.

Controller owns full offline pytest and ruff; independent reviewers inspect exact contracts and scoped probes, specification first and quality second. Freeze executable files before the authoritative run. A clean committed worktree must import the actual new modules and exercise new templates/assets before push. Record exact counts and any genuine failures rather than substituting old suites.

### 5. Authorized delivery

Affected services: public `prumo` and static-preview `prumo-backoffice`; preserve `prumo-ingest`, CMS/history, schema, statistical data, Authelia and Traefik. Read current operations and existing production-probe/prebuild/activation helpers first. Bind-mounted live checkout must not advance during build: build the pushed exact SHA from a detached context through `dc-web`; pin current rollback images, verify immediate preactivation baselines, stop only the bind-mounted reader, fast-forward and recreate the two readers via normal `dc-web-up` aliases. Verify exact-release hosted CI before activation.

Read back actual images, health, untouched worker identity/image/start/restarts and CMS/schema hashes; exercise the new selection and point-reading operation at both public addresses. Observe the installed readers, then write installed evidence, update HANDOFF and the owner roadmap. Keep report HEAD separate from runtime CI SHA; a prose-only closeout must not recreate services. The user requested notification only once the new iteration is online; required progress notes stay minimal.
