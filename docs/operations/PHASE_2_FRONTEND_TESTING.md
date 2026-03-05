# Phase 2: Frontend Testing Roadmap

**Target**: 50-60 frontend tests using **vitest** (Vite-native test runner)
**Effort**: ~15-20 hours
**Duration**: Week 2
**Coverage Goal**: Frontend state 0% → 70%, Frontend components 0% → 60%

---

## Overview

Phase 2 focuses on **JavaScript/TypeScript frontend testing** covering:
- State management (language selection, lens persistence, caching)
- Component rendering (KPI cards, search bar, language selector)
- Integration flows (language change → title update, search → explore)
- Responsive layouts (mobile, tablet, desktop)

---

## 2.1 State Management Tests (vitest)

### Files to Create

```
tests/js/
├── test_language_state.js     # localStorage, language-change events
├── test_lens_state.js          # Ideology selection, custom lens
├── test_cache_state.js         # 5-min client cache invalidation
└── test_router_state.js        # Hash routing, section navigation
```

### Test Cases

#### `test_language_state.js` (12 tests)

```javascript
describe('Language State Management', () => {
  // localStorage persistence
  test('getOutputLanguage() returns stored language', ...)
  test('setOutputLanguage() persists to localStorage', ...)
  test('language persists across page reload', ...)

  // language-change event
  test('language-change event fires on selector change', ...)
  test('event includes new language in detail.language', ...)
  test('all listeners receive event', ...)

  // default language
  test('default language is "pt"', ...)
  test('invalid language falls back to "pt"', ...)

  // All 5 languages work
  test('supports pt, cv, fr, es, en', ...)

  // Language selector
  test('language selector dropdown toggles', ...)
  test('flag images load for each language', ...)
})
```

#### `test_lens_state.js` (10 tests)

```javascript
describe('Ideology Lens State', () => {
  // Lens selection
  test('lens parameter parsed from URL hash', ...)
  test('lens state persists in localStorage', ...)

  // Custom lens
  test('custom lens saves to localStorage', ...)
  test('custom lens loads on page reload', ...)
  test('custom lens name stored correctly', ...)

  // Lens events
  test('lens-change event fires on selection', ...)
  test('event includes new lens ID', ...)

  // All 10 lenses load
  test('all 10 lenses available in dropdown', ...)
  test('neutral is default lens', ...)

  // UI updates
  test('methodology section updates on lens change', ...)
})
```

#### `test_cache_state.js` (8 tests)

```javascript
describe('Client-Side Cache', () => {
  // 5-minute TTL
  test('cache expires after 5 minutes', ...)
  test('expired cache triggers API call', ...)
  test('valid cache prevents API call', ...)

  // Cache keys
  test('cache key includes language', ...)
  test('cache key includes lens', ...)
  test('different language invalidates cache', ...)

  // Cache invalidation
  test('manual force=1 clears cache', ...)
  test('F5 refresh clears cache', ...)
})
```

#### `test_router_state.js` (9 tests)

```javascript
describe('Hash Routing', () => {
  // Section navigation
  test('#painel activates painel section', ...)
  test('#comparativos activates comparativos', ...)
  test('#explorador activates explorador', ...)
  test('#ajuda activates help', ...)
  test('#metodologia activates methodology', ...)

  // Hash parsing
  test('hash includes section name', ...)
  test('invalid hash falls back to painel', ...)

  // Deep linking
  test('deep link with indicator works', ...)
  test('back button navigates history', ...)
})
```

---

## 2.2 Component Tests (vitest + happy-dom)

### Files to Create

```
tests/js/sections/
├── test_painel_rendering.js       # KPI cards, sparklines
├── test_search_bar.js              # Fuzzy search, synonyms
├── test_language_selector.js       # Flag images, dropdown
└── test_chart_rendering.js         # ECharts initialization
```

### Test Cases

#### `test_painel_rendering.js` (14 tests)

```javascript
describe('Painel Section Rendering', () => {
  // Section structure
  test('7 sections render', ...)
  test('each section has name and KPIs', ...)
  test('KPI cards display id, label, value', ...)

  // KPI card data
  test('KPI card shows current value', ...)
  test('KPI card shows YoY change', ...)
  test('KPI card shows sentiment (positive/negative/neutral)', ...)
  test('KPI card shows source label', ...)

  // Sparklines
  test('sparkline SVG renders', ...)
  test('sparkline has 10 data points', ...)
  test('sparkline updates on data change', ...)

  // Catálogo section
  test('Catálogo Completo section loads', ...)
  test('all 422+ indicators visible', ...)
  test('indicators grouped by category', ...)
})
```

#### `test_search_bar.js` (11 tests)

```javascript
describe('Global Search Bar', () => {
  // Fuzzy matching
  test('search finds exact match', ...)
  test('search finds partial match (trigram)', ...)
  test('search is case-insensitive', ...)

  // Synonym expansion
  test('"carro" expands to fuel patterns', ...)
  test('"energia" expands to energy patterns', ...)
  test('"cobre" expands to commodity patterns', ...)

  // Results
  test('search results show indicator name', ...)
  test('search results show category', ...)
  test('click result navigates to Explorador', ...)

  // Keyboard
  test('Ctrl+K opens search bar', ...)
  test('Escape closes search bar', ...)
})
```

#### `test_language_selector.js` (9 tests)

```javascript
describe('Language Selector FAB', () => {
  // Position
  test('FAB positioned at top-right (fixed)', ...)
  test('FAB z-index is 9999', ...)

  // Flags
  test('flag images load from flagcdn.com', ...)
  test('correct ISO code for each language', ...)
  test('PT → pt, CV → cv, EN → gb', ...)

  // Dropdown
  test('dropdown toggles on FAB click', ...)
  test('dropdown shows all 5 languages', ...)
  test('selection updates language state', ...)
  test('tooltip shows "Lingua / Language / Langue"', ...)
})
```

#### `test_chart_rendering.js` (10 tests)

```javascript
describe('ECharts Integration', () => {
  // Chart initialization
  test('ECharts instance created', ...)
  test('chart container exists', ...)
  test('chart renders without errors', ...)

  // Data binding
  test('chart data matches API response', ...)
  test('chart updates on data change', ...)

  // Resize handling
  test('chart resizes on window resize', ...)
  test('chart responsive on mobile', ...)

  // Tooltip
  test('tooltip shows on hover', ...)
  test('tooltip includes value and date', ...)
  test('tooltip styled correctly', ...)
})
```

---

## 2.3 Integration Tests (vitest + happy-dom)

### Files to Create

```
tests/js/integration/
├── test_full_painel_flow.js      # Load → change language → update
├── test_search_to_explore.js     # Search indicator → deep-link
├── test_lens_propagation.js      # Change lens → updates all sections
└── test_responsive_layout.js     # Mobile/tablet/desktop layouts
```

### Test Cases

#### `test_full_painel_flow.js` (8 tests)

```javascript
describe('Full Painel Flow', () => {
  // Load → render
  test('page loads and Painel section renders', ...)
  test('all KPI cards visible on load', ...)
  test('API call completes in <2s', ...)

  // Language change
  test('change language updates localStorage', ...)
  test('language-change event fires', ...)
  test('KPI data re-fetches in new language', ...)

  // UI updates
  test('Painel title translates to new language', ...)
  test('all card labels translate', ...)
})
```

#### `test_search_to_explore.js` (7 tests)

```javascript
describe('Search to Explorador Flow', () => {
  // Search
  test('search returns 5+ results', ...)
  test('results include indicator name and source', ...)

  // Deep link
  test('click result navigates to Explorador', ...)
  test('URL includes indicator parameter', ...)
  test('Explorador loads time series for indicator', ...)

  // Cross-section state
  test('language persists from Painel → Explorador', ...)
  test('lens persists from Painel → Explorador', ...)
})
```

#### `test_lens_propagation.js` (6 tests)

```javascript
describe('Lens Propagation', () => {
  // Methodology section
  test('methodology updates on lens change', ...)
  test('custom lens loads in textarea', ...)

  // Painel analysis
  test('Painel AI analysis updates for new lens', ...)

  // Headlines
  test('headline regenerates for new lens', ...)
  test('headline language matches current language', ...)

  // All sections
  test('all sections show correct lens context', ...)
})
```

#### `test_responsive_layout.js` (6 tests)

```javascript
describe('Responsive Layouts', () => {
  // Mobile
  test('mobile layout: 320px viewport', ...)
  test('mobile: navigation is hamburger menu', ...)
  test('mobile: KPI cards stack vertically', ...)

  // Tablet
  test('tablet layout: 768px viewport', ...)
  test('tablet: 2-column grid for KPIs', ...)

  // Desktop
  test('desktop layout: 1920px viewport', ...)
  test('desktop: 3-column grid for KPIs', ...)
})
```

---

## Setup Requirements

### Install vitest

```bash
npm install -D vitest happy-dom @testing-library/dom
```

### Update vite.config.js

```javascript
import { defineConfig } from 'vite'
import { getViteConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html']
    }
  }
})
```

### Create vitest config (vitest.config.js)

```javascript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['tests/**/*.test.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'tests/']
    }
  }
})
```

---

## Test Fixtures

### Mock Data

```javascript
// tests/fixtures.js
export const mockPanelData = {
  sections: [...],
  updated: '2026-01-31'
}

export const mockLanguages = {
  pt: 'português',
  cv: 'kriolu',
  fr: 'français',
  es: 'español',
  en: 'english'
}

export const mockLenses = [
  'pcp', 'cae', 'be', 'livre', 'pan', 'ps', 'ad', 'il', 'chega', 'neutro'
]
```

### Mock API

```javascript
// tests/mocks.js
import { vi } from 'vitest'

export const mockFetch = vi.fn(async (url) => ({
  json: async () => mockPanelData,
  status: 200
}))
```

---

## Running Tests

```bash
# Run all frontend tests
npm run test:frontend

# Run specific test file
npm run test:frontend -- tests/js/test_language_state.js

# Watch mode (rerun on change)
npm run test:frontend -- --watch

# Coverage report
npm run test:frontend -- --coverage
```

---

## Coverage Goals After Phase 2

| Component | Target | Estimated |
|-----------|--------|-----------|
| Frontend state | 70% | 75% |
| Frontend components | 60% | 65% |
| Overall | 50% | 55% |

---

## Integration with Phase 1

- Phase 1 (backend) tests run via pytest
- Phase 2 (frontend) tests run via vitest
- Both report to CI/CD in Phase 3
- Combined coverage: ~45-55%

---

## Next: Phase 3

After Phase 2 completes, Phase 3 will add:
- GitHub Actions workflows (test.yml, nightly-report.yml)
- Combined pytest + vitest execution
- Coverage reports
- Email notifications
