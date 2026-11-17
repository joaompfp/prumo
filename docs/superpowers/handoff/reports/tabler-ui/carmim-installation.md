# Tabler/carmim interface: installed release

Runtime: 14f845ec2ca006fa992c460fd2af579940ac28bd. Owner approved merge, push and installation while requesting the previous carmim highlights and keeping the new plumb-bob geometry. Main was fast-forwarded from 7a35f47 and its exact remote SHA verified before the clean f0nix checkout was updated. Hosted CI 44090471137 passed on this exact code. Images were prebuilt through dc-web while the old containers served, then recreated with dc-web-up prumo and dc-web-up prumo-backoffice. No raw Compose command ran.

## Installed services

Public web: image sha256:47f3feb6cf3455ca6a8872ed832091b11423cbfbf3604ddcf99aef0a24fee1d9, StartedAt 2026-11-17T13:20:58.803961973Z. Backoffice: image sha256:027cb9b3487d3c2fd846e8651e885b24fc12931afddbbe577a33019c89f4cf14, StartedAt 2026-11-17T13:21:00.364134607Z. Both healthy, zero restarts.

The worker is untouched: container 3921475705a35df28b81a7d381e4d388918616c681607a116ac9df69ad334e4b, image sha256:ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3, StartedAt 2026-11-17T01:45:15.558866311Z, restart count zero. Every captured worker field matches the baseline. No migration, ownership repair, source-data write, content publication, credential provisioning, Authelia or Traefik change ran. Schema remains 0019; next migration is 0020.

CMS documents, revisions and events, schema and migration fingerprints match immediately before/after the release; quick_check ok, no FK violations. The presentation release does not freeze normal scheduled ingestion or claim a whole live-database hash is unchanged. The pre-existing encrypted-environment and backoffice-include edits remain untouched and uncommitted; they are not part of the scoped infrastructure-pointer update.

## Verification

Final controller suite on frozen runtime 14f845e: 2,688 passed, 7 network deselected, 3 warnings in 1,280.12 seconds. Ruff and Admin JavaScript syntax clean. The earlier pre-focus controller run was interrupted and remains separate. Both exact logs are retained losslessly as gzip archives, with hashes in carmim-delivery.json. Independent specification/quality reviews and scoped actual-focus re-review approved; see carmim-review.md.

The local browser proof uses a fresh 217,755,648-byte SQLite online backup from production. It passed 205 lifecycle/responsive/accessibility-fallback checks and 17 computed-colour groups in light/dark mode, preserving all 20 non-CMS table fingerprints. Measured small-text samples are at least 5.54:1; the actual focused outline is 8.08:1 light and 9.93:1 dark. Carmim replaces petrol highlights, while semantic states and the two chart lines remain explicit. Plumb-bob path geometry is unchanged.

Installed public browser smoke passed 90 checks across cae.joao.date and joao.date/dados at 320/390/768/1440: populated home, carmim/paper, no overflow, summary without scripts/admin toolkit, exact CSS/favicon/chart-bundle bytes, key routes/CSV, unknown-series 404, preserved SVG and exact first/last keyboard readout on the dual-axis comparison. There are no public page/CSP errors or off-site asset requests. Ten occurrences of the existing shared-edge Permissions-Policy vr warning remain explicitly recorded; this is not a warning-free public-console claim.

The read-only trusted-proxy/state probe passed 33 checks: installed editor, preview and operational sections, protected local assets, no-store and script policy, anonymous/forged/non-owner refusal and cross-origin POST refusal without writing. The actual public Admin URL still challenges through Authelia. This is technical internal-proxy acceptance, not a human owner login or human screen-reader pass. The CMS mutation cycle ran only on the isolated copy; no live trial content needed cleanup.

Two initial installed-helper failures are retained: carmim-production-initial.json compared tuple migration rows with a JSON list; carmim-production-preview-check.json incorrectly rejected the already-existing preview style-src policy as an executable-script exception. The schema/migrations were confirmed equal in their serialized receipts, the preview policy was confirmed unchanged from baseline, and only the checker was corrected. No application fix or second recreation was needed.

The screenshot review's estimated public provisional-badge/placeholder contrast was checked against actual computed values: 5.93:1 and 4.61:1 on white. The second header row is present in the earlier accepted screenshot too; no new layout change was made from that visual suggestion.

## Evidence and recovery

Machine receipts: carmim-ci.json, carmim-delivery.json, carmim-production-before.json, carmim-production-state.json and carmim-production/public-smoke.json. Final local screens/contrast: carmim-browser/. Installed screens: carmim-production/. The probe sources sit alongside these receipts.

Operator baseline and readbacks are on f0nix at /home/joao/prumo-operations/tabler-carmim-20261117T125839Z. Recovery code is 7a35f47. Previous web image sha256:5ae9cfbad41ebaaead7f065e4766ae3c72cd5827f67c359fe661bd7ffb781b5c is pinned as prumo:rollback-tabler-carmim-20261117T125839Z; previous Admin image sha256:3e8e3d44be23be110595121412e665b28e61754a20e1ef4af8b5b880e1e9bd41 as prumo-backoffice:rollback-tabler-carmim-20261117T125839Z. Follow the existing schema-unchanged dc-web release contract with the recorded old code/images, without moving remote main backwards or restoring the database. Preserve authored CMS history and new source collection.

Current editor: https://joao.date/dados/admin/cms/page/inicio. Roadmap: /home/joao/vaults/projects/prumo/roadmap-e-implementacao.md. Source rights/DGEG, lag classification, worker observation/SIGBUS, dated analyses, AI drafts and human assistive-technology acceptance are separate, unchanged workstreams.
