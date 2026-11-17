# Prumo chart bundle tooling

Pinned local source for `static/js/prumo-charts.min.js`. Production copies `static/` only;
Node and npm are build-time tools and never enter the runtime image or answer a request.

Versions are exact in `package.json` and `package-lock.json`:

- ECharts 6.1.0
- ZRender 6.1.0 (transitive)
- tslib 2.3.0 (transitive)
- esbuild 0.25.12

The entry point imports only `LineChart`, `GridComponent`, `TooltipComponent` and
`CanvasRenderer`, plus Prumo's adapter. The adapter uses `tooltip.renderMode = 'html'`, but the
formatter returns DOM nodes filled with `textContent`, never an HTML string: publisher titles
cannot become markup, and CSS wraps the long values instead of clipping them.

## Rebuild

From the repository root:

```bash
npm ci --prefix tools/charts --ignore-scripts --no-audit --no-fund
node tools/charts/build.mjs
```

The build writes:

- `static/js/prumo-charts.min.js` (generated asset, committed)
- `static/js/prumo-charts.manifest.json` (SHA-256, raw and gzip bytes, versions)
- `static/js/prumo-charts.NOTICE.txt`
- `static/js/licenses/echarts-APACHE-2.0.txt`
- `static/js/licenses/zrender-APACHE-2.0.txt`
- `static/js/licenses/tslib-0BSD.txt`

The script fails when the raw bundle exceeds 650,000 bytes or the local gzip measurement
exceeds 220,000 bytes. Gzip figures are local measurements at level 9 with `mtime=0`, not a
claim about production transfer encoding.

The generated bundle contains upstream ECharts localisation strings verbatim, including one
em dash in library code. `tests/test_typography.py` exempts it only while its SHA-256 matches the
recorded hash; a rebuild is therefore an explicit reviewed change.

## Reproducibility check

```bash
sha256sum static/js/prumo-charts.min.js
node tools/charts/build.mjs
sha256sum static/js/prumo-charts.min.js
```

The two hashes must match and equal `sha256` in the manifest.
