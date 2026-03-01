/* ═══════════════════════════════════════════════════════════════
   europa.js — EU27 comparação europeia (V7 progressive disclosure)
   Control UI redesigned: preset chips, collapsible picker,
   compact year select, URL hash state, share button.
   Data logic (fetch + ECharts rendering) unchanged from V5.
   CAE Dashboard V7 — M3 (Criativo)
   ═══════════════════════════════════════════════════════════════ */

let _europaChart = null;

App.registerSection('europa', async () => {
  const container = document.getElementById('europa');
  const body = container.querySelector('.section-body');

  // V5: Multi-indicator support (direct DB query mode)
  const EUROPA_INDICATORS = [
    // Legacy IPI datasets (use /api/europa Eurostat client)
    { id: 'manufacturing',   label: '🏭 IPI Transformadora',   mode: 'legacy', dataset: 'manufacturing' },
    { id: 'total_industry',  label: '📊 IPI Total Indústria',   mode: 'legacy', dataset: 'total_industry' },
    { id: 'metals',          label: '⚙️ Metais e Metalurgia',   mode: 'legacy', dataset: 'metals' },
    { id: 'chemicals',       label: '🧪 Química e Plásticos',   mode: 'db', source: 'EUROSTAT', indicator: 'chemicals_pharma' },
    { id: 'transport',       label: '🚗 Material de Transporte', mode: 'db', source: 'EUROSTAT', indicator: 'transport_eq' },
    // V5: Direct DB indicators
    { id: 'unemployment',      label: '📉 Desemprego (%)',       mode: 'db', source: 'EUROSTAT', indicator: 'unemployment' },
    { id: 'gdp_per_capita_eur',label: '💶 PIB/capita (€)',       mode: 'db', source: 'EUROSTAT', indicator: 'gdp_per_capita_eur' },
    { id: 'gov_debt_pct_gdp',  label: '📋 Dívida Pública %PIB', mode: 'db', source: 'EUROSTAT', indicator: 'gov_debt_pct_gdp' },
    { id: 'employment_rate',   label: '👷 Taxa de Emprego',      mode: 'db', source: 'EUROSTAT', indicator: 'employment_rate' },
    { id: 'birth_rate',        label: '👶 Natalidade (/1000)',   mode: 'db', source: 'WORLDBANK', indicator: 'birth_rate' },
    { id: 'rnd_pct_gdp',       label: '🔬 I&D % PIB',           mode: 'db', source: 'WORLDBANK', indicator: 'rnd_pct_gdp' },
    { id: 'fdi_inflows_pct_gdp',label: '💸 IDE Entradas %PIB',  mode: 'db', source: 'WORLDBANK', indicator: 'fdi_inflows_pct_gdp' },
  ];

  // V5: Base year / unit label per indicator (for dynamic subtitle)
  const INDICATOR_UNITS = {
    'manufacturing':       'base 2021=100',
    'total_industry':      'base 2021=100',
    'metals':              'base 2021=100',
    'chemicals':           'base 2021=100',
    'transport':           'base 2021=100',
    'unemployment':        '%',
    'gdp_per_capita_eur':  '€ por habitante',
    'gov_debt_pct_gdp':    '% do PIB',
    'gov_deficit_pct_gdp': '% do PIB',
    'employment_rate':     '%',
    'rnd_pct_gdp':         '% do PIB',
    'fdi_inflows_pct_gdp': '% do PIB',
    'birth_rate':          '/1000 hab.',
  };

  function getIndicatorFootnote(ind) {
    const unit = INDICATOR_UNITS[ind.id] || '';
    const src  = ind.mode === 'db' ? ind.source : 'Eurostat';
    const suffix = ind.mode === 'legacy' ? ' · Série dessazonalizada' : '';
    return `Fonte: ${src}${unit ? ' · ' + unit : ''}${suffix}`;
  }

  // V5 fix: dynamically update section-eyebrow breadcrumb when indicator changes
  function updateSectionEyebrow(ind) {
    const eyebrow = container.querySelector('.section-eyebrow');
    if (!eyebrow) return;
    const unit = INDICATOR_UNITS[ind.id];
    const unitLabel = unit ? unit.toUpperCase() : '';
    eyebrow.textContent = `COMPARAÇÃO EUROPEIA · PT vs EU${unitLabel ? ' · ' + unitLabel : ''}`;
  }

  const COUNTRY_GROUPS = [
    {
      label: 'Referência',
      countries: ['EU27'],
      names: { EU27: 'UE-27' },
      defaultSelected: ['EU27'],
    },
    {
      label: 'Ocidental',
      countries: ['DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT'],
      names: { DE:'DE', FR:'FR', IT:'IT', ES:'ES', NL:'NL', BE:'BE', AT:'AT' },
      defaultSelected: ['DE', 'FR', 'ES'],
    },
    {
      label: 'Leste',
      countries: ['PL', 'CZ', 'HU', 'RO', 'BG', 'LT'],
      names: { PL:'PL', CZ:'CZ', HU:'HU', RO:'RO', BG:'BG', LT:'LT' },
      defaultSelected: ['PL', 'CZ', 'HU'],
    },
    {
      label: 'Nórdicos',
      countries: ['SE', 'DK', 'FI'],
      names: { SE:'SE', DK:'DK', FI:'FI' },
      defaultSelected: [],
    },
    {
      label: 'Outros ⚠',
      countries: ['EL', 'IE', 'EE', 'LV', 'SI', 'HR', 'SK', 'CY', 'LU', 'MT'],
      names: { EL:'EL', IE:'IE', EE:'EE', LV:'LV', SI:'SI', HR:'HR', SK:'SK', CY:'CY', LU:'LU', MT:'MT' },
      defaultSelected: [],
    },
  ];

  // V7: Preset chips (progressive disclosure — replace old preset buttons)
  const PRESETS = [
    { label: 'PT vs Ibérica',  countries: ['PT', 'ES', 'EU27_2020'] },
    { label: 'PT vs Vizinhos', countries: ['PT', 'ES', 'FR', 'DE', 'IT'] },
    { label: 'Mediterrâneo',   countries: ['PT', 'ES', 'IT', 'EL', 'HR'] },
    { label: 'Nórdicos',       countries: ['PT', 'SE', 'DK', 'FI', 'NO'] },
    { label: 'Leste',          countries: ['PT', 'PL', 'CZ', 'HU', 'RO'] },
    { label: 'Todos EU',       countries: null },  // null = all available
    { label: 'Personalizar',   countries: 'custom' },  // expand picker
  ];

  const LOCKED_COUNTRIES = new Set(['PT']);

  const selectedCountries = new Set();
  COUNTRY_GROUPS.forEach(g => g.defaultSelected.forEach(c => selectedCountries.add(c)));
  LOCKED_COUNTRIES.forEach(c => selectedCountries.add(c));

  let _viewMode = 'lines'; // 'lines' | 'snapshot'
  let _activeIndicator = EUROPA_INDICATORS[0];
  let _startYear = 2015;
  let _activePreset = null;

  function allCountryCodes() {
    const all = new Set();
    COUNTRY_GROUPS.forEach(g => g.countries.forEach(c => all.add(c)));
    return [...all];
  }

  const COUNTRY_FLAGS = {
    PT:'🇵🇹', ES:'🇪🇸', DE:'🇩🇪', FR:'🇫🇷', IT:'🇮🇹', NL:'🇳🇱', BE:'🇧🇪',
    AT:'🇦🇹', LU:'🇱🇺', PL:'🇵🇱', CZ:'🇨🇿', SK:'🇸🇰', HU:'🇭🇺', RO:'🇷🇴',
    BG:'🇧🇬', HR:'🇭🇷', SI:'🇸🇮', EE:'🇪🇪', LV:'🇱🇻', LT:'🇱🇹', SE:'🇸🇪',
    DK:'🇩🇰', FI:'🇫🇮', EL:'🇬🇷', IE:'🇮🇪', CY:'🇨🇾', MT:'🇲🇹', NO:'🇳🇴',
    EU27:'🇪🇺', EU27_2020:'🇪🇺', EU:'🇪🇺',
  };

  function getCountryColor(code) {
    if (code === 'EU27' || code === 'EU27_2020' || code === 'EU') return '#4A90D9';
    if (LOCKED_COUNTRIES.has(code)) return '#CC0000';
    return SWD.COUNTRY_COLORS[code] || '#999';
  }

  function buildPickerHTML() {
    return COUNTRY_GROUPS.map(group => {
      const pills = group.countries.map(code => {
        const isLocked   = LOCKED_COUNTRIES.has(code);
        const isSelected = selectedCountries.has(code);
        const color      = getCountryColor(code);
        const pillClass  = ['country-pill', isSelected ? 'selected' : '', isLocked ? 'locked' : ''].filter(Boolean).join(' ');
        const style = isSelected ? `background:${color};border-color:${color};color:#fff;` : '';
        return `<div class="${pillClass}" style="${style}" data-code="${code}" title="${code}">
          ${COUNTRY_FLAGS[code] || ''} ${code}
        </div>`;
      }).join('');
      return `<div class="country-group">
        <div class="country-group-label">${group.label}</div>
        <div class="country-pills">${pills}</div>
      </div>`;
    }).join('');
  }

  // ── URL hash state ───────────────────────────────────────────────
  function buildHash() {
    return `#europa?ind=${_activeIndicator.id}&countries=${Array.from(selectedCountries).join(',')}&since=${_startYear}&view=${_viewMode}`;
  }

  function pushHash() {
    try { history.replaceState(null, '', buildHash()); } catch(_) {}
  }

  function parseHash() {
    const hash = location.hash;
    if (!hash.startsWith('#europa?')) return null;
    const params = new URLSearchParams(hash.slice('#europa?'.length));
    return {
      ind:       params.get('ind'),
      countries: params.get('countries') ? params.get('countries').split(',') : null,
      since:     parseInt(params.get('since') || '2015', 10),
      view:      params.get('view') || 'lines',
    };
  }

  // Restore state from hash if present
  const hashState = parseHash();
  if (hashState) {
    const restoredInd = EUROPA_INDICATORS.find(i => i.id === hashState.ind);
    if (restoredInd) _activeIndicator = restoredInd;
    if (hashState.countries) {
      selectedCountries.clear();
      hashState.countries.forEach(c => selectedCountries.add(c));
      LOCKED_COUNTRIES.forEach(c => selectedCountries.add(c));
    }
    if (!isNaN(hashState.since)) _startYear = hashState.since;
    _viewMode = hashState.view || 'lines';
  }

  // ── Toast ────────────────────────────────────────────────────────
  function showToast(msg) {
    let toast = document.getElementById('europa-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'europa-toast';
      toast.className = 'toast-notification';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2200);
  }

  try {
    body.innerHTML = `
      <style>
        .country-group { margin-bottom: 10px; }
        .country-group-label { font-size: 10px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 600; }
        .country-pills { display: flex; flex-wrap: wrap; gap: 4px; }
        .country-pill { display: inline-flex; align-items: center; gap: 3px; padding: 3px 8px; min-height: 24px; border-radius: 12px; border: 1.5px solid #ddd; cursor: pointer; font-size: 11px; font-weight: 500; background: #fff; color: #555; transition: all 0.15s; user-select: none; }
        .country-pill:hover { border-color: #999; color: #333; }
        .country-pill.selected { color: #fff; border-color: transparent; }
        .country-pill.locked { cursor: default; }
      </style>

      <!-- Barra topo: indicador + toggle -->
      <div class="europa-top-bar">
        <span class="control-label">INDICADOR</span>
        <select class="swd-select europa-indicator-select" id="europa-indicator-select" style="flex:1;max-width:300px">
          ${EUROPA_INDICATORS.map(ind =>
            `<option value="${ind.id}" ${ind.id === _activeIndicator.id ? 'selected' : ''}>${ind.label}</option>`
          ).join('')}
        </select>
        <button id="eu-view-toggle" class="swd-select" style="cursor:pointer;padding:5px 12px;white-space:nowrap">
          ${_viewMode === 'lines' ? '📈 Linhas' : '📊 Snapshot'}
        </button>
        <button class="share-btn" id="eu-share-btn">🔗 Partilhar</button>
      </div>

      <!-- Preset chips + ano selector -->
      <div class="europa-presets" id="europa-presets">
        ${PRESETS.map(p =>
          `<button class="preset-chip${_activePreset === p.label ? ' active' : ''}" data-preset="${p.label}">${p.label}</button>`
        ).join('')}
        <select class="europa-since-select" id="europa-since">
          <option value="2010" ${_startYear === 2010 ? 'selected' : ''}>Desde 2010</option>
          <option value="2015" ${_startYear === 2015 ? 'selected' : ''}>Desde 2015</option>
          <option value="2018" ${_startYear === 2018 ? 'selected' : ''}>Desde 2018</option>
          <option value="2020" ${_startYear === 2020 ? 'selected' : ''}>Desde 2020</option>
          <option value="2022" ${_startYear === 2022 ? 'selected' : ''}>Desde 2022</option>
        </select>
      </div>

      <!-- Country picker (hidden by default, collapsible) -->
      <details class="europa-picker-wrap" id="eu-picker-details">
        <summary class="europa-picker-summary">▸ Países seleccionados</summary>
        <div class="europa-picker-inner country-picker" id="eu-country-picker">
          ${buildPickerHTML()}
        </div>
      </details>

      <div id="eu-legend" class="inline-legend" style="margin-bottom:var(--sp-md)"></div>
      <div class="chart-card" style="padding:var(--sp-lg)">
        <div class="chart-container tall" id="europa-chart"></div>
      </div>
      <div class="footnote" id="eu-footnote">
        ${getIndicatorFootnote(_activeIndicator)}
      </div>`;

    const indicatorSelect  = document.getElementById('europa-indicator-select');
    const pickerEl         = document.getElementById('eu-country-picker');
    const pickerDetails    = document.getElementById('eu-picker-details');
    const startYearSel     = document.getElementById('europa-since');
    const viewToggleBtn    = document.getElementById('eu-view-toggle');
    const shareBtn         = document.getElementById('eu-share-btn');

    // ── Indicator selection ──────────────────────────────────────
    indicatorSelect.addEventListener('change', () => {
      _activeIndicator = EUROPA_INDICATORS.find(i => i.id === indicatorSelect.value) || EUROPA_INDICATORS[0];
      const fnEl = document.getElementById('eu-footnote');
      if (fnEl) fnEl.textContent = getIndicatorFootnote(_activeIndicator);
      updateSectionEyebrow(_activeIndicator);
      loadEuropa();
    });

    // ── View toggle ──────────────────────────────────────────────
    viewToggleBtn.addEventListener('click', () => {
      _viewMode = _viewMode === 'lines' ? 'snapshot' : 'lines';
      viewToggleBtn.textContent = _viewMode === 'lines' ? '📈 Linhas' : '📊 Snapshot';
      loadEuropa();
    });

    // ── Share button ─────────────────────────────────────────────
    shareBtn.addEventListener('click', () => {
      const url = location.origin + location.pathname + buildHash();
      navigator.clipboard.writeText(url).then(() => showToast('🔗 Link copiado!'), () => showToast('Link: ' + url));
    });

    // ── Year selector ────────────────────────────────────────────
    startYearSel.addEventListener('change', () => {
      _startYear = parseInt(startYearSel.value, 10);
      loadEuropa();
    });

    // ── Preset chips ─────────────────────────────────────────────
    function setActiveChip(label) {
      _activePreset = label;
      document.querySelectorAll('.preset-chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.preset === label);
      });
    }

    document.querySelectorAll('[data-preset]').forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = PRESETS.find(p => p.label === btn.dataset.preset);
        if (!preset) return;

        if (preset.countries === 'custom') {
          // Toggle country picker visibility
          pickerDetails.open = !pickerDetails.open;
          setActiveChip(preset.label);
          return;
        }

        const codes = preset.countries ? new Set(preset.countries) : new Set(allCountryCodes());
        LOCKED_COUNTRIES.forEach(c => codes.add(c));
        selectedCountries.clear();
        codes.forEach(c => selectedCountries.add(c));

        // Rebuild picker
        pickerEl.innerHTML = buildPickerHTML();
        attachPickerListeners();
        setActiveChip(preset.label);

        // Close custom picker
        pickerDetails.open = false;
        loadEuropa();
      });
    });

    // ── Country pill listeners ────────────────────────────────────
    function attachPickerListeners() {
      pickerEl.addEventListener('click', e => {
        const pill = e.target.closest('[data-code]');
        if (!pill) return;
        const code = pill.dataset.code;
        if (LOCKED_COUNTRIES.has(code)) return;
        const color = getCountryColor(code);
        if (selectedCountries.has(code)) {
          selectedCountries.delete(code);
          pill.classList.remove('selected');
          pill.style.background = '';
          pill.style.borderColor = '';
          pill.style.color = '';
        } else {
          selectedCountries.add(code);
          pill.classList.add('selected');
          pill.style.background = color;
          pill.style.borderColor = color;
          pill.style.color = '#fff';
        }
        // Custom selection — clear active preset chip
        setActiveChip('Personalizar');
        loadEuropa();
      });
    }

    attachPickerListeners();

    // ── Data fetch + chart render ─────────────────────────────────
    async function loadEuropa() {
      const countries = Array.from(selectedCountries).join(',');
      if (!countries) return;

      pushHash();

      document.getElementById('eu-legend').innerHTML =
        `<div class="loading-state" style="height:32px"><div class="loading-spinner"></div><span>A carregar…</span></div>`;

      try {
        let series = [];
        let dataLabel = _activeIndicator.label;

        if (_activeIndicator.mode === 'db') {
          // V5: direct DB query via /api/compare
          const url = `/api/compare?indicator=${encodeURIComponent(_activeIndicator.indicator)}&source=${_activeIndicator.source}&countries=${countries}&since=${_startYear}`;
          const data = await API.get(url);
          series = (data.series || []).map(s => ({
            country: s.country,
            label:   s.label,
            data:    (s.data || []).filter(d => {
              const yr = parseInt((d.period || '').slice(0, 4), 10);
              return yr >= _startYear;
            }),
          }));
        } else {
          // Legacy: use Eurostat client
          const months = (new Date().getFullYear() - _startYear + 1) * 12;
          const url = `/api/europa?dataset=${_activeIndicator.dataset}&countries=${countries}&months=${months}`;
          const data = await API.get(url);
          series = (data.series || []).map(s => ({
            country: s.country,
            label:   s.label || s.country,
            data:    (s.data || []).filter(d => {
              const yr = parseInt((d.period || '').slice(0, 4), 10);
              return yr >= _startYear;
            }),
          }));
        }

        if (!series.length) {
          document.getElementById('eu-legend').innerHTML =
            `<span style="color:var(--c-muted)">Sem dados para estes países/indicador.</span>`;
          return;
        }

        // Update section title
        const ptSeries = series.find(s => s.country === 'PT');
        const euSeries = series.find(s => ['EU27','EU27_2020','EU'].includes(s.country));
        const titleEl = container.querySelector('.section-title');
        if (titleEl && ptSeries?.data?.length) {
          const ptLast = ptSeries.data.at(-1)?.value;
          if (euSeries?.data?.length && ptLast != null) {
            const euLast = euSeries.data.at(-1)?.value;
            if (euLast != null) {
              const diff = ptLast - euLast;
              titleEl.textContent = diff < -2
                ? `Portugal ${Math.abs(diff).toFixed(1)} ${_activeIndicator.mode === 'db' ? 'unidades' : 'pp'} abaixo da UE-27`
                : diff > 2
                ? `Portugal ${diff.toFixed(1)} ${_activeIndicator.mode === 'db' ? 'unidades' : 'pp'} acima da UE-27`
                : `Portugal acompanha UE-27 (${diff >= 0 ? '+' : ''}${diff.toFixed(1)})`;
            }
          } else {
            titleEl.textContent = `${dataLabel.replace(/[🏭📊⚙️🧪🚗📉💶📋👷👶🔬💸]/gu, '').trim()} — comparação europeia`;
          }
        }

        if (_viewMode === 'snapshot') {
          renderSnapshot(series);
        } else {
          renderLines(series);
        }
      } catch(e) {
        console.error('[europa] load error:', e);
        document.getElementById('eu-legend').innerHTML =
          `<div class="error-state">⚠ Erro: ${e.message}</div>`;
      }
    }

    // ── Chart renderers (V5 — unchanged) ─────────────────────────
    function renderLines(series) {
      const flags = COUNTRY_FLAGS;

      const legendHtml = series.map(s => {
        const color = SWD.COUNTRY_COLORS[s.country] || SWD.COLORS.other;
        const last  = s.data?.at(-1)?.value;
        const lastStr = last != null ? fmt.num(last) : 'n/d';
        return `<div class="legend-item">
          <span>${flags[s.country] || ''}</span>
          <div class="legend-dot" style="background:${color}"></div>
          <span style="font-weight:${s.country==='PT'?'700':'400'};color:${s.country==='PT'?'#1A1A1A':'var(--c-text-sub)'}">${s.label || s.country}</span>
          <span style="color:${color};font-weight:600">${lastStr}</span>
        </div>`;
      }).join('');

      document.getElementById('eu-legend').innerHTML = legendHtml ||
        '<span style="color:var(--c-muted)">Sem dados.</span>';

      const refSeries = series.find(s => s.data?.length) || series[0];
      const periods = (refSeries?.data || []).map(d => fmt.period(d.period));

      const chartSeries = series.map(s => {
        const country = s.country;
        const color   = SWD.COUNTRY_COLORS[country] || SWD.COLORS.other;
        const isPT    = country === 'PT';
        const isEU    = ['EU27','EU27_2020','EU'].includes(country);
        return {
          type: 'line',
          name: s.label || country,
          data: (s.data || []).map(d => d.value),
          symbol: 'none',
          lineStyle: { color, width: isPT ? 3 : isEU ? 2 : 1.5 },
          itemStyle: { color },
          z: isPT ? 10 : isEU ? 5 : 1,
          endLabel: {
            show: true,
            formatter: ({ value }) => `${country} ${fmt.num(value)}`,
            fontSize: 10, color,
            fontFamily: 'Inter, system-ui, sans-serif',
          },
        };
      });

      const chartEl = document.getElementById('europa-chart');
      if (_europaChart) { SWD.destroyChart(_europaChart); }
      _europaChart = SWD.createSWDChart(chartEl, {
        ...SWD.baseOptions(),
        xAxis: SWD.timeAxis(periods, { interval: Math.max(0, Math.floor(periods.length / 8) - 1) }),
        yAxis: SWD.valueAxis({ scale: true }),
        series: chartSeries,
        grid: { containLabel: true, left: 40, right: 85, top: 20, bottom: 30 },
      });
    }

    function renderSnapshot(series) {
      // Snapshot view: horizontal bar chart, latest value per country, sorted desc
      const snapData = series
        .map(s => ({
          country: s.country,
          label:   s.label || s.country,
          value:   s.data?.at(-1)?.value ?? null,
        }))
        .filter(d => d.value != null)
        .sort((a, b) => b.value - a.value);

      document.getElementById('eu-legend').innerHTML =
        `<span style="color:var(--c-muted);font-size:var(--fs-xs)">Snapshot — último valor disponível por país · ordenado desc.</span>`;

      const labels = snapData.map(d => d.label);
      const values = snapData.map(d => d.value);
      const colors = snapData.map(d =>
        d.country === 'PT' ? SWD.COLORS.pt : SWD.COUNTRY_COLORS[d.country] || SWD.COLORS.other
      );
      const avgValue = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;

      const chartEl = document.getElementById('europa-chart');
      if (_europaChart) { SWD.destroyChart(_europaChart); }
      _europaChart = SWD.createSWDChart(chartEl, {
        ...SWD.baseOptions(),
        xAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#999' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
        yAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10, color: '#666' } },
        series: [{
          type: 'bar',
          data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
          barMaxWidth: 24,
          label: { show: true, position: 'right', fontSize: 10, formatter: ({ value }) => fmt.num(value) },
          markLine: avgValue != null ? {
            silent: true,
            symbol: ['none', 'none'],
            data: [{ xAxis: avgValue, lineStyle: { type: 'dashed', color: '#aaa', width: 1 } }],
            label: { formatter: `Média: ${fmt.num(avgValue)}`, color: '#aaa', fontSize: 9 },
          } : undefined,
        }],
        grid: { containLabel: true, left: 80, right: 60, top: 10, bottom: 20 },
      });
    }

    updateSectionEyebrow(_activeIndicator);
    await loadEuropa();
  } catch(e) {
    console.error('[europa] init error:', e);
    body.innerHTML = App.errorHTML(e.message);
  }
});
