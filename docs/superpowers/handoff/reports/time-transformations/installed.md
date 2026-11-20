# Installed notebook time alignment and transformations

Installed on 2026-11-20 at 18:15 UTC after the owner's explicit commit, push, merge and deployment authorization. Runtime source: `76908372bdc60bfe17da7f6b26ea2f2dd818e32c`, pushed and read back on `main`. Subsequent report-only commits do not require rebuilding these images.

## Public result

Both `https://cae.joao.date` and `https://joao.date/dados` serve the new Caderno. Native A/S/Q/M/D overlays retain actual periods and missing cells. Annual harmonisation, base100 levels and percentage-point rate changes are explicit, reviewed analytical views, with original/base inputs and independent mathematical verification. The annual mean of monthly HICP year-on-year rates is qualified as different from official annual inflation. Native same-frequency charts and bounded UTC-day PT15M charts keep their existing contracts.

Public services were recreated without a schema migration, statistical-data edit, CMS publication, ownership change, ingestion restart or authentication/shared-edge change. The backoffice was included because its private static preview consumes the public renderer and templates.

## Release gates and receipts

Hosted CI [44789496972](https://github.com/joaompfp/prumo/actions/runs/44789496972) passed on the exact installed runtime SHA: 3,075 passed, 19 skipped, seven live deselected, three warnings, 458.70 seconds. Both lint and test jobs succeeded. `production/ci.json` and `production/ci-44789496972.log.gz` preserve the result.

The final local full offline run at `b17901f` passed 3,092 tests, seven deselected, three warnings in 1,732.26 seconds. It predates the caption/methodology changes in `7690837` and is not described as a new full-suite run of that later commit. A clean detached checkout of the committed release passed 287 focused tests with module paths resolved inside that checkout; ruff passed. Preserve those scopes separately from exact-main CI.

The real-copy acceptance passed 110 matrix cells, 2,605 matrix assertions and 223 functional checks. All 23 table fingerprints and the schema of the isolated copy were unchanged. Its receipts, original failures and screenshots remain in this report directory. Independent specification and quality correction loops are documented in [README](README.md); human screen-reader acceptance remains separate.

`production/acceptance.json` records 115 passing installed checks across both public prefixes at 390 and 1440 pixels, covering native/annual/base100/pp views, exact first/last keyboard tooltips and persistent readout, full table lengths, units/caveat, horizontal overflow, methodology, unknown series, actual compiled bytes and public Authelia challenge. There were no application/CSP errors or off-origin requests. Sixteen instances of the existing shared-edge `vr` Permissions-Policy warning remain; the shared edge was not changed.

The keyboard-test screenshots retain their active tooltip. Separate `installed-joao-*-neutral.png` captures were taken after a real pointer enter/leave dismissed that transient overlay. Mobile inspection then confirmed complete axes, distinct series and no horizontal clipping; metadata below the screenshot edge is ordinary vertical scrolling. The payload confirms the correct spaces in the complete series titles. These neutral captures supplement rather than overwrite the keyboard evidence.

The decoded installed bundle is 510,109 bytes, SHA256 `5ec098d90cb667f8f2486828a18274861e52a782a48319d457c0baf6e8eaec4b`, matching the pinned manifest. Actual gzip response bodies were 180,999 bytes through `cae.joao.date` and 180,908 through `joao.date/dados`, not local compression estimates.

`production/post-install.json` records 33 passing technical/state/Admin checks; `production/preview.json` records ten private static-preview checks, all true. This verifies the technical access boundary and preview, not a human login/publication through the owner's account.

## Installed service identity and preservation

Public image `3ecad22a1e437138a889f8bc9e69353f4981503a48fc3caf42100394ec47f051`, container `cb06e4c55709`, started at `2026-11-20T18:15:03.568296677Z`.

Backoffice image `6e14cef109d0c9002dbc24b758a4985b47831d07ef25c45e3ce81d39b445deb2`, container `9f92329d94fe`, started at `2026-11-20T18:15:05.217957821Z`.

Both readers were healthy with zero restarts. Each actual image equals its new runtime tag and differs from the retained rollback image. Full identities are in `production/activated-images.json`.

The complete worker baseline is unchanged: container `3921475705a35df28b81a7d381e4d388918616c681607a116ac9df69ad334e4b`, image `ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3`, started at `2026-11-17T01:45:15.558866311Z`, zero restarts. Schema, migrations through `0019_statistics_cms`, all CMS document/history/event fingerprints and the pre-existing infrastructure diff match the immediate pre-activation receipt. SQLite quick_check is `ok`, with no foreign-key violations. A moving ingestion database is not claimed byte-identical.

## Activation and recovery

Prebuild used an approved-SHA detached worktree and a build-context-only override through the established `dc-web` alias. It verified that the still-running checkout, all services, schema and CMS stayed unchanged. Activation required exact-main CI success and rollback tags equal to the still-running images. Only the public bind-mounted reader was stopped before advancing its checkout; recreation used the normal `dc-web-up` aliases, never the temporary build override.

Durable operator receipts and build logs: `f0nix:/home/joao/prumo-operations/time-transformations-release-20261120`. The actual executed scripts are [prebuild.sh](prebuild.sh) and [activate.sh](activate.sh). They are dated, single-release procedures, not instructions to rerun against an occupied receipt directory.

Recovery checkout: `913eb2fff75dbaf3447b58091f69c2bb43e96fda`. Retained tags are `prumo:rollback-time-transformations-20261120` and `prumo-backoffice:rollback-time-transformations-20261120`, respectively images `4c3def73053300afddf39cf62679ab9448873afd327d45c3759fa35af2465eb8` and `2cd23e48e0e7030f94ef5268ce7cc7be75a0e8299738ce50f7eacee06e8a97d5`.

If a verified reader regression requires rollback, preserve the current evidence, stop the affected bind-mounted public reader before restoring its runtime checkout, then restore only the readers through the existing deployment contract. Do not restore an old database, run bootstrap or restart ingestion for this schema-unchanged UI release. Never activate with the prebuild override. The existing [operations runbook](../../../../data/operations.md) remains authoritative.

## Resume point

Phase T of the analytical-workspace roadmap is installed. Phase B's structured point reading/generalisation to other analytical pages is still future, followed by discovery, multiseries CMS authoring and dated/approved-AI drafts. Human screen-reader acceptance, rights/DGEG, old periods, operational actions and worker observation remain separate open scopes.

Owner roadmap: `/home/joao/vaults/projects/prumo/roadmap-e-implementacao.md`. Technical resume point: `../../HANDOFF.md`.
