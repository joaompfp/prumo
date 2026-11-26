# Spec review: batch selection repair

Base `65c1832`, reviewed head `8603231`, branch `fix/selection-ux`. Read-only review.

## Verdict

GAP. One concrete finding. The batch action itself passes its stated contracts. The requested focus item, loss of unsent checkbox state when searching again in the Caderno quick search, reproduces. Everything else in the requested repair passes.

## Gap: unsent quick-search checks and unchecks do not survive the search form

The Caderno quick search has two independent forms:

- `#notebook-search-form` (`app/templates/_notebook_search.html:6-13`) carries hidden `s` fields for every already addressed reference, the query and the chart settings.
- `#notebook-batch-form` (`app/templates/_notebook_search.html:19-30`) carries the result checkboxes, the `ordem` metadata, the non-visible addressed references and the batch action.

A checked box that has not yet been submitted belongs only to the batch form. It is not a control of the search form, and `static/js/selection.js` only syncs the form that contains the count (`static/js/selection.js:27-57`). It does not mirror checkbox state into the search form.

Reproduced with the real app against the fixture database, by mutating the batch checkbox state and then serializing the independent search form as a native GET (no browser needed):

1. `GET /caderno?s=ine.hicp_yoy.PT&q=desemprego` returns the UNEMP result as an unchecked checkbox in the batch form.
2. The search form serializes as `s=ine.hicp_yoy.PT&q=desemprego`. UNEMP is absent.
3. Submitting that URL renders UNEMP unchecked again and returns the server count to 1 reference. The checked-but-unsent UNEMP choice is gone.

Probe output:

```text
search-form GET carries [('s', 'ine.hicp_yoy.PT'), ('q', 'desemprego')]
UNEMP in search-form pairs False
after search: UNEMP checkbox [('ine.unemployment_monthly.PT', False)]
```

The reverse also reproduces. On `GET /caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT&q=desemprego`, the search form still contains a hidden `s=ine.unemployment_monthly.PT`. The probe unchecks that visible member in the batch form; the search form still serializes both values and restores the member:

```text
search form hidden s before uncheck ['ine.hicp_yoy.PT', 'ine.unemployment_monthly.PT']
after search: UNEMP checkbox [('ine.unemployment_monthly.PT', True)]
```

This is the page-level reading of "no hidden duplicate visible checked member" that the implementation misses. The batch form avoids the duplicate because `app/notebook.py:224-226` excludes visible result ids from `batch_hidden`. The existing search form still emits a hidden duplicate for every visible checked member at `app/templates/_notebook_search.html:7`. Unchecking therefore removes the member only when the batch action is the next submission.

The focused tests encode the existing search-form behavior rather than catch the focus item: `tests/app/test_notebook.py:343-353` asserts that the search form still carries both `HICP` and `UNEMP` while only checking that the batch form has one `s` for `UNEMP`.

Impact: a reader who ticks one or more new results, then refines the query before pressing `Acrescentar selecionadas`, loses those ticks silently. A reader who unchecks an existing member and then searches gets the member back. The live count can show the unsent choice and then revert on the search response, which is confusing but not a server-side truncation.

Fix direction: one form owner for the query and the checkboxes is the only option that also holds with JavaScript unavailable; a JavaScript-only mirror would fix the enhanced path but not the no-JS path.

## Passing contracts

- `/pesquisa` has one form owner. Selectable rows carry native checkboxes, no competing one-series `Criar caderno` link, and a server-marked `is-selected` row. Theme rows keep their one-series link and have no checkboxes. CMS cards are unchanged.
- The catalogue results bar is visible with the multiple-selection instruction, a server count and the local enhancement. The count updates from the form's `s` fields.
- The Caderno batch form submits to `/pesquisa` with `acao=abrir`. It preserves addressed references that have no visible result as hidden `s`, carries `ordem` for the addressed order and carries the actual chart fields, including the `frequencia` to `frequencia_grafico` alias.
- Within the batch form, a visible checked member emits only its checkbox. Unchecking it and pressing the batch action removes only that reference; the probe produced `/caderno?s=ine.hicp_yoy.PT` from a two-reference selection. New checks append after the addressed order.
- An unavailable addressed reference remains in the batch form as a hidden `s` with its `ordem` entry and survives the handoff.
- Twelve references remain the handoff limit. A thirteenth returns a 200 catalogue recovery page with `13 referências selecionadas`, the explicit over-limit notice and the full selection. There is no redirect and no silent truncation. The six-series chart limit is unchanged.
- Successful catalogue pages with rows and notebook quick-search result pages load the local `/static/js/selection.js` and receive `script-src 'self'; script-src-attr 'none'`. A notebook page with a chart payload also loads its pre-existing local chart bundle. Empty searches, malformed references, 404 pages, CSV exports and unpublished notebook pages keep the base no-script policy. The chart JSON block on a notebook page with a chart is pre-existing and non-executable.
- No Admin or backoffice template gained the selection asset; the diff contains no backoffice changes.
- `selection.js` uses no cookies, network, storage, `eval` or `innerHTML`. The asset is local and dependency free.
- No ingestion, schema, font, data or CMS publication boundary files changed.

## Minor, non-blocking

- On the Caderno page the server renders `N referências selecionadas`, but `selection.js` immediately rewrites it to `N selecionadas` because `countText` uses the catalogue wording. The count is correct; the visible copy is inconsistent.
- `NotebookResult.action_path` is still computed in `app/notebook.py:212-220` but the new quick-search template no longer uses it. This is residual dead path code, not a reader-visible regression.
- The design report's statement that "a visible member emits only its checkbox" is true inside the batch form but not page-wide, because of the search form duplicate described above.

## Verification performed

- `git diff 65c1832..8603231` for runtime, templates, CSS, JavaScript, presentation and tests.
- Targeted pytest: 4 tests passed (`test_quick_search_offers_one_batch_action_without_per_result_links`, `test_quick_search_batch_never_duplicates_a_visible_member_and_keeps_it_checked`, `test_catalogue_batch_selection_is_primary_and_theme_keeps_its_shortcut`, `test_selection_pages_use_only_the_local_asset_and_the_narrow_script_policy`).
- Targeted probes with `/home/joao/projects/prumo-pipeline/.venv-ci/bin/python` using the real `create_app` and `tests.app.conftest.build` fixture database, including mutating the batch checkbox state before serializing the independent search form.
- The claimed 204-test run was not repeated; no full suite, browser run or framework setup was performed.
- No runtime files were edited and nothing was committed.
