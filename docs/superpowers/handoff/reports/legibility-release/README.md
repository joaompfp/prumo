# Legibility, Caderno and European comparisons release

## Scope and approval

The owner approved installation of the pending larger-type/Caderno and European-country
comparison candidate, with a further modest typography increase. The final runtime is
`42c581f`, following the initial ten-percent increment `3a88b1f`. Public body is 28.05px;
Admin root is 26.4px and body 23.1px. Carmim, the plumb-bob icon and local licensed
Lato/TeX Gyre Schola faces are preserved. Controls, metadata and fixed chart labels grow
with the reading roles. The narrow header, figure composition, SVG gutter, canvas unit
clearance and Portuguese heading hyphenation have been checked and corrected without
shrinking text or changing statistical tokens.

This combined branch also carries the stateless Caderno and the five-country electricity,
GDP per inhabitant and debt comparisons. It affects only `prumo` and `prumo-backoffice`.
It changes no schema, ingestion, registry, source rights, authored CMS document, credentials
or shared edge. The worker must retain its exact identity, image, start and restart count.
Existing CMS charts remain one-series/pairs; curated country pages are not an N-series CMS
editor. Human screen-reader acceptance remains separate.

## Development acceptance

The independent specification and quality reviews approved the increment. The scoped
follow-up review approved the final clipping corrections. Read `spec-review.md`,
`quality-review.md`, `typography-followup.md` and `followup-review.md`; earlier findings and
bundle hashes describe their own revisions, not the final runtime.

A consistent read-only-source online SQLite backup of production was verified and copied
into isolated scratch. Final browser proofs are `browser-cms-final/acceptance.json` and
`browser-countries-final/acceptance.json`, reduced in `development-summary.json`:

- 783 checks, 485 type samples, minimum 1.65 times the installed pre-legibility role size;
- 410 country-comparison checks across both mount shapes and four widths;
- exact pointer, touch and keyboard values, complete table/provenance, SVG fallback,
  print, no page overflow, local fonts, no successful-page errors or off-origin requests;
- complete private save/preview/publish/unpublish/history recovery on the isolated copy;
- all 20 protected data-table fingerprints unchanged by the CMS proof; all 23 tables
  unchanged by the read-only country comparison proof; quick_check ok and no FK errors.

The first CMS receipt (`browser-cms/acceptance.json`) retains a helper-only failure caused
by a relative screenshot output path. The absolute-path rerun passed. Intermediate
accepted receipts remain distinguishable from the final-runtime receipts. A temporary
independent report used forbidden punctuation; only its authored punctuation was corrected,
then all 18 typography checks passed. No original statistical receipt was modified.

The controller full offline suite PASSED: 2,785 passed, seven network tests deselected,
three warnings in 1,432.38 seconds. It launched at runtime `42c581f`; runtime, assets and
tests stayed byte-identical through the documentation checkout `9b3f280`. Ruff across
app/ingest/presentation/backoffice/tests and both JavaScript syntax checks are clean.
A detached committed checkout at `9b3f280` passed 130 affected tests and the actual
entrypoint, routes/assets and module-origin checks. Raw logs are archived losslessly
in `receipts/`, with uncompressed digests in `final-gates.json`. The exact branch remote
was read back after push. Hosted CI and installed behavior remain separate release gates.

## Reproduction

Run `online_snapshot.py` on f0nix through stdin with a fresh `--output` path and copy that
verified file into the approved local scratch root. It is an isolated acceptance snapshot,
not a backup service and never a source-data write. Refuse an existing destination.

```bash
PRUMO_QA_DB=/absolute/scratch/production-copy.sqlite3 \
 .venv-ci/bin/python -m uvicorn qa_server:app \
 --app-dir docs/superpowers/handoff/reports/legibility-release \
 --host 127.0.0.1 --port 8124 --workers 1
```

Use the existing legibility-notebook and european-comparisons `browser_acceptance.py`
helpers with `PRUMO_QA_URL`, `PRUMO_QA_DB` and an unused absolute `PRUMO_QA_OUT` beneath
this report tree. Those scripts require an isolated database and do not target production.
The CMS helper deliberately mutates only its scratch copy. The final installed read-only
smoke helper here uses `PRUMO_PROD_OUT` and never publishes content.

## Release and recovery contract

Pre-release code is `6f851d4`. Old web and Admin images are pinned with the tag
`rollback-legibility-20261117T224217Z`. Operator baseline, online acceptance snapshot and
subsequent installed receipts live at
`f0nix:/home/joao/prumo-operations/legibility-release-20261117T224217Z`.

Merge and push only after passed release gates. Inspect actual live mounts before changing
the f0nix checkout: this web container bind-mounts app/templates and static assets, so an
early fast-forward would alter the live page before the new Python image starts. The
prebuild therefore used a detached worktree at the exact approved remote main SHA, with a
temporary context-only override supplied to `dc-web -f ... build prumo prumo-backoffice`.
Filtered Compose output proved both build contexts; other stack services were not built
or recreated. Old images were pinned first. Keep the live checkout at its old revision
until activation, then briefly stop only public web, fast-forward the clean checkout to
the approved SHA and recreate public web then backoffice with their normal `dc-web-up`
aliases. The image rebuild is cached. Never run up with the temporary build manifest.
Never recreate `prumo-ingest` or change shared routing for this release. Commit only the
changed application gitlink in f0nix infrastructure, preserving pre-existing secrets/
compose edits. Read back exact remote refs.

For recovery, freeze editorial actions, rebuild old code from `6f851d4` in the deployment
context through the same aliases or recover the pinned image tags using the existing stack
procedure. Preserve source data, schema and authored history; no database restore is needed.
The restored older public site will simply omit Caderno/country routes and use its earlier
typography. Do not reset remote main backwards or restart the worker to downgrade this UI.

Installation is complete: see [installed.md](installed.md), the exact pre/post activation
receipts and `production/public-smoke.json`. Hosted CI passed on9d122f9 before activation;
217 installed public and33 Admin/state checks passed. Worker, CMS and schema fingerprints
match. Only web/backoffice changed; the human screen-reader gate remains separate.
