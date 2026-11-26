# Spec re-review: notebook one-form selection state

Reviewed head `daadbba1a488ebe0889e32f24ea87d50a689f757`, current `HEAD`, one commit after the
reviewed head of the original report (`8603231`). Read-only re-review, scoped to the single prior
finding about unsent notebook ticks and unchecks being lost on a subsequent search.

## Verdict

CLOSED. The prior finding no longer reproduces from the template, the route or the targeted
native-form tests. No concrete residual remains within that finding.

## What closes it

The Caderno quick search now has one form, `#notebook-search-form`
(`app/templates/_notebook_search.html:6-61`). The query input, the result checkboxes, the hidden
off-page references, the `ordem` metadata and the chart fields all belong to that one form.

- Ticking an unsubmitted result now submits it with the search. The result row emits a real
  checkbox named `s` (`app/templates/_notebook_search.html:39`), and the search button submits
  the form with `acao=pesquisar_caderno` (`:16`). The old independent search form, which could
  not see the batch checkboxes, is gone.
- Unchecking a visible addressed member now removes it on the next search. `batch_hidden`
  excludes every id that has a visible result (`app/notebook.py:222-226`), so only off-page
  addressed references travel as hidden `s` inputs (`app/templates/_notebook_search.html:9`).
  A visible member therefore emits only its checkbox, checked or unchecked.
- The route cannot resurrect an unchecked member. `/pesquisa` builds the selection from the
  submitted `s` values only (`app/main.py:232-240`); `preserve_order` keeps retained addressed
  order and appends new ticks, but only for ids that are actually present in the submission
  (`app/discovery_selection.py:58-66`). An absent id never returns.
- The batch action remains `acao=abrir` (`app/templates/_notebook_search.html:26`) and is now a
  submit button of the same form. Its redirect drops the query, as before, while carrying the
  checked selection, `ordem` and chart fields.

## Route claims verified

- A valid search action with at most twelve references redirects with 303 to the notebook
  address built by `selection_path`, with the trimmed query, the chart settings and the
  `#pesquisa` fragment (`app/main.py:263-278`).
- `notebook.parse_query` rejects a query over 200 characters or containing control characters
  before `_read` is called (`app/main.py:269-272`).
- A search action over twelve references does not truncate and does not redirect: it falls
  through to the catalogue search page, which renders the full selection and the over-limit
  notice with status 200 (`app/main.py:273-283`).
- The `frequencia_grafico` alias is carried by `batch_chart_fields` and mapped back by
  `read_chart_settings`; a visible group side that is unchecked is pruned rather than restored.

## Verification performed

- One diff inspection of `git show daadbba` for `app/main.py`, `app/templates/_notebook_search.html`,
  `app/templates/notebook.html` and the notebook tests. No other commit or repository-wide
  discovery was performed.
- One targeted test command with
  `/home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest -q` covering the unified
  form, a tick surviving search, an uncheck surviving search, zero results, chart settings,
  the over-limit recovery, the malformed-query 404 before the database, and the public prefix.
  Result: 8 passed, 1 warning in 8.45s.
- The implementer's full 27-test and 80-test runs were not repeated.

## Residuals

None for this finding. The previously noted non-blocking items, the JavaScript count wording on
the notebook page and the unused `NotebookResult.action_path`, are unchanged and outside this
scoped finding. No runtime files were edited and nothing was committed.
