# Installed four-significant-figure presentation

Main/runtime `63662ba6468464d8c17eceac405de1a620bd7986` was pushed, read back and installed on f0nix on 2026-11-25 at 20:09 UTC, continuing the owner-authorized UI correction/publication with the refined significant-figure rule. The previous installed checkout was `6b9307f893d5363927fecd9b4c103fecf3654165`. Later report-only commits do not replace the tested runtime or require another rollout.

## Live behavior

Normal statistical readings now show at most four significant figures, with Decimal HALF_UP, Portuguese separators and no redundant fractional zeros. The decimal-place count follows magnitude. Small nonzero values remain numeric rather than being replaced by a fixed centesimal bound; extreme magnitudes use compact scientific notation. Counts, dates, identifiers and operational audit evidence remain exact.

`2.35673648910157` displays as `2,357`; `80.7926829268293` as `80,79`; `0.0123456` as `0,01235`; and `12345` as `12 350`. Cards, catalogue, tables, SVG, interactive point readings and static CMS previews share the same formatter. No font or layout reduction was made.

Live examples:

- https://joao.date/dados/series/worldbank.trade_balance_pct_gdp.DE
- https://joao.date/dados/series/worldbank.life_expectancy.DE
- https://joao.date/dados/comparar/eletricidade-domestica
- https://joao.date/dados/metodologia#precisao

Publisher tokens, internal calculations, numerical domains/coordinates, source receipts and CSV data keep their full precision. Revision and calculation evidence retains original-value disclosures. Comparisons remain authored in the authenticated CMS; public pages display only the published revision. No live content was edited or published.

## Verification scopes

Exact-runtime hosted CI [45689882466](https://github.com/joaompfp/prumo/actions/runs/45689882466) passed 3,364 tests, with 29 skipped, seven live deselected and three warnings, in 738.80 seconds. Both test and lint jobs passed. The final clean committed checkout passed 255 affected tests and broader ruff, with actual imported modules confirmed inside that checkout. The earlier 1,009-pass/seven-failure development run predates the corrected expected text/golden assertions and is not presented as an all-green full run. Development proof and independent-review disposition are in [README.md](README.md).

Installed browser acceptance passed 255 checks across sixteen reported-example/address/viewport cases, plus home, catalogue, Caderno, authored comparisons, calculated detail, methodology, unchanged CSS and no-JavaScript SVG fallback. Both public addresses were tested at 320/390/768/1440 pixels. Keyboard first/last point reading and tooltip, four-significant-figure payload/table readings and exact source CSV tokens passed. No application errors or off-origin requests; 28 instances of the pre-existing shared-edge Permissions-Policy vr warning remain outside this change. Visual inspection confirmed the live `2,357 % do PIB` card is legible and unclipped on mobile. Human screen-reader acceptance remains separate.

Read-only installed Admin acceptance passed 54 checks of the nine actual editors, 45 numeric/static/private-CSP preview checks, 36 state/access checks and 13 homepage-preview checks. The before/after invariant collector covers ten exact route/address cases and proves the original coordinates unchanged. All six complete CSV bodies match except the single documented request-time export-clock line; raw bodies and hashes are retained. No statistical token or static export metadata is excluded from the comparison.

## Services and preserved state

Only public web and the static-preview backoffice were rebuilt/recreated through the established dc-web aliases. The mount-safe detached-context prebuild preserved the old live checkout and all service baselines. The rollback tags were verified against the actual running readers immediately before activation. Only the bind-mounted public reader was stopped before fast-forwarding its checkout; the build-only override was not used for activation.

Public web: container `51d50672cd5e0074a766362a5b7321f0c6a5c0f174402214de53bf723e60646e`, image `sha256:162f7ef7bbbedbea3c893230590cf0cb1dcaf553bd8f26443623a63e9d97f881`, StartedAt `2026-11-25T20:09:25.653255924Z`.

Backoffice: container `7433663b2e404d554cc40b6279808b59c8ffefd4fac4707e6a76229b03f0e79f`, image `sha256:eebc6d10a6781ffe9773a6307504b43bbfb4d9c4dbae85312c845aba7d463538`, StartedAt `2026-11-25T20:09:27.318994108Z`.

Both are healthy, zero restarts, and their actual images match the rebuilt runtime tags and differ from rollback. Full worker baseline unchanged: container `fd1f7b572bd8f355de68f3ea21e19eed2d3f81cb45b168c111cb1bb2c343d5e0`, image `sha256:8679a19d535a450343c5bd130104c58a466dddb095957cf610e48684cfd28af9`, StartedAt `2026-11-23T08:32:43.627785908Z`, zero restarts.

Immediate pre/post activation and post-browser schema/migration and CMS document/revision/event fingerprints match, including the authored homepage. Quick integrity is ok and there are no foreign-key violations. Unrelated tracked infrastructure edits are preserved. Scheduled source ingestion remains active, so no frozen whole-production-file claim is made. No migration, source refresh, live CMS write, licence/ownership, authentication or shared-edge change ran.

The initial reader observation completed at 2026-11-25 20:24:27 UTC after 900.036764 seconds, with 30 matching container/readiness samples and zero restarts. The final 36-check state/access probe passed again at 20:24:42 UTC; worker identity/image/start/restarts, schema/migrations, CMS/history and unrelated-infrastructure hashes still match. This interval does not close the separate historical worker-cause/24-hour register.

## Recovery and evidence

Operator directory: `f0nix:/home/joao/prumo-operations/significant-figures-release-20261125T195130Z`. Exact source/export checks are in [exact_invariants.py](exact_invariants.py); public browser checks are in [browser_check.py](browser_check.py). Release evidence is archived under `release/` with raw and lossless-archive hashes in its manifest.

Recovery code: `6b9307f893d5363927fecd9b4c103fecf3654165`. Reader images are retained as:

- `prumo:rollback-significant-20261125T195130Z` = `sha256:852643e970e63e265997bcb7eb55bba569e607bd8d33c1fcb18d5a6e6d8b3dbd`.
- `prumo-backoffice:rollback-significant-20261125T195130Z` = `sha256:db6dbf97c2ed482b2570bebd31ed156273532fe7d75c2aefa532e799f4e8a299`.

For a schema-compatible rollback, stop only the bind-mounted public reader before restoring its checkout, then restore the affected readers through the established aliases and pinned images. Preserve database, CMS history, worker and shared edge. Do not restore the database for a display-only release.

Phase E, source rights/DGEG, old-period classification, operational writes and human accessibility acceptance remain separate; no next product phase was started.
