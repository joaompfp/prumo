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

  // ── Static entries (titles resolved via i18n at render time) ────
  const SECTIONS = [
    { id: 'painel',       icon: '📊', titleKey: 'nav.painel',       subKey: 'search.sections.painel_sub' },
    { id: 'comparativos', icon: '🌍', titleKey: 'nav.comparativos', subKey: 'search.sections.comparativos_sub' },
    { id: 'explorador',   icon: '🔍', titleKey: 'nav.analise',      subKey: 'search.sections.explorador_sub' },
    { id: 'metodologia',  icon: '📄', titleKey: 'nav.metodologia',  subKey: 'search.sections.metodologia_sub' },
    { id: 'ajuda',        icon: '❓', titleKey: 'nav.ajuda',        subKey: 'search.sections.ajuda_sub' },
  ];

  const HELP_TOPICS = [
    { key: 'search.help.what_is',          section: 'ajuda' },
    { key: 'search.help.real_time',        section: 'ajuda' },
    { key: 'search.help.seasonal',         section: 'ajuda' },
    { key: 'search.help.use_in_report',    section: 'ajuda' },
    { key: 'search.help.eu27',             section: 'ajuda' },
    { key: 'search.help.ai_analysis',      section: 'ajuda' },
    { key: 'search.help.grey_countries',   section: 'ajuda' },
    { key: 'search.help.composite',        section: 'ajuda' },
    { key: 'search.help.embed',            section: 'metodologia' },
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

    // ── COMBUSTÍVEIS / CARBURANTES (Carro, combustível patterns) ──
    carro:         ['diesel','gasoline','gasolina','gasóleo','gasoleo','lpg','combustível','fuel','petrol','auto','vehicle'],
    carros:        ['diesel','gasoline','gasolina','gasóleo','gasoleo','lpg','combustível','fuel','petrol','auto','vehicles'],
    diesel:        ['road_fuels_diesel','price_diesel','diesel_pretax','petroleum_diesel','carro','combustível','fuel'],
    gasoline:      ['road_fuels_gasoline','price_gasoline','gasoline_pretax','gasolina','fuel','combustível'],
    gasolina:      ['gasoline','road_fuels_gasoline','price_gasoline','combustível','fuel','petrol'],
    lpg:           ['road_fuels_lpg','price_lpg_auto','lpg_auto','combustível','gas','propane','butane'],
    combustível:   ['diesel','gasoline','gasolina','gasóleo','lpg','fuel','petrol','carro','preço combustível'],
    combustivel:   ['diesel','gasoline','gasolina','gasóleo','lpg','fuel','petrol','carro','preço combustível'],
    'preco_combustivel': ['price_diesel','price_gasoline','price_lpg_auto','fuel price','combustível'],
    'preco_fuel':  ['price_diesel','price_gasoline','price_lpg_auto','preco_combustivel','diesel','gasoline'],

    // ── ELETRICIDADE / ENERGIA ELÉTRICA (Luz, tarifa patterns) ──
    tarifa:        ['electricidade','eletricidade','energia','electricity','preco_eletricidade','access','btn'],
    tarifas:       ['electricidade','eletricidade','energia','electricity','preco_eletricidade','access','btn'],
    'preco_eletricidade': ['access','btn','tarifa','electricity','electricidade','energy price'],
    'preco_energia': ['access','btn','tarifa','electricity','energy','renewable','wind','solar'],
    eléctrica:     ['eletricidade','electricity','energia','light','power','tarifa','access'],
    electrica:     ['eletricidade','electricity','energia','light','power','tarifa','access'],
    access:        ['electricidade','eletricidade','tarifa','price','consumption','btn'],
    btn:           ['access','electricidade','eletricidade','tarifa','consumption','energy'],

    // ── ENERGIAS RENOVÁVEIS ──
    renovável:     ['renewable','solar','wind','hydro','biomass','capacity','geothermal'],
    renovavel:     ['renewable','solar','wind','hydro','biomass','capacity','geothermal'],
    solar:         ['capacity_solar_pv','renewable','wind','hydro','energy','capacity'],
    vento:         ['wind','capacity_wind','renewable','hydro','solar','energy','capacity'],
    hídrica:       ['hydro','capacity_hydro','renewable','water','dam','wind','solar'],
    hidrica:       ['hydro','capacity_hydro','renewable','water','dam','wind','solar'],

    // ── CONSUMO (Consumo patterns) ──
    consumo:       ['consumption','consumir','energia','electricity','gas','petróleo','water','demand'],
    consumir:      ['consumo','consumption','demand','usage'],
    consumos:      ['consumo','consumption','demand','usage'],

    // ── INDÚSTRIA / PRODUÇÃO (Fabrico, indústria patterns) ──
    fabrico:       ['manufacturing','production','indústria','industria','fábricas','fabricas','ipi'],
    produção:      ['producao','production','industrial','manufacturing','indústria','industria'],
    producao:      ['produção','production','industrial','manufacturing','indústria','industria'],
    'producao_industrial': ['industrial_production','ipi','manufacturing','production'],
    'producao_ind': ['industrial_production','ipi','manufacturing','production'],

    // ── COMMODITIES (Metais, preços patterns) ──
    cobre:         ['copper','commodity','metal','price','mine'],
    alumínio:      ['aluminum','aluminio','metal','commodity','price'],
    aluminio:      ['aluminum','metal','commodity','price','alumínio'],
    ferro:         ['iron','iron_ore','commodity','metal','steel','price'],
    aço:           ['steel','commodity','metal','iron','price'],
    ouro:          ['gold','commodity','precious','metal','price'],
    prata:         ['silver','commodity','precious','metal','price'],
    níquel:        ['nickel','commodity','metal','price'],
    niquel:        ['nickel','commodity','metal','price','níquel'],
    zinco:         ['zinc','commodity','metal','price'],

    // ── AGRÍCOLA / COMMODITIES AGRÍCOLAS ──
    milho:         ['corn','commodity','agricultural','price','grain'],
    trigo:         ['wheat','commodity','agricultural','price','grain'],
    soja:          ['soybean','commodity','agricultural','price','grain'],
    açúcar:        ['sugar','commodity','agricultural','price'],
    acucar:        ['sugar','commodity','agricultural','price','açúcar'],
    algodão:       ['cotton','commodity','agricultural','price'],
    algodao:       ['cotton','commodity','agricultural','price','algodão'],
    café:          ['coffee','commodity','agricultural','price'],
    cafe:          ['coffee','commodity','agricultural','price','café'],

    // ── COMMODITIES ENERGÉTICAS ──
    brent:        ['oil','crude','petroleum','price','commodity','energy'],
    crude:        ['oil','brent','petroleum','energy','commodity'],
    carvao:       ['coal','combustível','fuel','energy','consumption'],
    'gas_natural': ['natural_gas','fuel','energy','consumption','gas','combustível'],
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

    // Re-render search results when UI language changes
    window.addEventListener('i18n-change', () => {
      if (_input && _input.value.trim()) render(_input.value);
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
    const secMatches = SECTIONS.filter(s => {
      const title = i18n.t(s.titleKey).toLowerCase();
      const sub   = i18n.t(s.subKey).toLowerCase();
      return title.includes(q) || sub.includes(q) || s.id.includes(q);
    });
    if (secMatches.length) {
      html += `<div class="search-group-label">${i18n.t('search.group_sections')}</div>`;
      for (const s of secMatches) {
        html += itemHTML(s.icon, i18n.t(s.titleKey), i18n.t(s.subKey), null, `nav:${s.id}`);
        count++;
      }
    }

    // 2. Help topics
    const helpMatches = HELP_TOPICS.filter(h => i18n.t(h.key).toLowerCase().includes(q));
    if (helpMatches.length) {
      html += `<div class="search-group-label">${i18n.t('search.group_help')}</div>`;
      for (const h of helpMatches) {
        html += itemHTML('❓', i18n.t(h.key), '', null, `nav:${h.section}`);
        count++;
      }
    }

    // 3. Indicators — synonym expansion + fuzzy fallback (max 15)
    const alias = SRC_ALIASES[q] || '';
    const terms = _expandQuery(q);
    const FUZZY_THRESHOLD = 0.45;

    // Score each indicator: label match > indicator code match > description-only match > fuzzy
    const scored = [];
    for (const item of _flatIndicators) {
      const lbl  = item.label.toLowerCase();
      const code = item.indicator.toLowerCase();
      const src  = item.source.toLowerCase();
      const desc = item.description.toLowerCase();
      const hay  = [lbl, src, code, desc].join(' ');

      // Tiered scoring: label/code match ranks above description-only match
      let score = 0;
      for (const t of terms) {
        if (lbl.includes(t))       { score = Math.max(score, 3); }
        else if (code.includes(t)) { score = Math.max(score, 2.5); }
        else if (hay.includes(t))  { score = Math.max(score, 1); }
      }
      if (!score && alias && hay.includes(alias)) score = 1;

      // Bonus: original query (not synonym) matches label directly
      if (lbl.includes(q)) score += 1;

      if (score > 0) {
        scored.push({ item, score });
      } else if (q.length >= 3) {
        // Fuzzy only for queries ≥3 chars — score against label + description
        const fs = Math.max(
          _fuzzyScore(q, lbl),
          _fuzzyScore(q, desc) * 0.8
        );
        if (fs >= FUZZY_THRESHOLD) scored.push({ item, score: fs });
      }
    }
    scored.sort((a, b) => b.score - a.score);
    const indMatches = scored.slice(0, 15).map(s => s.item);

    if (indMatches.length) {
      html += `<div class="search-group-label">${i18n.t('search.group_indicators')}</div>`;
      for (const item of indMatches) {
        html += itemHTML('📈', item.label, item.sourceLabel, item.unit,
          `ind:${item.source}/${item.indicator}`);
        count++;
      }
    }

    if (count === 0) {
      html = `<div class="search-no-results">${i18n.t('search.no_results', { query: esc(rawQuery) })}</div>`;
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
