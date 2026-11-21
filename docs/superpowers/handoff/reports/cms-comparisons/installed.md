# Installed CMS-owned comparisons

Installed on f0nix on 2026-11-21 at 15:33 UTC after the owner's correction that real comparisons belong in the backoffice. Runtime/main `a9add13399b257c6d49897d6acb769becfcb2083` is pushed and installed; later report-only commits do not change the running application.

## Product and content

The real nine comparisons are immutable, audited CMS chart documents: the three original pairs, the three Portugal multiaxis compositions and the three European country comparisons. All have published revision pointers, a retained draft, and creation/publication audit events. A repeated import preserved all nine. There is no on-GET bootstrap and no overwrite of existing operator drafts or publications. Original installation trials stay unpublished; the authored homepage is unchanged.

The operator can edit title, notes, one to six series, per-series axes, temporal window, native/annual view, reviewed transformations and comparison category in Admin, then save privately, preview and publish deliberately. The library lists real comparisons and supports the existing duplication/withdrawal/restoration lifecycle. Public `/comparar` is CMS-owned and every detail reads only the published revision. Public URL settings cannot override the composition and the details have no composition form or link into a configurable Caderno. Exact point inspection, complete tables and disclosed provenance remain. The Caderno remains a separate exploratory tool.

Admin library: `https://joao.date/dados/admin/cms#comparacoes`.

Actual populated editors include:

- `/dados/admin/cms/chart/taxas-juro-credito-depositos`
- `/dados/admin/cms/chart/divida-saldo-pib-per-capita`
- `/dados/admin/cms/chart/comercio-externo-pib-per-capita`
- `/dados/admin/cms/chart/eletricidade-domestica`

Public canonical examples: `/comparar/taxas-juro-credito-depositos` and `/comparar/eletricidade-domestica`, on both public mount shapes. The older `/comparar/paises/{slug}` URLs redirect to the eligible published CMS counterpart.

## Verification

Exact runtime hosted CI [44918693857](https://github.com/joaompfp/prumo/actions/runs/44918693857) passed: 3,183 passed, 25 skipped, seven network deselected, three warnings in 647.13 seconds. Ruff passed. JSON and lossless log archive are in `production/`.

A clean detached checkout of `a9add13` passed 91 focused tests with all imported providers resolved inside that checkout; broader ruff was clean. Controller final working-tree probes passed 123, including the repaired older public fixtures, new editor round-trip regressions and typography/boundary guards. The earlier local whole run is retained as development evidence with its six obsolete-fixture failures/errors; it is not described as a green final whole suite. Specification passed; quality findings were repaired in `2aad448` and independently re-reviewed as approved.

The complete isolated production-copy workflow passed 79 browser checks, including an actual four-to-five-series edit/save/private preview/publication/readback/restoration, both prefixes, mobile/desktop, keyboard/touch exact values, no-JavaScript, blocked-bundle and print fallbacks. All protected-table, schema and authored-home fingerprints remained identical after the workflow. Directory HTTP median was 58.00ms over ten requests on that copy, not an installed-edge measurement.

Installed public acceptance passed 348 checks across both public addresses and 390/1440 widths, covering all nine real comparisons, every series and table row, exact Home/End values, absence of public composition controls, no overflow, canonical legacy redirects, 404 and Authelia challenge. The existing shared-edge Permissions-Policy `vr` warning occurred 40 times; no application errors, other console warnings or off-origin requests were observed. Human screen-reader acceptance remains open.

Read-only installed Admin checks visited all nine exact populated editors and verified every selected series, per-slot axis and category, plus prefix-correct save/publish actions. The existing technical proxy/state probe passed 25 checks and the static private preview probe passed. Internal proxy evidence is not a new human Authelia login.

## Installed state and preservation

Public web: container `8c430cb1c083`, image `11410e96aad1`, StartedAt `2026-11-21T15:33:04.489936936Z`.

Backoffice: container `e37375c3ef26`, image `85f02ae7566d`, StartedAt `2026-11-21T15:33:06.267617454Z`.

Both are healthy with zero restarts; their actual images match rebuilt runtime tags and differ from retained rollback images. Only these readers were recreated through the existing `dc-web` aliases. Prebuilding used a clean detached approved-SHA context while the bind-mounted live checkout stayed on its old version. Only the affected bind-mounted public reader was stopped for the fast-forward.

The authorized content publication wrote CMS documents/revisions/events only. `production/content.json` compares transaction-consistent fingerprints immediately around initialization: all non-CMS tables, source observations, evidence, quarantine, derived values, schema and homepage are unchanged. Database quick_check is ok with zero foreign-key violations. No SQL migration, source-data edit, ownership, credentials, Authelia or Traefik operation ran.

The worker was NOT restarted by this release and matches the complete immediate pre/post-activation baseline. It had already reached restart count three and StartedAt `2026-11-21T15:04:10.860527167Z` before the first production operation at 15:21. Its earlier autonomous restarts and renewed observation window remain unresolved; the prior count-one checkpoint is historical, not the release baseline.

## Receipts and recovery

Operator directory: `f0nix:/home/joao/prumo-operations/cms-comparisons-release-20261121`. The online acceptance snapshot and executed helper copies are separately under `f0nix:/home/joao/prumo-operations/cms-comparisons-20261121`. Versioned scripts `prebuild.sh`, `activate.sh`, `publish_content.py`, `admin_content_probe.py` and `installed_browser.py` record the actual paths/contracts. These dated scripts are installation evidence, not permission to repeat a live import blindly.

Rollback code: `53db524b797991dbcab48e95ba4c316ee561b39e`. Retained tags `prumo:rollback-cms-comparisons-20261121` and `prumo-backoffice:rollback-cms-comparisons-20261121` pin the former images `31dcfe0b95b3` and `c570979021b2`. Freeze editorial writes and retire only affected new publications with the newer editor before downgrading if necessary. Preserve revisions/history and source data; no database restore or ingestion restart is required. Old code would resume its old code-curated directory and cannot edit new analytical documents, so that rollback is a service recovery, not the equivalent CMS product.

Phase D is installed. General analytical-page polish, discovery, dated analysis and human-approved AI drafts remain separate roadmap scope. Rights/DGEG, old-period classification, operational write actions and actual worker observation remain open.
