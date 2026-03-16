# Análise Tab — UI Improvements

**Date:** 2026-03-16
**Tested with:** Playwright browser, desktop viewport 1280×900

## Critical Issues

### 1. Source filter locks after selecting indicator
**Severity:** Critical — blocks core workflow
**Steps:** Select INE indicator → search "desemprego" → "Sem resultados"
**Cause:** When user clicks an indicator, the source dropdown auto-sets to that indicator's source. Next search is restricted to that source only.
**Fix:** Do NOT change the source filter when an indicator is selected. Or reset to "Todas as fontes" after each selection. The filter should only change when the user explicitly changes it.
**Screenshots:** `ui_search_desemprego_blocked.png`, `ui_search_brent_blocked.png`

### 2. Removed indicator still appears in search (gold_price)
**Severity:** Medium — confusing, selecting it will fail
**Cause:** `FRED/gold_price` was removed from catalog constants but may still exist in the database or the catalog is cached at startup.
**Fix:** Verify the catalog API excludes it. May need container restart or cache clear.

## UX Improvements

### 3. Indicator code shown in search results
**Current:** Each result shows `label` on left and `indicator_id` on right (e.g. `hicp_yoy`)
**Problem:** The code (hicp_yoy, wages_industry_cae) is dev jargon — confuses normal users, wastes horizontal space.
**Fix:** Hide the code by default. Show source name + unit instead. Code can be in a tooltip or in the ficha técnica.

### 4. Fuzzy search too permissive
**Example:** Searching "inflação" returns "Salários na Indústria" — no obvious relevance.
**Fix:** Tighten fuzzy matching threshold. Prioritize exact substring matches over fuzzy. Consider searching label + description but ranking label matches higher.

### 5. Ficha técnica too verbose — pushes chart off screen
**Current:** Full ficha técnica (description, code, unit, frequency, coverage, observations, cite button) is expanded inline for each selected indicator.
**Problem:** With 3 indicators selected, the ficha occupies ~600px and pushes the chart below the fold. Users need to scroll past metadata they didn't ask for to see the chart.
**Fix options:**
  - a) Collapse ficha by default, expand on click (accordion)
  - b) Move ficha below the chart
  - c) Show compact version: just label + source + unit per indicator, expand for full metadata

### 6. Dual-axis banner placement
**Current:** "Dois eixos verticais — esquerdo: % · direito: USD/bbl" appears between date controls and AI analysis, easy to miss.
**Fix:** Move it to just above or inside the chart area, as a subtle overlay or chart subtitle.

### 7. No indication of data frequency mismatch
**Current:** When mixing monthly + quarterly indicators, no visual cue.
**Fix:** Show small badge on chips like "Mensal" / "Trimestral" or a note when frequencies differ: "Nota: séries com frequências diferentes — PIB é trimestral."

### 8. Chart not visible without scrolling
**Current:** With 2+ indicators, the chart is pushed below the fold by chips + date controls + AI panel + ficha.
**Fix:** Either collapse AI/ficha by default, or pin the chart area so it's always visible. The chart is the primary output — it should be the first thing users see after selecting indicators.

## Working Well

- Dual-axis detection and labelling works correctly
- Chips with source prefix (INE/EUROSTAT/FRED) are clear and coloured
- "Limpar" button works
- Guided paths (Custo de Vida, Emprego, etc.) work
- Chart renders correctly with 3 mixed-frequency indicators after connectNulls fix
- Legend with scroll works for long indicator names
