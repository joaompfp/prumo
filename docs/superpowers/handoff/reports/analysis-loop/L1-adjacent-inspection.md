# L1 adjacent chart inspection - implementation report

Scope: the public chart shell and every consumer that shows secondary series metadata. The
public GET/HEAD application, CMS-published configuration, source data, schema and migrations are
unchanged.

## Delivered composition

- Canvas first, then the native range and its structured selected-point rows, then the existing
  compact colour/pattern legend, then one native `details` disclosure summarised as
  `Séries, eixos e fontes`.
- The inspector is hidden by CSS until the local adapter has drawn a canvas successfully. A
  blocked bundle or disabled JavaScript leaves the server SVG, legend and disclosure with no
  empty control block between the plot and its key.
- Multi-series readout rows consume the prepared payload only: prepared style swatch, title,
  prepared axis membership, prepared unit and the exact inspected native period. No unit or
  scale is inferred from translated labels, and no domain is recalculated in the browser.
- The union period and the per-side native observation are distinguished in the row labels
  instead of repeating a bare chain of latest dates in the caption.
- Mixed-frequency captions say that per-series dates are in `Séries, eixos e fontes`; the
  disclosure itself names each side's original period and source.
- Full coverage is named `Todo o histórico` instead of `Máximo` in the notebook, the series
  detail range and the authored chart window text.
- Print opens the disclosure, including its native details-content wrapper, and hides the
  disclosure summary. Static Admin previews keep the populated disclosure in the document.
- Primary, derived, notebook, CMS analysis chart and CMS inline-block chart consumers all keep
  the same order and fallback. The shared `chart_meta` boundary extracted in the base commit is
  reused; no second metadata representation was added.

## Files

- `app/templates/_chart.html`: order and closed-by-default disclosure.
- `app/templates/_cms_analysis.html`, `app/templates/_notebook_chart.html`: period/source
  metadata and mixed-frequency caption.
- `app/cms_reads.py`, `app/reads.py`, `presentation/notebook.py`: `Todo o histórico` and the
  mixed-period note.
- `static/css/chart-inspector.css`: progressive inspector visibility, swatch, unit/native
  labels and print disclosure rules.
- `tools/charts/src/adapter.js` and regenerated `static/js/prumo-charts.*`: prepared style,
  axis and unit on readout rows.
- Tests under `tests/app/` and `tests/test_typography.py`.

## Verification

Environment: existing shared `.venv-ci` (Python 3.12.3, pytest 9.2.0), local Chromium for the
browser-backed suites. No production, live CMS or database operation.

- `pytest tests/app/test_notebook_chart.py tests/app/test_notebook_workspace.py tests/test_typography.py -q`: 69 passed.
- `pytest tests/app/test_chart_interaction.py tests/app/test_chart_layout.py tests/app/test_calendar_interaction.py tests/app/test_analytical_pages.py -q`: 32 passed.
- `pytest tests/app/test_cms_home.py tests/app/test_cms_multiseries.py tests/app/test_cms_reads.py -q`: 50 passed.
- `pytest tests/app/test_comparisons.py tests/app/test_country_comparisons.py tests/app/test_series_list_views.py tests/app/test_interactive.py -q`: 84 passed.
- `pytest tests/app/test_notebook.py tests/app/test_notebook_caption.py tests/app/test_notebook_settings.py tests/app/test_notebook_analysis.py -q`: 57 passed.
- `pytest tests/test_legibility_assets.py tests/backoffice/test_boundaries.py -q`: 11 passed.
- `ruff check` on every changed Python and test file: passed.
- `git diff --check`: passed.
- Bundle rebuilt with `node tools/charts/build.mjs`: SHA-256
  `c66af18bbf7295d73183ef0a46ee829611c10f67073c3345e21d75656cd55e53`, 512096 bytes,
  gzip 174687. A second build produced the same SHA; manifest and NOTICE match.

## Caveats

- The controller owns the full offline suite and release gates. This report records scoped
  suites only.
- `tests/app/test_notebook_workspace.py` and `tests/app/test_notebook_chart.py` contain hunks
  that also changed on another isolated branch; integration is the controller's responsibility.
- Print opening of a closed native disclosure relies on the `::details-content` mechanism in
  current Chromium; the fallback child-selector rule is retained.
- Human screen-reader acceptance remains open, as it does for the wider release.
- No live CMS or production browser acceptance was performed.
