/* ═══════════════════════════════════════════════════════════════
   search.js — Global Search Bar (Ctrl+K / Cmd+K)
   Inline bar below nav — searches indicators, sections, help
   ═══════════════════════════════════════════════════════════════ */

const Search = (() => {
  const BASE = window.__BASE_PATH__ || '';

  let _input, _results;
  let _catalog = null;
  let _flatIndicators = [];
  let _activeIdx = -1;
  let _items = [];
  let _catalogLoading = false;

  // ── Static entries ──────────────────────────────────────────────
  const SECTIONS = [
    { id: 'painel',       icon: '📊', title: 'Painel',       sub: 'Indicadores-chave de Portugal' },
    { id: 'comparativos', icon: '🌍', title: 'Comparativos', sub: 'PT vs Europa e Mundo' },
    { id: 'explorador',   icon: '🔍', title: 'Análise',      sub: 'Explorador de séries temporais' },
    { id: 'metodologia',  icon: '📄', title: 'Metodologia',  sub: 'Como as análises IA são geradas' },
    { id: 'ajuda',        icon: '❓', title: 'Ajuda',        sub: 'O que é o Prumo, guia, FAQ' },
  ];

  const HELP_TOPICS = [
    { q: 'O que é o Prumo PT',             section: 'ajuda' },
    { q: 'Dados em tempo real',             section: 'ajuda' },
    { q: 'Ajustamento sazonal',             section: 'ajuda' },
    { q: 'Usar dados num relatório',        section: 'ajuda' },
    { q: 'EU27_2020',                       section: 'ajuda' },
    { q: 'Análise com IA',                  section: 'ajuda' },
    { q: 'Países a cinzento',               section: 'ajuda' },
    { q: 'Indicadores compostos',           section: 'ajuda' },
    { q: 'Embed — incorporar gráfico',      section: 'metodologia' },
  ];

  const SRC_ALIASES = {
    ocde: 'oecd', oecd: 'ocde',
    'banco mundial': 'worldbank', worldbank: 'banco mundial',
    'banco de portugal': 'bportugal', bportugal: 'banco de portugal',
  };

  // ── Init ──────────────────────────────────────────────────────
  function init() {
    _input   = document.getElementById('search-input');
    _results = document.getElementById('search-results');
    if (!_input || !_results) return;

    // Keyboard shortcut: Ctrl+K / ⌘K
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        _input.focus();
        _input.select();
      }
    });

    // Keyboard nav inside input
    _input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { _input.blur(); clear(); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); return; }
      if (e.key === 'ArrowUp')   { e.preventDefault(); moveActive(-1); return; }
      if (e.key === 'Enter') {
        e.preventDefault();
        if (_items[_activeIdx]) _items[_activeIdx].click();
        return;
      }
    });

    // Search on input
    _input.addEventListener('input', () => {
      fetchCatalogOnce();
      render(_input.value);
    });

    // Focus — fetch catalog eagerly
    _input.addEventListener('focus', fetchCatalogOnce);

    // Close results on outside click
    document.addEventListener('mousedown', (e) => {
      const bar = document.getElementById('search-bar');
      if (bar && !bar.contains(e.target)) clear();
    });
  }

  // ── Lazy catalog fetch ────────────────────────────────────────
  async function fetchCatalogOnce() {
    if (_catalog || _catalogLoading) return;
    _catalogLoading = true;
    try {
      const r = await fetch(`${BASE}/api/catalog`);
      _catalog = await r.json();
      _flatIndicators = [];
      for (const [src, srcInfo] of Object.entries(_catalog)) {
        for (const [ind, indInfo] of Object.entries(srcInfo.indicators || {})) {
          _flatIndicators.push({
            source: src,
            sourceLabel: srcInfo.label || src,
            indicator: ind,
            label: indInfo.label || ind,
            description: indInfo.description || '',
            unit: indInfo.unit || '',
          });
        }
      }
      // Re-render if there's a pending query
      if (_input.value.trim()) render(_input.value);
    } catch (_) { /* catalog unavailable */ }
    _catalogLoading = false;
  }

  function clear() {
    _results.innerHTML = '';
    _items = [];
    _activeIdx = -1;
  }

  // ── Render results ────────────────────────────────────────────
  function render(rawQuery) {
    const q = rawQuery.toLowerCase().trim();
    _results.innerHTML = '';
    _items = [];
    _activeIdx = -1;

    if (!q) return;

    let html = '';
    let count = 0;

    // 1. Sections
    const secMatches = SECTIONS.filter(s =>
      s.title.toLowerCase().includes(q) ||
      s.sub.toLowerCase().includes(q) ||
      s.id.includes(q)
    );
    if (secMatches.length) {
      html += `<div class="search-group-label">Secções</div>`;
      for (const s of secMatches) {
        html += itemHTML(s.icon, s.title, s.sub, null, `nav:${s.id}`);
        count++;
      }
    }

    // 2. Help topics
    const helpMatches = HELP_TOPICS.filter(h => h.q.toLowerCase().includes(q));
    if (helpMatches.length) {
      html += `<div class="search-group-label">Ajuda</div>`;
      for (const h of helpMatches) {
        html += itemHTML('❓', h.q, '', null, `nav:${h.section}`);
        count++;
      }
    }

    // 3. Indicators (max 15)
    const alias = SRC_ALIASES[q] || '';
    const indMatches = _flatIndicators.filter(item => {
      const srcLower = item.source.toLowerCase();
      return item.label.toLowerCase().includes(q) ||
             srcLower.includes(q) ||
             (alias && srcLower.includes(alias)) ||
             item.indicator.toLowerCase().includes(q) ||
             item.description.toLowerCase().includes(q);
    }).slice(0, 15);

    if (indMatches.length) {
      html += `<div class="search-group-label">Indicadores</div>`;
      for (const item of indMatches) {
        html += itemHTML('📈', item.label, item.sourceLabel, item.unit,
          `ind:${item.source}/${item.indicator}`);
        count++;
      }
    }

    if (count === 0) {
      html = `<div class="search-no-results">Sem resultados para "${esc(rawQuery)}"</div>`;
    }

    _results.innerHTML = html;
    _items = Array.from(_results.querySelectorAll('.search-item'));

    // Attach click handlers
    _items.forEach(el => {
      el.addEventListener('click', () => {
        const action = el.dataset.action;
        _input.value = '';
        clear();
        _input.blur();
        if (action.startsWith('nav:')) {
          App.navigate(action.slice(4));
        } else if (action.startsWith('ind:')) {
          const parts = action.slice(4);
          window.location.hash = `explorador?s=${encodeURIComponent(parts)}`;
        }
      });
    });
  }

  function itemHTML(icon, title, sub, badge, action) {
    return `<div class="search-item" data-action="${esc(action)}">
      <span class="search-item-icon">${icon}</span>
      <div class="search-item-text">
        <div class="search-item-title">${esc(title)}</div>
        ${sub ? `<div class="search-item-sub">${esc(sub)}</div>` : ''}
      </div>
      ${badge ? `<span class="search-item-badge">${esc(badge)}</span>` : ''}
    </div>`;
  }

  // ── Keyboard navigation ───────────────────────────────────────
  function moveActive(dir) {
    if (!_items.length) return;
    if (_activeIdx >= 0) _items[_activeIdx].classList.remove('active');
    _activeIdx += dir;
    if (_activeIdx < 0) _activeIdx = _items.length - 1;
    if (_activeIdx >= _items.length) _activeIdx = 0;
    _items[_activeIdx].classList.add('active');
    _items[_activeIdx].scrollIntoView({ block: 'nearest' });
  }

  // ── Escape HTML ───────────────────────────────────────────────
  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  return { init };
})();

window.Search = Search;

document.addEventListener('DOMContentLoaded', () => {
  Search.init();
});
