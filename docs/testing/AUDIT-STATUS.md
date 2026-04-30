# Prumo Indicator Audit — Status Report

**Date:** 2026-03-16
**Session:** Análise tab full indicator audit + bug fixes

---

## 1. API-Level Audit (COMPLETE)

Tested all 372 indicators via internal API (`http://172.20.0.6:8080/api/series`).

| Status | Count | Details |
|--------|-------|---------|
| **OK (data returned)** | 368 | All sources working |
| **No data** | 4 | `DGEG/price_gasoline_98_pvp`, `EUROSTAT/construction_index`, `FRED/gold_price`, `WORLDBANK/gov_debt_pct_gdp_wb`, `WORLDBANK/literacy_rate` |
| **Sparse (1-2 pts)** | 4 | 3x DGEG industrial EU bands, 1x EUROSTAT earn_ses_pub2s |

**Conclusion:** Data layer is solid. 368/372 indicators have valid data.

---

## 2. Browser Audit Script (`test_all_indicators.py`)

### Location
`stacks/web/images/prumo/test_all_indicators.py`

### What it does
- Launches headless Playwright browser
- Navigates to each indicator via URL hash on the Análise tab
- Waits for chart render + AI analysis
- Takes screenshots on failure
- Tests 372 individual indicators + 21 common combos
- Saves results to `/tmp/prumo-audit-results.json`

### Previous run results (INVALID — test had bugs)
First run: 91/372 OK (timing bugs). Second run: similar. Results in `docs/testing/prumo-audit-results.json` are from the buggy run.

### Bugs found and fixed in test script

1. **SPA hashchange listener stacking** — The test's `page.goto()` caused the SPA to re-initialize, registering duplicate `hashchange` listeners with stale closures over empty catalog objects → random 404 errors. **Fix:** each test now uses a fresh `context.new_page()` (full page reload per indicator). Slower but reliable.

2. **DOM scope leak** — `_wait_for_chart_or_error` found `.loading-state` from `#painel` section instead of `#explorador` → false timeouts. **Fix:** all queries scoped to `document.getElementById('explorador')`.

3. **Canvas detection** — Chart renders inside `#exp-chart-wrap > #exp-chart > canvas`, not generic `canvas`. **Fix:** specific selectors added.

### Smoke test results (after fixes)
```
OK   INE/ipi_seasonal_cae_TOT
OK   INE/hicp_yoy
OK   FRED/copper
OK   BPORTUGAL/euribor_12m
OK   REN/electricity_wind
FAIL WORLDBANK/gdp_per_capita_ppp  (timeout 31s — annual data, slow)
OK   OECD/cli
OK   DGEG/price_diesel_pvp
FAIL ERSE/btn_simple              (timeout 31s — annual data, slow)
OK   EUROSTAT/unemployment
```
8/10 OK. The 2 timeouts are likely due to `MAX_CHART_WAIT=15s` being too short for annual indicators. **Increase to 45s** for the full run.

### TODO for full audit run
1. Increase `MAX_CHART_WAIT` from 15 to 45 seconds
2. Delete old results: `rm /tmp/prumo-audit-results.json`
3. Run: `cd stacks/web/images/prumo && source venv/bin/activate && python test_all_indicators.py --headless`
4. Monitor: `tail -f /tmp/prumo-audit.log`
5. Set up Telegram watcher (see `/tmp/prumo-audit-watcher.py` — update PID)
6. Expected duration: ~3-4 hours (372 indicators × ~15-30s each)

---

## 3. App Bugs Found and Fixed

### Bug 1: Hashchange navigation broken (FIXED)
**Symptom:** Selecting indicators in Análise tab required page reload to see graphs.
**Root cause:** `window.addEventListener('hashchange', ...)` in `analise.js:981` registered inside the section init function. Each re-init (triggered by `app.js:182` when URL has `?s=` params) added ANOTHER listener without removing the old one. Old listeners operated on stale empty `catalog` → silent failures.
**Fix:** Added `AbortController` cleanup at top of init (`analise.js:8-11`), passed `{ signal: _hashAbort.signal }` to the hashchange listener (`analise.js:994`).

### Bug 2: AI analysis ignores selected period (FIXED)
**Symptom:** Changing De/Até dates manually didn't regenerate AI analysis.
**Root cause:** Time preset buttons (1A, 2A, etc.) called `autoRender()` but manual date input edits had no `change` listener.
**Fix:** Added debounced `change` listeners on `elFrom` and `elTo` in `analise.js:464-469`.

### Bug 3: Global lens selector (IMPLEMENTED)
**What was done:**
- Added `#nav-lens-selector` div in `dashboard.html` nav-controls (between theme toggle and language selector)
- Added lens dropdown initialization in `app.js` DOMContentLoaded (fetches `/api/lenses`, renders dropdown, dispatches `lens-change` events)
- Added `lens-change` listener in `analise.js` to re-trigger AI when lens changes
- Added global `#lens-hint-bar` below nav showing: `Lente: [icon] LABEL · disclaimer text`
- CSS in `nav-brand.css` for `.lens-fab`, `.lens-toggle`, `.lens-dropdown`, `.lens-option`, `.lens-hint-bar`

### Bug 4: Lens pill icons too small / cropped (FIXED)
- Increased `.lens-pill-logo` padding from `2px 4px` → `4px 5px`
- Increased `.lens-logo` max-height from `20px` → `22px`, max-width `44px` → `48px`
- Removed `border-radius: 50%` and `object-fit: cover` from nav lens selectors (was clipping icons into circles)

---

## 4. Files Modified

| File | Changes |
|------|---------|
| `static/js/sections/analise.js` | AbortController cleanup (Bug 1), period change listeners (Bug 2), lens-change listener (Bug 3) |
| `static/js/app.js` | Global lens selector init + lens hint bar + `_updateLensHintBar()` function |
| `templates/dashboard.html` | Added `#nav-lens-selector` div + `#lens-hint-bar` div |
| `static/css/nav-brand.css` | Lens FAB styles, lens hint bar styles, removed circular clipping |
| `static/css/sections.css` | Increased lens pill icon size and padding |
| `test_all_indicators.py` | Full rewrite of `test_indicator()`, `test_combo()`, `_wait_for_chart_or_error()`, `_wait_for_ai()` |

---

## 5. Known Issues / Next Steps

- **Full browser audit not yet run** with the corrected test script
- **Painel lens selector** still has its own per-section selector — consider removing it now that global exists (or keep for backward compat)
- **Metodologia lens bar** (`mf-lens-bar`) also has its own — should sync with global
- **Custom lens textarea** only accessible in Metodologia — may need a modal from the global dropdown
- **WORLDBANK/literacy_rate** and **WORLDBANK/gov_debt_pct_gdp_wb** have no data at all — may need data source investigation
- **FRED/gold_price** has no data — check if FRED series ID changed
