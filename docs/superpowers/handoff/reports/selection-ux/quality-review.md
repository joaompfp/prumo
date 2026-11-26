# Quality review: batch selection and one-form notebook search

Reviewed head `daadbba1a488ebe0889e32f24ea87d50a689f757` against base `65c1832`. Read-only
review of the changed runtime, templates, CSS, JavaScript, presentation and tests. No runtime
files were edited and nothing was committed.

## Verdict

One mandatory issue. The unified quick-search form is correct in isolation, but the notebook
page still has a second form that owns the addressed selection. Pending ticks and unchecks are
therefore not safe page-wide.

## Mandatory issue: the chart settings form still drops pending quick-search state

The chart settings form at `app/templates/_notebook_chart.html:46-56` submits its own hidden
`s` list built only from `page.addressed` (`:47`). The quick-search checkboxes live in the
separate `#notebook-search-form` (`app/templates/_notebook_search.html:6-61`, checkbox at
`:39`). `static/js/selection.js:27-49` only updates the count text and the row class; it does
not mirror checkbox state into the chart form.

Two concrete sequences lose state:

1. On `/caderno?s=ine.hicp_yoy.PT&q=desemprego`, tick the UNEMP result in the quick search, then
   open the chart settings, change a setting and submit. The chart form sends only
   `s=ine.hicp_yoy.PT`; the ticked UNEMP is gone.
2. On `/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT&q=desemprego`, uncheck UNEMP in
   the quick search, then apply a chart setting. The chart form still sends both `s` values,
   so the unchecked member returns.

A read-only probe against the fixture database with
`/home/joao/projects/prumo-pipeline/.venv-ci/bin/python` produced:

```text
quick-search UNEMP checkbox: unchecked
chart-form hidden s: ['ine.hicp_yoy.PT']
```

The chart form contains no UNEMP control at all, so a browser-side tick on that checkbox cannot
be serialized by the chart form. Submitting it returns the committed selection only.

This is the same state-loss class as the finding that motivated the repair, not a new feature
request. It is reachable by a normal action on the same page, and the notebook page gives no
warning that applying chart settings will discard pending ticks. The one-form ownership claim is
true only inside the search form, not page-wide. A JavaScript-only mirror would not fix the
no-JavaScript path, for the same reason the earlier repair could not use one.

Closing direction: one form owner for the chart controls and the result checkboxes, with
distinct submit actions or `formaction` targets, so every native submission carries the current
checkbox state. If the chart form is deliberately a separate transaction, that decision needs
explicit copy that pending ticks are discarded, and the no-JavaScript state-loss remains.

## Passing contracts

- The quick-search form has one owner for `q`, the result checkboxes, hidden off-page `s`
  fields, `ordem` and the aliased chart fields (`_notebook_search.html:6-61`). The search button
  submits `acao=pesquisar_caderno` (`:16`); the batch button submits `acao=abrir` (`:26`).
- `batch_hidden` excludes every id with a visible result (`app/notebook.py:222-226`), so a
  visible addressed member emits only its checkbox. Unchecking it removes it; off-page and
  unavailable addressed references remain hidden and retained.
- Order is preserved from submitted ids only. `preserve_order` retains prior addressed order
  and appends new checks, and an id absent from `s` never returns
  (`app/discovery_selection.py:58-67`). Hidden off-page fields precede visible checkboxes in a
  native submission, which the tests model.
- `/pesquisa` handles `acao=pesquisar_caderno` and `acao=abrir` with a 303 to the canonical
  notebook (`app/main.py:263-278`). The search handoff keeps `q` and adds `#pesquisa`; the batch
  handoff drops `q`. A selection of at most twelve redirects. Thirteen or more falls through to
  the catalogue recovery page with the full selection and the over-limit notice.
- `pesquisar_caderno` validates `q` with `notebook.parse_query` before any read, rejecting over
  200 characters and control characters with the generic 404 (`app/main.py:269-272`). The
  malformed-query test proves the 404 happens before the database is opened.
- Chart settings survive the handoff and use the `frequencia_grafico` alias
  (`app/notebook.py:255`, `app/templates/_notebook_search.html:11`). An unchecked chart group
  side is pruned rather than restored. The last explicit side becomes the honest off state.
- The selection asset is local and only runs on successful catalogue pages with rows and
  notebook pages with quick-search results (`app/templates/search.html:110`,
  `app/templates/notebook.html:50`, `app/notebook_routes.py:55-58`). Empty pages, no-result
  notebook pages, 404 and 503 responses keep the base no-script policy. The asset uses no
  network, storage, cookies, `eval` or `innerHTML` (`static/js/selection.js`).
- The catalogue removes the competing one-series `Criar caderno` action from selectable rows,
  marks checked rows on the server, and keeps the theme-page shortcut (`_series_results.html`,
  `tests/app/test_discovery_search.py:286`, `tests/app/test_discovery_selection.py:586`).
- The new tests cover the unified form, tick survival, uncheck removal, absent off-page
  retention, order append, chart pruning, over-limit recovery, malformed-query rejection before
  the database, the mount prefix and the CSP split (`tests/app/test_notebook.py:351-583`).

No order, security or primary-flow boundary defect was found in the repaired search form.

## Non-blocking residuals

- **Raw reference ceiling.** The notebook quick search renders every result from
  `reads.search`, which is capped at 100 rows (`app/reads.py:1071-1085`), but
  `parse_references` accepts at most 48 raw `s` values (`app/discovery_selection.py:20,37-49`).
  A reader who ticks 37 or more new results from an existing twelve-reference notebook submits
  49 raw values and gets the generic 404 instead of the over-limit recovery page. The catalogue
  form has a related pre-existing 48 plus one edge. The ordinary 13-reference recovery path is
  correct. Capping the rendered checkboxes or widening the parser bound within the URL budget
  would remove the edge.
- **Dead path computation.** `NotebookResult.action_path` (`app/notebook.py:100`) and the path
  computation at `app/notebook.py:212-220` have no template consumer after the repair. They are
  wasted work on every result row, up to 100 rows per request. Removing them would simplify the
  composition.
- **Count wording.** `selection.js:23-25` hardcodes `1 selecionada` and `N selecionadas`. The
  notebook server renders `1 referência selecionada` and `N referências selecionadas`
  (`presentation/notebook.py:500-505`), so the notebook count changes wording after the first
  JavaScript sync. This is the residual already noted in the spec reviews; the count is correct.
- **Two catalogue counts.** The results bar count is live (`search.html:82`), while the review
  summary still shows the last submitted count (`:57`). The note at `:58` says the count
  describes the last submission, which is no longer true of the live bar. The values can differ
  while a reader ticks rows. This is a copy and presentation inconsistency, not a data loss.
- **No-JavaScript count notice.** The catalogue has a `noscript` note explaining that the count
  changes on submit (`search.html:85`); the notebook batch bar has no equivalent. The form still
  submits correctly without JavaScript, but the count remains the last submitted value while
  the reader ticks boxes.

## Verification performed

- One diff inspection of `git diff 65c1832..HEAD` for `app/main.py`, `app/notebook.py`,
  `app/notebook_routes.py`, the notebook and catalogue templates, both stylesheets,
  `static/js/selection.js`, `presentation/notebook.py` and the changed tests.
- One targeted read-only probe with the project test interpreter and the fixture database to
  establish the chart-form hidden selection and the quick-search checkbox ownership.
- The parent's 237 focused tests, ruff and node checks were not repeated. No browser setup and
  no full suite were run.
- No runtime edits and no commit. This report is the only file created.
