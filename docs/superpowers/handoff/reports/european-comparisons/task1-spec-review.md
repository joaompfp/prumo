# Task 1 specification review

Verdict: PASS

Scope: `a3445e8..12cfbfa`, code commits `dc6a43e` then `e63692e`, report `12cfbfa`.

## Verified

- Pair compatibility: `comparison_model` keeps its signature and fields; `SeriesPoint.a`/`.b`, `ComparisonValue` and `ComparisonPoint` remain available. All five pair SVG goldens (`cmp_dual`, `cmp_gap`, `cmp_single`, `cmp_negative`, `cmp_empty`) are byte-identical, and the pair payload key order and nested values are pinned. `tests/app/test_chart_model.py tests/app/test_chart_engine.py`: 33 passed.
- Shared factory: `app/chart_model.py:553` enforces 3 to 6 series, unique non-empty labels, row shape and exact text tokens; any row with a missing or non-finite value is dropped whole at lines 583-585. Group geometry reuses `padded_domain`, `ordinals_for`, `positions` and `break_indices`; the model has one shared axis, empty `ticks_b`, and styles `g0` to `gN`.
- Rendering parity: both the SVG and the payload traverse the same `SeriesPoint.values`. Style keys `g0` to `g5` are defined in `static/css/prumo.css:544` and `tools/charts/src/adapter.js:143`; colours and dash arrays match, with `g0` using Carmim `--accent`.
- Payload: pair and line shapes are unchanged. A group carries one axis and explicit `axis: 0` on every series (`app/interactive.py:69`). The adapter rejects more than two axes, rejects a group without exactly one axis, and falls back to ink for an unknown style.
- Assets: a clean archive rebuild reproduced `debf2758...`, the manifest, the NOTICE and all licence texts byte-identically. The committed bundle SHA-256 matches the manifest.
- Scope: the diff contains no reads, routes, CMS, catalogue, registry, schema or data changes.

## Non-blocking observations

- `tests/app/test_chart_engine.py:152` covers a textual missing token (`n.d.`) but has no group case for `NaN` or `Infinity`. The group path uses the already non-finite-safe `decimal_or_none`, and a manual probe dropped those periods, so this is test coverage rather than a behavior defect.
- `tests/app/test_chart_engine.py:257` pins `g0` and generic adapter strings, not each `g1` to `g5` colour and dash pair. Current CSS and adapter values match the specification table, but future drift in those five styles would not fail this test.
- `group_model` relies on the documented caller contract for unique, oldest-first periods (`app/chart_model.py:558`). The pair engine has the same contract. This is not a Task 1 defect, but the Task 2 read model must preserve it.

No full suite was run. No blocking defects found.
