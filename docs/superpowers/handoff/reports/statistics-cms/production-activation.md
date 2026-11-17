# Production activation of Admin and statistics CMS

Runtime revision: f493045791af6ada2b37463079a679dd1779c3cf. Schema: 0019. The owner authorized the combined release, then renewed the expired Traefik restart approval. Application containers were installed at 01:45 UTC on 2026-11-17; the public Admin router became active at 01:58:12 UTC.

## Edge activation

The normal stack command `bash -lic 'dc-core restart traefik'` completed successfully. Traefik retained container 18d3fa7d2f83 and image 1363849f5ded, with StartedAt 2026-11-17T01:58:12.980334382Z. The API reports 54 enabled routers and no disabled routers, including prumo-admin@file at priority 60. Its middleware order remains sanitize, Authelia, secret injection, prefix stripping.

Anonymous requests to https://joao.date/dados/admin/ and /dados/admin/cms return 302 to the Authelia portal with the original destination preserved. The browser displayed the sign-in form. A second probe ran from f0nix with public DNS resolved through Cloudflare DoH and curl pinned to joao.date's public IPv4 address; it received the same 302 without sending traffic over the Tailscale destination. No session cookie or credential is included in this report.

The neighboring /dados/administration path returns the public app's 404. Both public /healthz routes return 200. The direct http://100.118.19.6:8089/ returns 401. The complete internal lock probe passed 17 checks: canonical proxy identity, missing/forged/non-owner/direct-port identity refusal, health minimality, exact-origin/CSRF rejection, prefixed forms and security headers. This is not a human Authelia owner login.

## Technical publication proof

The trusted internal-proxy trial exercised the live service, not an isolated database. It created a two-axis chart and a page with text/card/chart blocks. Public readbacks passed on cae.joao.date and joao.date/dados. A later private draft did not change published content; an obsolete form received 409; restoring history created a draft without replacing the public revision. The resumed workflow passed 28 checks.

The initial scratch probe incorrectly asserted that the static preview contained no script elements at all. Its only script element was non-executable application/json data, with no src. The deployed preview correctly suppressed executable chart JavaScript and retained the SVG. The assertion was corrected in the release helper, not in application code, and the technical workflow continued on the same trial documents.

Final exact database readback:

| Kind | Slug | Version | Published revision |
|---|---|---|---|
| chart | ensaio-grafico-20261117 | 3 | NULL |
| page | ensaio-instalacao-20261117 | 6 | NULL |

Both public document addresses return 404 on both prefixes and the trial page is absent from /paginas. Immutable history remains, with 9 cms_event rows. No trial content remains published. PRAGMA quick_check is ok and foreign_key_check returns no violations.

## Public chart and transfer smoke test

The live /dados/comparar/credito-e-taxa page creates one ECharts canvas. Changing the range control with ArrowLeft updated the exact live readout to October 2009: Euribor 1,2426 %, credit 108 088,2 million euros. There was no horizontal document overflow and no external script origin. This smoke test does not repeat the full pre-release pointer/touch/resolution matrix. The browser backend does not expose console capture, so a clean live console is not claimed.

The installed local asset /dados/static/js/prumo-charts.min.js?v=d02fbfaa8b5a returned 200, Content-Encoding gzip and 179,641 compressed wire-body bytes. This is a live HTTP response measurement, distinct from the build's local gzip measurement.

## Container continuity and logs

The restart did not recreate or restart any Prumo container:

| Container | Image prefix | StartedAt UTC | Restarts |
|---|---|---|---|
| prumo-ingest | ff50b981e4cd | 2026-11-17T01:45:15.558866311Z | 0 |
| prumo | ba41eb17c8f1 | 2026-11-17T01:45:23.938574495Z | 0 |
| prumo-backoffice | 4f22c6da5142 | 2026-11-17T01:45:25.017364041Z | 0 |

Traefik had no error-class log lines in the activation window. Authelia logged three read timeouts on GET / at 01:58:45, 02:00:45 and 02:02:46 UTC; the tested authorization redirects and browser login portal worked. Their cause was not investigated in this scoped release. Do not report all shared-service logs as error-free.

## Verification and remaining acceptance

Focused Admin/typography/container-contract tests: 109 passed, 1 warning in 18.21 seconds; full-scope ruff clean. The full application suite and hosted CI were run before release on f493045; they were not rerun for the Traefik restart. Later documentation-only commits do not change the installed runtime.

Owner login and publication through a real Authelia browser session remain for human acceptance. Human screen-reader acceptance also remains open. Technical publication through an internally supplied proxy identity is explicitly not either of those proofs. Source rights, DGEG, lag classification, SIGBUS monitoring and the fresh 24-hour worker observation remain separate.

Durable operator receipts and the pre0019 recovery database are under /home/joao/prumo-operations/cms-release-20261117T012653Z on the corresponding hosts. The local admin-lock.json, cms-live-workflow.json and public-asset-transfer.json contain technical checks without credentials. Rollback requires the documented c9a2e5f runtime and pre0019 database with all writers stopped; remove the public Admin route first.
