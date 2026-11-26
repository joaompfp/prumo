# Design review: Prumo analysis loop

Read-only independent product/design and specification review. No application, CMS, database, production, or outbound communication was changed. No commits were made.

Baseline reviewed: worktree `/home/joao/projects/prumo-analysis-loop` at `3b29735` (runtime `63662ba`), roadmap `docs/superpowers/plans/2026-11-26-analysis-loop-roadmap.md`, evidence `/home/joao/reports/prumo-ollama-critique-20261125T210214Z/REPORT.md`, and the current templates, read models, tests and CSS named below.

## Verdict

**NOT PASS as written for the L1-L3 iteration.** The product direction is sound and L4-L6 are reasonable future phases. L2 cannot start safely because its native selection state model, the Caderno entry point, over-limit handling and the shared result-template scope are not specified. L1 is close but needs one explicit composition contract for order and series identity. L3 is implementable once the catalogue-only matching boundary is named.

The plan correctly keeps the current reading scale, CMS authorship, the local ECharts/SVG split, four significant figures and the existing card/chart limits. It also correctly does not adopt the rejected rounding or canvas-cropping findings.

## What is sound

- L1 treats the inspector as a composition change, not a new chart library or a global type reduction. The existing payload already carries series title, style and unit, plus axis membership for grouped and calendar charts, so the readout can consume prepared data rather than recalculate.
- The public/editorial boundary is preserved: reader selection stays in the address; authored comparisons stay in the authenticated CMS; no public configuration is added to a published comparison.
- L3 is scoped to catalogue discovery, not a new search service or a speculative concept graph. The existing normalization and catalogue read are the right base.
- L4 is feasible with the existing CMS hero, card and chart blocks. It does not require a new page model unless a populated prototype proves one.
- L5 and L6 are correctly placed after the selection workflow and are explicitly gated on separate design and evidence.
- The plan retains the separate rights/DGEG, stale-period, operational, worker and human screen-reader gates. A UI release closes none of them.

## Blocking design gaps

### B1. L2 has no single owner for native selection state

Current code has one GET form for the query and filters, with the results list outside it, and pagination links built from query/filter state only:

- `app/templates/search.html:12-38`: the `discovery-search` form owns `q`, `tema`, `grupo`, `fonte`, `frequencia`; the result list and pager are siblings.
- `app/reads.py:1069-1082`: `prev_path` and `next_path` are built from `q` and filters, never from a selection.
- `app/templates/_series_results.html` has no selection control; each result has only the individual `Criar caderno` link.

The plan says "keep query/filter state and selection in native GET submissions", "unchecking current results", "changing page/query", and "one action to open Caderno". Those requirements do not define whether a checked box is committed immediately or only after a submit. The obvious implementation, a second selection form plus hidden `s` inputs for earlier references, cannot satisfy the stated cases. Hidden inputs cannot reflect a box the reader has just checked, and a filter, query or page submission from another form cannot see it. If pagination stays as links, checked-but-not-submitted boxes are lost on page change. If the page is one form, pagination must become submit buttons, which changes the current link contract and the search landmark.

Required decision, before markup or tests:

- Choose one native model and write its transition table. Recommended: one GET form owns query, filters, checkboxes and page; `Procurar`, `Aplicar filtros` and pager controls are submits in that form; `Abrir caderno` is a submit with `formaction` pointing at the Caderno route; off-page selected references are hidden inputs only when the same id is not rendered as a checkbox on this page. Keep the search landmark scoped to the query/filter group, not the whole result list.
- Alternative if pagination links must remain: make selection explicit with an `Atualizar seleção` submit; pagination links carry only committed references; state clearly that in-flight checks are not carried by a link. This is simpler but must not be mixed with the single-form model.
- Add tests for: check Germany and Spain, change page, change query, uncheck Spain, open Caderno. Assert no reference is lost, removed references stay removed, no duplicate `s` is emitted, and the final Caderno has the expected count.

Without this decision the acceptance can be read two ways and the implementation will either lose checks or ship a second, inconsistent selection model.

### B2. The Caderno has no entry point to the new catalogue selection

The new `/pesquisa` selection is meant to support "add to existing references". The current Caderno still sends `Acrescentar` to its bounded in-page search, not to the complete catalogue:

- `app/templates/_notebook_chart.html:21`: `Acrescentar` links to `#pesquisa`.
- `app/templates/_notebook_search.html:5-12`: the in-page search form preserves the addressed series but searches through `reads.search`, with the old phrase matching and 100-row cap. It adds one series at a time through links.
- `app/reads.py:1024-1039`: `reads.search` is the bounded notebook contract, deliberately separate from `search_page`.

So a reader with three series in a Caderno who wants to add Germany, Spain and Portugal has no path to `/pesquisa` that carries those three references. The old one-at-a-time loop remains the main path, and the new multi-select surface starts from zero. The plan's L2 file list does not include `_notebook_chart.html`, `_notebook_search.html` or their tests, so this journey is outside the slice as written.

Required decision:

- Add a link from the Caderno chart area to `/pesquisa?s=...` carrying the current addressed references, and a clear return action from the selection page to the Caderno. Keep the local quick-add search only if it still has a distinct job; label the two paths so they do not look like duplicates.
- Add a journey test that starts with three addressed series, opens the catalogue with those references, selects three more, removes one, and opens the Caderno with five. The test should prove that the original three were not rebuilt from scratch.

### B3. Over-limit and unavailable references have no defined discovery behavior

`notebook.parse_selection` returns `None` when the address has more than twelve `s` values before deduplication, and returns `None` for a malformed id:

- `app/notebook.py:25-42`: the pre-deduplication limit and the generic refusal.
- `app/notebook.py:195-198`: at twelve references, an add action becomes `None`.
- `app/templates/_notebook_search.html:31-37`: the bounded search already shows a limit message instead of an add link.

The plan says to use the existing parser before opening the database and also says "never silently truncate an over-limit request" and "preserve unavailable addressed references honestly". If `/pesquisa` calls `parse_selection` directly, thirteen checked boxes or a malformed id produce `None`; a syntactically valid but withdrawn id passes the parser and is only discovered when the Caderno renders. The page can either 404, drop the whole selection, or drop the invalid id. A 404 destroys the search context; dropping is silent truncation. The plan does not choose.

Required decision:

- Use a discovery-specific bounded representation. Keep all syntactically valid addressed references for redisplay, even when the count exceeds twelve or an id is no longer eligible. Show a visible notice, withhold or disable `Abrir caderno`, and let the reader uncheck. Use `parse_selection` only for the final Caderno handoff, or add a lenient parser with a hard upper bound and explicit tests for thirteen values, a duplicate that would fit after deduplication, a malformed id and a withdrawn id.
- Define the tray wording. If eligibility is not resolved on the discovery page, call the count "referências selecionadas", not "séries", and let the Caderno show its skipped count. If the tray is meant to say "séries", resolve titles and eligibility for up to twelve ids in the same snapshot and show unavailable references separately.

"Remove a selection" also needs a defined surface for references that are not on the current page. A count alone cannot be removed without navigating back. Either render a tray row per selected reference with a remove action, or state that only current-page references can be removed and provide a clear "limpar seleção" fallback.

### B4. The shared result template would put selection controls on theme pages without a contract

`_series_results.html` is shared:

- `app/templates/search.html:42`: the catalogue includes the shared list.
- `app/templates/theme.html:30`: each theme family includes the same list.
- `app/main.py:184-186`: the theme route accepts `grupo`, `fonte`, `frequencia` and `pagina`, but not `s`.
- `app/reads.py:957-980`: `ThemePage` carries theme filters and pager paths, not selection.

If the selection markup is added to `_series_results.html` unconditionally, every theme page gets checkboxes with no valid form owner, or a form action that drops the theme context, or a route that ignores `s`. That is a public broken control, not a cosmetic issue. The plan lists `_series_results.html` but not `theme.html`, the theme route or theme tests.

Required decision:

- Either scope the selection UI to `/pesquisa` through an explicit template flag and keep theme pages on the individual `Criar caderno` entry, or extend `ThemePage` and the theme route with the same selection state. Do not ship half the control. Add a test that the non-selection page has no checkbox and the selection page has one owner per control.
- Add `app/templates/_cms_blocks.html:83` to the L1 consumer list. It calls `chart_shell` for CMS homepage chart blocks. The plan names `_cms_analysis.html`, `_notebook_chart.html` and primary/derived templates, but omits this consumer and the Admin preview path.

### B5. L1 does not specify the order that preserves series identity

Current `_chart.html` order is:

- `app/templates/_chart.html:3-13`: chart scroll, then caller metadata, then legend, then chart controls.

The plan says to move `.chart-controls` immediately after `.chart-scroll` and before the secondary series metadata. It does not say where the legend and the new disclosure go. The literal change yields: canvas, controls/readout, metadata disclosure, legend. That pushes the legend, the only current color/pattern key, below the metadata. On a 390px first view the plot already ends near the bottom of the viewport; the legend would move further down, and the readout rows currently contain title and value but no swatch. The result is a readout without the visual key in the first view, which contradicts the plan's own priority on series identity.

Required decision:

- Specify the full order: canvas, inspector, legend, secondary metadata disclosure. If the legend must sit below the inspector, add the existing swatch/pattern to each readout row from `payload.series[index].style`, reusing `.legend-swatch` / `swatch-*`; do not add a parallel style calculation.
- Define the disclosure summary text and print behavior. A closed native `details` is acceptable on screen, but print must open it. The existing print rules cover only `.notebook-workspace` details (`static/css/prumo.css:990-1009`); authored/CMS chart pages need their own rule. The plan's L1 acceptance includes print and both mounts, so this must be explicit.
- Add a no-JavaScript rule. Today `.chart-controls` keeps `min-height: 56px` while the range is hidden and the readout is empty; moving that block directly under the canvas would create a blank gap between the plot and the legend when JavaScript is blocked. Hide the controls until `.chart-enhanced` exists, or collapse the block when the readout is empty. Test no-JS and blocked-bundle states, not only print.
- Add a measured no-shrink guard: the plot SVG/canvas box at 390 and 320 must be at least the baseline 354x264 and 320-width equivalent, with no horizontal overflow. Do not let the inspector or a first-viewport assertion shrink the plot.

## Additional required corrections

These are not separate gates, but they will cause avoidable regressions if left implicit.

- **L1 test contracts change.** `tests/app/test_notebook_workspace.py:307-309` asserts `chart-scroll < notebook-chart-sources < chart-controls`. `tests/app/test_chart_layout.py:210-218` asserts the legend and controls keep their tops after enhancement. `tests/app/test_discovery_search.py:213` asserts exactly one form on `/pesquisa`. These encode the old composition. Update them with the new order and intent; do not weaken the legibility, exact-value or no-JS assertions.
- **L1 readout unit and axis.** The current readout shows the series title, native period and value, and hides a native period equal to the union period. It does not show the axis side. The payload has `unit` and, for grouped and calendar charts, `axis`; legacy pairs infer the two axes by position. Consume those fields if the row needs an explicit scale label. Do not introduce a second unit or axis calculation.
- **L2 selection control accessibility.** A raw checkbox is a small touch target. Wrap the checkbox and a visible label in a label with at least a 44px hit area, keep focus visible, and do not nest the series title link inside the same label. The title link and the checkbox must remain separate actions. Test 320px and 390px, keyboard Tab/Space, and a screen-reader name that includes the series title.
- **L2 result composition.** The current `.series-result` grid uses a title/value/action column plus a facts row (`static/css/discovery.css:18-45`). Adding a checkbox must not shrink the result type or hide period, source or fetched metadata. Recompose the grid or stack at the existing 820/600 breakpoints, and test 320px and 390px for overflow and readable values. The approved reading scale applies to selection controls and the tray, not only to the results.
- **L2 7-12 handoff.** `app/notebook_chart.py:829-830` returns a `choose` state with no chart when more than six sides are addressed. A reader who selects eight countries in the catalogue lands on eight cards and no chart. Keep the six-plot bound, but state the handoff: show "N cartões, escolha até 6 para o gráfico", never auto-drop cards, and keep the choose control near the chart. Add tests for seven and twelve selected references.
- **L3 shared matching boundary.** `app/reads.py:988-1002` builds one haystack with `search_aliases`; both `reads.search` (`1024`) and `reads.search_page` (`1042`) use it. Adding "energia" to that haystack would broaden the Caderno's bounded suggestions, which the plan says must not happen. Add a catalogue-only haystack or an explicit parameter, and test that `reads.search("energia")` keeps its current result set while `reads.search_page("energia")` gains eligible energy series.
- **L3 vocabulary source.** Use curated theme titles and reviewed aliases, not the theme blurb. The current blurb is "Produção e preços de eletricidade." (`presentation/catalog/pt.py:263`); appending it would make generic words such as "produção" and "preços" match every energy series. State which fields are searchable.
- **L3 empty state.** The L3 outcome promises "useful verified empty states", but implementation slice 3 only extends matching. Either keep the existing generic empty state and remove the promise, or define verified suggestions with counts from the same snapshot and never name a theme with zero eligible series. The latter needs a small read-model change that is not in the slice.
- **L2 tray placement.** A selection summary that sits only at the top of a 24-result page is not visible after selecting a result near the bottom. Use a native sticky summary at the top or bottom of the results, or place the summary immediately after the results with a visible count and open action. Do not use an overlay that covers result content on mobile.

## L4-L6 roadmap review

| Phase | Verdict | Concrete requirement |
|---|---|---|
| L4. CMS-authored data-first entry | PASS as direction | Use the existing CMS hero, card and chart blocks and `Action.href` for the comparison entry. Do not add a new homepage code path or a new block type until a populated prototype with real published content proves the need. "Compact" must mean spacing and composition, not smaller type: keep the H1 and 28.05px body. Require an actual published revision, an operator reorder/save/publish round trip, and preservation of drafts. |
| L5. Comparable-country discovery | PASS after L2 | Group by the exact comparable concept (indicator definition plus unit, multiplier and base year), not by family title alone. Show geography coverage and truthful counts, and keep each series' unit and definition visible. Add an explicit order (country, period, source) rather than an unexplained list order. Related published comparisons should be read from the published CMS index and shown as links, never as public editors. |
| L6. Focus and dated analysis | PASS only as separate specs | Split focus mode from dated analysis/AI. Build focus only after a measured trigger: plot box and scroll distance to the readout at 390/768/1440, plus a real task check. For dated analysis, add an explicit as-of date to the CMS revision or page metadata and render it; do not infer it from the newest data point. Keep AI commentary as a private draft with actor/reason audit and human approval, never automatic publication. No universal normalization. |

## Prioritized brainstorm for later phases

1. **Selection tray with resolved labels and per-reference removal (L2, now).** A persistent summary that lists up to twelve references, marks unavailable ones, and removes one without losing the others. Benefit: makes the twelve-card bound understandable and makes "remove a selection" real across pages.
2. **Caderno-to-catalogue bridge carrying `s` (L2, now).** Add the missing entry from the Caderno to `/pesquisa?s=...` and a return action. Benefit: completes the continuous journey and removes the repeated one-at-a-time loop that the evidence identified.
3. **One native state model, documented as a transition table (L2, now).** Use the same model for query, filters, pagination, selection and the Caderno action. Benefit: prevents dead checkboxes, lost selections and divergent tests.
4. **Homepage data band from existing CMS blocks (L4).** Compose a short hero, two or three card blocks and one authored comparison action with real published content. Benefit: puts unit, period and source above the fold without a new renderer or a type reduction.
5. **Exact-concept grouping with coverage counts (L5).** Group only what is genuinely comparable and show which geographies are present, missing or differently defined. Benefit: country comparison becomes faster without hiding definition differences.
6. **Published-comparison chips on series and search results (L5).** Read published CMS chart membership and show "Ver comparação publicada" where a real match exists. Benefit: connects discovery to authored analysis without turning search into an editor.
7. **Focus measurement and a dated-analysis field (L6).** Measure the L1 composition before adding a focus mode; add an explicit as-of date and human-approved AI draft state to the CMS when that phase starts. Benefit: avoids a speculative UI and keeps provenance legible.

## Rejected findings not reopened

- The four-significant-figure policy is correct. `98 290`, `174 800` and `3,31` are not inconsistent, and `3,310` is not a requirement. Original tokens, geometry, calculations and CSV remain exact.
- The 390px canvas is not cropped. It ends within the viewport; the legend continues below. No fixed 320-340px plot height is adopted without measurement.
- The plan does not replace the chart engine, add a public comparison editor, add an external search service or reduce the global reading scale. Those remain out of scope.

## Recommended gate

- Do not start L2 markup or implementation until B1-B4 are written into the plan, with the state transition table and the over-limit response.
- Resolve B5 before changing `_chart.html`; then implement L1 with the no-JS, print and plot-size guards.
- Name the catalogue-only matching boundary before implementing L3.
- Keep L4-L6 as future phases with separate specs. No live CMS edits, no production release and no full-suite claim belongs to this review.

## Addendum - adjudication of B1–B5 against the binding resolutions (26/11/2026)

Scoped second pass. Read only the roadmap's new "Binding review resolutions before implementation" section and this report; no repository, production or test re-audit. The section is treated as self-contained and as superseding the earlier slice shorthand.

**Verdict: PASS for B1–B5.** Every blocker now has one stated resolution, and the resolutions do not contradict each other or the retained acceptance criteria.

| Blocker | Resolution now stated | Verdict |
|---|---|---|
| B1. No single owner for native selection state | One `discovery-form` GET form owns query, filters, checkboxes, tray and pager; the search landmark is limited to the query/filter group; pager, tray removal and open are named submits; the transition table defines check + search/filter (page one, checks and off-page refs retained), check + page, uncheck (id absent, no hidden duplicate), tray removal (remove one, preserve the rest), open (`acao=abrir` to canonical Caderno with ordered unique refs and compatible settings), Caderno entry and clear/change actions; no link carries unsaved checks; the final handoff has no duplicate `s`. | Resolved |
| B2. No Caderno → catalogue entry | The "Enter from Caderno" row carries addressed `s` and the actual chart settings; `abrir` returns with compatible settings; deliberate removals prune only their group entries; L2 now owns `_notebook_search.html` and the `_notebook_chart.html` add-link. | Resolved |
| B3. Undefined over-limit/unavailable behavior | Lenient discovery recovery with a 48-raw-valid ceiling before dedup; malformed or over-ceiling input gets a generic invalid-address response before DB work with no identifier echo; 13–48 references are retained, visibly counted and blocked from `abrir`, never truncated; ordered dedup is explicit and separate from the unchanged strict Caderno parser. Tray wording is `referências selecionadas`; names/eligibility resolve from the same catalogue snapshot; unavailable refs get a generic label, visible state and remove control and up to twelve pass to the existing skipped-state contract; every selected ref has a native remove submit; the summary is in-flow/sticky and cannot cover mobile result actions; counting describes the last response. | Resolved |
| B4. Shared result template without a contract | Selection is an explicit opt-in context in the shared partial; theme pages keep their single-series entry and have no orphan checkboxes; `_cms_blocks.html` and static Admin previews are added to the L1 consumers. | Resolved |
| B5. L1 order/identity unspecified | Order is canvas → inspector (range, then selected-period rows) → compact color/pattern legend → disclosure with summary `Séries, eixos e fontes`; rows use prepared style swatches and prepared axis/unit membership; the inspector is hidden until enhancement, avoiding a no-JS gap; the disclosure is forced open in print including its details-content wrapper; installed mobile canvas dimensions and functional text are not reduced; the control stays outside every configuration form. | Resolved |

Residual precision gaps, not contradictions: the section states behavior but does not restate every test named in B1–B3 (open-Caderno expected count, theme-page no-checkbox, 13/duplicate/malformed/withdrawn cases), and B5 cites "installed" dimensions rather than the 354×264 baseline. The normative rules plus implementation slice 2's red tests and slice 4's baseline comparison still admit only one implementation; B2's local quick-add versus catalogue labelling is implicit. None blocks implementation.
