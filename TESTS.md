# CAE Dashboard: Test Suite Spec (v1)

**Target:** 0% → 75% coverage
**Stack:** stacks/web/images/prumo (Python/FastAPI or Flask backend + frontend)
**App:** joao.date/dados — 422+ education indicators, multilingual, fuzzy search, batch headlines

## Priority 1 — Core Data Layer
- [ ] Indicator loading: all 422+ indicators parse without error
- [ ] Indicator schema validation: required fields present (id, value, label, year)
- [ ] Missing/null value handling: graceful degradation, no crashes
- [ ] Data freshness: latest year per indicator is within expected range

## Priority 2 — Search & Filter
- [ ] Fuzzy search returns results for known indicator names (PT + EN)
- [ ] Fuzzy search on empty query returns full list
- [ ] Filter by category/year narrows results correctly
- [ ] Search is case-insensitive

## Priority 3 — Multilingual
- [ ] PT and EN label keys exist for every indicator
- [ ] Language switch renders all labels (no missing keys → raw key shown)
- [ ] URL/slug is language-agnostic

## Priority 4 — Batch Headlines
- [ ] Headline generation doesn't crash on any indicator
- [ ] Output is non-empty string for valid indicators
- [ ] Handles LLM timeout/error gracefully (fallback text, not 500)

## Priority 5 — API Endpoints (if applicable)
- [ ] `/indicators` returns 200 with expected count
- [ ] `/indicators/<id>` returns correct data
- [ ] Invalid ID returns 404, not 500

## Out of scope (prototype)
- Load testing, auth, accessibility
