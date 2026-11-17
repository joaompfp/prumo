# Tabler interface and Prumo identity

## Status and scope

Implemented on `pipeline-rebuild`, runtime `0162e7c0009a1da431a5ead44e604151bf8743b5`. Main remains `7a35f47`; this report does not authorize or claim a deployment. A read-only public favicon fetch still matched the installed baseline exactly during acceptance. No database migration, operational source change, access rule, shared-edge change or production mutation ran.

The backoffice now uses local Tabler 1.7.5 controls, cards, tables, badges and navigation, with the existing native forms/disclosures and progressive Admin script. The palette is paper/petrol green with a restrained brass detail and separate semantic danger colour. The new mark is a hanging plumb bob. The public site shares the identity and refines its existing search, filters, navigation, buttons, chart interval links and surfaces; it does not load the admin toolkit. SVG summaries and the pinned ECharts analytical/detail bundle retain their current roles.

## Evidence

- `admin-implementation.md`: implementer scope and initial 299-test result. Its intercepted vendor CSS was an interim probe, not final installed-asset acceptance.
- `spec-review.md`: independent compliance PASS. F1 closed by committing vendor/build/identity assets in `07a981c`. F2 closed by unconditional vendor HTTP assertion in `5f3e4e2`. F3 is accepted as intentional CSS-only public work: no public template changes are needed for the requested surfaces, table hover, filter/search controls and colours. Browser acceptance checks real rendered output.
- `quality-review.md`: initially not approved because Tabler's important utility overrode neutral badge text colour, reducing small-text contrast.
- `quality-rereview.md`: scoped approval after `0162e7c`; measured neutral-badge ratios 5.11:1 in light mode and 7.53:1 in dark mode. The selector-level regression and final browser composite measurements cover the fix.
- `browser/acceptance.json`: final 205-check browser receipt; all checks passed, zero page/CSP errors, zero warnings and no external requests. It includes the identical before/after fingerprints of all 20 non-CMS tables, quick integrity check and foreign-key results.
- `browser/*.png`: actual application captures in light/dark, at 390 and 1440 pixels, plus icon-size proof. The checks also exercise 320 and 768 pixels.

Human screen-reader acceptance remains separate. The browser receipt does not claim a real Authelia owner session. The controller full suite on runtime `0162e7c` completed with **2,682 passed, 7 deselected, 3 warnings in 1,286.74 seconds**. Ruff and Admin JavaScript syntax checks are clean. The exact raw full-suite log is preserved losslessly in `release-suite.log.gz`; `delivery.json` records its SHA-256 and the runtime revision. Earlier development runs were deliberately interrupted for final UI fixes and are not reported as passing suites.

## Reproduce the local toolkit

From the repository root:

```bash
.venv-ci/bin/python tools/ui/vendor_tabler.py
```

This reads only the exact named CSS member from the SHA-512-pinned npm archive and verifies the upstream MIT licence by SHA-256. The npm archive omits the licence, so the build fetches and byte-verifies it separately. There is no package-script execution or arbitrary archive extraction. The only CSS transformations are removal of a source-map reference and replacing the two upstream generated quote separators with ASCII hyphens. Original source-data receipts are not changed. Imports and nonembedded resource URLs fail the build.

The committed receipt is `static/vendor/tabler/1.7.5/manifest.json`. A second build into isolated scratch produced identical CSS, licence and manifest. Local CSS size: 683,684 bytes, 85,019 bytes with deterministic gzip. That is a local compression measurement, not an installed edge transfer claim. No Tabler/Bootstrap JavaScript or remote font is included.

## Reproduce application acceptance

The source copy used here is the existing production-derived `prumo-home-qa/acceptance3.sqlite3`, copied using SQLite's backup API into a new isolated `prumo-tabler/acceptance.sqlite3`. It is not a fresh live-production snapshot. A previously populated 17-block homepage and the real publisher values are retained; repeated acceptance runs create local CMS revisions/audit only.

```bash
export PRUMO_QA_DB=/home/joao/.hermes/cache/scratch/prumo-tabler/acceptance.sqlite3
.venv-ci/bin/python -m uvicorn qa_server:app \
  --app-dir docs/superpowers/handoff/reports/tabler-ui \
  --host 127.0.0.1 --port 8117
```

In another terminal, with the same `PRUMO_QA_DB`:

```bash
.venv-ci/bin/python docs/superpowers/handoff/reports/tabler-ui/browser_acceptance.py
```

The QA server refuses databases outside scratch. Browser acceptance exercises actual labelled save, private preview, publish, stale-publication refusal, unpublish, restore, republish, no-JavaScript save and blocked icon fonts; the original public values are read back. It also checks exact first/last chart values by keyboard, retained dual axes and SVG printing, labels, active location, reduced motion, local assets, CSP and source-table fingerprints. The regular suite additionally contains the existing pointer/touch chart-interaction regressions.

One intermediate capture helper used `.bo-nav`, a nonexistent selector, alongside the toolbar. It was corrected to require the actual seven `nav.nav` anchors and their geometry rather than accepting an empty set. Another intermediate contrast probe emitted a Canvas read-frequency diagnostic; the helper now requests the appropriate probe context. Neither correction changed application runtime or muted real errors.

## Future installation boundary

Owner release approval is still required. Only `prumo` and `prumo-backoffice` need rebuilding/recreation. The worker, schema 0019, authored homepage content, Authelia and Traefik are unchanged. Use the existing `docs/data/operations.md` and `docs/data/cms.md` release contract, a clean f0nix checkout at the exact approved remote SHA and the existing `dc-web-*` aliases. Preserve/pin the previous web and backoffice images before rebuilding.

After an approved merge/push and remote fast-forward, the service-specific operations are:

```bash
bash -lic 'dc-web-up prumo'
bash -lic 'dc-web-up prumo-backoffice'
```

Verify both public prefixes, local CSS/favicon hashes, strict Admin protection, a technical CMS operation with cleanup if authorized, logs and unchanged worker identity/image/StartedAt/restart count. No shared-edge restart or credential provisioning is part of this release. Rollback uses the earlier code and the pinned web/backoffice images; do not restore the database or erase authored CMS history for a presentation-only rollback.
