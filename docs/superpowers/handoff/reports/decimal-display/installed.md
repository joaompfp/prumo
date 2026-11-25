# Installed numeric-display correction

Owner-authorized merge, push and installation on 2026-11-25. Exact main/release: `1ad4f16d53adc9bcb59768368aefbf8e1090bf66`; runtime implementation `082c4d2`, test follow-up `4c8cb3b`. The former installed checkout was `50ede366131fc355f4c8f43f0e31a3bfd2f3bf79`. A later report-only commit does not replace this tested runtime revision or require another rollout.

## Live presentation

Normal statistical reader values use at most two decimal places, Decimal HALF_UP, Portuguese separators and no unnecessary trailing zeros. Tiny nonzero readings use honest bounds. Cards, catalogue, tables, chart SVG/readout/tooltips and static CMS previews share the formatter. The reported examples now display `2,36` and `80,79`, without shrinking the approved reading scale.

- https://joao.date/dados/series/worldbank.trade_balance_pct_gdp.DE
- https://joao.date/dados/series/worldbank.life_expectancy.DE

Original observation tokens, calculations, coordinate values and CSV data retain their precision. Explicit original-value evidence remains available for revisions/cross-checks/calculation inputs. The CMS remains the authoring boundary for editorial comparisons; public pages still show only published compositions. No content was created, edited or published during this release.

## Verification scopes

Hosted CI [45658810915](https://github.com/joaompfp/prumo/actions/runs/45658810915) passed on the exact release SHA: 3,286 passed, 29 skipped, seven live deselected and three pytest warnings, in 434.42 seconds. Both lint and test jobs succeeded. The hosted environment's optional browser skips do not replace the installed browser checks. Node action deprecation/post-cleanup notices remain in the archived CI log.

Fresh detached committed checkout: 155 affected formatter/evidence/model/calendar/annual-analysis/legibility/typography/boundary tests passed in 45.731 seconds, with no skipped tests. Imported app/ingest/presentation modules resolved inside that checkout; broader ruff passed. Development's earlier incomplete whole-suite run and its targeted repair retain their original scopes in `README.md` and `gates.json`; this release CI is a separate fresh all-green run.

Installed public acceptance: 244 checks across 16 populated original-example/address/viewport combinations, plus home/catalogue/Caderno/calculated/CMS-comparison routes, no-JavaScript fallback, exact CSS and anonymous Authelia challenge. Both public addresses were tested at 320/390/768/1440 CSS pixels. Headline, table and payload display values are bounded; keyboard first/last readout and tooltip work; original numerical coordinates and raw CSV tokens are exact. No application errors or off-origin browser requests. The 26 pre-existing shared-edge Permissions-Policy `vr` warnings remain outside this release.

Read-only production acceptance also passed 54 real comparison-editor/static-preview checks, 45 precision/private-CSP checks across all nine real previews, 36 state/access checks and 13 homepage-preview checks. A separate 39-check reconciliation proved the original coordinates identical for all eight route/address cases and all six CSV bodies identical apart from their documented request-time export-clock record, including original hashes reconstructed with the independently bounded before/after timestamps.

Neutral value-card captures from real production are in `release/worldbank.trade_balance_pct_gdp.DE-1440.png` and `release/worldbank.life_expectancy.DE-390.png`; companion widths/examples are retained. Visual inspection found neither broken digits nor clipped units. Human screen-reader acceptance remains a separate open gate.

## Installed service and data state

Only `prumo` and `prumo-backoffice` were rebuilt/recreated, using the established `dc-web-*` aliases. The detached-context prebuild preserved the old live checkout and all service baselines. Immediately before activation, both pinned recovery images still matched the running readers. Only the bind-mounted public reader was stopped before fast-forwarding its checkout; the context-only build override was never used for activation. The new running images match their rebuilt runtime tags and differ from recovery.

Public web: container `2c95af762ac75231a8713164eff95395396e203aff66919bd6dab72f235c1036`, actual image `sha256:852643e970e63e265997bcb7eb55bba569e607bd8d33c1fcb18d5a6e6d8b3dbd`, StartedAt `2026-11-25T17:02:32.761509093Z`.

Backoffice: container `f236f75469604347920041eb75de8605c8a0e26f92313998092cf63ea7875441`, actual image `sha256:db6dbf97c2ed482b2570bebd31ed156273532fe7d75c2aefa532e799f4e8a299`, StartedAt `2026-11-25T17:02:34.430437655Z`.

Both are healthy, zero restarts. Complete worker baseline unchanged: container `fd1f7b572bd8f355de68f3ea21e19eed2d3f81cb45b168c111cb1bb2c343d5e0`, image `sha256:8679a19d535a450343c5bd130104c58a466dddb095957cf610e48684cfd28af9`, StartedAt `2026-11-23T08:32:43.627785908Z`, zero restarts. No migration, worker restart, source refresh, source-data/CMS write, ownership/rights, authentication or shared-edge change ran.

Immediate pre/post-activation and post-acceptance snapshots have identical schema/migration and CMS document/revision/event fingerprints, including the authored homepage. Quick integrity is ok; no foreign-key violations. Unrelated tracked infrastructure diffs were unchanged during prebuild, activation and the immediate acceptance. Source ingestion stays active, so this is not a frozen whole-production-database hash assertion.

Initial reader observation completed at 2026-11-25 17:17:34 UTC after 900.031338 seconds, with 29 sampled baselines unchanged and both readers healthy/zero restarts. The final 36-check state/access probe passed again, with original schema/migration/CMS fingerprints and worker baseline preserved. This presentation-release observation does not close the separate historical worker-cause/24-hour register.

## Retained checker failures

The first browser checker assumed every plotted primary-series period must be in its detail table. The existing source-detail contract deliberately shows the latest 60 of 65 life-expectancy periods and prints that limit; authored comparisons have a different complete-table contract. The corrected check verifies the declared primary-table cap plus bounded table values. No application or table-population code changed in response.

The first export comparison hashed the entire CSV, including its dynamic `Exportado a` clock, and therefore failed despite identical geometry, lengths and numerical tokens. Both failed raw receipts are retained. The supplemental reconciliation changes only that single verified footer clock, requires an exact match to each previously recorded raw SHA-256 and proves every other byte identical. No exported value or static metadata was excluded, normalized or rounded.

The final whole-infrastructure hash guard detected concurrent changes under `stacks/web/images/schedule-app` during the observation. The failed `post-observation-infra-drift` receipt is retained. Excluding only that newly changed subtree reconstructs the exact original full unrelated-diff SHA-256, proving that all previously present edits are intact. `final_probe.py` retains every original worker/schema/CMS/access assertion and changes only the explicitly reconciled unrelated-diff baseline. Its final 36 checks passed. The other application's files were not edited, restored, staged or committed by this release.

## Evidence and recovery

Operator directory: `f0nix:/home/joao/prumo-operations/decimal-display-release-20261125T165109Z`. Exact helpers and lossless receipts are under `release/`; `release/manifest.json` pins original and archive hashes. Dated activation helpers are evidence, not permission to rerun them blindly. Readers use canonical `mode=ro&readonly_shm=1` URIs.

Retained recovery code: `50ede366131fc355f4c8f43f0e31a3bfd2f3bf79`. Recovery images:

- `prumo:rollback-decimal-20261125T165109Z` = `sha256:05eb87f97c6885c867ca64f3aa9155f295ed17a65c765f5f07f478ef53fba726`.
- `prumo-backoffice:rollback-decimal-20261125T165109Z` = `sha256:f297f139b3d234434ea4d2862baa474895732d87484362c3635914078421420e`.

For a schema-compatible rollback, stop only the affected bind-mounted public reader before restoring its checkout, then restore these readers using the established aliases and retained images. Preserve database, authored CMS history, worker and shared edge. Do not restore the database for this UI release.

Numeric display is installed. Phase E dated analyses/human-approved AI, source rights/DGEG, old-period classification, operational actions and human accessibility acceptance remain separate; no new product phase was started during this release.
