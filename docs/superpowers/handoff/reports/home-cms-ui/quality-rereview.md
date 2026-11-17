# Quality re-review - final fixes (one h1, dirty guard, form cap)

Scope: read-only re-review at HEAD `0d004e2` of the three findings closed by
`quality-fixes.md`. I read the commit diff, the current template/JS/route code, two selected
transport regressions, and `browser/acceptance.json`. I did not rerun the full suite (the
controller owns it), did not write either database, and did not touch production. No commit.

Verdict: **APPROVED**

## 1. Exactly one h1

- `app/templates/cms_page.html` renders the generic page-header `h1` only when
  `page.has_hero` is false. `has_hero` is true when any `HeroBlockView` is present, so a
  page with a hero gets one `h1` from the block and none from the shell; a page without a
  hero keeps the shell `h1` with the page title.
- `ingest/cms.py::shape_problem` rejects more than one `HeroBlock`. `canonical_for` applies
  it to every save, and `Cms._page_problem` applies it inside the publish transaction via
  `_require_publishable`, before any write. It is not a pydantic validator, so legacy stored
  two-hero bodies remain parseable, visible, restorable and canonical.
- `test_second_hero_is_refused_on_save_and_on_publish_without_writes` proves a two-hero save
  is refused with no revision or audit event, and a legacy two-hero draft cannot be
  published with meta, revisions and events unchanged.

## 2. Dirty stored-action guard

- Publish, unpublish, restore and duplicate forms all carry `data-requires-clean`.
- `static/js/admin.js` catches a submit-button click and the submit event, before browser
  validation can hide the state and before the later `data-confirm` listener. When dirty it
  calls `preventDefault` and `stopImmediatePropagation`, leaves `submitting` false, shows the
  stored-action warning, and focuses `.draft-save`. No POST or confirmation is reached.
- The generated `.select-filter` search input is ignored by the dirty watcher because it only
  hides options and changes no submitted value. Changing the underlying select still marks
  the draft dirty.
- The `<noscript>` copy states that without JavaScript the button publishes the stored draft
  only, and links to the stored-draft preview.

## 3. Bounded transport

- `CMS_FORM_MAX_BYTES` is `12_582_912` (12 MiB). Both the numeric `Content-Length` guard and
  the streamed-byte guard enforce it; no unbounded read was introduced. `MAX_FIELDS` remains
  1,000, above the roughly 890 names of the rendered maximum-block form.
- The schema ceiling is bounded directly from the real constants: 20 verification blocks x
  6 steps x 4,000 astral characters is 480,000 characters, 5.49 MiB at 12 encoded bytes per
  4-byte character, before small titles and labels. A conservative union of every block form
  field at its model maximum measures 8,446,560 encoded bytes (8.06 MiB); the fixes doc's
  rendered-field figure is 8.42 MiB. Both are below the 12 MiB cap.
- Two selected regressions passed: `test_large_schema_valid_verification_block_survives_form_transport`
  (a 288,374-byte body saves 303 with six 4,000-character steps) and
  `test_form_over_the_transport_cap_is_413_and_writes_nothing` (cap + 1 returns 413 with no
  writes). Local result: `2 passed, 1 warning in 2.96s`.

## Receipt and residual risk

`browser/acceptance.json` contains 72 checks, all passed, with an empty `errors` list and
`integrity: ok`; all 20 protected table fingerprints are unchanged. The receipt includes
`dirty publication refused before POST`, `dirty publication kept text and stored content`,
`draft edit preserved`, `draft edit remains private`, `no-JS save accepted`, `complete home
content created by real form`, the five preserved home sections, `all non-CMS table
fingerprints unchanged`, single-main-heading checks at 320/390/768/1440, and `no external
requests` and `no page or CSP errors`.

The only residual is a revision already published with two heroes before this rule. No such
revision is deployed here because these blocks are new on this feature branch; saving a second
hero is refused and republishing an old two-hero revision unchanged is refused as well.

No new stylistic scope, no whole-history/network/production access, no runtime change, no
commit.
