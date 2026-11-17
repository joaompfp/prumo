# Tabler interface and Prumo identity

## Status and scope

Installed on f0nix on 2026-11-17, runtime `14f845e`, after explicit owner release approval, main merge/push and hosted CI `44090471137`. The owner rejected the initial petrol-green colour direction: final highlights are carmim `#9b1c2e` on warm paper/charcoal, with the approved plumb-bob geometry intact. Only public web and backoffice were recreated; no schema, source-data, CMS-content, worker or shared-edge change. See [installed carmim release](carmim-installation.md) and the production receipts.

The backoffice now uses local Tabler 1.7.5 controls, cards, tables, badges and navigation, with the existing native forms/disclosures and progressive Admin script. The final palette is warm paper/charcoal/carmim with a restrained brass detail and labelled semantic state colours. The new mark is a hanging plumb bob. The public site shares the identity and refines its existing search, filters, navigation, buttons, chart interval links and surfaces; it does not load the admin toolkit. SVG summaries and the pinned ECharts analytical/detail bundle retain their current roles.

## Final carmim release evidence

`carmim-review.md` records the palette reviews and the actual-focus correction. `carmim-delivery.json`, `carmim-final-suite.log.gz`, `carmim-ci.json`, `carmim-browser/acceptance.json` and `carmim-browser/contrast.json` establish the final 2,688-test/205-browser-check/17-colour-group gate on runtime 14f845e. `carmim-interrupted-suite.log.gz` is deliberately interrupted pre-fix evidence, never a passing result. The final acceptance copy is a fresh 217,755,648-byte SQLite online backup from production, not the earlier copy below.

For the final acceptance, use the same QA server on port 8118 with `PRUMO_QA_DB=/home/joao/.hermes/cache/scratch/prumo-tabler-carmim/production-copy.sqlite3`, and set `PRUMO_QA_URL=http://127.0.0.1:8118` and `PRUMO_QA_OUT` to a separate output folder for the browser driver. `carmim_contrast.py` reads the actual loaded cascade and focused outline rather than trusting root tokens. `production_probe.py` and `public_production_smoke.py` are read-only installed checks; the former uses the existing internal proxy credential without printing it and is not a human login.

## Earlier implementation evidence (historical green-palette checkpoint)

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

## Installed release and recovery

The owner-authorized release used the exact pushed main SHA, a clean f0nix checkout and the existing dc-web aliases. Previous images were pinned before building. Only these services were recreated:

```bash
bash -lic 'dc-web-up prumo'
bash -lic 'dc-web-up prumo-backoffice'
```

Schema 0019, authored CMS content/history, worker identity/image/start/restarts and the pre-existing infrastructure edits were read back unchanged. No shared-edge restart or credential provisioning ran. Recovery uses old code 7a35f47 and the two rollback-tabler-carmim-20261117T125839Z image tags through the documented aliases. Do not move remote main backwards, restore the database or erase authored history for this presentation-only rollback. Full installed receipt: carmim-installation.md.
