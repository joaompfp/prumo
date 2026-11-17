# CMS editor refinement - compact header and collapsible blocks

## Trigger

The 1440 px homepage editor capture showed stacked metadata before the work:
a repeated homepage identity, version shown twice, an oversized slug beside the
H1, a permanent preview note, a duplicate "Rascunho" heading, and 17 fully
expanded block fieldsets. The save action and its required reason field sat at
the very bottom of that page.

## Changes

- Header is one compact block: page title only in the H1, slug demoted to a
  monospace item in a single status line with version and publish state.
  Removed the kicker, badge row and the duplicate back/preview explanation.
  Breadcrumbs and the preview action remain.
- The four jump links are still plain anchors in the existing section nav.
  They are not tabs and need no JavaScript.
- The draft form now opens with a sticky save toolbar. It contains the single
  required `draft-note` field (moved from the bottom) and the `op=save` button.
  The toolbar has an opaque surface background, stacks on small screens and
  keeps the save button at least 44 px high. The publish form remains a
  separate form with its own reason field and action.
- Every content block is now a native `<details>`/`<summary>` disclosure. The
  first block starts open, the rest start closed. Summaries use Portuguese
  content labels ("Cabeçalho de abertura", "Texto", "Gráfico", and so on) plus
  a short title/text snippet instead of the raw type code.
- Page identity is a disclosure too. It starts open on ordinary pages and
  closed for the reserved home page, where it is metadata rather than the
  public hero heading. It opens automatically on a server error so a required
  title is never hidden behind a collapsed summary after a refused save.
- The add-block form is also a disclosure, open by default so the existing
  "Adicionar bloco" jump link lands on its fields.
- Closed disclosures keep every input in the document and none are disabled.
  Field names, ids, values, hidden `version` and `block_count`, block actions
  and the save/add action values are unchanged. There is exactly one draft
  reason field and no duplicate field names.
- CSS stays scoped to `.editor-form` and the editor header. Editor controls
  and summaries are at least 44 px high where practical, checkboxes keep their
  natural width, snippets wrap, and the existing reduced-motion rule still
  applies. No icon-only controls were added.

## Verification

Command:

```text
/usr/bin/python3.12 -m pytest -q tests/backoffice/test_editor_usability.py
```

Result: 3 passed.

The three focused tests cover:

1. Single compact header status, anchor jump links, and save toolbar before
   the identity/block work with one `draft-note`.
2. Native block disclosures, first block open, Portuguese labels, no disabled
   inputs, add form present, home identity collapsed and normal identity open.
3. Draft form contract: expected names and values, one `version`, one
   `block_count`, one `note`, no duplicate field names, and a save round trip.

Browser verification is intentionally left to the controller; this report does
not claim a browser check.

## Files changed

- `backoffice/templates/cms_editor.html`
- `static/css/admin.css`
- `tests/backoffice/test_editor_usability.py`
- `docs/superpowers/handoff/reports/home-cms-ui/editor-refinement.md`

Services, routes, publish semantics, handoff and roadmap documents, and other
tests were not modified.
