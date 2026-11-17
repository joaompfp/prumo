# Statistics CMS v1: operator guide and release contract

Status: implemented on pipeline-rebuild, NOT installed. The public Admin path does not exist in production until the authorized release enables it. Development data and trial publications are not production content.

## Access after release

Use the footer Admin link, or https://joao.date/dados/admin/. Authelia performs two-factor authentication; the application separately admits only the configured operator identity. There is no VPN bypass. The direct Tailscale port refuses ordinary page requests after proxy mode is enabled; /healthz remains non-sensitive liveness/readiness.

The content dashboard is /dados/admin/cms. Its Páginas and Gráficos links are editorial tools; the existing overview, series, queue and derived views remain operational tools. The older /editorial/inicio editor still controls the built-in home card list and is not replaced by the CMS.

## A page from draft to public

On Páginas, create a page with a permanent lower-case hyphenated slug, a title, an introduction and a section. The section controls where the page is listed in the public catalogue. Public addresses are /paginas/{slug}, with /dados prepended on joao.date; Páginas in the footer lists every published section, including Geral.

Use the labelled controls to add text, an indicator card or a reusable chart. Up/down/remove buttons save a new draft with the submitted ordering. There is a maximum of twelve blocks. Text is plain escaped text, never HTML. Every save and publication needs a reason for the audit trail. The slug stays fixed; duplicate to a new slug when a new address is needed.

Saving does not change the public page. The preview is deliberately static, using the draft and the same public data/rendering, with SVG charts and tables; it is labelled as a preview and is accessible only inside Admin. Public chart interaction is exercised separately. Review the publication diff and preview, enter the reason, then publish. Publication swaps the live revision atomically.

Unpublish removes the public route from the page index and returns 404 at its address; it does not delete history. Restore copies a selected revision into a NEW private draft. Inspect and publish that draft to change the public page. A form from an older version returns 409 without writing; reload and review the current state instead of repeating the stale form.

## Reusable charts

Create a chart in Gráficos with one series or two distinct series. The selector shows the source, geography, frequency, unit and first/latest served periods. A calculated single-series chart can use a compatible derived key from its own base series. Units and source data are never editable.

The window is maximum, one, five or ten years, relative to the latest data period, not the clock on the reader's device. A 15-minute chart needs one explicit available UTC day; day is refused for other frequencies. No weekly/daily aggregation is invented. Two-series charts need equal frequency and common finite periods. Different units require the explicitly labelled dual scale; there is no automatic resampling or implied causal conclusion.

Publish the chart before adding it to a page. Pages reference a chart by its slug, so publishing an edited chart affects every page using it; the chart editor lists those usages before publication. To change just one page, duplicate the chart first and reference the copy. /graficos/{slug} contains the complete plotted-value table and per-series provenance and links. The graphic on a page links to this detail.

A reference is checked at publication and on each public read. A source losing redistributability or a run being withdrawn makes that affected block unavailable, without deleting observations or hiding the rest of the page. A page cannot be newly published with an already ineligible chart. Sources still awaiting rights remain withheld in the CMS too.

## Integrity and errors

CMS content occupies only cms_document, cms_revision and cms_event. The migration is additive 0019_statistics_cms; deployed 0001-0018 are unchanged. Draft/live pointers reference immutable revisions of the same document. Every successful mutation carries the authenticated actor, a reason and a version. The restricted writer permits only these three tables and the existing three editorial tables; source/observation writes and DDL are refused. Recursive triggers and protected pragma settings prevent REPLACE or pragma changes from bypassing immutability/FK/CHECK safeguards.

422 means invalid fields or an ineligible reference. 409 means a stale version. 503 means the mount/schema is unavailable or the writer is busy; no partial publication is stored. None of these errors is a request to edit source observations. Original source values, timestamps and archived evidence retain their own policies and manual-refresh instructions.

## Installation is a combined migration release

Do not install the older Admin-only slice by itself as though the complete branch had no schema change. This branch carries migration 0019 and must follow the existing migration release procedure in operations.md: record code and image rollback points, stop writers, retain a pre-migration recovery copy, verify includes/shared uid, then worker first, public web, backoffice. Both read-only and editorial openers require an exact schema version; old web/backoffice code refuses a newer database. Rollback needs BOTH old code and the pre-migration database, with all writers stopped. A code-only backoffice rollback after 0019 leaves it unavailable.

The worker/web/backoffice order uses the existing f0nix login-shell aliases dc-web-up prumo-ingest, dc-web-up prumo and dc-web-up prumo-backoffice, never raw Docker Compose. Inspect and copy every changed deploy include before the release. No data-directory ownership change is assumed necessary: verify the current shared uid 1000:1000 and permissions rather than recursively modifying a live directory.

Admin edge preparation and authentication checks are in ../../deploy/README-admin.md. Host distinction matters: the backoffice secret/non-secret variables belong in f0nix:/home/joao/docker/secrets/web.enc.env; the same proxy secret and Traefik environment belong in f3nix:/home/joao/docker/secrets/core.enc.env and its core stack. They are different hosts, not two files to edit blindly in one checkout. Never enable the router while the backoffice is still in local mode. Enforce the exact two_factor path before broad access rules; the application owns the narrower user allowlist.

Only after the migrated backoffice is in proxy mode and the direct port is demonstrably locked should the edge/router become active. The edge also needs a Traefik environment change and an Authelia reload/restart. These affect shared components and are part of the separate release authorization. Do not claim live outside-VPN access from local proxy-header tests.

## Release acceptance still requiring the live system

Verify actual new images/StartedAt, migration 0019, database integrity/FKs and protected-data continuity. Exercise a real owner publication through Authelia and read it back publicly, then restore/unpublish only that explicitly chosen acceptance page. Check anonymous challenge, non-owner refusal, forged identity/direct-port refusal, same-origin forms, both public prefixes, public summaries without scripts and detail charts with exact point inspection. Measure the actual edge transfer encoding and compressed bundle size; local gzip numbers are not a production network result.

A human screen-reader pass remains a separately recorded acceptance gate. Automated accessibility-tree and keyboard checks passed; they do not substitute for a person using assistive technology. No release is claimed here.

## Out of scope

Dated analysis snapshots, automatic stale-comment review, AI draft commentary, arbitrary calculations/aggregation, a free HTML designer and operational actions that withdraw/reverify source runs. AI commentary is a future reviewed draft add-on, never automatic publication. The next free migration is 0020; operational backoffice actions no longer reserve 0019.
