# Prumo statistics CMS v1

Date: 2026-11-16
Status: implementation authorized by the owner after the product brainstorm. Release remains a separate gate.
Baseline: c9a2e5f, schema 0018.

## Product contract

The owner can enter Admin without a VPN, create a statistics page with an editorial title, introduction and ordered blocks, preview, publish, edit, duplicate, unpublish and recover a previous revision. The backoffice also maintains reusable chart definitions, including operator-selected two-series comparisons. None of these actions edits observations, units, licences, verification evidence or source metadata. Editorial wording is content, not a translation-catalogue entry. This supersedes the earlier code-only editorial-page and code-only-pair restriction for this CMS, not for the existing built-in pages.

Implement a complete, deliberately bounded v1: live statistical pages, plain escaped text, indicator cards and reusable charts with their value tables. No HTML builder, arbitrary numerical tables, uploads, new statistical calculations, mixed-frequency aggregation, automatic AI publication or external CMS. Existing built-in home composition and comparisons remain functional and unchanged apart from the Admin link and approved interactive rendering.

## Admin and identity

Canonical entry: https://joao.date/dados/admin/. A footer Admin link uses that absolute URL on both public hosts. Backoffice navigation, form actions, pagination and redirects work below /dados/admin as well as directly in development. Reuse one validated prefix helper rather than duplicating URL sanitation.

Infrastructure deployment requires an exact path-boundary router at priority above /dados and Authelia before StripPrefix. The exact-path ACL requires two_factor without a subject before broader ACLs, so an anonymous visitor is challenged instead of falling straight into a deny rule. Owner authorization is separately enforced by the application's verified proxy-secret plus Remote-User allowlist before any content is returned; every other authenticated user is refused. This corrects the earlier owner-allow/unconditional-deny proposal, which made the first Admin click a dead-end 403. No VPN bypass router. The route and ACL are versioned deployment templates; do not modify or restart the live edge as part of implementation.

The application production authentication mode must fail closed: trusted identity must not be obtained from forgeable Remote-User alone on the direct Tailscale port. Use a private proxy credential injected by Traefik, compared in constant time, plus an allow-listed Authelia Remote-User. Keep credentials in environment/encrypted infrastructure secrets, never in git or request logs. Exempt only non-sensitive liveness. Bind audit actors to the authenticated identity. Direct development mode is explicit, never the public deployment default. Same-origin checking uses a configured canonical HTTPS origin in proxy mode and exact request origin in development; a malicious forwarded proto/host/prefix cannot authorize writes. Keep body limits, no-store, DNS-rebinding protection and strict form-action/frame/base policies.

Provisioning the proxy credential and enabling the ACL/router are release actions. Until then the existing private backoffice stays unchanged. Supply tested preparation and rollback instructions and config contracts; do not claim the public entry is online.

## Interactive charts

Implement the separately reviewed 2026-11-16-interactive-charts-design.md. Refactor chart preparation first with unchanged SVG; then use a pinned locally built ECharts engine and adapter on comparisons, primary/calculated detail and CMS chart pages. SVG stays the accessible, failure, no-JavaScript and print alternative; summary/list cards stay script-free. Point values are server-formatted exact strings from the same snapshot. Dual axes remain explicit and labelled. No data fetch after page load, CDN, smoothing, silent resampling or rounding of source values. Preserve scoped CSP and both public prefixes.

## CMS persistence and boundaries

Add migration 0019; never edit deployed 0001-0018. Operational writes previously earmarked for 0019 move to 0020 or later and are not implemented here.

Store page/chart documents with immutable revisions, current draft/published pointers and optimistic version numbers, plus append-only actor/reason audit events. Publication swaps a pointer in the same transaction as the audit event. Saving drafts and restoring history do not modify published content. A chart publication may update the pages referring to it; show its usages before publishing. Restoring an old document creates a new draft, not a mutation of history. Slugs are immutable; duplicate for a new address. Deletion is unpublication, not destruction of history. Failed or stale mutations write nothing. Restrict the existing second writable SQLite opener to editorial/CMS tables and prohibit DDL and observation writes. Worker still owns migrations.

SQL stays in ingest/db.py. Pure validated document contracts live separately from storage. Services validate eligibility and call storage; routes parse forms and dispatch to services off the async event loop; templates render prepared views. Refactor shared public chart/eligibility preparation before reusing it. No generic plugin or block registration architecture.

Page content: slug, title, introduction, section (economy/demography/energy/general), ordered text/card/chart blocks. Text is escaped plain paragraphs. Card blocks reference an eligible primary series and optional compatible derived key. Chart blocks reference a published library chart by slug. The editor uses ordinary labelled fields and add/move/remove controls; requiring the owner to edit JSON does not satisfy this feature. Limits: 12 blocks/page, 160 title characters, 4000 introduction/text characters and an explicit bounded form body. Reject literal and encoded em dashes in authored editorial text.

Chart content: slug, editorial title/note, one or two primary series (one compatible calculated series is allowed for single-series charts), supported time window and explicit single/dual scale. Show canonical unit, frequency, geography and coverage beside the choices. Two-series charts require distinct series, equal frequency and common finite periods; mismatched units require dual axes. No mixed-frequency transformation or inferred causal claim. Each line retains its own title, unit, source link and provenance for the last displayed period. E-REDES remains one explicitly chosen UTC day, with no aggregation. Publish refuses invalid/ineligible references. Public reads revalidate at read time: a withdrawn/licence-revoked series cannot be exposed via a CMS page. Drop an unavailable block, display a generic public availability note and log the reason, leaving the rest of the page usable. Never leak internal licence notes or raw identifiers.

Public routes: /paginas index, /paginas/{slug}, /graficos/{slug}; only published documents are visible, drafts/unpublished/unknown yield 404. Integrate section-filtered links in existing theme pages without replacing their statistical catalogue. Public reads remain strictly read-only and all statistical reads filter fetched, active, primary and redistributable data. Previews exist only in the authenticated backoffice, are no-store and do not rely on a public preview switch.

## Acceptance

Prove the complete workflow with synthetic fixtures and a copy of production: new page/chart, draft edits with live content unchanged, preview, publish, edit, stale-form conflict, unpublish, restore and republish, duplicate and chart usage. Test Origin, proxy credential and identity spoofing, hostile prefixes, XSS strings, body/field bounds, punctuation, rights revocation, withheld derived bases and reference changes. Compare source/observation/quarantine/derived fingerprints before/after; restricted writer must refuse direct changes. Upgrade a populated 0018 database through open_db with integrity/FK checks and timing. Verify rollback planning explicitly requires the pre-migration database as well as old code.

Run browser QA for actual labelled editor controls, ordering, both prefixes and desktop/mobile; verify exact interactive point inspection, keyboard, touch and fallback from the chart spec. Record accessibility limits honestly. Freeze the final tree after visual fixes, run the full offline suite and lint, then independent specification and quality reviews with bounded fix/re-review loops. Handoff, operations and the owner's roadmap carry accurate implemented-versus-deployed status. No live migration, edge restart, merge to main or deployment without a separately authorized release.

## Later roadmap

After this cycle: dated analysis snapshots and comment staleness review; broader page templates and navigation management if needed; owner-reviewed AI draft commentary with input provenance and approval, never on-demand public generation; separately specified operational write actions; DGEG technical reconciliation, source rights, lag classification, SIGBUS follow-up and elapsed worker acceptance. These remain visible and are not relabelled completed by the CMS release.
