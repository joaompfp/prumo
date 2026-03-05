# Contributing to Prumo

Thanks for helping improve Prumo. This guide keeps contributions practical and consistent for an open-source data product.

## Proposing a New Data Source

Open an issue (or draft PR) with:

1. **Source name and provider**
2. **Official URL** (API docs or official dataset page)
3. **What indicator(s) it adds** and why they matter for the dashboard
4. **Geographic and temporal coverage** (PT-only, EU, global; monthly/quarterly/yearly)
5. **Collector approach** (API endpoint, file download, scraping fallback)

If accepted, also add/update:

- collector code under `collectors/`
- indicator mappings/catalog metadata where relevant
- [`SOURCES.md`](./SOURCES.md)

## Data Quality Criteria

All new sources should meet these minimum checks:

- **Provenance:** official institution, regulator, or internationally recognized statistical body
- **Update frequency:** cadence is explicit and suitable for dashboard refresh cycles
- **Methodology caveats:** known breaks/revisions/seasonality caveats are documented
- **Reproducibility:** query parameters and transformation logic are clear in code

If quality is partial (for example, unstable endpoints), document trade-offs in the PR.

## Pull Request Workflow

1. Fork/branch from main (`feature/<short-name>`)
2. Keep PRs focused (one source or one coherent improvement)
3. Include a short PR description:
   - what changed
   - why
   - affected sources/indicators
   - any caveats
4. Update docs when relevant (`README.md`, `SOURCES.md`, notes in `docs/`)
5. Wait for review before merge

## Code Style and Testing Basics

- Follow existing Python style in this repo (small functions, clear naming, explicit error handling)
- Reuse shared helpers/constants where possible instead of duplicating logic
- Avoid silent data coercion; log or comment non-obvious transformations
- Run tests before opening PR:

```bash
pytest
```

For collector changes, include at least one validation note in the PR (sample payload, expected schema, or before/after row count).
