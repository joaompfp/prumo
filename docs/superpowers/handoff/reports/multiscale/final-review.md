# Multiscale final scoped review: tooltip sync and release procedure

Verdict: APPROVED. No blocking race, feedback, cancellation, regression, or scope defect was
found in this delta. The earlier whole-feature approval in `quality-review.md` stands.

## Scope and evidence

- Read-only review of `6cf8b9c` against `ecc0e93`. Inspected `tools/charts/src/adapter.js`,
  `tests/app/test_group_interaction.py`, the asset manifest, NOTICE, typography hash, and the
  working-tree `prebuild.sh` and `activate.sh`.
- The two controller copy files (`presentation/portugal_comparisons.py` and
  `tests/app/test_portugal_comparisons.py`) were not reopened.
- Independent focused run: `.venv-ci/bin/python -m pytest tests/app/test_group_interaction.py -q`
  reported 6 passed, 1 warning in 12.08 s.
- No source, runtime, git, CMS, or deployment change was made. The controller reports 19/19 on
  its actual-data browser harness; that harness was not rerun here.

## Tooltip synchronization

- `syncTip` defers one `showTip` to a zero-delay task, after native pointer handling. Every later
  move clears the previous timer, so a burst coalesces to the latest point.
- The deferred callback rechecks `current === point`. A later pointer, keyboard, range, or native
  axis selection makes a stale callback a no-op.
- `syncingTip` suppresses `updateAxisPointer` only while the explicit `showTip` dispatch runs, so
  the tooltip action cannot feed back and rewrite the selected row. No recursion remains.
- `pointerleave` calls `cancelTip` before `hideTip`, so a pending show cannot resurrect a tooltip
  after exit.
- Pointer paths still call `show(point, false)`, so mouse movement does not write `.chart-live`.
  Touch release keeps the existing `locate` plus `showTip` path.

## Regression test

- Six periods and a responsive shell make the first, middle, and last points reachable at 390 and
  1440 pixels.
- The test asserts the selected range row and the exact text of every tooltip line at each
  position. That covers both reported failures: hidden tooltip at the first edge and stale
  previous row at the last edge.
- It runs against the committed minified bundle under the production-shaped CSP, so it exercises
  the shipped asset, not the source file.
- The bundle hash `2330b172258ffed4ffd88bc7abe1d4e98f4a6d06f1a37292148770f1dac12157` matches the
  manifest, NOTICE, and `tests/test_typography.py`.

## Release procedure

- A diff against the reviewed `time-transformations` copies shows only receipt, rollback tag, and
  prebuilt tag names changed in `prebuild.sh`, and only receipt and tag names changed in
  `activate.sh`.
- `activate.sh` gates on the exact main push CI run: `headSha` equals the target, workflow `CI`,
  event `push`, branch `main`, completed with success, and every job successful.
- Rollback images are pinned from the live containers before the build and rechecked before
  activation. Activation records the new image IDs and asserts each running image differs from
  its rollback tag.
- The live checkout is clean and fast-forwarded only to the exact target. Services touched are
  limited to `prumo` and `prumo-backoffice`; there are no worker, edge, migration, or CMS mutation
  actions. The generated compose file resets includes and declares only those two services.

## Residual observations, non-blocking

- The new test does not directly assert the `pointerleave` cancellation path or that `.chart-live`
  stays empty during mouse movement. Source inspection confirms both, and a focused assertion
  would harden future changes but is not required for this release.
- The test uses a fixed 240 ms settle window. It passed here and in the controller harness, and the
  deferred work is a zero-delay task, so the margin is adequate.

## Verdict

APPROVED.
