# ECharts feasibility evidence

Measured 2026-11-16 against Prumo baseline `3cb9d51`. This folder is a synthetic renderer/build experiment, not application code, a production dataset, a finished feature or deployment evidence. The app's current live `/comparar` answered HTTP 200 with zero scripts and its existing restrictive Content Security Policy (CSP).

## Results

ECharts 6.1.0, ZRender 6.1.0, tslib 2.3.0; build with esbuild 0.25.12, Node 22.23.2 and npm 12.0.2. Exact npm dependency resolutions and publisher integrity values are in `package-lock.json`. Only `LineChart`, `GridComponent`, `TooltipComponent` and `CanvasRenderer` are imported.

| Build | Bytes | Local gzip bytes | SHA-256 |
|---|---|---|---|
| `engine.min.js` | 501,845 | 170,575 | `59c0adfc6391c33092c3ed5171050a0e51ce3c2c870cc2a36d385ed73f233844` |
| Official complete `echarts.min.js` | 1,121,883 | 368,202 | `b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0` |

The engine size excludes a future Prumo adapter. Compressed bytes are Python gzip level 9 with `mtime=0`; no production transfer/compression claim follows.

`probe.py` serves only on loopback with the proposed strict policy, runs an installed Chromium, moves the real mouse at 1440 px and taps an interior point at 390 px. It asserts the canvas exists and the tooltip callback received the exact supplied display strings, with no console errors/warnings, CSP violations or off-origin requests. Both recorded views also have no horizontal overflow. The fixture explicitly calls its values test data; none is passed off as a publisher observation.

Desktop tooltip: `3,90 %` and `1 234 567,80 milhões de euros`. Mobile tooltip: `4,10 %` and `1 256 789,00 milhões de euros`. Both values appear for the same selected period. `measurement.json` is the recorded output with version and limitation annotations; `proof-1440.png` and `proof-390.png` are the corresponding captures.

Read-only public HTTP spot checks of the existing application (no chart payload yet):

| Path | Current HTML bytes |
|---|---|
| `/series/ine.ipc_yoy.PT` | 123,013 |
| `/series/ine.hicp_yoy.PT` | 55,817 |
| `/comparar/credito-e-taxa` | 183,945 |
| `/comparar/euribor-e-inflacao` | 162,190 |

These responses were all 200. They are candidate baselines only; there was no exhaustive largest-page or added-payload measurement.

## Limits and failed attempts

An initial exact tap on the first mobile plot boundary produced no tooltip; the interior tap passed. This does not close first/last-point hit targets, touch scrolling or single-point interaction. They remain release gates in the design. The fixture's default axis tick formatting is not proposed Prumo presentation: the actual adapter must use Portuguese axis formatting and the current design tokens.

The first harness run also encountered an incidental favicon 404, fixed by an explicit data favicon. A Playwright polling expression triggered a CSP eval error in the harness; arrow-function predicates fixed the harness without changing the policy. Those failed runs are not the reported passing evidence.

No keyboard/assistive-technology, no-JavaScript, print, partial-failure, shared-snapshot, real-data payload size, server latency or integrated chart-colour checks were performed. The source is intentionally a small capability probe. The application suite was not rerun for this document-only change, and there is no claim of implementation acceptance.

## Reproduce on this host

`python3` on the agent host has Playwright; Prumo's `.venv-ci` currently does not. The probe uses the existing Chromium at `/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`. Another host must supply an installed browser and update that explicit probe path; no browser install is attempted by the script.

Copy to scratch so the measurement and image outputs do not overwrite this recorded evidence:

```bash
(
  set -eu
  src=/home/joao/projects/prumo-pipeline/docs/superpowers/handoff/reports/echarts-feasibility
  work=/home/joao/.hermes/cache/scratch/prumo-echarts-reproduce
  mkdir -p "$work"
  cp "$src/engine.js" "$src/proof.js" "$src/proof.css" "$src/proof.html" \
    "$src/probe.py" "$src/package.json" "$src/package-lock.json" "$work/"
  npm ci --prefix "$work" --ignore-scripts --no-audit --no-fund
  "$work/node_modules/.bin/esbuild" "$work/engine.js" --bundle --minify \
    --format=iife --target=es2020 --outfile="$work/engine.min.js"
  python3 "$work/probe.py"
)
```

The copied reproduction command above was exercised separately from the versioned source folder, in `/home/joao/.hermes/cache/scratch/prumo-echarts-reproduce`. It passed both browser probes and produced the same engine hash and byte sizes. This folder has no generated runtime asset or `node_modules` and is not copied into the production image by the Dockerfile.

## References

Design: `../../../specs/2026-11-16-interactive-charts-design.md`.

Official import/build guidance: https://echarts.apache.org/handbook/en/basics/import/

Renderer guidance: https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/

Publisher package metadata: https://registry.npmjs.org/echarts/6.1.0
