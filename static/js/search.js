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

  // ── Synonym dictionary — maps popular search terms → indicator keywords ──
  // Each key expands the search to also match any of its synonym values
  const SEARCH_SYNONYMS = {
    // Habitação / imobiliário
    casa:        ['habitação','habitacao','imobiliário','imobiliario','rendas','arrendamento','alojamento','housing','hpi','dwellings'],
    casas:       ['habitação','habitacao','imobiliário','imobiliario','rendas','arrendamento','alojamento','housing','hpi'],
    renda:       ['arrendamento','habitação','habitacao','rendas','alojamento','housing'],
    rendas:      ['arrendamento','habitação','habitacao','alojamento','housing'],
    habitação:   ['casa','casas','imobiliário','imobiliario','arrendamento','housing','hpi','dwellings'],
    habitacao:   ['casa','casas','imobiliário','imobiliario','arrendamento','housing','hpi','dwellings'],
    imobiliário: ['habitação','habitacao','casa','casas','hpi','housing','dwellings'],
    imobiliario: ['habitação','habitacao','casa','casas','hpi','housing','dwellings'],

    // Energia / eletricidade / gás
    luz:           ['electricidade','eletricidade','energia','electricity','kwh','preço energia','tarifas'],
    eletricidade:  ['electricidade','energia','electricity','kwh','luz','tarifas'],
    electricidade: ['eletricidade','energia','electricity','kwh','luz','tarifas'],
    energia:       ['electricidade','eletricidade','electricity','gás','gas','renováveis','renovaveis','kwh'],
    gás:           ['gas','energia','natural gas','combustíveis','combustiveis'],
    gas:           ['gás','energia','natural gas','combustíveis','combustiveis'],
    gasolina:      ['combustíveis','combustiveis','gasóleo','gasoleo','petróleo','petroleo','fuel','oil'],
    gasóleo:       ['combustíveis','combustiveis','gasolina','petróleo','petroleo','fuel','diesel'],
    gasoleo:       ['combustíveis','combustiveis','gasolina','petróleo','petroleo','fuel','diesel'],
    combustível:   ['gasolina','gasóleo','gasoleo','petróleo','petroleo','fuel','oil'],
    combustivel:   ['gasolina','gasóleo','gasoleo','petróleo','petroleo','fuel','oil'],
    petróleo:      ['oil','crude','brent','gasolina','combustíveis','combustiveis'],
    petroleo:      ['oil','crude','brent','gasolina','combustíveis','combustiveis'],

    // Emprego / trabalho
    emprego:       ['desemprego','trabalho','employment','unemployment','taxa emprego','ocupação','ocupacao'],
    desemprego:    ['emprego','unemployment','taxa desemprego','jobless'],
    trabalho:      ['emprego','desemprego','employment','salários','salarios','horas','earnings'],
    salário:       ['salários','salarios','wages','earnings','remuneração','remuneracao','rendimento'],
    salario:       ['salários','salarios','wages','earnings','remuneração','remuneracao','rendimento'],
    salários:      ['salário','wages','earnings','remuneração','remuneracao','rendimento'],
    salarios:      ['salário','wages','earnings','remuneração','remuneracao','rendimento'],
    ordenado:      ['salário','salarios','wages','earnings','rendimento','remuneração'],

    // Preços / inflação
    preços:        ['inflação','inflacao','ipc','cpi','hicp','preço','price','prices'],
    precos:        ['inflação','inflacao','ipc','cpi','hicp','preço','price','prices'],
    inflação:      ['ipc','cpi','hicp','preços','precos','price index','deflator'],
    inflacao:      ['ipc','cpi','hicp','preços','precos','price index','deflator'],
    carestia:      ['inflação','inflacao','ipc','cpi','preços','precos'],
    custo:         ['preços','precos','inflação','inflacao','custo de vida','despesa'],

    // PIB / crescimento
    pib:           ['gdp','produto interno bruto','crescimento','growth','economia'],
    gdp:           ['pib','produto interno bruto','crescimento','growth'],
    crescimento:   ['pib','gdp','growth','expansão','expansao'],
    economia:      ['pib','gdp','crescimento','growth','produção','producao'],
    recessão:      ['pib','gdp','contração','contracao','crise','recession'],
    recessao:      ['pib','gdp','contração','contracao','crise','recession'],

    // Dívida / finanças públicas
    dívida:        ['divida','debt','défice','deficit','finanças públicas','financas publicas'],
    divida:        ['dívida','debt','défice','deficit','finanças públicas','financas publicas'],
    défice:        ['deficit','dívida','divida','debt','saldo orçamental'],
    deficit:       ['défice','dívida','divida','debt','saldo orçamental'],

    // Indústria / produção
    fábricas:      ['fabricas','indústria','industria','produção industrial','ipi','manufacturing'],
    fabricas:      ['fábricas','indústria','industria','produção industrial','ipi','manufacturing'],
    indústria:     ['industria','produção industrial','manufacturing','ipi','fábricas','fabricas'],
    industria:     ['indústria','produção industrial','manufacturing','ipi','fábricas','fabricas'],

    // Comércio
    exportações:   ['exportacoes','exports','comércio','comercio','balança comercial','trade'],
    exportacoes:   ['exportações','exports','comércio','comercio','balança comercial','trade'],
    importações:   ['importacoes','imports','comércio','comercio','balança comercial','trade'],
    importacoes:   ['importações','imports','comércio','comercio','balança comercial','trade'],

    // Turismo
    turismo:       ['tourism','turistas','alojamento','hóspedes','hospedes','dormidas'],
    turistas:      ['turismo','tourism','hóspedes','hospedes','dormidas'],

    // Educação
    escola:        ['educação','educacao','escolaridade','education','ensino','alunos'],
    educação:      ['educacao','escola','escolaridade','education','ensino'],
    educacao:      ['educação','escola','escolaridade','education','ensino'],

    // Saúde
    saúde:         ['saude','health','hospitais','esperança de vida','mortalidade'],
    saude:         ['saúde','health','hospitais','esperança de vida','mortalidade'],
    hospital:      ['saúde','saude','health','hospitais','mortalidade'],

    // Demografia
    população:     ['populacao','population','demografia','natalidade','mortalidade','emigração','imigracao'],
    populacao:     ['população','population','demografia','natalidade','mortalidade','emigração','imigracao'],
    nascimentos:   ['natalidade','população','populacao','fertilidade','fertility'],
    emigração:     ['emigracao','imigração','imigracao','migração','migracao','population'],
    emigracao:     ['emigração','imigração','imigracao','migração','migracao','population'],

    // Pobreza / desigualdade
    pobreza:       ['poverty','desigualdade','gini','risco de pobreza','exclusão social'],
    desigualdade:  ['gini','pobreza','poverty','inequality','rendimento'],
    pobres:        ['pobreza','poverty','risco de pobreza','exclusão social'],
  };

  // ── Trigram fuzzy scoring ──────────────────────────────────────
  function _trigrams(s) {
    const t = new Set();
    const p = ` ${s} `;
    for (let i = 0; i < p.length - 2; i++) t.add(p.slice(i, i + 3));
    return t;
  }
  function _fuzzyScore(query, text) {
    if (text.includes(query)) return 1;
    const qt = _trigrams(query), tt = _trigrams(text);
    let shared = 0;
    for (const t of qt) if (tt.has(t)) shared++;
    return shared / qt.size;
  }

  // ── Expand query into [original + synonym terms] ─────────────
  function _expandQuery(q) {
    const terms = [q];
    // Check if any synonym key is contained in the query (or equals it)
    for (const [key, syns] of Object.entries(SEARCH_SYNONYMS)) {
      if (q === key || q.includes(key)) {
        for (const s of syns) if (!terms.includes(s)) terms.push(s);
      }
    }
    return terms;
  }

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

    // 3. Indicators — synonym expansion + fuzzy fallback (max 15)
    const alias = SRC_ALIASES[q] || '';
    const terms = _expandQuery(q);
    const FUZZY_THRESHOLD = 0.45;

    // Score each indicator: 1 = exact/synonym hit, 0..1 = fuzzy
    const scored = [];
    for (const item of _flatIndicators) {
      const hay = [
        item.label.toLowerCase(),
        item.source.toLowerCase(),
        item.indicator.toLowerCase(),
        item.description.toLowerCase(),
      ].join(' ');

      // Exact / synonym match — check all expanded terms
      let exact = false;
      for (const t of terms) {
        if (hay.includes(t)) { exact = true; break; }
      }
      if (!exact && alias && hay.includes(alias)) exact = true;

      if (exact) {
        scored.push({ item, score: 1 });
      } else if (q.length >= 3) {
        // Fuzzy only for queries ≥3 chars — score against label + description
        const fs = Math.max(
          _fuzzyScore(q, item.label.toLowerCase()),
          _fuzzyScore(q, item.description.toLowerCase()) * 0.8
        );
        if (fs >= FUZZY_THRESHOLD) scored.push({ item, score: fs });
      }
    }
    scored.sort((a, b) => b.score - a.score);
    const indMatches = scored.slice(0, 15).map(s => s.item);

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
