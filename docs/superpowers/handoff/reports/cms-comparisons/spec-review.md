# CMS-owned comparisons correction: specification review

**Verdict: PASS** for the corrected specification implementation.

Scope: baseline `53db524`, candidate `616fb05` plus the current task-owned dirty diff and new files. This was a read-only review: no code edits, no git index changes, no network access, and no live database writes. One read-only query was run against the isolated production copy; the full suite and browser matrix were not rerun.

## Binding acceptance

### 1. Immutable CMS chart contract - PASS

The existing `ChartDocument` keeps its canonical body and gains only optional fields:

- `series_a`, optional `series_b`, and `series_extra` with `MAX_EXTRA_SERIES = 4` and `MAX_SERIES = 6`; the model validator rejects duplicates and totals above six (`ingest/cms.py:38-39`, `331-362`, `425-433`).
- `axes` is either null for automatic allocation or one 0/1 assignment for every selected series; single scale allows only the left axis and dual requires both axes (`ingest/cms.py:407-414`, `436-442`).
- `frequency` is `original` or `annual`; `transform` is `original`, `base100`, or `pp`; `base` is an optional four-digit year and is rejected without a transformation; transformed output requires annual frequency; `day` is refused for annual or transformed views (`ingest/cms.py:25-26`, `416-423`, `443-452`).
- `comparison_group` is null or one of `portugal`, `countries`, `general` (`ingest/cms.py:27`, `353`).
- `derived_key` remains single-series only and is rejected with extra series, axes, annual/transformed settings, or a comparison category (`ingest/cms.py:432-433`, `453-456`).
- `canonical_body` uses `exclude_unset=True`, so old revisions without the new optional keys keep their exact canonical text and remain restorable (`ingest/cms.py:510-525`).

Focused contract and regression coverage exists in `tests/ingest/test_cms_multiseries.py`, `tests/app/test_cms_multiseries.py`, and `tests/backoffice/test_cms_multiseries_routes.py`.

### 2. Native backoffice authoring - PASS

- Six ordered native `<select>` slots plus six optional axis `<select>` controls are in the shared macro, with no JSON editor (`backoffice/templates/cms_macros.html:41-95`).
- Window, scale, frequency, transformation, base year, comparison category, and day use labelled native controls (`backoffice/templates/cms_macros.html:99-185`).
- The editor includes both macros (`backoffice/templates/cms_editor.html:415-416`), and the dashboard creation form exposes the same contract; both are covered by `tests/backoffice/test_cms_multiseries_routes.py:173-312`.
- The form parser maps `series_a`, `series_b`, `series_extra_0..3`, `axis_0..5`, `frequency`, `transform`, `base`, and `comparison_group`; inactive axis slots are ignored; axes must be all automatic or all selected-series explicit (`backoffice/cms_routes.py:324-395`).
- Submitted values and expected versions survive refusals for recovery (`backoffice/cms_routes.py:472-489`; `tests/backoffice/test_cms_multiseries_routes.py:212-249`).
- Complete field impact is visible in the publication diff, including all six series slots and every analytical field (`backoffice/cms_routes.py:633-707`; test `:155-170`).
- Legacy posted chart forms still store the original body shape without materialising new keys (`backoffice/cms_routes.py:335-338`; test `:127-139`, `:251-261`).
- Both the editor and dashboard work without JavaScript by construction; the browser pack confirms six series controls in a script-disabled context.

### 3. Public comparison catalogue and reader - PASS

- `/comparar` reads only published CMS chart revisions from `cms_comparisons.index`; no built-in comparison fallback remains (`app/main.py:241-249`, `app/cms_comparisons.py:44-73`).
- `/comparar/{slug}` uses the published CMS revision only and accepts no query parameters that could override series, axes, scale, window, or transformation (`app/main.py:261-274`; test `tests/app/test_cms_comparisons.py:73-78`).
- Legacy country URLs redirect only when an eligible published CMS comparison with `comparison_group == "countries"` exists; otherwise they return 404 (`app/main.py:251-259`; test `:110-116`).
- The detail template uses the shared authored analysis view with all series, table cells, evidence, and provenance, and it contains no composition form or Caderno composition link (`app/templates/_cms_analysis.html:1-35`; test `tests/app/test_cms_comparisons.py:49-70`).
- Drafts remain private; withdrawing removes the catalogue entry and detail, restore does not republish, and restore/publish/duplicate continue through the existing CAS and audit service (`tests/app/test_cms_comparisons.py:81-89`; `backoffice/cms.py:288-322`).
- Library charts without a comparison category remain available at `/graficos/{slug}` but are absent from `/comparar` (`tests/app/test_cms_comparisons.py:92-96`).
- The exploratory Caderno remains a separate tool; the comparison reader does not link into a notebook configuration (`tests/app/test_cms_comparisons.py:61`).

### 4. Actual imported content - PASS

`backoffice/comparison_import.py:32-54` builds exactly the nine prior compositions:

- three pairs: `inflacao-e-desemprego`, `euribor-e-inflacao`, `credito-e-taxa`;
- three Portuguese multi-axis groups: `taxas-juro-credito-depositos`, `divida-saldo-pib-per-capita`, `comercio-externo-pib-per-capita`;
- three European country groups: `eletricidade-domestica`, `pib-por-habitante`, `divida-publica`.

The isolated production copy confirms nine published CMS documents with the reviewed titles and series:

- Portugal group: six entries, with two series in each pair and four/three/three series in the Portuguese multi-axis groups.
- Countries group: three entries with five countries each.
- `eletricidade-domestica` prepares publicly with five sides and 37 table rows.
- The final isolated `taxas-juro-credito-depositos` state is the restored four-series original at version 9 after the browser author/edit/restore run; the import receipt records its initial version 2 import.

`backoffice/comparison_import.py:57-93` is idempotent for existing publications, refuses collisions with private drafts before the first write, and uses the audited CMS create/publish service. `docs/superpowers/handoff/reports/cms-comparisons/isolated-import.json` records nine published imports, nine preserved reruns, unchanged protected tables, unchanged `inicio` home state, unchanged schema, clean integrity, and no foreign-key violations.

### 5. Shared engine, purity, and boundaries - PASS

- Authored chart preparation goes through the same `notebook_chart.prepare` path as the Caderno; `cms_reads._shared_chart_view` is an adapter over that engine, not a second chart implementation (`app/cms_reads.py:418-493`).
- Annual output signatures are revalidated by `calendar_notebook.prepare_annual`, including explicit axis membership (`app/calendar_notebook.py:433-448`).
- `app/statistical_definitions.py` is pure and database-free; `app/cms_comparisons.py` uses only `Db` methods (`app/statistical_definitions.py:1-36`, `app/cms_comparisons.py:1-73`).
- The directory is metadata-only by design: it uses `db.public_catalogue` plus `cms_reads.chart_definition_problem`, while full drawing happens on detail opening (`app/cms_comparisons.py:44-70`, `app/cms_reads.py:387-415`). This is the documented performance tradeoff, not a correctness gap.
- The country guard compares source, family, frequency, unit, multiplier, base year, seasonal adjustment, and native dimensions except geography; all 15 imported country series (three groups of five) are Eurostat and pass it (`app/statistical_definitions.py:20-36`, `app/cms_reads.py:395-400`).
- No migration, worker, scheduler, or edge routing changes are present in the candidate diff. The changes are confined to the typed document, backoffice, read service, templates/CSS, importer, and tests.

### 6. Acceptance evidence - PASS

- Browser pack: 74/74 checks passed, covering both mount prefixes, 390/768/1440/1920 public views, exact table cells, keyboard interaction, no composition controls, private draft, script-free preview, publish/readback, five-series authoring, no-JS SVG, and no external requests (`docs/superpowers/handoff/reports/cms-comparisons/browser/result.json`; `browser_check.py`).
- Screenshot pack exists at `docs/superpowers/handoff/reports/cms-comparisons/browser/` (`public-390.png`, `public-1440.png`, `editor-1440.png`).
- The controller reports 97 focused tests and 107 earlier guard/regression tests passed, with ruff clean. The full suite was still running under the parent at review time.

## Residual release and verification items, not spec implementation gaps

- The production copy has not been installed. The isolated copy proves the importer and reader; the production install, post-install readback, and live release gates remain release-pending work.
- Full-suite completion and the final clean-checkout gate are still release gates under the parent.
- Human screen-reader acceptance remains open as stated in the plan.
- The 74-check browser pack covers keyboard and no-JS behavior but does not add explicit touch or print checks from plan Task 5. The shared chart interaction code was not part of this correction, so I treat this as an acceptance-evidence item to add at release, not a code defect.
- The country guard parses Eurostat native identities explicitly; other publishers' native formats are documented as adapter-owned and rely on the validated family. All imported country content is Eurostat, so this does not affect the requested nine compositions.

No required implementation omission was found in this correction.
