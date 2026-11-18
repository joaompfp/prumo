# Installed: notebook charts and public navigation

Owner authorized merge and installation. Main was fast-forwarded and pushed to
`361eca76d0fb2536c130d9f5315d8251cec07b96`, independently read back from origin.
Latest runtime change is `7baa127`; later candidate commits concern tests and evidence.
Installed on f0nix on 2026-11-18 at 07:51 UTC. Subsequent documentation commits do not
require recreating these images.

## Actual installed services

| Service | Image | StartedAt UTC | Restarts |
|---|---|---|---|
| prumo | `660146a830bd2a786f1d718f4fd7f43f1bc1b05c45e9a6a8a9750cf39bd04b79` | 2026-11-18T07:51:38.316298061Z | 0 |
| prumo-backoffice | `09da694b39eefb63948571346506bafabc0e62de4226755966a041c79a7739ec` | 2026-11-18T07:51:40.018905927Z | 0 |
| prumo-ingest | `ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3` | 2026-11-17T01:45:15.558866311Z | 0 |

Web and backoffice are healthy. Their actual running image ids equal their rebuilt
runtime tags and differ from their rollback images. The worker's complete id, image,
start, restart and running-state baseline matches exactly. Schema/migrations and CMS
content/history/audit hashes are unchanged, quick_check is ok and foreign_key_check
returns no rows. The authored homepage remains published as before. No live CMS content
was created, edited or republished by this release.

## Public delivery and acceptance

The Caderno can draw an explicit subset of up to six of its twelve selected indicators,
with native shared scales or deliberately selected dual scales for two series. Frequency,
unit and finite common-period checks, exact values/table/provenance, shareable window/day
and explicit empty/off states are installed. Selection is address-based, not a CMS write.
Grouped app-like navigation, joined aligned search, native mobile menu, Carmim, local fonts
and the existing enlarged type are installed on both public prefixes. CMS previews carry
the same new public header but remain private and static. The CMS chart editor itself
still authors one or two series, not arbitrary N-series documents.

- https://joao.date/dados/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT
- https://cae.joao.date/caderno
- https://joao.date/dados/admin/cms/page/inicio

Installed public browser proof: 2,117 passed checks at 320/390/768/900/901/1024/1440 on
both actual public prefixes. This includes one/two/five/six series, seven requiring an
explicit subset, mixed-scale refusal, deliberate dual axes, E-REDES day, complete tables,
native GET subset/empty/share forms, exact keyboard/pointer/touch, menu disclosure geometry,
SVG/no-JavaScript/blocked-bundle/print and actual accessibility-tree names. Exact served
CSS/font/favicon/bundle bytes match the approved source. No page/CSP errors or off-origin
public requests. A separate neutral-state capture proves the chart tooltip hides on
pointerleave on both mounts at 390/1440; active-slider screenshots are not neutral states.

Thirty-three read-only state/trusted-proxy/Admin checks passed, including owner/proxy
restrictions, cross-origin refusal and unchanged worker/schema/CMS/infra edits. Ten
additional preview checks passed for shared navigation, public data links, Admin-prefixed
assets and strict no-executable-script CSP. Anonymous public Admin still challenges through
Authelia. These technical checks do not impersonate a human owner login or screen-reader
acceptance.

Actual edge chart transfer: gzip, 180,001 wire-body bytes, 506,637 decoded bytes, SHA256
`70a45c776a6bf397f75ddd0e22807ec837a7ba3a4b0545b61d2ff79c9a4e3d0a`.
The unchanged shared-edge Permissions-Policy vr warning appeared 150 times; there are no
other console warnings in the accepted run. The public edge overrides X-Robots-Tag with
`none,noarchive,nosnippet,notranslate,noimageindex,`; noindex is preserved but follow is not
the effective HTTP policy. Direct app headers and HTML meta remain `noindex, follow`.
Shared-edge policy was not modified to change these existing behaviors.

## Verification scope

Exact-main hosted CI `44260267298` PASSED before activation: 2,826 passed, 9 skipped,
7 network deselected, 3 warnings, 694.45 seconds; lint also passed. `ci.json` and the
lossless CI log retain the exact head and conclusions. The earlier complete local selected
population was 2,835 passed with no selected skips; its receipts remain in the development
report and are not a newly rerun complete local suite. Fresh release acceptance from the
detached committed checkout passed 95 affected tests with correct local provider imports;
ruff is clean.

Independent activation-script review requested explicit rollback-to-live image matching
and actual-new-image checks, both implemented and exercised. The scoped reader scripts
include one-series keyboard coverage. Earlier runtime specification/quality reviews remain
in the development report. A prebuild check initially required that the merged stack have
only two services; inspection proved unrelated root services remain in the manifest while
only the explicitly selected readers use the detached context and are built. That checker
was corrected, without changing the runtime manifest. The first public receipt failed an
exact robots-header assertion; the existing edge override above explains the difference.
The accepted checker requires a noindex/none HTTP directive AND the exact app meta policy.
The failing public receipt is retained under production-initial. Runtime code was not
changed for either checker correction.

## Activation, infrastructure and recovery

Prebuild used the detached approved-main checkout and prebuild.yml through `dc-web` with
explicit reader-only build targets while the old checkout/containers remained unchanged.
Only the bind-mounted public reader was briefly stopped before fast-forwarding its clean
checkout, then normal `dc-web-up prumo` and `dc-web-up prumo-backoffice` recreated the readers.
The temporary build-only override was NEVER used for up. No migration, worker restart,
source-data write, ownership repair, credentials, Authelia or Traefik operation ran.

Rollback code is `24a3dc7ed824933d4bd1130662b62b9908c9783b`. Pinned images, read back before
and after activation:

- `prumo:rollback-notebook-navigation-20261118T074000Z` = `9720261db70b7771f0761a853db569022ec4b3d1517a6ff602667118723ae3f4`
- `prumo-backoffice:rollback-notebook-navigation-20261118T074000Z` = `69f85bab26b387b876f7fe14a52e45404c93895433a2802dc0f72b8d85b4ddc6`

Use the normal stack aliases and a clean old-code deployment context for a UI rollback.
Stop only the bind-mounted public reader before changing its checkout; do not move remote
main backwards. Recreate web and backoffice only. Preserve database/history/worker; no DB
restore is needed for this schema-unchanged release. Old code does not implement the new
Caderno chart options. Full operator receipts remain at
`f0nix:/home/joao/prumo-operations/notebook-navigation-release-20261118T074000Z`.
Infrastructure commit `6112479` records only the installed application submodule pointer
on f0nix; pre-existing encrypted-environment and backoffice-include edits are preserved.
That host-local infrastructure commit was not pushed as a separate infrastructure release.

Human screen-reader acceptance, source rights/DGEG, lag classification, operational write
actions and elapsed worker observation remain outside this release. Future multiseries CMS,
dated analysis snapshots and human-approved AI draft commentary are not started here.
