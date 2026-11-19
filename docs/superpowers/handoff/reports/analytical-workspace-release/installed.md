# Installed: analytical notebook workspace

Owner explicitly authorized merge, commit, push and installation after the populated prototype checkpoint. Main was fast-forwarded to `913eb2fff75dbaf3447b58091f69c2bb43e96fda`, pushed and read back from origin. Runtime is `050d69e`; the rest of the approved analytical-workspace roadmap is not included in this installation.

Installed on f0nix on 2026-11-19 at 16:55 UTC. Only public web and the backoffice static-preview consumer were recreated. No migration, worker restart, source-data write, CMS publication/edit, ownership, credentials, Authelia or Traefik change ran. Human screen-reader acceptance remains open; this installation authorization is not a user study or acceptance of the future phases.

## Installed services and preservation

| Service | Actual image id | StartedAt UTC | Restarts |
|---|---|---|---|
| prumo | `4c3def73053300afddf39cf62679ab9448873afd327d45c3759fa35af2465eb8` | 2026-11-19T16:55:08.339212855Z | 0 |
| prumo-backoffice | `2cd23e48e0e7030f94ef5268ce7cc7be75a0e8299738ce50f7eacee06e8a97d5` | 2026-11-19T16:55:09.910355718Z | 0 |
| prumo-ingest | `ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3` | 2026-11-17T01:45:15.558866311Z | 0 |

Both readers are healthy, their actual container images match their rebuilt runtime tags and differ from retained rollback images. The complete worker id/image/start/restart/running baseline matches exactly. Schema/migrations and authored CMS document/revision/event row fingerprints match pre-activation. quick_check is ok and foreign_key_check returns zero rows. The authored homepage and history remain intact. Scheduled ingestion was not paused and is free to update its own source tables; this is not a frozen fingerprint claim for actively collected data.

## Delivered and measured

The Caderno places its plot first, with compact title/status and Acrescentar/Configurar beside the result. A fluid stage grows in width and height on large monitors; native settings are after the figure and opening them does not displace the plot. The common plotted period is distinct from each card's own latest period. Source/unit/retrieval metadata sits next to the chart, and search is before the cards. Statistical payload, exact display strings, full table, native GET state, twelve-card/six-series limits, deliberate two axes, UTC-day limits and SVG alternatives remain.

| Installed viewport | Canvas top | Canvas width x height |
|---|---|---|
| 390x844 | 573.41 | 354.00x264.00 |
| 1440x1000 | 326.66 | 1179.69x455.78 |
| 1920x1080 | 330.66 | 1386.72x535.77 |
| 3774x1870 | 330.66 | 2400.00x927.27 |

Actual first-view screenshots are neutral, with scrollY=0. The complete two-series plot and axes fit at 390x844, 1440x1000 and 1920x1080. Body remains 28.05px. Opening settings changes plot top by less than 1px in every tested viewport. The adjacent metadata/legend repetition and different global-header/workspace edges remain known phase B/C refinements, not newly completed work.

Try the installed page:

https://joao.date/dados/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT

https://cae.joao.date/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT

## Fresh verification and limits

Exact-main hosted CI [44569621926](https://github.com/joaompfp/prumo/actions/runs/44569621926) passed before activation: 2,847 passed, nine skipped, seven live tests deselected, three warnings, 391.80 seconds; lint passed. Raw hosted log is retained losslessly in receipts. Fresh controller checks from clean detached committed checkout `913eb2fff75dbaf3447b58091f69c2bb43e96fda` passed 67 notebook/workspace/typography/legibility/boundary tests plus 33 chart/settings tests, 100 in total. Actual imports were verified to originate in that checkout; broader ruff passed. Earlier development full-suite results retain their actual revisions in the prototype report and are not re-labelled as a fresh local full-suite run here.

Installed public browser acceptance: 459 checks passed across both real prefixes and eleven viewport widths from 320 to 3774px. It covers first-view geometry, local fonts/type, full tables, settings without plot displacement, native add/window state, explicit off/empty/incompatible cases, six sides, deliberate dual axes, exact first/interior/last pointer and touch readings, keyboard/live output, accessible named range, no-JavaScript/blocked-bundle/print SVG, public exports/routes, exact served asset bytes and Authelia challenge. No page/CSP errors or off-origin requests. The unchanged shared-edge vr Permissions-Policy warning appeared 44 times; no warning-free-public-console claim is made.

Thirty-three read-only installed state/Admin checks and ten private static-preview checks passed. Proxy/owner restrictions, direct/forged/non-owner refusal and cross-origin form refusal remain intact. The preview includes the same shell, public data links and Admin-prefixed local CSS while forbidding executable scripts. These internal technical checks do not impersonate a human login or human screen-reader test.

Actual installed chart transfer: gzip, 180,002 wire-body bytes, 506,637 decoded bytes, SHA256 `70a45c776a6bf397f75ddd0e22807ec837a7ba3a4b0545b61d2ff79c9a4e3d0a`. The compiled chart bundle is unchanged by this release.

## Activation and checker correction

Prebuild used a detached approved-main context and context-only dc-web override while the old checkout and all services remained unchanged. Activation stopped only the live-bind-mounted public reader, fast-forwarded its clean checkout and used the normal dc-web-up aliases for public web and backoffice. The temporary prebuild manifest was never used for up. The exact hosted run, SHA, branch and push event were checked first; pinned rollback tags matched the running old images immediately before the change.

The initial post-activation checker demanded equality of the OUTER OCI index to the prebuild index. It stopped after the healthy readers were recreated because BuildKit regenerated its attestation. No runtime fix or second recreation was performed. Both complete exporter logs are retained: platform runtime manifest AND executable config digests match exactly between prebuild and activation for each service. Only attestation and outer-index digests differ. `build-equivalence.json` enforces that comparison and separately proves actual container image equals its newly built tag and differs from rollback. The failed original activation log and the unsuccessful old-index inspection are not represented as application faults or hidden as a successful initial checker.

## Recovery and next boundary

Recovery checkout `361eca76d0fb2536c130d9f5315d8251cec07b96` is the actual previous installed checkout (runtime `7baa127`). Pinned tags, verified before and after activation:

prumo:rollback-analytical-workspace-20261119T164616Z = 660146a830bd2a786f1d718f4fd7f43f1bc1b05c45e9a6a8a9750cf39bd04b79

prumo-backoffice:rollback-analytical-workspace-20261119T164616Z = 09da694b39eefb63948571346506bafabc0e62de4226755966a041c79a7739ec

A UI rollback must restore the clean old-code checkout as well as the readers, since app/templates and static are live binds. Stop only public web before changing its checkout; use a detached recovery checkout without moving remote main backwards, then the normal dc-web-up prumo and dc-web-up prumo-backoffice aliases. Verify actual assets/images and worker baseline afterwards. Preserve the database, CMS history and worker; no DB restore is needed. The older installed notebook/navigation runbook documents the same mount-safe recovery contract.

Operator receipts: f0nix:/home/joao/prumo-operations/analytical-workspace-release-20261119T164616Z. Infrastructure commit `112a2c99b8af2dfc5f1c4346f8053d609425433c` records only the application submodule pointer on f0nix; unrelated encrypted-environment and include edits are unchanged. This host-local infrastructure branch was not pushed as an unrelated infrastructure release.

Next roadmap work is phase B structured point reading/shared analytical pages, followed by C discovery/navigation, D multiseries CMS authoring and E dated analyses/approved AI drafts. No next phase was started by this release. Rights/DGEG, lag classification, operational actions, worker elapsed observation and human accessibility acceptance remain separate.
