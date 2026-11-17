# Specification fixes: homepage CMS states and editor input preservation

Scope: the blocking findings B1, B2 and B3 of
`docs/superpowers/handoff/reports/home-cms-ui/spec-review.md`, plus the one-line `admin.js`
suspicion. No migration, public render change, deployment or new feature was added.

## B1. The dashboard no longer claims `/` before the first publication

`Cms.home()` now returns `published_once`, read through the existing
`Db.cms_published_once` audit query. The dashboard home panel has three distinct states:

- `published`: badge `Publicada` and `O CMS gere o que aparece em /`.
- never published: badge `Rascunho privado`, `Ainda não publicada: o site mantém a página
  inicial antiga até à primeira publicação.`
- published once and now unpublished: badge `Despublicada`, `A página inicial está por
  publicar: / mostra o estado neutro até nova publicação.`

The prepared-only state no longer says the CMS controls `/`, and the post-unpublish state is
no longer labelled as a private draft. Regression:
`tests/backoffice/test_cms_home.py::test_dashboard_reports_the_home_head_after_preparation`
covers prepared, published and unpublished, including the absence of the wrong sentences.

## B2. Submitted values survive `FormError` and stale-version conflicts

`backoffice/cms_routes.py` gains `_submitted_document`, a display-only reconstruction of the
editor's document shape from the raw form fields. It is used only when a save is refused before
a valid document exists. It is never validated and never written; `_document_from_fields`
remains the only authoritative parser and the next submit is validated from scratch.

The reconstruction preserves:

- page title, introduction and section exactly as typed;
- block type, text, card references, chart reference, heading, verification and sources fields;
- hero actions at their submitted slots, including a label with a blank `href`;
- theme and step slots at their submitted positions;
- an unknown block type, which is also shown as an explicit invalid option in the type select;
- a pending `add` block, mapped into the block list as the block it was trying to append.

`editor_page` accepts `values` and renders the reconstruction when no authoritative document
exists. The save form's `note` value is also re-rendered from the submission. Chart saves
preserve the submitted title and note text. On `CmsConflict`, the re-render keeps the submitted
document and the stale expected version in every mutation form, so the operator must reload
deliberately instead of resubmitting against a silently refreshed version.

Regressions in `tests/backoffice/test_cms_routes.py`:

- `test_form_error_keeps_every_submitted_page_value`: hero title plus introduction plus an
  action whose `href` is blank.
- `test_form_error_keeps_values_when_the_block_count_is_not_a_number`: malformed
  `block_count` still preserves the title and block text.
- `test_form_error_keeps_values_when_the_note_is_missing`: a missing audit note does not reset
  the page fields.
- `test_form_error_keeps_the_submitted_chart_title_and_note`: chart title and note survive.
- `test_stale_version_is_409_and_writes_nothing` now also asserts that the submitted text and
  the stale hidden `version=1` are re-rendered.

Every regression asserts the stored metadata and revision history are unchanged.

## B3. Reorder controls have visible text

`backoffice/templates/editorial_page.html` now renders `Subir` and `Descer` as visible text next
to the aria-hidden arrows instead of inside an `.sr-only` span. With the icon font blocked, the
action remains readable. Regression:
`tests/backoffice/test_admin_ui.py::test_reorder_controls_keep_visible_text_when_the_icon_font_fails`.

## `static/js/admin.js`

The suspicion was checked at byte level: `data-show-for` already used a single-backslash
whitespace regex (`split(/\s+/)`), so no source change was needed. A regression
(`test_admin_script_splits_the_show_for_attribute_on_whitespace`) now asserts the correct
single-backslash form and rejects the double-escaped one.

## Icon font subset

The minor finding was left as the documented local 3.6 kB subset, as allowed by the task. No
glyph was removed because B3 touched text, not the font asset.

## Verification

```
.venv-ci/bin/python -m pytest -q tests/backoffice/test_cms_routes.py \
  tests/backoffice/test_cms_home.py tests/backoffice/test_admin_ui.py
69 passed, 1 warning in 59.91s
```

```
.venv-ci/bin/python -m ruff check backoffice/cms.py backoffice/cms_routes.py \
  tests/backoffice/test_cms_routes.py tests/backoffice/test_cms_home.py \
  tests/backoffice/test_admin_ui.py
All checks passed
```
