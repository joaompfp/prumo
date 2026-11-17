# Statistics CMS v1: operator guide and release contract

Status 2026-11-17: application release f493045 is installed with schema 0019; main is pushed and its hosted CI passed. Public Admin activation completed at 01:58:12 UTC after renewed owner approval. https://joao.date/dados/admin/ redirects anonymous visitors to Authelia, including through a public-IPv4 probe from f0nix. The direct backoffice port remains locked. The technical production trial published and read back a page/chart on both public prefixes, checked private drafts, stale forms and restore, then unpublished both; immutable audit history remains. This internal-proxy test is not a human owner login. Owner browser acceptance and human screen-reader acceptance remain pending. See the current HANDOFF and operations.md for release and recovery points.

## Access after release

Use the footer Admin link, or https://joao.date/dados/admin/. Authelia performs two-factor authentication; the application separately admits only the configured operator identity. There is no VPN bypass. The direct Tailscale port refuses ordinary page requests after proxy mode is enabled; /healthz remains non-sensitive liveness/readiness.

The content dashboard is /dados/admin/cms. Its Páginas and Gráficos links are editorial tools; the overview, series, queue and derived views remain operational tools. The installed f493045 release still uses /editorial/inicio for the built-in home. The homepage/UI extension below replaces that path after its separate release; do not confuse branch behavior with the installed runtime.

## A page from draft to public

On Páginas, create a page with a permanent lower-case hyphenated slug, a title, an introduction and a section. The section controls where the page is listed in the public catalogue. Public addresses are /paginas/{slug}, with /dados prepended on joao.date; Páginas in the footer lists every published section, including Geral.

Use the labelled controls to add text, an indicator card or a reusable chart. Up/down/remove buttons save a new draft with the submitted ordering. The installed release allows twelve blocks; the homepage extension raises the limit to twenty and adds the current homepage section types. Text is plain escaped text, never HTML. Every save and publication needs a reason for the audit trail. The slug stays fixed; duplicate to a new slug when a new address is needed.

Saving does not change the public page. The preview is deliberately static, using the draft and the same public data/rendering, with SVG charts and tables; it is labelled as a preview and is accessible only inside Admin. Public chart interaction is exercised separately. Review the publication diff and preview, enter the reason, then publish. Publication swaps the live revision atomically.

Unpublish removes the public route from the page index and returns 404 at its address; it does not delete history. Restore copies a selected revision into a NEW private draft. Inspect and publish that draft to change the public page. A form from an older version returns 409 without writing; reload and review the current state instead of repeating the stale form.

## Homepage and UI extension: implemented, awaiting release

The deliverable is the complete CURRENT homepage stored as CMS content, not an empty example or a card-only import. The reserved page `inicio` contains its existing opening copy and links, highlights heading and twelve indicator references, theme directory, verification chain and institution section. On the production copy this is seventeen ordered blocks. Statistical values, source names, theme counts, overall counts and latest verified collection date are resolved read-only on every request, not frozen into prose.

After installation, Página inicial in Admin opens `/dados/admin/cms/home`, then its normal page editor `/dados/admin/cms/page/inicio`. Native block disclosures show a concise outline; open the block you want to change. The reason and Guardar rascunho action are at the top. The section types have labelled fields, including links, steps, titles and notes. Change the order or remove sections through the same controls as other content. Only one opening block is allowed per new page, so the public page has a single main heading. Existing historical revisions remain immutable and readable.

Until first publication, preparing a home draft does not change public `/`. The authorized initializer below creates AND publishes the complete home during installation, so the owner receives an existing content page to edit rather than a setup task. Existing custom content is never overwritten: an already published home is a no-op, and an existing unpublished draft is refused for deliberate review. Every step records actor and reason. No GET creates content.

Once published, the CMS owns `/` on both public mounts. Draft edits and restoration remain private. Unpublication shows a neutral homepage with navigation; it never resurrects old default cards. An unreadable published body fails closed with 503. Loss of eligibility suppresses only affected blocks with a public availability note, even when no cards survive. `/paginas/inicio` redirects to `/` only when published; it is omitted from the ordinary page index. The old home editor redirects to the CMS and its old POST actions refuse changes after preparation.

The editor requires saving pending changes before publish, unpublish, restore or duplicate. A local JavaScript guard stops these actions before a POST and focuses the save action; filter-only searches do not dirty the draft. Without JavaScript, native disclosures and all forms still work, and publication explicitly acts on the STORED draft. Preview that stored draft and save edits before using its separate publication form. Invalid typed fields are shown back without writing, and an old version token stays old even after validation errors.

Admin uses local Bootstrap Icons 1.11.3 (MIT), subset to a 3,684-byte font; icons supplement visible labels. No CDN or new UI runtime. Styles/scripts/fonts use only same-origin assets, without inline script or eval. Motion is limited to control feedback and respects reduced-motion preferences. On mobile the navigation wraps and CMS records stack with labels instead of requiring horizontal table scrolling. Public lists and cards retain SVG and no scripts; analytical charts retain their approved local ECharts enhancement.

### Installation and content initialization

This extension has NO database migration: schema stays0019, next free0020. It needs a coordinated public-web/backoffice code release plus the explicit first CMS home publication. The worker, Authelia and Traefik do not need recreation. Pin current web/backoffice images, record their starts and the worker baseline, update the clean f0nix deployment checkout to the approved main SHA, and prebuild both affected images through `dc-web`. Recreate public web then backoffice through their `dc-web-up` aliases BEFORE the new block content is published. Re-read the exact images/health and compare worker identity/image/StartedAt/restarts with its baseline.

The helper lives in the repository, not the Docker image. From the verified deployment checkout, send the exact versioned helper on stdin to the new backoffice container. Its working directory is `/app`, so it imports the installed service. The stdin form was exercised locally, including a second no-op run. The following write is ONLY for a release authorized to initialize and publish the home:

```bash
(
  set -euo pipefail
  cd /home/joao/docker/stacks/web/images/prumo
  test -f scripts/init_home_content.py
  docker exec -i prumo-backoffice python3 - \
    --db /data/prumo.sqlite3 --editorial-db /data-w/prumo.sqlite3 \
    --actor joao --prepare-note 'Importar a homepage atual completa para o CMS' \
    --publish --publish-note 'Publicar a mesma homepage a partir do CMS' \
    < scripts/init_home_content.py
)
```

A refusal leaves any existing draft for review. Do not clear it with SQL or repeat a destructive import. Read back `page/inicio` and its creation/publication audit events, the exact card references and every existing section on both public home URLs. Then check the authenticated editor, draft isolation, CSP/local assets and unknown routes. Recheck worker continuity; do not claim source tables stayed byte-identical over live scheduled ingestion. Isolated acceptance proves that the CMS itself leaves them unchanged.

For a code rollback, freeze editorial writes and use the recorded old web/backoffice images/code through the normal aliases, without moving remote main backwards or restoring source data. The old public code ignores the CMS home and renders the preserved legacy homepage. Keep all new CMS rows/history intact; old backoffice code cannot edit new block shapes, and ordinary pages that used new block types are unavailable until newer code returns. If those pages were published, retire them deliberately with the new editor before the downgrade. A database rollback is not required for schema0019-to0019 and must not discard newer ingestion or authored history.

Verification evidence: `../superpowers/handoff/reports/home-cms-ui/README.md`. Production installation and human screen-reader acceptance remain separate gates.

## Reusable charts

Create a chart in Gráficos with one series or two distinct series. The selector shows the source, geography, frequency, unit and first/latest served periods. A calculated single-series chart can use a compatible derived key from its own base series. Units and source data are never editable.

The window is maximum, one, five or ten years, relative to the latest data period, not the clock on the reader's device. A 15-minute chart needs one explicit available UTC day; day is refused for other frequencies. No weekly/daily aggregation is invented. Two-series charts need equal frequency and common finite periods. Different units require the explicitly labelled dual scale; there is no automatic resampling or implied causal conclusion.

Publish the chart before adding it to a page. Pages reference a chart by its slug, so publishing an edited chart affects every page using it; the chart editor lists those usages before publication. To change just one page, duplicate the chart first and reference the copy. /graficos/{slug} contains the complete plotted-value table and per-series provenance and links. The graphic on a page links to this detail.

A reference is checked at publication and on each public read. A source losing redistributability or a run being withdrawn makes that affected block unavailable, without deleting observations or hiding the rest of the page. A page cannot be newly published with an already ineligible chart. Sources still awaiting rights remain withheld in the CMS too.

## Integrity and errors

CMS content occupies only cms_document, cms_revision and cms_event. The migration is additive 0019_statistics_cms; deployed 0001-0018 are unchanged. Draft/live pointers reference immutable revisions of the same document. Every successful mutation carries the authenticated actor, a reason and a version. The restricted writer permits only these three tables and the existing three editorial tables; source/observation writes and DDL are refused. Recursive triggers and protected pragma settings prevent REPLACE or pragma changes from bypassing immutability/FK/CHECK safeguards.

422 means invalid fields or an ineligible reference. 409 means a stale version. 503 means the mount/schema is unavailable or the writer is busy; no partial publication is stored. None of these errors is a request to edit source observations. Original source values, timestamps and archived evidence retain their own policies and manual-refresh instructions.

## Historical initial CMS installation: combined 0019 migration release

The following contract belongs to the original f493045 CMS installation, not the schema-unchanged homepage extension above. Do not install the old Admin-only slice as though that original CMS release had no schema change. The original release carries migration 0019 and follows the migration procedure in operations.md: record code and image rollback points, stop writers, retain a pre-migration recovery copy, verify includes/shared uid, then worker first, public web, backoffice. Both read-only and editorial openers require an exact schema version; old web/backoffice code refuses a newer database. Rollback needs BOTH old code and the pre-migration database, with all writers stopped. A code-only backoffice rollback after 0019 leaves it unavailable.

The worker/web/backoffice order uses the existing f0nix login-shell aliases dc-web-up prumo-ingest, dc-web-up prumo and dc-web-up prumo-backoffice, never raw Docker Compose. Before any build, require a clean deployment checkout at /home/joao/docker/stacks/web/images/prumo, fetch origin, switch to main, fast-forward from origin/main and compare the full installed SHA with the approved remote SHA. A push on f3nix does not update that build context. Inspect and copy every changed deploy include before the release. No data-directory ownership change is assumed necessary: verify the current shared uid 1000:1000 and permissions rather than recursively modifying a live directory.

For this combined release, retain the pre0019 database and all three image ids under the same operator receipt directory. To recover, remove the public Admin router FIRST and verify that the path no longer reaches the backoffice. Stop prumo-ingest, prumo and prumo-backoffice through the stack alias and confirm each State.Running is false. Preserve the failed-release database with SQLite backup before restoring; do not overwrite the only copy of any editorial work. Validate the pre0019 copy with integrity_check and foreign_key_check, restore it to the exact prumo.sqlite3 path, and remove only that file's -wal and -shm with all writers still stopped. Restore the recorded compose includes and encrypted environments. Switch the deployment checkout to the recorded old code in detached HEAD without moving remote main backwards, then rebuild/start worker, public web and backoffice in that order using dc-web-up. Confirm schema0018, the recorded protected-table fingerprints and both health endpoints before reopening anything. Do not start a0019 worker on the restored0018 database: it would migrate it again. The Admin-only rollback below is not this schema recovery.

Admin edge preparation and authentication checks are in ../../deploy/README-admin.md. Host distinction matters: the backoffice secret/non-secret variables belong in f0nix:/home/joao/docker/secrets/web.enc.env; the same proxy secret and Traefik environment belong in f3nix:/home/joao/docker/secrets/core.enc.env and its core stack. They are different hosts, not two files to edit blindly in one checkout. Never enable the router while the backoffice is still in local mode. Enforce the exact two_factor path before broad access rules; the application owns the narrower user allowlist.

Only after the migrated backoffice is in proxy mode and the direct port is demonstrably locked should the edge/router become active. The edge also needs a Traefik environment change and an Authelia reload/restart. These affect shared components and are part of the separate release authorization. Do not claim live outside-VPN access from local proxy-header tests.

## Release acceptance still requiring the live system

Verify actual new images/StartedAt, migration 0019, database integrity/FKs and protected-data continuity. Exercise a real owner publication through Authelia and read it back publicly, then restore/unpublish only that explicitly chosen acceptance page. Check anonymous challenge, non-owner refusal, forged identity/direct-port refusal, same-origin forms, both public prefixes, public summaries without scripts and detail charts with exact point inspection. Measure the actual edge transfer encoding and compressed bundle size; local gzip numbers are not a production network result.

A human screen-reader pass remains a separately recorded acceptance gate. Automated accessibility-tree and keyboard checks passed; they do not substitute for a person using assistive technology. The application and public Admin route are installed; human owner login/publication acceptance remains separate from the technical internal-proxy publication proof.

## Out of scope

Dated analysis snapshots, automatic stale-comment review, AI draft commentary, arbitrary calculations/aggregation, a free HTML designer and operational actions that withdraw/reverify source runs. AI commentary is a future reviewed draft add-on, never automatic publication. The next free migration is 0020; operational backoffice actions no longer reserve 0019.
