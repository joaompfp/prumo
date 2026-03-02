/* =================================================================
   comparativos.js — PT vs Europa + PT vs Mundo (unified)
   CAE Dashboard V10 — all countries, dynamic catalog, composite sources
   ================================================================= */

let _cmpChart = null;

App.registerSection('comparativos', async () => {
  const container  = document.getElementById('comparativos');
  const body       = container.querySelector('.section-body');
  const BASE       = window.__BASE_PATH__ || '';

  // ── Country definitions ────────────────────────────────────────
  const FLAGS = {
    PT:'🇵🇹', ES:'🇪🇸', DE:'🇩🇪', FR:'🇫🇷', IT:'🇮🇹', NL:'🇳🇱', BE:'🇧🇪',
    AT:'🇦🇹', LU:'🇱🇺', PL:'🇵🇱', CZ:'🇨🇿', SK:'🇸🇰', HU:'🇭🇺', RO:'🇷🇴',
    BG:'🇧🇬', HR:'🇭🇷', SI:'🇸🇮', EE:'🇪🇪', LV:'🇱🇻', LT:'🇱🇹', SE:'🇸🇪',
    DK:'🇩🇰', FI:'🇫🇮', IE:'🇮🇪', EL:'🇬🇷', GR:'🇬🇷', CY:'🇨🇾', MT:'🇲🇹',
    EU27:'🇪🇺', EU27_2020:'🇪🇺', EU:'🇪🇺',
    GB:'🇬🇧', NO:'🇳🇴', CH:'🇨🇭', TR:'🇹🇷',
    US:'🇺🇸', CA:'🇨🇦', JP:'🇯🇵', KR:'🇰🇷', AU:'🇦🇺', MX:'🇲🇽',
    AO:'🇦🇴', MZ:'🇲🇿', CV:'🇨🇻', GW:'🇬🇼', ST:'🇸🇹',
    CN:'🇨🇳', IN:'🇮🇳', BR:'🇧🇷', ZA:'🇿🇦', AR:'🇦🇷', CL:'🇨🇱', RU:'🇷🇺',
    NG:'🇳🇬', EG:'🇪🇬', ID:'🇮🇩', TH:'🇹🇭', MY:'🇲🇾',
  };

  const COUNTRY_NAMES = {
    PT:'Portugal',    ES:'Espanha',     DE:'Alemanha',   FR:'França',
    IT:'Itália',      NL:'Países Baixos',BE:'Bélgica',   AT:'Áustria',
    LU:'Luxemburgo',  PL:'Polónia',     CZ:'Chéquia',    SK:'Eslováquia',
    HU:'Hungria',     RO:'Roménia',     BG:'Bulgária',   HR:'Croácia',
    SI:'Eslovénia',   EE:'Estónia',     LV:'Letónia',    LT:'Lituânia',
    SE:'Suécia',      DK:'Dinamarca',   FI:'Finlândia',  IE:'Irlanda',
    EL:'Grécia',      GR:'Grécia',      CY:'Chipre',     MT:'Malta',
    EU27:'UE-27',     EU27_2020:'UE-27', EU:'UE',
    GB:'Grã-Bretanha',NO:'Noruega',     CH:'Suíça',      TR:'Turquia',
    US:'EUA',         CA:'Canadá',      JP:'Japão',      KR:'Coreia do Sul',
    AU:'Austrália',   MX:'México',
    AO:'Angola',      MZ:'Moçambique',  CV:'Cabo Verde', GW:'Guiné-Bissau',
    ST:'São Tomé',
    CN:'China',       IN:'Índia',       BR:'Brasil',     ZA:'África do Sul',
    AR:'Argentina',   CL:'Chile',       RU:'Rússia',
    NG:'Nigéria',     EG:'Egito',       ID:'Indonésia',  TH:'Tailândia',
    MY:'Malásia',
  };

  // Country groups for picker — order matters (displayed top to bottom)
  const COUNTRY_GROUPS = [
    { group: 'REFERÊNCIA',       countries: ['EU27_2020'] },
    { group: 'UE 27',            countries: ['PT','DE','FR','IT','ES','NL','BE','AT','PL','CZ','SK','HU','RO','BG','HR','SI','EE','LV','LT','SE','DK','FI','IE','EL','CY','LU','MT'] },
    { group: 'RESTO DA EUROPA',  countries: ['GB','NO','CH','TR'] },
    { group: 'OCDE (não-EU)',    countries: ['US','CA','JP','KR','MX'] },
    { group: 'PALOP',            countries: ['AO','MZ','CV','GW','ST'] },
    { group: 'EMERGENTES',       countries: ['CN','IN','BR','ZA','AR','CL'] },
    { group: 'OUTROS',           countries: ['NG','EG','ID','TH','MY'] },
  ];

  const ALL_COUNTRIES = COUNTRY_GROUPS.flatMap(g => g.countries);

  const PRESETS = [
    { label: 'PT vs Espanha',   countries: ['PT','ES','EU27_2020'] },
    { label: 'Mediterrâneo',    countries: ['PT','ES','IT','EL','EU27_2020'] },
    { label: 'Nórdicos',        countries: ['PT','SE','DK','FI','NO','EU27_2020'] },
    { label: 'Leste',           countries: ['PT','PL','CZ','HU','RO','SK','BG','EU27_2020'] },
    { label: 'Todos EU',        countries: ['PT','DE','FR','IT','ES','NL','BE','AT','PL','CZ','SK','HU','RO','BG','HR','SI','EE','LV','LT','SE','DK','FI','IE','EL','CY','LU','MT','EU27_2020'] },
    { label: 'G7',              countries: ['PT','US','GB','FR','DE','IT','JP','CA'] },
    { label: 'PALOP',           countries: ['PT','AO','MZ','CV','GW','ST'] },
    { label: 'Emergentes',      countries: ['PT','CN','IN','BR','ZA','AR','CL'] },
  ];

  const LOCKED = new Set(['PT']);

  function countryColor(code) {
    if (LOCKED.has(code)) return '#CC0000';
    if (code.startsWith('EU')) return '#4A90D9';
    return (SWD.COUNTRY_COLORS && SWD.COUNTRY_COLORS[code]) || '#999';
  }

  // ── Fetch indicator catalog ────────────────────────────────────
  let CATALOG = [];
  try {
    const r = await fetch(`${BASE}/api/comparativos/catalog`);
    if (r.ok) CATALOG = await r.json();
  } catch(e) { console.warn('[comparativos] catalog fetch failed', e); }

  if (!CATALOG.length) {
    body.innerHTML = '<p style="padding:2rem;color:var(--c-muted)">Catálogo indisponível.</p>';
    return;
  }

  // ── State ─────────────────────────────────────────────────────
  let _ind         = CATALOG.find(i => i.default) || CATALOG[0];
  let _source      = _ind.source || 'COMPOSITE';
  let _selected    = new Set(['PT','ES','DE','EU27_2020']);
  let _available   = new Set(ALL_COUNTRIES);  // countries with data for current ind
  let _startYear   = 2015;
  let _viewMode    = 'lines';
  let _activePreset = 'PT vs Espanha';

  // Source metadata for display
  const SOURCES_META = {
    'COMPOSITE': { label: 'Compostos ★',   desc: 'Eurostat EU27 + Banco Mundial (cobertura global)' },
    'EUROSTAT':  { label: 'Eurostat',      desc: 'EU27 · alta frequência (mensal/trimestral)' },
    'WORLDBANK': { label: 'Banco Mundial', desc: 'Cobertura global · dados anuais' },
  };

  function buildSourceSelect(active) {
    const present = [...new Set(CATALOG.map(i => i.source))];
    const order = ['COMPOSITE', 'EUROSTAT', 'WORLDBANK'].filter(s => present.includes(s));
    return order.map(s => {
      const m = SOURCES_META[s] || { label: s, desc: '' };
      return `<option value="${s}" ${s === active ? 'selected' : ''}>${m.label} — ${m.desc}</option>`;
    }).join('');
  }

  function buildIndicatorSelect(src, activeId) {
    const filtered = CATALOG.filter(i => i.source === src);
    const groups = {}, order = [];
    for (const ind of filtered) {
      const g = ind.group || 'Outros';
      if (!groups[g]) { groups[g] = []; order.push(g); }
      groups[g].push(ind);
    }
    return order.map(g =>
      `<optgroup label="${g}">${
        filtered.filter(i => i.group === g).map(i =>
          `<option value="${i.id}" ${i.id === activeId ? 'selected' : ''}>${i.label}</option>`
        ).join('')
      }</optgroup>`
    ).join('');
  }

  // ── Fetch available countries for current indicator ────────────
  async function fetchAvailableCountries() {
    try {
      const url = `${BASE}/api/comparativos/countries?source=${encodeURIComponent(_ind.source)}&indicator=${encodeURIComponent(_ind.indicator)}`;
      const r = await fetch(url);
      if (r.ok) {
        const list = await r.json();
        _available = new Set(list);
        // EL and GR are the same (Greece in different conventions)
        if (_available.has('EL')) _available.add('GR');
        if (_available.has('GR')) _available.add('EL');
      }
    } catch(e) { _available = new Set(ALL_COUNTRIES); }
  }

  // ── URL hash ──────────────────────────────────────────────────
  function buildHash() {
    return `#comparativos?ind=${_ind.id}&countries=${[..._selected].join(',')}&since=${_startYear}&view=${_viewMode}`;
  }
  function pushHash() { try { history.replaceState(null, '', buildHash()); } catch(_) {} }

  function parseHash() {
    const h = location.hash;
    if (!h.startsWith('#comparativos?') && !h.startsWith('#europa?') && !h.startsWith('#mundo?')) return null;
    const q = h.includes('?') ? h.slice(h.indexOf('?') + 1) : '';
    const p = new URLSearchParams(q);
    return {
      ind:       p.get('ind'),
      countries: p.get('countries') ? p.get('countries').split(',') : null,
      since:     parseInt(p.get('since') || '2015', 10),
      view:      p.get('view') || 'lines',
    };
  }

  const hashState = parseHash();
  if (hashState) {
    const found = hashState.ind ? CATALOG.find(i => i.id === hashState.ind) : null;
    if (found) { _ind = found; _source = found.source || 'COMPOSITE'; }
    if (hashState.countries) {
      _selected = new Set(hashState.countries);
      LOCKED.forEach(c => _selected.add(c));
    }
    if (!isNaN(hashState.since)) _startYear = hashState.since;
    _viewMode = ['lines','snapshot'].includes(hashState.view) ? hashState.view : 'lines';
    _activePreset = null;
  }

  // Fetch available countries for initial indicator
  await fetchAvailableCountries();

  // ── Render skeleton ───────────────────────────────────────────
  body.innerHTML = `
    <div class="cmp-top-bar">
      <div class="cmp-source-row">
        <label class="control-label" for="cmp-source-select">FONTE</label>
        <select class="swd-select" id="cmp-source-select" style="min-width:220px">
          ${buildSourceSelect(_source)}
        </select>
      </div>
      <div class="cmp-ind-row">
        <label class="control-label" for="cmp-ind-select">INDICADOR</label>
        <select class="swd-select" id="cmp-ind-select" style="flex:1;min-width:200px;max-width:420px">
          ${buildIndicatorSelect(_source, _ind.id)}
        </select>
      </div>
      <div class="cmp-top-bar-right">
        <div class="eu-view-tabs" id="cmp-view-tabs">
          <button class="eu-view-tab ${_viewMode==='lines'?'active':''}"    data-view="lines">Linhas</button>
          <button class="eu-view-tab ${_viewMode==='snapshot'?'active':''}" data-view="snapshot">Snapshot</button>
        </div>
        <button class="share-btn" id="cmp-share">Partilhar</button>
      </div>
    </div>

    <div class="cmp-presets" id="cmp-presets">
      ${PRESETS.map(p =>
        `<button class="preset-chip${_activePreset===p.label?' active':''}" data-preset="${p.label}">${p.label}</button>`
      ).join('')}
      <select class="europa-since-select" id="cmp-since">
        <option value="2000" ${_startYear===2000?'selected':''}>Desde 2000</option>
        <option value="2010" ${_startYear===2010?'selected':''}>Desde 2010</option>
        <option value="2015" ${_startYear===2015?'selected':''}>Desde 2015</option>
        <option value="2018" ${_startYear===2018?'selected':''}>Desde 2018</option>
        <option value="2020" ${_startYear===2020?'selected':''}>Desde 2020</option>
      </select>
    </div>

    <details class="cmp-picker-details" id="cmp-picker-details">
      <summary class="cmp-picker-summary">
        <span class="cmp-picker-arrow">▶</span>
        <span class="cmp-picker-label">PAÍSES SELECCIONADOS</span>
      </summary>
      <div class="cmp-picker-body" id="cmp-picker-body"></div>
    </details>

    <div id="cmp-note" style="font-size:11px;color:var(--c-muted);margin-bottom:4px;min-height:16px"></div>
    <div id="cmp-legend" class="inline-legend" style="margin-bottom:var(--sp-md)"></div>
    <div class="chart-card" style="padding:var(--sp-lg)">
      <div class="chart-container tall" id="cmp-chart"></div>
    </div>
    <div class="footnote" id="cmp-footnote"></div>`;

  // ── Country picker rendering ───────────────────────────────────
  function renderPicker() {
    const body = document.getElementById('cmp-picker-body');
    body.innerHTML = COUNTRY_GROUPS.map(g => `
      <div class="eu-picker-group">
        <div class="eu-picker-label">${g.group}</div>
        <div class="eu-picker-row">
          ${g.countries.map(code => {
            const isSelected  = _selected.has(code);
            const isLocked    = LOCKED.has(code);
            const isAvailable = _available.has(code);
            const color       = countryColor(code);
            const style = isSelected
              ? `background:${color};border-color:${color};color:#fff;`
              : !isAvailable ? 'opacity:0.25;cursor:default;' : '';
            const classes = ['country-chip',
              isSelected  ? 'selected' : '',
              !isAvailable ? 'unavailable' : '',
            ].filter(Boolean).join(' ');
            return `<div class="${classes}" style="${style}" data-code="${code}"
                         title="${COUNTRY_NAMES[code] || code}${!isAvailable ? ' (sem dados)' : ''}">
              <span class="chip-flag">${FLAGS[code] || ''}</span>
              <span class="chip-code">${code === 'EU27_2020' ? 'EU27' : code}</span>
            </div>`;
          }).join('')}
        </div>
      </div>`
    ).join('');

    // Click handlers
    body.querySelectorAll('.country-chip:not(.unavailable)').forEach(chip => {
      chip.addEventListener('click', () => {
        const code = chip.dataset.code;
        if (LOCKED.has(code)) return;
        if (_selected.has(code)) {
          _selected.delete(code);
        } else {
          _selected.add(code);
        }
        _activePreset = null;
        document.querySelectorAll('#cmp-presets .preset-chip').forEach(b => b.classList.remove('active'));
        renderPicker();
        loadData();
      });
    });
  }

  renderPicker();

  // ── Source change (cascade: updates indicator select) ─────────
  document.getElementById('cmp-source-select').addEventListener('change', async e => {
    _source = e.target.value;
    // Pick first indicator of new source, or keep current if same source
    const first = CATALOG.find(i => i.source === _source);
    if (first) _ind = first;
    // Rebuild indicator dropdown
    document.getElementById('cmp-ind-select').innerHTML = buildIndicatorSelect(_source, _ind.id);
    await fetchAvailableCountries();
    for (const c of [..._selected]) {
      if (!_available.has(c) && !LOCKED.has(c)) _selected.delete(c);
    }
    renderPicker();
    updateNote();
    loadData();
  });

  // ── Indicator change ──────────────────────────────────────────
  document.getElementById('cmp-ind-select').addEventListener('change', async e => {
    _ind = CATALOG.find(i => i.id === e.target.value) || CATALOG[0];
    await fetchAvailableCountries();
    // Remove selected countries that are now unavailable
    for (const c of [..._selected]) {
      if (!_available.has(c) && !LOCKED.has(c)) _selected.delete(c);
    }
    renderPicker();
    updateNote();
    loadData();
  });

  // ── View tabs ─────────────────────────────────────────────────
  document.getElementById('cmp-view-tabs').addEventListener('click', e => {
    const btn = e.target.closest('[data-view]');
    if (!btn) return;
    _viewMode = btn.dataset.view;
    document.querySelectorAll('#cmp-view-tabs .eu-view-tab').forEach(b =>
      b.classList.toggle('active', b.dataset.view === _viewMode)
    );
    loadData();
  });

  // ── Presets ───────────────────────────────────────────────────
  document.getElementById('cmp-presets').addEventListener('click', e => {
    const btn = e.target.closest('[data-preset]');
    if (!btn) return;
    const preset = PRESETS.find(p => p.label === btn.dataset.preset);
    if (!preset) return;
    // BUG-1 FIX: include ALL preset countries regardless of _available.
    // Filtering here caused PALOP/non-EU countries to be silently dropped
    // when the current indicator was EUROSTAT-only (e.g. unemployment).
    _selected = new Set(preset.countries);
    LOCKED.forEach(c => _selected.add(c));
    _activePreset = preset.label;
    document.querySelectorAll('#cmp-presets .preset-chip').forEach(b =>
      b.classList.toggle('active', b.dataset.preset === _activePreset)
    );
    renderPicker();
    loadData();
  });

  // ── Since year ────────────────────────────────────────────────
  document.getElementById('cmp-since').addEventListener('change', e => {
    _startYear = parseInt(e.target.value, 10);
    loadData();
  });

  // ── Share ─────────────────────────────────────────────────────
  document.getElementById('cmp-share').addEventListener('click', () => {
    const url = location.origin + location.pathname + buildHash();
    navigator.clipboard.writeText(url).then(
      () => App.showToast('Link copiado!'),
      () => App.showToast('Link: ' + url)
    );
  });

  function updateNote() {
    const note = document.getElementById('cmp-note');
    if (!note) return;
    if (_ind.source === 'COMPOSITE') {
      note.textContent = `★ Indicador composto: ${_ind.note || 'Eurostat EU27 + Banco Mundial (global)'}`;
    } else if (_ind.source === 'WORLDBANK') {
      note.textContent = 'Fonte: Banco Mundial · dados anuais · cobertura global';
    } else {
      note.textContent = '';
    }
  }

  updateNote();

  // ── Data fetch + render ───────────────────────────────────────
  async function loadData() {
    const countriesStr = [..._selected].join(',');
    if (!countriesStr) return;
    pushHash();

    document.getElementById('cmp-legend').innerHTML =
      `<div class="loading-state" style="height:32px"><div class="loading-spinner"></div><span>A carregar…</span></div>`;

    try {
      const url = `/api/comparativos/data?source=${encodeURIComponent(_ind.source)}&indicator=${encodeURIComponent(_ind.indicator)}&countries=${countriesStr}&since=${_startYear}`;
      const data = await API.get(url);

      let series = (data.series || []).map(s => ({
        country: s.country,
        label:   COUNTRY_NAMES[s.country] || s.label || s.country,
        data:    (s.data || []).filter(d => parseInt((d.period || '').slice(0,4), 10) >= _startYear),
      })).filter(s => s.data.length > 0);

      if (!series.length) {
        document.getElementById('cmp-legend').innerHTML =
          `<span style="color:var(--c-muted)">Sem dados para os países/indicador seleccionados.</span>`;
        return;
      }

      // Update title
      const ptS = series.find(s => s.country === 'PT');
      const titleEl = container.querySelector('.section-title');
      if (titleEl && ptS?.data?.length) {
        const v = ptS.data.at(-1)?.value;
        titleEl.textContent = v != null
          ? `Portugal — ${_ind.label}: ${fmt.num(v)}${_ind.unit_label ? ' ' + _ind.unit_label : ''}`
          : `${_ind.label} — comparação`;
      }

      const fn = document.getElementById('cmp-footnote');
      if (fn) fn.textContent = `Fonte: ${_ind.source === 'COMPOSITE' ? 'Eurostat + Banco Mundial' : _ind.source} · ${_ind.label}${_ind.unit_label ? ' · ' + _ind.unit_label : ''}`;

      _viewMode === 'snapshot' ? renderSnapshot(series) : renderLines(series);

    } catch(e) {
      console.error('[comparativos] load error:', e);
      document.getElementById('cmp-legend').innerHTML =
        `<div class="error-state">Erro: ${e.message}</div>`;
    }
  }

  // ── Line chart ────────────────────────────────────────────────
  function renderLines(series) {
    const refSeries = series.find(s => s.data?.length) || series[0];
    const periods   = (refSeries?.data || []).map(d => fmt.period(d.period));

    const legendHtml = series.map(s => {
      const color   = countryColor(s.country);
      const last    = s.data?.at(-1)?.value;
      const lastStr = last != null ? fmt.num(last) : 'n/d';
      return `<div class="legend-item">
        <span>${FLAGS[s.country] || ''}</span>
        <div class="legend-dot" style="background:${color}"></div>
        <span style="font-weight:${s.country==='PT'?'700':'400'};color:${s.country==='PT'?'#1A1A1A':'var(--c-text-sub)'}">${s.label}</span>
        <span style="color:${color};font-weight:600">${lastStr}</span>
      </div>`;
    }).join('');
    document.getElementById('cmp-legend').innerHTML = legendHtml || '<span style="color:var(--c-muted)">Sem dados.</span>';

    const chartEl = document.getElementById('cmp-chart');
    if (_cmpChart) { SWD.destroyChart(_cmpChart); _cmpChart = null; }

    const chartSeries = series.map(s => {
      const color = countryColor(s.country);
      const isPT  = s.country === 'PT';
      return {
        type: 'line', name: s.label,
        data: s.data.map(d => d.value),
        symbol: 'none',
        lineStyle: { color, width: isPT ? 2.5 : 1.5, opacity: isPT ? 1 : 0.75 },
        itemStyle: { color },
        z: isPT ? 10 : 1,
        emphasis: { focus: 'series' },
        blur: { lineStyle: { opacity: 0.12 } },
        endLabel: {
          show: true,
          formatter: ({ value }) => `${s.country === 'EU27_2020' ? 'EU27' : s.country} ${fmt.num(value)}`,
          fontSize: 10, color,
          fontFamily: 'Inter, system-ui, sans-serif',
        },
      };
    });

    _cmpChart = SWD.createSWDChart(chartEl, {
      ...SWD.baseOptions(),
      xAxis: SWD.timeAxis(periods, { interval: Math.max(0, Math.floor(periods.length / 8) - 1) }),
      yAxis: SWD.valueAxis({ scale: true }),
      series: chartSeries,
      grid: { containLabel: true, left: 40, right: 90, top: 20, bottom: 30 },
    });
  }

  // ── Snapshot bar chart ────────────────────────────────────────
  function renderSnapshot(series) {
    // Use last non-null value per series
    const points = series
      .map(s => ({ country: s.country, label: s.label, value: s.data?.at(-1)?.value }))
      .filter(p => p.value != null)
      .sort((a, b) => b.value - a.value);

    const labels = points.map(p => `${FLAGS[p.country] || ''} ${p.country === 'EU27_2020' ? 'EU27' : p.country}`);
    const values = points.map(p => p.value);
    const colors = points.map(p => countryColor(p.country));

    document.getElementById('cmp-legend').innerHTML =
      `<span style="color:var(--c-muted);font-size:12px">Último valor disponível · ${points.length} países</span>`;

    const avg = values.reduce((s, v) => s + v, 0) / values.length;
    const chartEl = document.getElementById('cmp-chart');
    if (_cmpChart) { SWD.destroyChart(_cmpChart); _cmpChart = null; }

    _cmpChart = SWD.createSWDChart(chartEl, {
      ...SWD.baseOptions(),
      xAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#999' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
      yAxis: { type: 'category', data: labels.slice().reverse(), axisLabel: { fontSize: 10, color: '#666', fontFamily: 'Inter, Noto Color Emoji, sans-serif' } },
      series: [{
        type: 'bar', data: values.slice().reverse(),
        itemStyle: { color: (params) => colors[points.length - 1 - params.dataIndex] },
        label: { show: true, position: 'right', formatter: p => fmt.num(p.value), fontSize: 10, color: '#555' },
        markLine: values.length > 2 ? {
          silent: true, symbol: 'none',
          data: [{ xAxis: avg, lineStyle: { color: '#aaa', type: 'dashed', width: 1 } }],
          label: { formatter: `Média: ${fmt.num(avg)}`, color: '#aaa', fontSize: 9 },
        } : undefined,
      }],
      grid: { containLabel: true, left: 60, right: 70, top: 10, bottom: 20 },
    });
  }

  // ── Initial load ──────────────────────────────────────────────
  loadData();
});
