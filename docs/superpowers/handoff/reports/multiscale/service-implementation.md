# Multiscale notebook service and curated Portugal comparisons

Slice: grouped two-axis compatibility in the Caderno read service and a curated Portugal section
on `/comparar`. Baseline `e6b6ded` (core chart contract). No push, deployment, CMS write, schema
change or second analytics path.

## One compatibility allocator

`app/notebook_chart.allocate_axes(signatures, scale) -> AxisPlan` is the single authority. A
signature is the raw stored `(unit, multiplier, base_year)` triple. It returns:

- `axes=(0, 1)` for the legacy two-side `dupla` chart, including two sides with one unit.
- Stable first-seen `0`/`1` membership for three to six sides with exactly two signatures.
- `problem="one_group"` for `dupla` with one signature, so the reader is sent to the common scale
  instead of a silent split.
- `problem="too_many_groups"` for `dupla` with three or more signatures.
- `problem="mixed_scale"` for `comum` with more than one signature.

`prepare` allocates once and passes the resulting tuple to the dense group path, the sparse
calendar path and the annual path. The dense path now calls
`reads.prepare_group_chart(..., units=..., axes=...)`; it previously passed only the first unit.
The calendar path calls `calendar_model(..., axes=axes)`. The annual path calls
`prepare_group_chart(..., units=..., axes=axes)`, and re-checks the allocation after annualisation
through `_annual_output_signature`. Reviewed annual methods are unit-gated and preserve the source
unit; a future method that changes the effective output unit now fails closed with the generic
draw refusal instead of joining a mismatched group.

Transformations remain common-scale only: `base100` and `pp` with `escala=dupla` still return the
existing shared-scale refusal before allocation.

## Reader surfaces

- `ChartChoice.unit_text` shows each card unit in the Caderno settings.
- `NotebookChart.axis_groups` renders the left/right group, shared unit and member labels in the
  settings panel.
- `ChartSide.axis_text` comes from the prepared model's `axis_labels` and renders inside the
  Caderno source metadata; grouped SVG and calendar legends keep the core `data-axis` contract.
- Two-side dual charts keep the reviewed pair legend and metadata without the new group block.
- Copy no longer says two axes mean two series. The one-group, many-group and shared-scale
  refusals each name the corrective action.

## Curated Portugal section

`presentation/portugal_comparisons.py` holds the reviewed definitions and copy.
`app/portugal_comparisons.index` resolves each definition against `reads.catalogue` on the same
read-only route snapshot, validates frequency, role, exact raw signature and unique series, and
builds the canonical link with `app.notebook.selection_path` plus
`notebook_chart.ChartSettings(mode="explicit", group=..., scale="dupla", window="10a")`.

| Slug | Series in reading order | Axes | Frequency | Window |
|---|---|---|---|---|
| `taxas-juro-credito-depositos` | `bportugal.euribor_12m.EA`, `bportugal.pt_10y.PT`, `bportugal.credit_housing.PT`, `bportugal.deposits_households.PT` | 0, 0, 1, 1 | M | 10a |
| `divida-saldo-pib-per-capita` | `eurostat.gov_debt_pct_gdp.PT`, `eurostat.gov_deficit_pct_gdp.PT`, `eurostat.gdp_per_capita_eur.PT` | 0, 0, 1 | A | 10a |
| `comercio-externo-pib-per-capita` | `worldbank.exports_pct_gdp.PT`, `worldbank.imports_pct_gdp.PT`, `eurostat.gdp_per_capita_eur.PT` | 0, 0, 1 | A | 10a |

Units are the reviewed raw tokens: `%`/`MEUR`, `% GDP`/`EUR per capita`, and `% PIB`/`EUR per
capita`. A missing, inactive, deactivated, withdrawn or re-scaled side hides the whole card. There
is no series drop and no dedicated comparison route: the card title and "Abrir no Caderno" action
point at the existing configured notebook.

The `/comparar` template adds the Portugal section and keeps the existing pair and country
sections and their mount-prefix links unchanged.

## Verification

Focused command and actual result:

```bash
.venv-ci/bin/python -m pytest tests/app/test_notebook_settings.py \
  tests/app/test_notebook_chart.py tests/app/test_notebook_analysis.py \
  tests/app/test_notebook_workspace.py tests/app/test_notebook_caption.py \
  tests/app/test_portugal_comparisons.py tests/app/test_comparisons.py \
  tests/app/test_country_comparisons.py -q
```

Result: `156 passed, 1 warning in 191.11s (0:03:11)`.

Lint:

```bash
.venv-ci/bin/ruff check app/notebook_chart.py app/calendar_notebook.py \
  app/portugal_comparisons.py app/main.py presentation/notebook.py \
  presentation/portugal_comparisons.py tests/app/test_notebook_chart.py \
  tests/app/test_notebook_analysis.py tests/app/test_notebook_settings.py \
  tests/app/test_portugal_comparisons.py tests/app/conftest.py
```

Result: `All checks passed!`.

Read-only live signature check against `registry/core.yaml` confirmed the exact reviewed units and
frequencies for all nine series (`%`, `MEUR`, `% GDP`, `EUR per capita`, `% PIB`; M and A). The
curated copy was checked for the absence of em dashes.

New coverage includes:

- allocator first-seen order, unit/multiplier/base separation, one group, excess groups, common
  scale and legacy pair dual;
- later-member extremes expanding both axis domains;
- six mixed-frequency sides on a sparse calendar with two groups;
- annual original sides and annualised output grouping, including a drift guard;
- three and four sides on grouped axes, canonical address retention, settings and metadata axis
  labels, and no positional "second series" copy;
- the three curated cards, each opening a grouped Caderno, a withdrawn source, a changed scale
  signature, and mount-prefix links.

## Not in this slice

No full application/backoffice rerun, browser layout pass, deployment, push, CMS mutation or
production data write. The controller owns the full suite and deployment.
