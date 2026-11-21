# CMS comparison publication path: quality review

**Verdict: REQUEST_CHANGES**

Read-only quality review after the PASS specification review. Scope: baseline `53db524`, candidate `616fb05`, plus the task-owned working diff and new files. I inspected the new public directory and reader, the importer, the shared definition checks and the typed form integration. No code, git index, network or live database writes were made. The 48 focused contract and route tests pass (`.venv-ci/bin/python -m pytest -q tests/app/test_cms_comparisons.py tests/backoffice/test_cms_multiseries_routes.py tests/ingest/test_cms_multiseries.py` -> 48 passed). The 74-check browser pack and the isolated import receipt were accepted from the specification review and were not rerun. Three small deterministic probes were run against temporary migrated databases.

## Required fixes

### 1. Editor cannot round-trip a non-contiguous series selection with explicit axes (blocking)

`ChartDocument.axes` is indexed by selected series (`ingest/cms.py:349,356-362,436-442`), while `chart_series_fields` indexes it by slot (`backoffice/templates/cms_macros.html:49-68`). `_chart_body` correctly produces selected-order axes (`backoffice/cms_routes.py:347-371`).

Repro: created a draft body with `series_a=A`, `series_b=None`, `series_extra=[C]`, `axes=[0,1]`, `scale=dual`. `GET /cms/chart/gap` selected axis 1 on the empty Serie B select and left the selected Serie C on automatic. Posting the rendered form unchanged returned 422 `eixo da serie extra 1 (...): escolha 0 ou 1 ...`. A realistic edit that clears Serie B from an imported multi-series group reaches the same state, and repairing the visible error can silently change an axis assignment.

Required fix: render a slot-shaped axis view, or map selected-order axes through the selected slots, for stored documents. Add a round-trip test with B empty and explicit axes. Rejecting the gap only in the parser is not enough unless the typed contract also rejects it everywhere.

### 2. Dashboard "Criar grafico" loses extra series and explicit axes on refusal (blocking)

`backoffice/templates/cms_list.html:216-217` passes raw `values` as `doc`; the shared macro reads `doc.series_extra` and `doc.axes` (`backoffice/templates/cms_macros.html:49-56`), which raw fields do not contain. `cms_new` re-renders with `values=fields` on both FormError and CmsRefused (`backoffice/cms_routes.py:958-960,969-971`).

Repro: POST `/cms/new` with A, B, a duplicate A in the Serie C slot, `axis_0=0`, `axis_1=1`, `axis_2=1`. The response was 422; the re-rendered Serie C select had no selected option and all six axis selects showed automatic. A corrected resubmit drops the extra-slot selection and the axes.

Required fix: pass a document-shaped recovery view built from the raw fields (the existing `_submitted_document` already returns slot-shaped axes), or make the macro accept the raw field names. Add a creation-refusal test covering extras and axes.

### 3. A transformed dual view with automatic axes can be saved but never published (important)

`ingest/cms.py:436-445` checks dual membership only when `axes` is explicit and checks the one-left-axis rule only when `axes is not None`. A body with `scale="dual"`, `frequency="annual"`, `transform="pp"`, `axes=None` is accepted by `parse_body` and `cms.create`; `cms.publish` then refuses with `chart/td: unavailable; nada foi publicado` because the shared preparation refuses transformed dual charts. This was observed on a temporary migrated database.

Required fix: reject `transform != "original"` with `scale != "single"` in `_coherent`, and/or force single scale in the form parser and UI, so the draft cannot be saved in an unpublishable state. Add a focused test.

## Verified behavior (core public and importer acceptance sound)

- Importer overwrite safety: `install` preserves every existing published document (`backoffice/comparison_import.py:75-81`), refuses an existing private draft before the first write (`:77-78`), and `cms_create` itself refuses an existing kind/slug (`ingest/db.py:1933-1936`). The rerun test preserves operator edits and versions.
- Public reader: `/comparar` and `/comparar/{slug}` read published CMS revisions only; drafts, unpublished documents and restore-only drafts stay private; library charts without a category are absent; query parameters cannot override composition; the country redirect is limited to a published `countries` comparison; withheld and inactive series are filtered before the index lists a chart. The analysis template has no composition form or `/caderno?` link. Mount-prefix and CSP checks pass.
- Empty and transform/axis boundaries: an empty selection is refused before any write (`backoffice/cms_routes.py:349-350`); explicit transformed axes with a right-axis member are refused by `ChartDocument`; annual, day and base coherence is enforced. Editor refusal recovery preserves raw fields and expected version. The dashboard creation path is the exception in fix 2.
- Actual content: the nine definitions match the reviewed slugs and series; the isolated receipt records nine published imports, nine preserved reruns, protected tables unchanged, home unchanged and schema unchanged. The 48 focused tests pass. The reported 74-check browser pack covers the four-to-five side edit, publication and restoration path; it does not report the gap or transformed-dual cases above.
- Authorization: no additional public route reaches the importer or a preview; the authenticated backoffice preview remains the only draft renderer. No published-only or restricted-writer bypass was found.

## Suggestions (non-blocking)

- Directory dead-link tradeoff: `cms_comparisons.index` skips parse, definition and title/unit failures, but a published chart can later fail full preparation (annual unsupported frequency, transform normalisation refusal, duplicate labels, missing source text) and remain listed while the detail 404s. Consider metadata checks for input frequencies and label uniqueness, and log skipped slugs.
- `country_signature` accepts a Eurostat native code with no `geo` dimension (`app/statistical_definitions.py:32`). All 15 imported country series have `geo`, so this is not a current content failure, but requiring it for Eurostat would match the old country page.
- Contract constants are duplicated in `backoffice/cms_routes.py:69-81` (`MAX_EXTRA_SERIES`, `SERIES_SLOTS`, `_FREQUENCIES`, `_TRANSFORMS`, `_COMPARISON_GROUPS`, `_BASE_YEAR`) versus `ingest/cms.py:25-39`; derive or share them to prevent drift.
- Dead legacy surfaces remain: `app/country_comparisons.py`, `app/portugal_comparisons.py`, `app/templates/compare.html`, `app/templates/compare_countries.html`, and old-module tests. They are no longer routed, but two still contain `/caderno?` composition links and could be reused accidentally. Remove or mark them retired.
- `install` returns a different shape for preserved entries (no `published_revision_id`) and lets `CmsDocumentError` or `ReadOnlyOpenError` escape instead of `CmsRefused` or `CmsUnavailable`; minor API consistency.
- `ComparisonSummary.note` is computed but never rendered; the index says `{{ row.series_count }} series` even for one. Minor cleanup or use the existing singular and plural copy.
- No direct tests for `chart_definition_problem` or `country_signature`; current coverage is route-level. Add helper tests for country identity, gap axes and transformed dual.

## Release note

Production is not installed and the full suite remains the parent gate. This review adds no release scope.
