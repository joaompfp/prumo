# CMS-owned comparisons implementation plan

> For Hermes: use subagent-driven-development for bounded implementation slices and sequential specification/quality reviews.

Goal: make the real comparisons already requested by the owner editable and publishable in the backoffice, with a read-only public presentation. A technical trial document is not the deliverable.

Architecture: extend immutable CMS chart revisions rather than introducing another content store. Reuse the verified chart preparation used by the Caderno behind an authored-chart adapter. The public comparison catalogue and details read published CMS revisions exclusively. The reader's exploratory Caderno remains separate and is never the canonical destination of an editorial comparison.

Tech stack: existing FastAPI/Jinja, typed Pydantic CMS documents, restricted SQLite writer, local ECharts/SVG, Tabler Admin forms. No statistical schema change or migration, ingestion operation, external dependency, authentication or shared-edge change is authorized by this slice.

## Binding content contract

Preserve all existing ChartDocument fields and their canonical immutable bodies. Add optional `series_extra` (zero to four references, total one to six distinct series), `axes` (null for validated automatic allocation, otherwise a 0/1 assignment per series), `frequency` (`original` or `annual`), `transform` (`original`, `base100`, `pp`), `base` (optional four-digit reference year) and `comparison_group` (null for library-only; `portugal`, `countries` or `general` for public Comparações). Derived-key charts remain single-series. Reject incompatible axes, unsupported transformations and ignored day/base settings. Preserve old revision restoration and CAS/audit semantics.

The editor supports all these fields using labelled native controls, with six ordered series choices and an optional explicit axis per chosen series. No JSON editing. Saving remains private; preview, publish, withdraw, duplicate and restore use the existing lifecycle. Public chart/pages have exact point interaction, table and provenance, with lengthy metadata disclosed secondarily. Public query parameters cannot override an authored comparison.

## Task 1: shared preparation and typed contract

Owner: model/read-service implementer. Files: ingest/cms.py, app/cms_reads.py, app/notebook_chart.py, app/calendar_notebook.py and focused model/service tests. Refactor the shared chart preparation before enabling authored multiseries. Keep prior single/pair payloads working. Add an optional `analysis` field to CmsChartView carrying the prepared NotebookChart for new authored analytical documents. Ensure shared title/axis membership drives SVG, payload, table and evidence consistently. Explicit side assignments must be validated against output scale signatures, including annualization. No public form or notebook-page composition dependency. Run focused CMS/model/notebook tests, not the whole suite.

## Task 2: real backoffice authoring

Owner: forms/UI implementer. Files: backoffice/cms_routes.py, backoffice/templates/cms_editor.html, backoffice/templates/cms_list.html, related Admin JS/CSS only if necessary, focused new Admin tests. Retain legacy posted forms as compatible input. New forms submit series_a, series_b, series_extra_0..3, axis_0..5 (empty for automatic or 0/1), frequency, transform, base and comparison_group. All six axes must be automatic or all selected-series assignments explicit; inactive empty slots are ignored. Error/conflict rendering preserves submitted fields and expected version. Complete diff and publication impact remain visible. Creation/editing/discovery must work without JavaScript and at the approved enlarged typography.

## Task 3: CMS-only catalogue and public reader

Owner: controller. Files: app/main.py, app/cms_routes.py, app/templates/compare_index.html, app/templates/cms_chart.html, app/templates/_cms_blocks.html, new CMS catalogue helpers and focused tests. /comparar lists only published, eligible CMS charts assigned a comparison group. /comparar/{slug} renders the same authored document as /graficos/{slug}, with no configuration forms or links that turn editorial comparisons into a notebook. Legacy country URLs redirect only to an eligible published CMS counterpart. Draft/unpublished/withdrawn content never revives a built-in definition. Keep both public mounts and the private static preview safe.

## Task 4: populate actual requested content

Owner: controller. Add a versioned idempotent importer for the existing three pairs, three European country groups and three Portuguese multi-axis compositions. Seed exact reviewed titles, notes, references, axis groups and windows as CMS chart documents, then publish through the restricted audited service. This is release content explicitly requested by the owner. Refuse collisions with existing operator drafts and never overwrite existing documents. Exercise the importer twice on an online production backup; edit a real imported comparison, preview, publish, verify public change, restore to draft and republish. Confirm all non-CMS table fingerprints unchanged. Deliver direct Admin edit links for the actual populated content.

## Task 5: acceptance and release

Run cheap typography/assets/boundary guards, focused regressions, browser workflows on an isolated production copy, sequential independent specification and quality reviews, controller full suite and a clean committed-checkout gate. Compare 390/768/1440/1920 public analytical views and Admin editing; require complete chart axes, keyboard/touch exact values, SVG/no-JS/print and script-free private previews. Preserve human screen-reader acceptance as open.

Commit only task-owned paths; push and read back exact refs. Carry the owner's live correction request through a web/backoffice-only release, using existing aliases and mount-safe prebuild, rollback pins and unchanged-worker gates. Install readers before invoking the importer. Read back published CMS heads, history/audit and both public addresses after initialization; no live test-only content substitutes for the imported product pages. Verify migration/schema unchanged and distinguish legitimate concurrent worker collection from content writes. Update HANDOFF, the analytical-workspace roadmap and /home/joao/vaults/projects/prumo/roadmap-e-implementacao.md with actual results and the corrected priority for CMS authorship.
