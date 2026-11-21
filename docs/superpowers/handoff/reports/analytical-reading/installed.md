# Installed phase B: shared analytical reading

Installed after the owner's authorization on f0nix on 2026-11-21 at 21:36 UTC. Release/main SHA: `53464477bbb34d511cafda9f2fdd48fb7462f908`; implementation through `4d6b4c6`. Subsequent report-only commits do not change the executable revision whose CI passed.

## Product boundary

Primary series, calculated series and CMS charts now prioritize the chart in the analytical working width. Point inspection uses a period and structured series/value rows, preserving exact server-formatted tokens, native periods, missing states and keyboard announcements. The native point selector has a 48px target. Native series interval/day/CSV actions remain reachable after the figure. SVG, complete tables, evidence, calculated caveats and print remain available.

The authenticated backoffice still authors the real comparisons: titles, series, axes, periods, transformations and publication. Public comparisons render only the published revision and expose no composition controls. The Caderno remains a separate exploration tool. This release did not create, edit, restore or publish live content.

Public example: https://joao.date/dados/comparar/taxas-juro-credito-depositos

Primary series: https://joao.date/dados/series/ine.hicp_yoy.PT

Actual CMS editor: https://joao.date/dados/admin/cms/chart/taxas-juro-credito-depositos

## Verification scopes

Exact-main hosted CI [44951525399](https://github.com/joaompfp/prumo/actions/runs/44951525399) passed: 3,193 passed, 29 skipped, seven live deselected, three warnings in 549.02 seconds. Ruff passed. The hosted environment skips optional browser tests; real-browser acceptance is recorded separately. Status is retained in `release/ci.json` and the exact raw job log in `release/ci.log.gz`.

A fresh detached committed checkout of `5346447` passed 84 focused analytical-route, point/calendar/group interaction, CMS-boundary, typography and licensed-asset tests in 105.70 seconds. Application, CMS, persistence and presentation imports were verified to resolve inside that checkout; broader ruff passed. The prior 3,222-test local full suite retains its earlier environment and runtime scope and is not relabelled as a fresh run here.

Installed public acceptance passed 1,392 assertions across 104 populated route/width/address cases. The matrix includes all nine real comparisons, primary monthly and 15-minute series, a calculated series and mixed-frequency Caderno at 320/390/1440/1920 on both addresses. It checks structured values at both endpoints, native controls, absence of public authoring, full comparison tables, functional type, useful plot geometry and selected first views. Additional installed checks cover no-JavaScript, blocked-bundle and print alternatives, actual linked bundle/inspector CSS bytes, CSV, health, 404 and the anonymous Authelia challenge. There were no application errors or off-origin requests. The 112 instances of the pre-existing shared-edge Permissions-Policy `vr` warning remain outside this UI release.

Read-only Admin acceptance passed 54 assertions over the nine exact populated editors and a static analytical preview. Six series/axis slots, prefix-correct private-save/deliberate-publish actions, strict preview script policy, actual SVG and Admin-prefixed CSS were verified. The state/access checker passed 33 checks and the separate static homepage preview passed ten. These technical proxy checks do not establish a new human Authelia login or human screen-reader acceptance.

The initial Admin checker expected the primary-series `detail-workspace` class on a CMS page, whose correct class is `authored-workspace`. `release/admin-initial.json` retains the failure. The repaired checker parses the actual CMS class set; the application was not changed or recreated to address this checker error. Two prebuild log-display commands had quoting/syntax errors after the successful build; the actual persisted prebuild checks were then read back and independently confirmed.

Neutral installed captures are `release/series-390.png`, `release/series-1440.png`, `release/taxas-juro-credito-depositos-390.png` and `release/taxas-juro-credito-depositos-1440.png`. They were captured at scrollY zero after fonts loaded and actual pointer entry/leave hid the tooltip. Visual inspection found no blocking clipping. A viewport crop does not imply a missing below-fold legend.

## Actual installed state

Public web: container `c5ceb92dd95aa78bdb2b0f4e17c3aa6e5aaadc84d3e45e16190dea19c203b9f7`, actual image `sha256:6022e973b69044e03d645ef56d6fd7df4577eddbb63ef9bce51ef1e2c52b031e`, StartedAt `2026-11-21T21:36:41.769711391Z`.

Backoffice: container `1cd948bdcabb6a070d99c6ee9a5c059d1fd0f20b898d9974963555a268e21576`, actual image `sha256:90cfbfaec6721b6c93944a45c3cbf9d3bdf80802906fbbe5990bc1f52de25d97`, StartedAt `2026-11-21T21:36:43.3708669Z`.

Both are healthy with zero restarts. Their actual images match the rebuilt runtime tags and differ from their pinned recovery images. Prebuilding used a detached approved-SHA worktree with a build-context-only override, while the bind-mounted live checkout and all services stayed unchanged. Activation stopped only the affected public reader for the checkout fast-forward, then recreated public web and backoffice through the normal aliases. The override was never used for activation.

The complete worker baseline is unchanged: container `3921475705a35df28b81a7d381e4d388918616c681607a116ac9df69ad334e4b`, image `sha256:ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3`, StartedAt `2026-11-21T15:04:10.860527167Z`, restart count three. These autonomous restarts preceded this release. The separate incident corrections on `pipeline-rebuild` through `68609ef` were deliberately excluded; historical cause and real observation remain open.

Immediate pre/post-activation and post-acceptance receipts show identical schema/migrations and CMS document/revision/event fingerprints, including the authored homepage. Database quick_check is ok and foreign-key violations are zero. Ingestion remains active, so a fixed live observation count or full-file hash is not the preservation claim. No migration, source-data/CMS write, licence, ownership, credential, Authelia or Traefik change ran. Existing unrelated infrastructure edits were preserved.

## Receipts and recovery

Operator directory: `f0nix:/home/joao/prumo-operations/analytical-reading-release-20261121T2122`. Exact executed helper copies and selected receipts are under `release/`; the manifest identifies the versioned population. These dated deployment scripts are evidence, not permission to repeat an activation blindly. The state probe uses a canonical URI with `mode=ro&readonly_shm=1`; do not substitute the older historical probe that lacks that reader-safety option.

Rollback checkout: `34ed8c008aa9cdbce23822f837eed9e51c09334e`. Retained image tags: `prumo:rollback-analytical-reading-20261121T2122` pins `11410e96aad1`; `prumo-backoffice:rollback-analytical-reading-20261121T2122` pins `85f02ae7566d`. Both were rechecked against the still-running images immediately before activation.

For a code-only rollback, stop only the bind-mounted public reader before restoring its checkout, then restore the affected readers through the established `dc-web`/`dc-web-up` aliases. Preserve the database, publications/history and ingestion. A schema restore or worker operation is not part of this rollback.

Phase B is installed. Phase C discovery/entry, phase E dated analyses/human-approved AI drafts, rights/DGEG, old-period classification, audited operational actions and worker-incident acceptance remain separate. Human screen-reader acceptance is still pending.
