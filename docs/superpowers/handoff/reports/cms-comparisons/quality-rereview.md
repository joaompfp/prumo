# CMS editor quality findings: scoped re-review

**Verdict: APPROVED**

Scope: closure of the three required fixes in `docs/superpowers/handoff/reports/cms-comparisons/quality-review.md`, verified against commit `2aad448`. Inspected only the five committed files and the diff against `616fb05`; no whole-branch audit, source discovery, network, browser or full-suite rerun. The earlier broad review remains the applicable quality record; this note only closes the three findings below.

## Finding 1: editor round-trips a non-contiguous selection with explicit axes (closed)

- `backoffice/cms_routes.py:464-486` adds `_chart_slot_document`. It copies the stored body, enumerates the truthy series references across the six editor slots (A, B, then up to four extras), and assigns each selected-order axis to that series' own slot; gaps and unused slots stay `""`.
- The editor render path uses it only for a stored body: `backoffice/cms_routes.py:843-847` reruns `_submitted_document` when `values is not None` (refused save, raw slots) and applies the mapping otherwise. The write path is untouched: `mutate` still saves `_document_from_fields` output, and `_diff` still compares the stored shape.
- `_chart_body` already rebuilds selected-order axes from the six slot controls (`backoffice/cms_routes.py:359-370`), so the mapped view round-trips.
- Verified: `tests/backoffice/test_cms_editor_roundtrip.py::test_gap_selection_with_explicit_axes_round_trips_unchanged` renders A, empty B, C with axes 0, empty, 1, posts unchanged, and stores `axes=[0,1]`. An independent probe with A, gap B, C, D and `axes=[0,1,0]` rendered `['0', None, '1', '0']`, kept `axes=[0,1,0]` on an unchanged submit, and stored `[1,1,0]` after moving A to the right axis in its own slot, confirming per-slot rather than positional mapping. An all-left dual was refused by the existing typed dual-membership rule, as expected.

## Finding 2: dashboard creation refusal loses extras and explicit axes (closed)

- `backoffice/cms_routes.py:884-887` builds `chart_doc` from `_submitted_document("chart", values)` when the submitted `kind` is `chart`, and the dashboard template now passes `chart_doc` to both chart macros (`backoffice/templates/cms_list.html:216-217`). Raw `values` still drive slug, title and note.
- Both creation refusal paths already route through `list_page` with `values=fields` (`backoffice/cms_routes.py:991-993, 1002-1004`), so FormError and CmsRefused both recover.
- Verified: `test_creation_refusal_preserves_extra_slot_and_explicit_axes` posts A, B, duplicate A in the C slot with axes 0, 1, 1; the 422 response keeps slug, A, B, the C-slot selection and all three axis selections, and no chart is created. Initial dashboard rendering still works with the empty `chart_doc` because the macros tolerate undefined keys.

## Finding 3: transformed dual view can be saved but never published (closed)

- `ingest/cms.py:445-446` adds the `_coherent` rule: `transform != "original"` requires `scale == "single"`. This sits in the typed `ChartDocument`, which `parse_body` enforces on create, save and publish preparation (`backoffice/cms.py:279, 287, 556`). The editor save path reaches it through `_document_from_fields`.
- Verified: `tests/ingest/test_cms_transform_contract.py` refuses transformed dual with automatic axes for both `pp` and `base100`, keeps transformed single-scale valid, and keeps dual without transformation valid. `test_transformed_dual_with_automatic_axes_is_refused_before_any_save` confirms the route returns 422, keeps version 1, and leaves metadata and revisions unchanged.

## Verification run

- `.venv-ci/bin/python -m pytest -q tests/backoffice/test_cms_editor_roundtrip.py tests/ingest/test_cms_transform_contract.py` -> 8 passed.
- Two temporary-migrated-database probes (slot mapping with three selected series and a gap; per-slot axis change) behaved as above.
- Working tree changes outside the five committed files belong to the parent workstream and were not touched; no code, index or commit changes were made by this re-review, and no full suite was rerun.

All three required fixes are present in the committed code and covered by the new regression tests. No remaining finding from the original review blocks closure.
