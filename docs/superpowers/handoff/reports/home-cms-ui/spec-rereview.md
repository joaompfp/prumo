# Specification re-review: homepage CMS states and editor input

Decision: **SPEC_PASS**

Scope: only the original blocking findings B1, B2 and B3 in `spec-review.md`, re-checked
against commit `792c96c` and the functions, templates and tests it changed. No broad
re-review, migration, source write, commit, browser run, network run or whole-suite run.

## Verification observed

One focused pytest invocation, seven tests:

```
.venv-ci/bin/python -m pytest -q \
  tests/backoffice/test_cms_routes.py::test_form_error_keeps_every_submitted_page_value \
  tests/backoffice/test_cms_routes.py::test_form_error_keeps_values_when_the_block_count_is_not_a_number \
  tests/backoffice/test_cms_routes.py::test_form_error_keeps_values_when_the_note_is_missing \
  tests/backoffice/test_cms_routes.py::test_form_error_keeps_the_submitted_chart_title_and_note \
  tests/backoffice/test_cms_routes.py::test_stale_version_is_409_and_writes_nothing \
  tests/backoffice/test_cms_home.py::test_dashboard_reports_the_home_head_after_preparation \
  tests/backoffice/test_admin_ui.py::test_reorder_controls_keep_visible_text_when_the_icon_font_fails
```

Result: **7 passed, 1 warning in 5.44s**.

I also read `Cms.home`, `Db.cms_published_once`, `_submitted_document`, `editor_page`,
`mutate`, `_diff`, `cms_list.html`, `cms_editor.html`, `editorial_page.html` and the added
regressions. No runtime or source edit was made beyond this report.

## B1. The dashboard reports the true home state: PASS

`Cms.home()` now returns `published_once`, read through the existing
`Db.cms_published_once`. That query looks for an append-only `cms_event` row with
`action = 'published'`, so it stays true after later saves, restores and unpublication.

`cms_list.html` now renders three distinct home states:

- prepared, never published: badge `Rascunho privado` and "Ainda não publicada: o site
  mantém a página inicial antiga até à primeira publicação."
- published: badge `Publicada` and "O CMS gere o que aparece em `/`."
- published then unpublished: badge `Despublicada` and "A página inicial está por
  publicar: `/` mostra o estado neutro até nova publicação."

The regression captures the `/cms` render context for all three states and asserts the
sentences above. It also asserts that `O CMS gere` is absent before the first publication
and after unpublication, and that `Rascunho privado` is absent after unpublication. Public
`/` lifecycle code was not changed by this commit, so the prepared state still serves the
legacy homepage. The dashboard claim now matches the public behavior.

## B2. Submitted editor values survive refusals: PASS

`_submitted_document` is display only. It is called only when no authoritative document
exists, uses the raw form values, performs no validation and writes nothing.
`_document_from_fields` remains the only parser and the next submit is validated again.

The reconstruction covers the values the editor reads: page title, introduction and
section; block type and text; card, chart and heading fields; hero eyebrow, title, note,
flags and action slots; theme and step slots; an unknown type, which is also offered as an
explicit invalid option in the type select; and a pending `add` block, mapped into the
block list. The save form's audit note is re-rendered from the submission as well.

The stale-version path is also correct. On `CmsConflict`, `editor_page` receives the
submitted expected version and every mutation form renders that stale value, not the fresh
metadata version. The submitted document is the validated one, so its values are shown.
The regression asserts status 409, the submitted text, `version=1` still present,
`version=2` absent, and unchanged metadata and revision history.

The four `FormError` regressions assert status 422, the typed title, introduction, hero
action label, block text and chart title/note where applicable, and unchanged metadata and
revision history. A missing audit note and a non-numeric `block_count` do not reset the
page values. The blank hero `href` case from the original finding is covered directly.

Residual, not blocking for this finding:

- A form that `_read_form` cannot parse at all, for example non UTF-8 or a repeated field,
  still has no values to re-render because parsing never completed. Those are transport
  failures, not the editor-value `FormError` cases in B2.
- A malformed save submitted with a stale version returns 422 before the version conflict
  is detected, and the hidden version is refreshed to the current one. This is the
  pre-existing behavior on validation errors, not the 409 conflict path that the
  stale-version regression covers. It is a concurrency-hardening question outside the
  original input-loss finding.

## B3. Reorder controls keep visible text: PASS

`editorial_page.html` now renders `Subir` and `Descer` as visible text after the
aria-hidden arrow, instead of inside an `.sr-only` span. The submit forms and their hidden
fields are unchanged. The regression rejects both old `.sr-only` spans and requires the
visible text after `aria-hidden="true"></i>`. With the local icon font blocked, the action
still has readable Portuguese text.

At review time `git status` showed no changes to `cms_editor.html` from the parallel visual
density pass. That pass is limited to the editor header and details sections. The raw
restoration path depends on `doc`, `values` and the form field names, so header and details
markup does not affect it. If the density pass later changes any form field name or removes
the `values` bindings, these regressions must be rerun.

## Minor and out of scope

The icon-font subset finding remains as documented: 37 glyphs defined, 10 unused. It is a
minor deviation and was not part of B1, B2 or B3. The parity and quality notes from the
first review were not re-assessed here and remain outside this pass, as do browser and
production-copy acceptance.

SPEC_PASS applies only to B1, B2 and B3 at `792c96c`.
