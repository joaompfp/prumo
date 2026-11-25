# Installed phase C: discovery and entry

Installed on f0nix after the owner's explicit merge and installation approval on 2026-11-25 at 13:37 UTC. Release/main SHA: `72fa437b70a1d78e4f6a9d861f7c0ceafca55474`; reviewed executable implementation through `cd55507`. Runtime/build/test inputs match that reviewed candidate. Later report-only commits do not replace the runtime revision whose CI passed.

Public catalogue: https://joao.date/dados/pesquisa

Example task: https://joao.date/dados/pesquisa?q=desemprego+Portugal

## Installed scope

The native navigation emphasizes Explorar, Comparações and Caderno. The complete discovery catalogue provides truthful totals, pagination, conjunctive accent-insensitive terms and theme/geography/source/frequency filters. Query and filters submit together. Unknown addressed filters remain visibly unavailable. Search/theme results show exact values, native periods, units, sources and collection dates, with a single-series Criar caderno action. Existing CMS cards expose that same entry without changing their stored content or ordering.

Published comparisons are still authored in the authenticated CMS; the frontend displays only published revisions. The separate Caderno remains reader-configured exploration. This release did not create, edit, publish, restore or remove any live editorial document. The authored homepage's first-view composition remains an explicit operator decision, not an installation initializer.

Only public web and the static-preview Admin consumer were recreated. No migration, source-data write, worker operation, ownership/rights change, credential change or shared-edge/authentication operation ran. Carmim, approved plumb-bob, licensed local fonts and the functional reading scale are preserved.

## Verification scopes

Exact-release hosted CI [45623191922](https://github.com/joaompfp/prumo/actions/runs/45623191922) passed: 3,249 passed, 29 skipped, seven live deselected and three pytest warnings in 735.90 seconds. Ruff passed. The hosted environment skips optional browser tests; browser acceptance below is separate. `release/ci.json` and the lossless `release/ci.log.gz` retain the exact run. Upstream GitHub action Node deprecation and post-checkout cleanup warnings are recorded in that log; both jobs succeeded.

A fresh detached committed checkout of `72fa437` passed 168 affected discovery/navigation/CMS/routes/boundary/typography/asset tests in 131.93 seconds, with one warning. Imports resolved inside that checkout and broader app/ingest/presentation/backoffice/tests ruff passed. Development's earlier 3,278-test full local run and 2,148 isolated browser checks keep their original scope.

Installed public acceptance passed 1,380 assertions across 126 populated route/width/address cases and four complete search/series/notebook/add/share journeys, with and without JavaScript. Both public addresses were exercised at 320/390/768/900/901/1100/1101/1440/1920 CSS pixels. Expanded navigation, truthful page transitions, active query/filter state, unknown filters, home-card entries, exact endpoint inspection of all nine published comparisons, no public authoring controls, local stylesheet bytes, strict CSP, keyboard focus, print and anonymous Authelia challenge passed. No browser application errors or off-origin requests occurred. The 156 instances of the pre-existing shared-edge Permissions-Policy `vr` warning remain outside this UI release.

Read-only installed state/access checks passed 36 assertions; the nine real Admin editors/static analytical preview passed 54, and the homepage's private static preview passed 13. A supplemental pass checked 21 mobile-geometry/native-input/export assertions, including primary and calculated CSV on both public addresses. These technical proxy checks do not substitute for human Authelia-login or screen-reader acceptance.

Neutral installed captures are in `release/search-390.png`, `release/search-1440.png`, `release/theme-390.png` and `release/theme-1440.png`. Visual review found no desktop clipping. Two mobile screenshot claims were adjudicated against live geometry: the catalogue link ends at X=372 with the correct 18px right gutter, and the native single-line query input preserves the full value and scrolls to both ends. Its input/button heights are both 63.125px. No application change was made in response to those claims.

## Actual production state

Public web: container `3124e94cb805e93319d04a01992e77e06b1daf3cbaf0ff4f37830fee3242668c`, actual image `sha256:05eb87f97c6885c867ca64f3aa9155f295ed17a65c765f5f07f478ef53fba726`, StartedAt `2026-11-25T13:37:40.935791599Z`.

Backoffice: container `ef599926a51603d9a199fe0c379d32d5cdf6679c9a72a32185eaafe7b19033e7`, actual image `sha256:f297f139b3d234434ea4d2862baa474895732d87484362c3635914078421420e`, StartedAt `2026-11-25T13:37:42.644008219Z`.

Both are healthy with zero restarts; actual images match their rebuilt runtime tags and differ from the pinned recovery images. Detached-context prebuild preserved the old live checkout and all three services. Activation stopped only the affected public bind-mounted reader before advancing its clean checkout, then recreated web/Admin through the normal `dc-web-up` aliases. The context-only override was never used for activation.

The entire worker baseline is unchanged: container `fd1f7b572bd8f355de68f3ea21e19eed2d3f81cb45b168c111cb1bb2c343d5e0`, image `sha256:8679a19d535a450343c5bd130104c58a466dddb095957cf610e48684cfd28af9`, StartedAt `2026-11-23T08:32:43.627785908Z`, restart count zero. This release does not close the separate worker historical-cause/24-hour acceptance register.

Immediate pre/post-activation and post-browser snapshots show identical schema/migrations and CMS document/revision/event hashes, including the authored homepage: 12 documents, 15 revisions and 29 events. Quick integrity is ok, with zero foreign-key violations. Ingestion remains active; preservation is not asserted through a fixed full database hash or frozen observation count. All unrelated tracked infrastructure diffs were fingerprinted and preserved.

The initial reader observation completed at 2026-11-25 13:52:43 UTC, with minimum reader uptime 900.040981 seconds and 12 sampled identity/readiness checks. Both readers remained healthy with zero restarts and the worker baseline was identical. The subsequent full 36-check state/access probe passed again, including unchanged schema/CMS fingerprints, quick integrity ok, zero FK violations and no error-class reader log lines. See `release/observation.json` and `release/post-observation.json`. This 15-minute UI observation is separate from worker operational acceptance.

## Receipts and recovery

Operator directory: `f0nix:/home/joao/prumo-operations/discovery-release-20261125T1324`. Exact executed helpers and selected receipts are under `release/`; the raw archive manifest preserves original byte hashes. These dated helpers are evidence, not permission to repeat activation blindly. Readers use canonical `mode=ro&readonly_shm=1` URIs.

The first prebuild verifier requested the newly introduced discovery stylesheet from the OLD release and correctly stopped before any service change. Its failed snapshot/log are preserved. The corrected verifier distinguishes the missing pre-release asset from the mandatory installed asset. A later geometry-only checker confused the main element's border box with its padded content box; its failure is retained separately and the corrected content-gutter check passed. Neither issue required changing application code or repeating activation.

Rollback checkout: `1a0bf131b44daa235c02806f047ec1bbf63bcbe0`. Retained recovery tags `prumo:rollback-discovery-20261125T1324` and `prumo-backoffice:rollback-discovery-20261125T1324` pin actual previous images `f5c6c991` and `b303b4ac`, respectively. Both matched the still-running old images immediately before activation.

For schema-compatible rollback, stop only the bind-mounted public reader before restoring that checkout; restore affected readers through the established aliases and retained images. Preserve source data, CMS content/history, the worker and shared edge. A database restore is not part of this UI rollback.

Phase C discovery/navigation is installed. Further authored-home first-view composition, phase E dated analyses/human-approved AI drafts, source rights/DGEG, old-period classification, operational actions and human accessibility acceptance remain separate.
