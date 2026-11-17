# Typography follow-up: SVG clipping, canvas gutter and figure wrapping

Date: 2026-11-17. Base commit: `3a88b1f` (`feat: increase Prumo type scale by ten percent`),
branch `pipeline-rebuild`. Scope: the four non-blocking findings left by the independent
quality review plus the 390px h1 break observed by the parent. No production, network, CMS,
push or deploy writes. The QA server at `http://127.0.0.1:8124` was read only and was not
restarted.

## Outcome

All concrete visual findings are closed with minimal changes. No text size was reduced. No
statistical title, value token or formatted number changed.

## Changes

### 1. SVG left gutter now covers real Lato digit advances

`app/chart_model.py` estimated `9.9` units per digit. Chromium with the served Lato subset at
18.15 units measures a tabular digit at `10.5217`, a group separator at `4.644` and a hyphen
at `6.739`. The old estimate under-counted `10 000 000` by 3.26 units and
`10 000 000 000` by 4.27 units.

`_text_width` now uses conservative per-character classes: `10.6` for digits and signs,
`4.8` for separators and punctuation. `_left_gutter` keeps a 15-unit allowance instead of
13. The renderer still anchors the tick at `model.left - 11`.

Browser verification with the rendered SVG (Chromium 1248, served Lato, 400 weight):

| Tick | Measured ink width | bbox.x before | bbox.x after |
| --- | ---: | ---: | ---: |
| `10 000 000` | 93.47 | -1.46 | 4.53 |
| `10 000 000 000` | 129.69 | -2.67 | 5.31 |

All tick text remains byte-exact. No value is rounded, truncated or reformatted.

### 2. Canvas top gutter has a CSS-pixel floor

`tools/charts/src/adapter.js` scaled `top` and `nameGap` with the stage width while the axis
name stays fixed at `19.8` CSS pixels. At 320px and 480px the name sat above the canvas.

The adapter now uses:

```js
const top = Math.max(31 * scale, 31);
const nameGap = Math.max(13 * scale, 13);
```

The grid and y-axis consume those values. The plotted geometry at the full 880px view is
unchanged. Browser screenshots at 320px and 480px show the unit name `número` fully inside
the canvas, including its accent.

### 3. Figure block stacks before the value column narrows

`static/css/prumo.css` keeps the metadata column at up to `24rem`. The value column therefore
fell to about 255px between 1101px and 1139px, where `11 424 031 número` broke into three
lines.

A new `@media (max-width: 1200px)` block collapses `.figure-block` to one column and moves the
metadata border to the top. The old 1100px query no longer touches the figure block. The value
still renders from the exact `value_display` token.

Browser measurements on `ine.population.PT` (`11 424 031 número`):

| Viewport | Grid | Value lines |
| ---: | --- | ---: |
| 1101px | one column, 963px | 1 |
| 1140px | one column, 1002px | 1 |
| 1201px | two columns, value 355.8px | 2 |
| 1440px | two columns, value 394.8px | 2 |

No horizontal overflow at any tested width. The two-line desktop layout is restored without
changing the font size or the number.

### 4. Portuguese hyphenation for h1

The 390px h1 `Produção total de eletricidade - Portugal` broke as `eletricidad` / `e`.
The `h1` rule now declares `hyphens: auto` and `-webkit-hyphens: auto`. The shared heading rule
keeps `overflow-wrap: anywhere` as the fallback.

Chromium 1248 with its Portuguese dictionary hyphenates the word as `ele-` / `tricidade` at
390px, with no horizontal overflow. The rendered break depends on the browser dictionary for
`pt-PT`; the CSS only requests it and the overflow fallback remains for browsers without one.

### 5. Documentation and comment corrections

- `.chart-axis-label` in the SVG is the axis unit name at `18.15px`; the canvas adapter draws
  its axis name at `19.8px`. `.chart-axis-title` at `19.8px` has no consumer.
- `tests/test_legibility_assets.py` comments now use the current `28.05px` public and `26.4px`
  Admin roots and state the correct SVG/canvas role split.
- `type-increment.md` and `tests/app/golden/README.md` carry the same correction.
- `app/chart_model.py` no longer claims the SVG top gutter holds a 19.8-unit axis name.

## Golden fixtures

All 11 `tests/app/golden/charts/*.svg` files are byte-identical to `HEAD`. None of the
fixtures contains a tick long enough to move the new gutter, so no coordinate changed. A
programmatic `ElementTree.itertext` comparison across all 11 files found no text difference;
the equality is exact because the bytes did not change.

## Bundle receipt

The pinned bundle was rebuilt twice with the same result.

| Item | Value |
| --- | --- |
| SHA-256 | `70a45c776a6bf397f75ddd0e22807ec837a7ba3a4b0545b61d2ff79c9a4e3d0a` |
| Bytes | 506637 |
| gzip level 9, mtime 0 | 173149 |
| ECharts / ZRender | 6.1.0 / 6.1.0 |
| esbuild | 0.25.12 |

`static/js/prumo-charts.manifest.json` and `static/js/prumo-charts.NOTICE.txt` match that
hash. The vendored-bundle exemption in `tests/test_typography.py` was updated to the same
hash. `node --check` passes.

## Tests executed

Focused only, no full suite:

```text
.venv-ci/bin/python -m pytest tests/app/test_typography_followup.py \
  tests/app/test_chart_model.py tests/app/test_type_increment.py \
  tests/app/test_legibility_review.py tests/test_legibility_assets.py \
  tests/test_typography.py tests/app/test_interactive.py \
  tests/app/test_chart_interaction.py tests/app/test_chart_layout.py -q
```

Result: 84 passed, 1 failed. The failure is
`tests/test_typography.py::test_repository_text_has_no_em_dashes` reporting the untracked,
parent-owned `spec-review.md` at lines 1, 8, 70 and 71. That file was not modified. The same
test still validates the new bundle hash before scanning and did not report the bundle.

Additional checks:

- `.venv-ci/bin/python -m pytest tests/app/test_typography_followup.py -q` -> 5 passed.
- `.venv-ci/bin/ruff check` on all changed Python files -> All checks passed.
- `node --check static/js/prumo-charts.min.js` -> OK.
- `git diff --check` -> clean.

## Browser probes

Read-only Playwright probes against the QA copy, whose static CSS and bundle are served from
this working tree:

- Figure block at 1101, 1140, 1201, 1240, 1440 and 390px: no horizontal overflow; value line
  counts as in the table above.
- Canvas at 320px and 480px: `número` fully visible above the plot.
- h1 at 390px: `ele-` / `tricidade` in Chromium with its dictionary.
- SVG text boxes: both long ticks have positive `bbox.x`.

## Remaining

The parent owns the full browser matrix, production verification, push and deploy. The only
test failure is the protected untracked review file described above.
