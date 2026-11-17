# CMS homepage and interface acceptance

Status: implemented on pipeline-rebuild, executable tree 0d004e2. NOT merged or installed. The live baseline remains f493045 on schema0019. The owner clarified that the existing homepage must be CREATED as actual CMS content, including every current section. A card-only import was replaced before acceptance.

## Delivered scope

The initialized `page/inicio` contains seventeen ordered blocks: the existing hero, highlights section head, twelve curated indicator cards, theme directory, verification chain and published institutions. Titles, copy, links, steps, labels and order are editable. Statistics, units, dates, source names and catalogue counts remain read-only live facts. The existing homepage is preserved until initial publication; later unpublication is neutral and never revives an unselected legacy list.

The Admin has content-first navigation, restrained local icons, meaningful status, native collapsible block outlines and a top reason/save toolbar. Native forms work without JavaScript. Local enhancement handles type disclosure, option filtering, unsaved-edit notices and an explicit save-first guard before stored-draft actions. Mobile navigation wraps and CMS records become labelled stacked cells. Public changes are control/spacing/focus feedback only; summaries remain script-free and cards keep SVG.

No new migration, source-data changes, AI hooks, external UI runtime, shared-edge changes or production content writes. Next free migration remains0020. Source-rights/DGEG/lag/worker-observation obligations remain separate.

## Evidence

`browser/acceptance.json` records 72 passed checks on the final executable tree. The online read-only production backup was 217,718,784 bytes with valid integrity and foreign keys. The browser/server use a new isolated copy; no live source database was opened writable.

The Chromium run created the real home through the labelled preparation form, checked all 17 blocks and static preview, published through the real form, read back the complete home and private draft changes, and saved again with JavaScript disabled. It compared the exact twelve card labels and displayed values with the original home, plus all existing sections. Both public prefixes and the Admin mount were exercised at 320, 390, 768 and1440 pixels. Assertions include no page overflow, fully visible mobile navigation/record cells, one public h1, no external requests or page/CSP errors, and keyboard focus. Attempting Publish after editing the hero produced zero POSTs, preserved the visible text and stored public bytes, and displayed the save-first warning.

All 20 non-CMS table fingerprints are identical before/after the complete browser workflow, including source, observation, quarantine, derived, verification/evidence, scheduler and legacy editorial records. Integrity is `ok`, with zero foreign-key violations. Final home head is version 4, draft revision 8, published revision 6; the saved draft is private. Immutable CMS audit events show preparation, publication and the later saves. The exact row tuples, hashes and checks are in the JSON receipt.

The first probe stopped because it tried to read a browser response body after navigation had discarded that network resource. The harness now captures those bytes immediately. That was not an application failure. An earlier full-suite attempt was deliberately interrupted before final quality fixes; it supplies no full passing result.

The initializer was separately exercised via stdin against another fresh production copy: the first call returned `published`, version 2/revision 6, and a second call returned `already_published` with the same head. This is the same invocation shape needed inside the installed container because the helper script itself is not copied into the Docker image.

A scoped timing run while the full suite was also running measured ten requests per route after two warm-ups. Public home median was 92.09 ms (104.41ms maximum); its mounted version 92.75 ms (195.89ms maximum). Admin dashboard median was 2000.69 ms and the populated editor 2192.62 ms; their HTML bodies were 414,594 and 3,911,160 bytes. These are local concurrent measurements, not production transfer/p95 claims. Repeated full series options remain a measured Admin performance limitation; local option filtering improves selection, not server preparation or HTML volume. The structured outcome is `browser/timings.json`.

The full suite on `0d004e2` completed with 2,665 passed, one failed, seven network tests deselected and three warnings in 1291.67s. The sole failure was the static SQL boundary scanner matching the word "select" in a comment. Comment-only follow-up `a291e7f` changes that word to "dropdown"; the Python AST is identical and every other runtime asset/test is unchanged (`browser/comment-equivalence.json`). Fresh boundary/CMS-route/typography checks then passed: 57 passed, one warning in33.93s. The original full result is retained unmodified with its failure in `browser/full-suite-0d004e2.log.gz` (lossless gzip, original SHA-256 b07eb18e160fe1eda0abfb5b1cf71fd5d270b6b0da461c9f73a4ef944aa66a72); no second whole-suite green run is claimed. Ruff across app/ingest/presentation/backoffice/tests and `node --check static/js/admin.js` pass. Hosted CI and actual release acceptance are not claimed here.

## Independent reviews

Initial specification review requested changes for misleading first-publication status, loss of unsaved form values on validation errors and icon-only legacy reorder buttons. Those were fixed with regressions; `spec-rereview.md` records SPEC_PASS. A follow-up keeps stale form tokens stale after invalid-field responses too.

Initial quality review requested changes for multiple main headings, publication of an old saved draft while visible edits were unsaved, and a transport cap below valid document capacity. `quality-fixes.md` records the fixes; `quality-rereview.md` records APPROVED after inspecting the final code and browser receipt. The 12MiB authenticated form cap is finite and checked by streamed bytes and Content-Length; focused real-form tests cover valid long content and refusal above the cap.

The pinned MIT icon font is 3,684 bytes; the font/source provenance is `static/fonts/icons/README.md`. The subset includes a small number of unused glyphs, a documented non-blocking residue. Human screen-reader acceptance remains unperformed; automated keyboard/tree/markup checks do not substitute for it.

## Reproduction and release

`qa_server.py` is a local-only mounted ASGI adapter over the actual public and Admin apps. `browser_acceptance.py` is the exercised Chromium harness; it requires an untouched isolated database at its configured scratch path, a baseline with no CMS home, the existing project test environment and the installed Chromium path. Copy the online baseline to a NEW acceptance filename, update the helper constants to that filename, start uvicorn at 127.0.0.1:8107 and execute the browser harness through `.venv-ci/bin/python`. It refuses failed assertions and emits the machine-readable receipt only after all checks and fingerprints pass. No secret or publisher raw database is committed.

Curated screenshots are in `browser/`: `editor-1440.png`, `editor-320.png`, `dashboard-390.png`, `home-1440.png`, the remaining viewport/prefix captures and the static/no-JavaScript views. Actual screenshots were inspected, leading to compact editor disclosures and mobile list/navigation corrections. The final mobile inspection found no visible blockers.

The current operator/release instructions are `docs/data/cms.md`, section "Homepage and UI extension". Release needs explicit owner approval for main/push/deploy of public web and backoffice PLUS initial full-home publication. No worker, schema, Authelia or Traefik change is required. Recheck current production for owner-created content before initialization; never overwrite an existing draft. Old code does not understand new block types, so the rollback procedure preserves authored history and describes that limitation instead of restoring source data.
