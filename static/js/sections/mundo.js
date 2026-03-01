/* =================================================================
   mundo.js — PT vs Mundo (comparação global)
   CAE Dashboard V9
   Estrutura baseada em europa.js, adaptada para indicadores mundiais.
   ================================================================= */

let _mundoChart = null;

App.registerSection('mundo', async () => {
  const container = document.getElementById('mundo');
  const body = container.querySelector('.section-body');

  // ── Indicadores disponíveis ───────────────────────────────────
  const MUNDO_INDICATORS = [
    { id: 'unemployment',                    label: 'Taxa de Desemprego (%)',    source: 'EUROSTAT',  indicator: 'unemployment' },
    { id: 'gdp_per_capita_eur',              label: 'PIB per capita (€)',        source: 'EUROSTAT',  indicator: 'gdp_per_capita_eur' },
    { id: 'hicp',                            label: 'Inflação (HICP %)',         source: 'EUROSTAT',  indicator: 'hicp' },
    { id: 'employment_rate_eurostat',        label: 'Taxa de Emprego (%)',       source: 'EUROSTAT',  indicator: 'employment_rate' },
    { id: 'gov_debt_pct_gdp',               label: 'Dívida Pública (% PIB)',   source: 'EUROSTAT',  indicator: 'gov_debt_pct_gdp' },
    { id: 'labour_productivity_person_real', label: 'Produtividade Laboral',     source: 'EUROSTAT',  indicator: 'labour_productivity_person_real' },
    { id: 'gdp_growth',                      label: 'Crescimento PIB (%)',       source: 'WORLDBANK', indicator: 'gdp_growth' },
    { id: 'gdp_usd',                         label: 'PIB (USD mil M)',           source: 'WORLDBANK', indicator: 'gdp_usd' },
    { id: 'internet_users_pct',              label: 'Utilizadores Internet (%)', source: 'WORLDBANK', indicator: 'internet_users_pct' },
  ];

  // ── Presets de países ─────────────────────────────────────────
  const PRESETS = [
    { label: 'Semelhantes', countries: ['PT', 'ES', 'GR', 'CZ', 'HU', 'PL', 'RO', 'SK'] },
    { label: 'OCDE Sul',    countries: ['PT', 'ES', 'GR', 'IT', 'TR'] },
    { label: 'Ibérica',     countries: ['PT', 'ES'] },
    { label: 'G7',          countries: ['US', 'GB', 'FR', 'DE', 'IT', 'JP', 'CA'] },
  ];

  const LOCKED = new Set(['PT']);

  const FLAGS = {
    PT:'🇵🇹', ES:'🇪🇸', GR:'🇬🇷', CZ:'🇨🇿', HU:'🇭🇺', PL:'🇵🇱', RO:'🇷🇴', SK:'🇸🇰',
    IT:'🇮🇹', TR:'🇹🇷', DE:'🇩🇪', FR:'🇫🇷', GB:'🇬🇧', US:'🇺🇸', JP:'🇯🇵', CA:'🇨🇦',
    BR:'🇧🇷', IN:'🇮🇳', CN:'🇨🇳', ZA:'🇿🇦', RU:'🇷🇺', AU:'🇦🇺', MX:'🇲🇽', KR:'🇰🇷',
    NL:'🇳🇱', BE:'🇧🇪', AT:'🇦🇹', SE:'🇸🇪', DK:'🇩🇰', FI:'🇫🇮', NO:'🇳🇴', CH:'🇨🇭',
    EU27:'🇪🇺', EU27_2020:'🇪🇺',
  };

  // Country colors: PT=red, others from SWD palette
  function countryColor(code) {
    if (LOCKED.has(code)) return '#CC0000';
    return (SWD.COUNTRY_COLORS && SWD.COUNTRY_COLORS[code]) || '#999999';
  }

  // ── State ─────────────────────────────────────────────────────
  let _activeInd    = MUNDO_INDICATORS[0];
  let _countries    = new Set(['PT', 'ES', 'GR', 'CZ', 'HU', 'PL', 'RO', 'SK']); // Semelhantes default
  let _startYear    = 2015;
  let _viewMode     = 'lines';  // 'lines' | 'snapshot'
  let _activePreset = 'Semelhantes';

  // ── URL hash state ────────────────────────────────────────────
  function buildHash() {
    const ind = `${_activeInd.source}/${_activeInd.indicator}`;
    return `#mundo?ind=${ind}&countries=${[..._countries].join(',')}&since=${_startYear}&view=${_viewMode}`;
  }

  function pushHash() {
    try { history.replaceState(null, '', buildHash()); } catch(_) {}
  }

  function parseHash() {
    const hash = location.hash;
    if (!hash.startsWith('#mundo?')) return null;
    const params = new URLSearchParams(hash.slice('#mundo?'.length));
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
    const [hSrc, hInd] = (hashState.ind || '').split('/');
    const found = MUNDO_INDICATORS.find(i => i.source === hSrc && i.indicator === hInd);
    if (found) _activeInd = found;
    if (hashState.countries) {
      _countries = new Set(hashState.countries);
      LOCKED.forEach(c => _countries.add(c));
    }
    if (!isNaN(hashState.since)) _startYear = hashState.since;
    _viewMode = hashState.view || 'lines';
    _activePreset = null;
  }

  // ── Render UI skeleton ────────────────────────────────────────
  try {
    body.innerHTML = `
      <!-- Barra topo: indicador + toggle vista -->
      <div class="mundo-top-bar">
        <span class="control-label">INDICADOR</span>
        <select class="swd-select mundo-indicator-select" id="mundo-ind-select" style="flex:1;max-width:320px">
          ${MUNDO_INDICATORS.map(ind =>
            `<option value="${ind.id}" ${ind.id === _activeInd.id ? 'selected' : ''}>${ind.label}</option>`
          ).join('')}
        </select>
        <button id="mundo-view-toggle" class="swd-select" style="cursor:pointer;padding:5px 12px;white-space:nowrap">
          ${_viewMode === 'lines' ? 'Linhas' : 'Snapshot'}
        </button>
        <button class="share-btn" id="mundo-share-btn">Partilhar</button>
      </div>

      <!-- Preset chips + ano selector -->
      <div class="mundo-presets" id="mundo-presets">
        ${PRESETS.map(p =>
          `<button class="preset-chip${_activePreset === p.label ? ' active' : ''}" data-preset="${p.label}">${p.label}</button>`
        ).join('')}
        <select class="europa-since-select" id="mundo-since">
          <option value="2000" ${_startYear === 2000 ? 'selected' : ''}>Desde 2000</option>
          <option value="2010" ${_startYear === 2010 ? 'selected' : ''}>Desde 2010</option>
          <option value="2015" ${_startYear === 2015 ? 'selected' : ''}>Desde 2015</option>
          <option value="2018" ${_startYear === 2018 ? 'selected' : ''}>Desde 2018</option>
          <option value="2020" ${_startYear === 2020 ? 'selected' : ''}>Desde 2020</option>
        </select>
      </div>

      <div id="mundo-legend" class="inline-legend" style="margin-bottom:var(--sp-md)"></div>
      <div class="chart-card" style="padding:var(--sp-lg)">
        <div class="chart-container tall" id="mundo-chart"></div>
      </div>
      <div class="footnote" id="mundo-footnote">
        Fonte: ${_activeInd.source} · ${_activeInd.label}
      </div>`;

    const indSelect    = document.getElementById('mundo-ind-select');
    const sinceSelect  = document.getElementById('mundo-since');
    const viewToggle   = document.getElementById('mundo-view-toggle');
    const shareBtn     = document.getElementById('mundo-share-btn');

    // ── Indicator change ─────────────────────────────────────────
    indSelect.addEventListener('change', () => {
      _activeInd = MUNDO_INDICATORS.find(i => i.id === indSelect.value) || MUNDO_INDICATORS[0];
      const fn = document.getElementById('mundo-footnote');
      if (fn) fn.textContent = `Fonte: ${_activeInd.source} · ${_activeInd.label}`;
      loadMundo();
    });

    // ── View toggle ───────────────────────────────────────────────
    viewToggle.addEventListener('click', () => {
      _viewMode = _viewMode === 'lines' ? 'snapshot' : 'lines';
      viewToggle.textContent = _viewMode === 'lines' ? 'Linhas' : 'Snapshot';
      loadMundo();
    });

    // ── Share ─────────────────────────────────────────────────────
    shareBtn.addEventListener('click', () => {
      const url = location.origin + location.pathname + buildHash();
      navigator.clipboard.writeText(url).then(
        () => App.showToast('Link copiado!'),
        () => App.showToast('Link: ' + url)
      );
    });

    // ── Year selector ─────────────────────────────────────────────
    sinceSelect.addEventListener('change', () => {
      _startYear = parseInt(sinceSelect.value, 10);
      loadMundo();
    });

    // ── Preset chips ──────────────────────────────────────────────
    function setActiveChip(label) {
      _activePreset = label;
      document.querySelectorAll('#mundo-presets .preset-chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.preset === label);
      });
    }

    document.querySelectorAll('#mundo-presets [data-preset]').forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = PRESETS.find(p => p.label === btn.dataset.preset);
        if (!preset) return;
        _countries = new Set(preset.countries);
        LOCKED.forEach(c => _countries.add(c));
        setActiveChip(preset.label);
        loadMundo();
      });
    });

    // ── Data fetch + render ───────────────────────────────────────
    async function loadMundo() {
      const countriesStr = [..._countries].join(',');
      if (!countriesStr) return;
      pushHash();

      document.getElementById('mundo-legend').innerHTML =
        `<div class="loading-state" style="height:32px"><div class="loading-spinner"></div><span>A carregar…</span></div>`;

      try {
        const url = `/api/mundo?indicator=${encodeURIComponent(_activeInd.indicator)}&source=${_activeInd.source}&countries=${countriesStr}&since=${_startYear}`;
        const data = await API.get(url);

        let series = (data.series || []).map(s => ({
          country: s.country,
          label:   s.label,
          data:    (s.data || []).filter(d => {
            const yr = parseInt((d.period || '').slice(0, 4), 10);
            return yr >= _startYear;
          }),
        }));

        if (!series.length) {
          document.getElementById('mundo-legend').innerHTML =
            `<span style="color:var(--c-muted)">Sem dados para estes países/indicador.</span>`;
          return;
        }

        // Update section title
        const ptS = series.find(s => s.country === 'PT');
        const titleEl = container.querySelector('.section-title');
        if (titleEl && ptS?.data?.length) {
          const ptLast = ptS.data.at(-1)?.value;
          titleEl.textContent = ptLast != null
            ? `Portugal — ${_activeInd.label}: ${typeof ptLast === 'number' ? ptLast.toFixed(1) : ptLast}`
            : `${_activeInd.label} — comparação mundial`;
        }

        if (_viewMode === 'snapshot') {
          renderSnapshot(series);
        } else {
          renderLines(series);
        }
      } catch(e) {
        console.error('[mundo] load error:', e);
        document.getElementById('mundo-legend').innerHTML =
          `<div class="error-state">Erro: ${e.message}</div>`;
      }
    }

    // ── Line chart ────────────────────────────────────────────────
    function renderLines(series) {
      const legendHtml = series.map(s => {
        const color = countryColor(s.country);
        const last  = s.data?.at(-1)?.value;
        const lastStr = last != null ? (typeof last === 'number' ? last.toFixed(1) : last) : 'n/d';
        return `<div class="legend-item">
          <span>${FLAGS[s.country] || ''}</span>
          <div class="legend-dot" style="background:${color}"></div>
          <span style="font-weight:${s.country==='PT'?'700':'400'};color:${s.country==='PT'?'#1A1A1A':'var(--c-text-sub)'}">${s.label || s.country}</span>
          <span style="color:${color};font-weight:600">${lastStr}</span>
        </div>`;
      }).join('');

      document.getElementById('mundo-legend').innerHTML = legendHtml ||
        '<span style="color:var(--c-muted)">Sem dados.</span>';

      const refSeries = series.find(s => s.data?.length) || series[0];
      const periods = (refSeries?.data || []).map(d => fmt.period(d.period));

      const chartSeries = series.map(s => {
        const color = countryColor(s.country);
        const isPT  = s.country === 'PT';
        return {
          type: 'line',
          name: s.label || s.country,
          data: (s.data || []).map(d => d.value),
          symbol: 'none',
          lineStyle: { color, width: isPT ? 3 : 1.5 },
          itemStyle: { color },
          z: isPT ? 10 : 1,
          endLabel: {
            show: true,
            formatter: ({ value }) => `${s.country} ${typeof value === 'number' ? value.toFixed(1) : value}`,
            fontSize: 10, color,
            fontFamily: 'Inter, system-ui, sans-serif',
          },
        };
      });

      const chartEl = document.getElementById('mundo-chart');
      if (_mundoChart) { SWD.destroyChart(_mundoChart); }
      _mundoChart = SWD.createSWDChart(chartEl, {
        ...SWD.baseOptions(),
        xAxis: SWD.timeAxis(periods, { interval: Math.max(0, Math.floor(periods.length / 8) - 1) }),
        yAxis: SWD.valueAxis({ scale: true }),
        series: chartSeries,
        grid: { containLabel: true, left: 40, right: 85, top: 20, bottom: 30 },
      });
    }

    // ── Snapshot (bar) chart ──────────────────────────────────────
    function renderSnapshot(series) {
      const snapData = series
        .map(s => ({
          country: s.country,
          label:   s.label || s.country,
          value:   s.data?.at(-1)?.value ?? null,
        }))
        .filter(d => d.value != null)
        .sort((a, b) => b.value - a.value);

      document.getElementById('mundo-legend').innerHTML =
        `<span style="color:var(--c-muted);font-size:var(--fs-xs)">Snapshot — último valor disponível · ordenado desc.</span>`;

      const labels = snapData.map(d => `${FLAGS[d.country] || ''} ${d.label}`);
      const values = snapData.map(d => d.value);
      const colors = snapData.map(d => d.country === 'PT' ? '#CC0000' : '#CCCCCC');
      const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;

      const chartEl = document.getElementById('mundo-chart');
      if (_mundoChart) { SWD.destroyChart(_mundoChart); }
      _mundoChart = SWD.createSWDChart(chartEl, {
        ...SWD.baseOptions(),
        xAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#999' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
        yAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10, color: '#666' } },
        series: [{
          type: 'bar',
          data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
          barMaxWidth: 24,
          label: { show: true, position: 'right', fontSize: 10, formatter: ({ value }) => typeof value === 'number' ? value.toFixed(1) : value },
          markLine: avg != null ? {
            silent: true,
            symbol: ['none', 'none'],
            data: [{ xAxis: avg, lineStyle: { type: 'dashed', color: '#aaa', width: 1 } }],
            label: { formatter: `Média: ${avg.toFixed(1)}`, color: '#aaa', fontSize: 9 },
          } : undefined,
        }],
        grid: { containLabel: true, left: 100, right: 60, top: 10, bottom: 20 },
      });
    }

    // ── Init: load with default preset ───────────────────────────
    await loadMundo();

  } catch(e) {
    console.error('[mundo] init error:', e);
    body.innerHTML = App.errorHTML(e.message);
  }
});
