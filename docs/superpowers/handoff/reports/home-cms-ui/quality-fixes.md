# Quality fixes - single h1, unsaved draft guard, form transport

Scope: exact HEAD `edef45e`, closing findings 1 to 3 of `quality-review.md`. No production,
main or push. Files changed are limited to the owned paths listed at the end. The full suite
was not rerun here on purpose; the controller owns the final run. The focused suites below
passed after the last edit.

## 1. Exactly one h1 in published content

- `app/templates/cms_page.html` now renders its page header `h1` only when `page.has_hero`
  is false. The breadcrumb, the section metadata and the introduction still render for a
  page whose hero carries the heading. `cms_home.html` already had the same guard.
- `ingest/cms.py` adds `shape_problem(document)`: a page with more than one `HeroBlock`
  returns a reader-facing reason. It is not a pydantic model validator on purpose. A body
  stored before the rule stays parseable, visible, restorable and canonical; `canonical_for`
  applies the rule to new saves and `Cms._page_problem` applies it inside the publish
  transaction, so a publication is refused with no write.
- Zero-hero pages keep the previous behaviour: the shell heading is `page.title`.

Probe against the real parser and canonicalizer:

```
canonical_for("page", two_heroes) -> CmsDocumentError: a página tem mais de um cabeçalho de abertura; use apenas um
require_canonical_body("page", canonical_legacy_two_hero_body) -> accepted (backward compatible read)
shape_problem(parsed_two_hero_page) -> a página tem mais de um cabeçalho de abertura; use apenas um
```

Regression coverage:

- `tests/app/test_cms_reads.py::test_page_with_a_hero_renders_exactly_one_h1_and_keeps_section_metadata`
- `tests/app/test_cms_reads.py::test_page_without_a_hero_keeps_the_page_title_as_its_single_h1`
- `tests/app/test_cms_home.py::test_published_home_with_one_hero_renders_exactly_one_h1`
- `tests/backoffice/test_cms_routes.py::test_second_hero_is_refused_on_save_and_on_publish_without_writes`
  checks that a two-hero save returns 422 without a revision or audit event, and that a
  legacy stored two-hero draft cannot be published, with meta, revisions and events unchanged.

## 2. Publish cannot discard unsaved edits

- `backoffice/templates/cms_editor.html` marks publish, unpublish, restore and duplicate with
  `data-requires-clean`. The publish copy now says it publishes the stored draft, that unsaved
  edits are not included, and that the preview shows the stored draft. A `<noscript>` block
  says the same without JavaScript and links to the stored-draft preview.
- `static/js/admin.js`: the dirty watcher now catches a click on a submit button in those four
  forms before browser validation, and also catches the submit event. When the draft form is
  dirty it prevents the submission, stops the confirmation listener from running, shows an
  inline dirty note asking for a save, and focuses the top save control (`.draft-save`). It
  does not set the global `submitting` flag on a cancelled action.
- The option filter created by the same script (`.select-filter`) is ignored by the dirty
  watcher because it only hides options and never changes a submitted value. The select's own
  change still marks the draft dirty.
- A normal draft save is unchanged.

Regression coverage: `tests/backoffice/test_editor_usability.py::test_saved_state_actions_carry_the_dirty_watch_contract`
checks all four forms, the stored-draft confirmation, the no-JavaScript copy and the guard
contract in `admin.js`. `node --check static/js/admin.js` passes. Browser-level interaction is
left to the controller's browser proof.

## 3. Bounded form transport capacity

Computed with `urllib.parse.urlencode`, using the astral character U+1D11E so every character
expands to 12 percent-encoded bytes:

- schema-valid maximum, 20 verification blocks with 6 steps of `MAX_TEXT`: 506,811 characters,
  6,084,908 encoded bytes, 5.803 MiB;
- every rendered field group at its maximum (values retained while switching a block type):
  8,832,838 encoded bytes, 8.424 MiB;
- `CMS_FORM_MAX_BYTES` is now 12,582,912 bytes (12 MiB), which covers both with headroom and
  stays a finite authenticated request bound. The numeric content-length and stream guards
  are unchanged; no unbounded read was introduced.

Regression coverage:

- `test_large_schema_valid_verification_block_survives_form_transport` submits a real form
  with one verification block whose six steps are 4,000 four-byte characters. The encoded
  body is 288,374 bytes, over the old 131,072 cap, and the save returns 303 with six stored
  steps of 4,000 characters.
- `test_form_over_the_transport_cap_is_413_and_writes_nothing` posts a body of
  `CMS_FORM_MAX_BYTES + 1` bytes and asserts 413 with unchanged metadata, revisions and events.
- The existing oversized-body test in `test_forms_refuse_cross_origin_duplicate_fields_and_oversized_bodies`
  now uses the new cap instead of the old 140,000-byte fixture.

## Verification

```
.venv-ci/bin/python -m pytest -q \
  tests/ingest/test_cms.py tests/ingest/test_cms_storage.py \
  tests/ingest/test_cms_pragma_bypass.py tests/ingest/test_cms_replace_bypass.py \
  tests/backoffice/test_cms_routes.py tests/backoffice/test_cms_home.py \
  tests/backoffice/test_editor_usability.py tests/backoffice/test_admin_ui.py \
  tests/app/test_cms_reads.py tests/app/test_cms_home.py
238 passed, 1 warning
```

After the final transport cap edit the four route regressions above were rerun: 4 passed.
`ruff check` passes on every changed Python file and no changed file contains U+2014.

## Residual risks

- A revision already published with two heroes before this fix is not rewritten. It would
  still serve two `h1` elements until an author saves and publishes a corrected draft. Saving
  a second hero is now refused, so the bad revision cannot be republished unchanged. This
  task wrote no production data.
- The browser interaction of the dirty guard is verified by template and JavaScript contract
  tests plus `node --check`, not by a real browser session here. The controller's browser
  proof is still the end-to-end check.
- The transport cap is a request bound, not a new per-field limit. All schema maxima and the
  editor field-count bound are unchanged.

## Files changed

- `ingest/cms.py`
- `backoffice/cms.py`
- `backoffice/cms_routes.py`
- `backoffice/templates/cms_editor.html`
- `app/templates/cms_page.html`
- `static/js/admin.js`
- `tests/app/test_cms_reads.py`
- `tests/app/test_cms_home.py`
- `tests/backoffice/test_cms_routes.py`
- `tests/backoffice/test_editor_usability.py`
- `docs/superpowers/handoff/reports/home-cms-ui/quality-fixes.md`
