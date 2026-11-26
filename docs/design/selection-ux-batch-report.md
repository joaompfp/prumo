# Batch selection repair

Branch `fix/selection-ux`, based on `65c1832`.

## Catalogue

- Selectable catalogue rows no longer carry a competing one-series `Criar caderno` link.
  The title still opens the series, and the checked row is the only selection affordance.
- A results bar above the list states the multi-select rule, shows the current count, and
  carries the nearby `Abrir caderno` action.
- Checked rows are marked on the server for a no-JavaScript response. The same rows update
  `is-selected` and the count while the reader checks or unchecks with the local helper.
- Theme pages are not selectable and keep their individual `Criar caderno` shortcut. CMS
  home cards keep theirs.

## Caderno quick search

- The result table now has one checkbox column and one `Acrescentar selecionadas` action.
- The batch form is a native GET to the existing `/pesquisa` boundary with `acao=abrir`,
  hidden addressed references that have no visible result, the bounded addressed `ordem`,
  and the actual chart settings through `discovery_selection.chart_form_params`.
- A visible member emits only its checkbox. It is checked when it already belongs to the
  notebook and unchecked when it does not, so unchecking removes it instead of leaving a
  hidden duplicate. Addressed references without a visible result remain hidden and are
  retained.
- The action still submits when JavaScript is unavailable. The server keeps the twelve-card
  handoff and six-series chart bounds. Thirteen or more references return the catalogue with
  an explicit over-limit notice, the full selection and the remove controls, never a silent
  truncation. Chart group sides that no longer belong to the selection are pruned by the
  existing catalogue boundary.

## Progressive asset and policy

- `static/js/selection.js` is local, dependency-free, and only updates the count text and row
  class. It uses no network, storage, cookies, inline handlers or `innerHTML`.
- Successful catalogue pages with results and notebook pages with quick-search results load
  that one asset. Their CSP adds `script-src 'self'; script-src-attr 'none'`.
- Empty searches, no-result notebook pages, 404/503 pages, CSV exports, theme pages and Admin
  static previews keep the base no-script policy. Chart payloads and chart rendering are
  unchanged.

## Verification

- `node --check static/js/selection.js`
- `.venv-ci/bin/ruff check app/ presentation/ tests/`
- `.venv-ci/bin/python -m pytest tests/app/test_discovery_selection.py tests/app/test_notebook.py tests/app/test_routes.py -q`
- `.venv-ci/bin/python -m pytest tests/app/test_discovery_search.py tests/app/test_series_list_views.py tests/app/test_notebook_workspace.py tests/app/test_notebook_analysis.py tests/app/test_notebook_chart.py -q`
- `.venv-ci/bin/python -m pytest tests/app/test_public_ui.py tests/app/test_routes.py tests/app/test_legibility_review.py tests/app/test_navigation.py tests/app/test_card_create.py -q`
- `.venv-ci/bin/python -m pytest tests/backoffice/test_admin_ui.py tests/backoffice/test_boundaries.py -q`
- Local Playwright check: checking and unchecking rows updates the count and row styling,
  `Abrir caderno` opens the checked reference, `Acrescentar selecionadas` appends it, and
  unchecking an existing member removes it. At 320px the body stays 28.05px, document width
  stays 320px, the batch button fills the bar and the notebook table keeps its local scroll.

No push, merge or deployment was performed. The parent owns handoff, roadmap, release and
the final browser acceptance.
