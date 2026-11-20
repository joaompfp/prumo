# Multiscale quality review: implementation after spec pass

Verdict: APPROVED. No blocking data, math, or integration defect was found in the reviewed
range. Three observations are recorded below; none requires a code change before release.

## Scope and method

Read-only independent review of the multiseries two-axis feature at `ecc0e93` plus the four
uncommitted copy changes and one test. The evidence trace is
`/home/joao/.hermes/cache/delegation/live/deleg_16ec2263/task-0.log`. This pass resumed that
trace instead of repeating its diff inspection, then read the exact source lines behind the
three open concerns: curated group validation, the annual output signature, and the catalogue
cache. No code, git, deployment, or CMS change was made.

## Evidence from the recorded probes

- Six plotted series across two compatible groups: axes `%` and `milhões de euros`, axis map
  `[0, 1, 0, 1, 0, 1]`, 121 monthly periods from September 2016 to September 2026, panel state
  `ready` (trace line 112).
- Twelve cards with six checked: same two axes and interleaved map, state `ready`, 18
  checkboxes with 6 checked, axis group labels `Eixo esquerdo` and `Eixo direito` (trace line
  176).
- Curated links: three advertised. The four-series link prepared axes `[0, 0, 1, 1]` and
  state `ready` (trace line 80). The annual three-series link prepared axes `[0, 0, 1]`,
  11 years from 2015 to 2025, state `ready` (trace line 120).
- Refused shapes: one group, three groups, and a mixed common-scale selection all return
  state `unavailable`, no chart, the specific reader message, and preserved settings (trace
  line 134).
- Annual controls: base 100 on a percentage selection is refused with the defined message;
  annual and annual with percentage points are `ready` (trace line 136).
- Adapter and asset: the served minified asset hash matches the manifest, and the adapter
  source and minified body carry the axis validator, `yAxisIndex`, and `usedAxes` coverage
  checks (trace lines 97 to 106).
- Copy discipline: no em dash in `app`, `presentation`, or the touched tests (trace line 153).
- Targeted test after the report draft: `.venv-ci/bin/python -m pytest
  tests/app/test_portugal_comparisons.py -q` collected 6 tests, all 6 passed in 8.03 s.

## Findings

1. Non-blocking, curation guard. `app/portugal_comparisons.py:52-97` validates that there are
   exactly two ordered groups, that every series exists with the expected role and frequency,
   and that every series matches its group unit, multiplier, and base year. It does not assert
   that the two group signatures differ from each other. Two groups with the same signature
   would pass `_resolve`, advertise a link on `/comparar`, and then the notebook would refuse
   to draw with the existing `partilham a mesma unidade` state. All three current definitions
   have distinct signatures and all three links render ready, so this is a latent curation
   hazard, not a present defect. A one-line set-size check would close it.

2. Non-blocking, tautological annual guard. `app/calendar_notebook.py:275-283` builds the
   annual output signature from `side.row` (the source row), and lines 430 to 435 re-run
   `allocate_axes` with those same source signatures before comparing to the allocation made
   from the source signatures. The comparison therefore cannot detect a changed annual output
   unit. The actual unit safety is in `analysis/transforms.py:151-159`: `_monthly_method`
   admits `mean` or `year_end` only for the reviewed unit sets, and `annualise` returns the
   source unit token. No wrong annual output was observed. The docstring overstates what the
   check proves; the code is correct for the reviewed methods.

3. Note, cache window. `app/reads.py:60,83-92` caches the `/comparar` index catalogue for 30
   seconds. Notebook eligibility does not depend on that cache: `prepare_card` resolves each
   slot through `db.series_facts` on the render handle (`app/reads.py:626-662`). A withdrawal
   inside the cache window can leave a card advertised for up to 30 seconds, but opening the
   link drops the series honestly. No stale values are exposed.

## Residual risk

The controller full suite was running outside this review and its result was not available.
No broad suite was rerun here, per instruction. The recorded targeted probes plus the source
reads above cover the agreed contract: maximum six plotted series, at least three raw series
in two groups, legacy dual behaviour independent at axes 0 and 1, unchanged common scale,
annual and native mixed values, and transforms on common scale only.

## Verdict

APPROVED for release. Findings 1 and 2 are follow-up quality items, not blockers.
