# Homepage CMS and interface: installed release

Runtime revision: b8421994f9d311714de8369a61c66d3ccdb6c1d0. The owner authorized installation of the populated homepage and the interface refinement. Main and the clean f0nix checkout already referenced this SHA at preflight; the release did not invent another merge. The existing main CI run 44055444383 passed on this exact revision: 2,657 passed, 9 skipped, 7 network tests deselected. Fresh local verification passed 92 focused tests, the full-scope ruff command and Admin JavaScript syntax validation.

## Installed scope

Public web was recreated at 2026-11-17T09:55:52.404401417Z, image 5ae9cfbad41ebaaead7f065e4766ae3c72cd5827f67c359fe661bd7ffb781b5c. Backoffice was recreated at 09:55:53.892237017Z, image 3e8e3d44be23be110595121412e665b28e61754a20e1ef4af8b5b880e1e9bd41. Both are healthy, with zero restarts. Builds and recreations used the documented dc-web aliases.

Worker 3921475705a35df28b81a7d381e4d388918616c681607a116ac9df69ad334e4b retains image ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3, StartedAt 2026-11-17T01:45:15.558866311Z and restart count zero. There was no schema migration, ownership change, worker restart or shared Authelia/Traefik operation. Schema remains 0019; next free migration 0020.

## Published content

Preflight found no reserved CMS home and initialization therefore did not overwrite an operator draft. After both readers were installed, the exact versioned scripts/init_home_content.py was sent on stdin to the new backoffice with the authorized preparation/publication reasons in cms.md. The write returned published and was independently read back:

- page/inicio, version 2, draft and published revision 6;
- 17 blocks: opening, highlights section, 12 indicator cards, themes, verification chain and institutions;
- creation event 10 at 09:57:20.977540 UTC and publication event 11 at 09:57:20.981536 UTC, actor joao;
- every one of the 20 non-CMS table fingerprints identical immediately before/after this publication;
- migrations unchanged, quick_check ok, no foreign-key violations.

The snapshot has 543,113 observations, 34,219 quarantine rows, 1,791 series and 6,665 served derived rows. These counts describe this scoped publication window, not a promise that normal future ingestion leaves the database unchanged. Runtime values, counts and dates remain live, not authored copies in the CMS body.

## Installed acceptance

The public Chromium smoke passed 113 checks across cae.joao.date and joao.date/dados at 320, 390, 768 and 1440 pixels. All 12 labels and exact displayed values match the pre-publication home; every existing section is present, there is one h1 and no horizontal page overflow. The summary stays script-free. Methodology, sources, comparisons and page index return 200; an unknown page returns 404. The reserved ordinary-page URL redirects permanently to the canonical home. The existing dual-axis comparison still creates its interactive canvas. No off-site public requests or unexpected page/console errors were observed.

The live backoffice passed 17 internal trusted-proxy checks: the populated editor renders, save/publish stay distinct, actions and local font/CSS/JS are prefix-correct, home and legacy editor entries redirect to the actual CMS editor, and missing/forged/non-owner requests are refused. Served asset hashes are in production-receipt.json. This is not a human login through Authelia. The public editor URL was separately opened in the browser and challenged through the real Authelia portal. Human owner editing/publication and screen-reader acceptance remain separate.

The initial smoke helper omitted HTTP 301 from its accepted redirect statuses; the installed application was correctly returning 301. A later blanket console assertion found the public Permissions-Policy header's unrecognized vr directive. Direct Uvicorn responses do not contain that header; public responses do. The final receipt retains all 10 occurrences separately as known shared-edge warnings and asserts the absence of other page/console failures. No shared policy was changed in this web/backoffice-only release, and a completely warning-free public console is not claimed.

## Evidence and recovery

Structured evidence is production-receipt.json. Durable operator receipts, captured home HTML, smoke scripts and responsive public screenshots are under /home/joao/prumo-operations/home-cms-ui-release-20261117T095414Z. Publication fingerprints and audit readback are also retained at the same absolute path on f0nix. The initial failed probe is preserved; no application code fix was needed during release.

The previous web and backoffice images are retained under prumo:rollback-home-cms-20261117T095414Z and prumo-backoffice:rollback-home-cms-20261117T095414Z. Their full hashes are in the receipt. The old runtime is f493045. Follow cms.md's schema-unchanged rollback: preserve all CMS revisions and source data; old public code ignores the new home and renders the legacy home, while old Admin cannot edit new block shapes. Do not restore a source-data snapshot for this content-format rollback.

The populated homepage is edited at https://joao.date/dados/admin/cms/page/inicio. Source rights, DGEG, lag classification, SIGBUS investigation, elapsed worker observation, dated analyses and AI drafts remain separate workstreams.
