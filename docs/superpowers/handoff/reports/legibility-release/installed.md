# Installed: larger type, Caderno and European comparisons

Installed on f0nix on 2026-11-17 after explicit owner release approval. Application checkout
and approved main revision: `9d122f90b9307b3a4a3848e5d7b99b92a9b27ca9`; latest runtime change
is `42c581f`. Later installation-documentation commits do not require recreating images.

## Active services

| Service | Image | StartedAt UTC | Restarts |
|---|---|---|---|
| prumo | `9720261db70b7771f0761a853db569022ec4b3d1517a6ff602667118723ae3f4` | 2026-11-17T23:54:20.670373527Z | 0 |
| prumo-backoffice | `69f85bab26b387b876f7fe14a52e45404c93895433a2802dc0f72b8d85b4ddc6` | 2026-11-17T23:54:22.191786981Z | 0 |
| prumo-ingest | `ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3` | 2026-11-17T01:45:15.558866311Z | 0 |

Only public web and backoffice were recreated; both are healthy. The entire worker
identity/image/start/restart baseline matches exactly. Schema/migrations and all three
CMS document/history/audit fingerprints match the immediate pre-activation baseline.
quick_check is ok and there are no foreign-key violations. The homepage remains the
operator's existing publication; this release did not publish or overwrite content.

## Delivery

Public body is 28.05px and Admin body 23.1px, a further ten percent above the previous
candidate. The measured functional-role floor is 1.65 times the old installed baseline.
Local Lato and TeX Gyre Schola, Carmim and the approved plumb-bob geometry are retained.
The Caderno and all curated country comparisons are now available under both prefixes.
Electricity compares PT/ES/FR/DE/IT in native EUR/kWh, the same household consumption band
2 500 to 4 999 kWh/year and taxes included; it is a historical semiannual mean, not a live
tariff. GDP per inhabitant uses current euros; debt uses percentage of GDP. No new
collection, aggregation, licence permission or multiseries CMS editor is implied.

- https://joao.date/dados/comparar/paises/eletricidade-domestica
- https://joao.date/dados/comparar/paises/pib-por-habitante
- https://joao.date/dados/comparar/paises/divida-publica
- https://joao.date/dados/caderno
- https://joao.date/dados/admin/cms/page/inicio

## Release evidence

The controller suite passed 2,785 tests, seven network tests deselected, three warnings;
ruff and JavaScript syntax are clean. Detached committed-checkout acceptance passed
130 affected tests with actual local imports/entrypoint/assets. Independent specification,
quality and follow-up reviews are approved. Hosted CI `44201658200` passed on exact main
revision `9d122f9` before activation; see `ci-44201658200.json`.

The final isolated production-copy proofs passed 783 CMS/legibility and 410 country checks,
with unchanged protected data and all read-only country-proof table fingerprints. They
cover the full editorial lifecycle only on the isolated copy, exact pointer/touch/keyboard,
print, no-JavaScript and blocked-bundle fallback, responsive geometry and loaded fonts.

Installed proof passed 217 public browser checks on both prefixes and four widths, plus
33 read-only trusted-proxy/Admin/state checks. Exact served CSS/font-sheet/favicon/bundle
bytes match the approved repository. Public body size, five-country values/full table,
prior two-axis comparison, Caderno selection, CSP,404 and Authelia challenge passed.
Anonymous, forged, wrong-secret and non-owner direct Admin requests are refused; cross-
origin form submission is refused without a write. Application logs have no error-class
lines. `pre-activation.json`, `post-install.json` and `production/public-smoke.json` retain
these exact checks rather than inferred success from checkout/container status alone.

The actual installed chart bundle transfer was gzip: 179,938 wire-body bytes for 506,637
uncompressed bytes, sha256 `70a45c776a6bf397f75ddd0e22807ec837a7ba3a4b0545b61d2ff79c9a4e3d0a`.
This is measured through the installed edge, separately from the 173,149-byte local Node
compression receipt. Public browsers reported 26 instances of the pre-existing shared-edge
Permissions-Policy vr warning, with zero page/CSP errors, unexpected warnings or off-origin
asset requests. No Traefik/Authelia change ran to silence that unrelated header warning.

Human screen-reader and owner Authelia-session acceptance remain separate from the technical
proxy tests. Rights/DGEG, data-lag classification, worker elapsed observation and future
multiseries CMS/dated analysis/AI draft work remain outside this release.

## Mount-safe activation and recovery

The public image has live app/static bind mounts. A detached approved-main worktree and
temporary build-context override allowed image prebuild while the installed checkout and
containers stayed old. Effective contexts were read back. After CI passed, only public web
was stopped, the clean live checkout fast-forwarded to the exact approved SHA, and normal
`dc-web-up prumo` then `dc-web-up prumo-backoffice` recreated the affected services. The
worker and shared edge were untouched. `activate.sh` is the exercised exact script; never
use the build-only override for up. All raw operator logs are retained losslessly in
`receipts/`, with uncompressed hashes in `installed-logs.json`.

Rollback: code `6f851d4`; pinned tags `prumo:rollback-legibility-20261117T224217Z` and
`prumo-backoffice:rollback-legibility-20261117T224217Z`, verified still retained after the
aliases' image cleanup. Old image ids are `47f3feb6cf3455ca6a8872ed832091b11423cbfbf3604ddcf99aef0a24fee1d9`
and `027cb9b3487d3c2fd846e8651e885b24fc12931afddbbe577a33019c89f4cf14`.
Use the documented stack aliases and a clean old-code deployment context; do not move
remote main backwards. Stop the bind-mounted public reader before changing its checkout.
Preserve data, migrations and CMS history; no DB restore or worker restart is needed.
Operator receipts: `f0nix:/home/joao/prumo-operations/legibility-release-20261117T224217Z`.
