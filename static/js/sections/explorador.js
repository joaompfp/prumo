/* ═══════════════════════════════════════════════════════════════
   explorador.js — World Bank-style multi-indicator explorer
   CAE Dashboard V7  (M4)
   ═══════════════════════════════════════════════════════════════ */

App.registerSection('explorador', async () => {
  const container  = document.getElementById('explorador');
  const body       = container.querySelector('.section-body');
  const BASE       = window.__BASE_PATH__ || '';

  // ── State ──────────────────────────────────────────────────────
  let catalog    = {};          // {SOURCE: {label, indicators: {IND: {...}}}}
  let selected   = [];          // [{source, indicator, label, unit}]
  let chartInst  = null;
  let viewMode   = 'chart';     // 'chart' | 'table'
  let lastSeries = [];          // [{source, indicator, label, unit, data:[{period,value}]}]

  // ── Source colours ────────────────────────────────────────────
  const SOURCE_COLOR = {
    INE:       '#003399',
    EUROSTAT:  '#003399',
    WORLDBANK: '#009999',
  };
  const srcColor = s => SOURCE_COLOR[s] || '#666';

  // ── Series colour palette ─────────────────────────────────────
  const SERIES_COLORS = ['#CC0000', '#4A90D9', '#2E7D32', '#E67E22', '#9B59B6'];

  // ── Date helpers ──────────────────────────────────────────────
  function nowYM() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  }
  function subtractYears(n) {
    const d = new Date();
    d.setFullYear(d.getFullYear() - n);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  }

  // ── Toast — usa App.showToast (WP-5 unified) ─────────────────────

  // ── Build HTML skeleton ───────────────────────────────────────
  body.innerHTML = `
    <div class="explorador-wrap">
      <div class="explorador-search-bar">
        <input id="exp-search" class="swd-input" type="text"
               placeholder="Pesquisar indicadores..." autocomplete="off">
        <select id="exp-source-filter" class="swd-select">
          <option value="">Todas as fontes</option>
        </select>
      </div>

      <div id="exp-results" class="explorador-results hidden"></div>

      <div class="explorador-chips" id="exp-chips">
        <span class="chip-placeholder" id="exp-chip-placeholder">Selecciona indicadores acima (máx. 5)</span>
      </div>

      <div class="explorador-timerange">
        <label>De: <input id="exp-from" class="swd-input compact" type="text"
                          placeholder="YYYY-MM" maxlength="7"></label>
        <label>Até: <input id="exp-to" class="swd-input compact" type="text"
                           placeholder="YYYY-MM" maxlength="7"></label>
        <div class="time-presets">
          <button class="time-preset-btn" data-years="1">1A</button>
          <button class="time-preset-btn" data-years="2">2A</button>
          <button class="time-preset-btn active" data-years="5">5A</button>
          <button class="time-preset-btn" data-years="10">10A</button>
          <button class="time-preset-btn" data-years="0">Tudo</button>
        </div>
        <button class="btn-primary" id="exp-render-btn">Ver →</button>
      </div>

      <div class="explorador-chart-container" id="exp-chart-wrap">
        <div class="explorador-empty-state">
          Selecciona indicadores para visualizar
        </div>
      </div>

      <div class="explorador-table-wrap hidden" id="exp-table-wrap">
        <div class="result-table-wrap">
          <table class="swd-table explorador-table" id="exp-table"></table>
        </div>
      </div>

      <div id="explorador-ficha" class="explorador-ficha"></div>

      <div class="explorador-actions">
        <button class="btn-toggle active" id="exp-btn-chart">Gráfico</button>
        <button class="btn-toggle" id="exp-btn-table">Tabela</button>
        <button class="btn-action" id="exp-btn-csv">CSV</button>
        <button class="btn-action" id="exp-btn-share">Partilhar</button>
      </div>
    </div>`;

  // ── Refs ──────────────────────────────────────────────────────
  const elSearch      = body.querySelector('#exp-search');
  const elSrcFilter   = body.querySelector('#exp-source-filter');
  const elResults     = body.querySelector('#exp-results');
  const elChips       = body.querySelector('#exp-chips');
  const elChipPH      = body.querySelector('#exp-chip-placeholder');
  const elFrom        = body.querySelector('#exp-from');
  const elTo          = body.querySelector('#exp-to');
  const elChartWrap   = body.querySelector('#exp-chart-wrap');
  const elTableWrap   = body.querySelector('#exp-table-wrap');
  const elTable       = body.querySelector('#exp-table');
  const elBtnChart    = body.querySelector('#exp-btn-chart');
  const elBtnTable    = body.querySelector('#exp-btn-table');
  const elBtnCSV      = body.querySelector('#exp-btn-csv');
  const elBtnShare    = body.querySelector('#exp-btn-share');
  const elRenderBtn   = body.querySelector('#exp-render-btn');

  // ── Set defaults ──────────────────────────────────────────────
  elFrom.value = subtractYears(5);
  elTo.value   = nowYM();

  // ── Fetch catalog ─────────────────────────────────────────────
  try {
    const resp = await fetch(`${BASE}/api/catalog`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    catalog = await resp.json();
  } catch (e) {
    body.innerHTML = App.errorHTML(`Erro ao carregar catálogo: ${e.message}`);
    return;
  }

  // Populate source filter
  Object.keys(catalog).sort().forEach(src => {
    const opt = document.createElement('option');
    opt.value = src;
    opt.textContent = catalog[src].label || src;
    elSrcFilter.appendChild(opt);
  });

  // ── Build flat indicator list ─────────────────────────────────
  function flatIndicators() {
    const list = [];
    for (const [src, srcInfo] of Object.entries(catalog)) {
      for (const [ind, indInfo] of Object.entries(srcInfo.indicators || {})) {
        list.push({
          source: src,
          indicator: ind,
          label: indInfo.label || ind,
          unit: indInfo.unit || '',
          description: indInfo.description || '',
        });
      }
    }
    return list;
  }

  // ── Search logic ──────────────────────────────────────────────
  function renderResults() {
    const query  = elSearch.value.toLowerCase().trim();
    const srcF   = elSrcFilter.value;
    const all    = flatIndicators();

    const filtered = all.filter(item => {
      const matchSrc = !srcF || item.source === srcF;
      const matchQ   = !query ||
        item.label.toLowerCase().includes(query) ||
        item.source.toLowerCase().includes(query) ||
        item.indicator.toLowerCase().includes(query);
      return matchSrc && matchQ;
    });

    if (!query && !srcF) {
      elResults.classList.add('hidden');
      return;
    }

    if (!filtered.length) {
      elResults.innerHTML = '<div class="exp-no-results">Sem resultados</div>';
      elResults.classList.remove('hidden');
      return;
    }

    // Group by source
    const groups = {};
    filtered.forEach(item => {
      (groups[item.source] = groups[item.source] || []).push(item);
    });

    let html = '';
    for (const [src, items] of Object.entries(groups)) {
      const srcLabel = catalog[src]?.label || src;
      html += `<div class="exp-group">
        <div class="exp-group-header" style="color:${srcColor(src)}">${srcLabel}</div>`;
      items.slice(0, 30).forEach(item => {
        const alreadySel = selected.some(s => s.source === item.source && s.indicator === item.indicator);
        html += `<div class="exp-result-item ${alreadySel ? 'already-selected' : ''}"
                      data-source="${item.source}" data-indicator="${item.indicator}"
                      data-label="${encodeURIComponent(item.label)}"
                      data-unit="${encodeURIComponent(item.unit)}">
          <span class="exp-item-label">${item.label}</span>
          <span class="exp-item-id">${item.indicator}</span>
          ${alreadySel ? '<span class="exp-item-tick">✓</span>' : ''}
        </div>`;
      });
      if (items.length > 30) {
        html += `<div class="exp-group-more">+ ${items.length - 30} mais. Refina a pesquisa.</div>`;
      }
      html += '</div>';
    }

    elResults.innerHTML = html;
    elResults.classList.remove('hidden');

    // Click to add
    elResults.querySelectorAll('.exp-result-item:not(.already-selected)').forEach(el => {
      el.addEventListener('click', () => {
        const src  = el.dataset.source;
        const ind  = el.dataset.indicator;
        const lbl  = decodeURIComponent(el.dataset.label);
        const unit = decodeURIComponent(el.dataset.unit);
        addIndicator(src, ind, lbl, unit);
        elSearch.value = '';
        elResults.classList.add('hidden');
      });
    });
  }

  elSearch.addEventListener('input', renderResults);
  elSrcFilter.addEventListener('change', renderResults);

  // Close results on outside click
  document.addEventListener('click', e => {
    if (!body.querySelector('.explorador-search-bar').contains(e.target) &&
        !elResults.contains(e.target)) {
      elResults.classList.add('hidden');
    }
  });

  // ── Chip management ───────────────────────────────────────────
  function addIndicator(source, indicator, label, unit) {
    if (selected.length >= 5) {
      App.showToast('Máximo de 5 indicadores atingido');
      return;
    }
    if (selected.some(s => s.source === source && s.indicator === indicator)) {
      App.showToast('Indicador já seleccionado');
      return;
    }
    selected.push({ source, indicator, label, unit });
    renderChips();
    renderFicha();
    autoRender();
  }

  function removeIndicator(source, indicator) {
    selected = selected.filter(s => !(s.source === source && s.indicator === indicator));
    renderChips();
    renderFicha();
    if (selected.length > 0) autoRender();
    else clearChart();
  }

  function renderChips() {
    // Remove existing chips (keep placeholder)
    elChips.querySelectorAll('.indicator-chip').forEach(c => c.remove());

    if (selected.length === 0) {
      elChipPH.style.display = '';
    } else {
      elChipPH.style.display = 'none';
      selected.forEach((s, i) => {
        const chip = document.createElement('span');
        chip.className = 'indicator-chip';
        chip.style.setProperty('--chip-color', srcColor(s.source));
        chip.style.setProperty('--chip-series-color', SERIES_COLORS[i] || '#999');
        chip.innerHTML = `
          <span class="chip-dot" style="background:${SERIES_COLORS[i] || '#999'}"></span>
          <span class="chip-text">${s.source} — ${s.label}</span>
          <button class="chip-remove" title="Remover">×</button>`;
        chip.querySelector('.chip-remove').addEventListener('click', () => {
          removeIndicator(s.source, s.indicator);
        });
        elChips.appendChild(chip);
      });
    }
  }

  // ── WP-10: Inline ficha técnica dos indicadores seleccionados ────
  function renderFicha() {
    const container = document.getElementById('explorador-ficha');
    if (!container || selected.length === 0) {
      if (container) container.innerHTML = '';
      return;
    }

    const freqLabel = f => ({
      monthly: 'Mensal', annual: 'Anual', weekly: 'Semanal',
      semester: 'Semestral', quarterly: 'Trimestral',
    }[f] || f || 'n/d');

    container.innerHTML = `
      <h3 class="ficha-inline-title">Ficha técnica dos indicadores seleccionados</h3>
      ${selected.map((s, i) => {
        const srcData = catalog[s.source] || {};
        const indData = (srcData.indicators || {})[s.indicator] || {};
        const color = SERIES_COLORS[i % SERIES_COLORS.length];
        return `<div class="ficha-inline-card">
          <div class="ficha-inline-header">
            <span class="ficha-color-dot" style="background:${color}"></span>
            <strong>${s.label}</strong>
            <span class="ficha-inline-source">${srcData.label || s.source}</span>
          </div>
          <div class="ficha-inline-body">
            ${indData.description ? `<p class="ficha-inline-desc">${indData.description}</p>` : ''}
            <div class="ficha-inline-meta">
              <span>Unidade: <strong>${s.unit || indData.unit || 'n/d'}</strong></span>
              <span>Frequência: <strong>${freqLabel(indData.frequency)}</strong></span>
              <span>Cobertura: <strong>${indData.since || '?'} — ${indData.until || '?'}</strong></span>
              <span>Observações: <strong>${indData.rows || 'n/d'}</strong></span>
            </div>
          </div>
        </div>`;
      }).join('')}`;
  }

  // ── Time range presets ────────────────────────────────────────
  body.querySelectorAll('.time-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      body.querySelectorAll('.time-preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const years = parseInt(btn.dataset.years, 10);
      elTo.value = nowYM();
      elFrom.value = years === 0 ? '' : subtractYears(years);
      if (selected.length > 0) autoRender();
    });
  });

  // ── Render button ─────────────────────────────────────────────
  elRenderBtn.addEventListener('click', () => render());

  // ── Auto-render on selection change ──────────────────────────
  function autoRender() {
    if (selected.length > 0) render();
  }

  // ── Clear chart ───────────────────────────────────────────────
  function clearChart() {
    if (chartInst) { SWD.destroyChart(chartInst); chartInst = null; }
    elChartWrap.innerHTML = '<div class="explorador-empty-state">Selecciona indicadores para visualizar</div>';
    elTableWrap.classList.add('hidden');
    lastSeries = [];
    // M2: Remove unit warning banner when chart is cleared
    const banner = document.getElementById('exp-unit-warning');
    if (banner) banner.remove();
    updateURL();
  }

  // ── Main render ───────────────────────────────────────────────
  async function render() {
    if (!selected.length) return;

    elChartWrap.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><span>A carregar séries…</span></div>';

    const fromV = elFrom.value || '';
    const toV   = elTo.value   || nowYM();

    try {
      // Fetch all series in parallel
      const fetches = selected.map(s => {
        let url = `${BASE}/api/series?source=${encodeURIComponent(s.source)}&indicator=${encodeURIComponent(s.indicator)}`;
        if (fromV) url += `&from=${fromV}`;
        if (toV)   url += `&to=${toV}`;
        return fetch(url).then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status} for ${s.source}/${s.indicator}`);
          return r.json();
        });
      });

      const results = await Promise.all(fetches);
      // Each result is an array; take first element per query
      lastSeries = results.map((arr, i) => {
        const item = Array.isArray(arr) && arr.length ? arr[0] : null;
        const sel  = selected[i];
        return {
          source:    sel.source,
          indicator: sel.indicator,
          label:     (item && item.label) || sel.label,
          unit:      (item && item.unit)  || sel.unit,
          data:      (item && Array.isArray(item.data)) ? item.data : [],
        };
      });

      // Determine Y-axis mode
      const units = [...new Set(lastSeries.map(s => s.unit).filter(Boolean))];
      const yMode = units.length <= 1 ? 'single'
                  : units.length === 2 ? 'dual'
                  : 'indexed';

      // M2: Warn on incompatible units
      if (units.length > 1) {
        let banner = document.getElementById('exp-unit-warning');
        if (!banner) {
          banner = document.createElement('div');
          banner.id = 'exp-unit-warning';
          banner.className = 'exp-warning-banner';
        }
        banner.textContent = `⚠️ Unidades incompatíveis (${units.join(' vs ')}) — o gráfico pode ser enganador. Considera usar o modo Indexado.`;
        if (!elChartWrap.parentNode.contains(banner)) {
          elChartWrap.parentNode.insertBefore(banner, elChartWrap);
        }
      } else {
        const banner = document.getElementById('exp-unit-warning');
        if (banner) banner.remove();
      }

      if (viewMode === 'chart') renderChart(yMode, units);
      else                      renderTable();

      updateURL();
    } catch (e) {
      elChartWrap.innerHTML = `<div class="error-state">Erro: ${e.message}</div>`;
      console.error('[explorador] render error:', e);
    }
  }

  // ── Chart rendering ───────────────────────────────────────────
  function renderChart(yMode, units) {
    const chartH = Math.max(elChartWrap.offsetHeight || 0, 400);
    elChartWrap.innerHTML = `<div id="exp-chart" style="width:100%;height:${chartH}px"></div>`;
    const chartEl = elChartWrap.querySelector('#exp-chart');

    if (chartInst) { SWD.destroyChart(chartInst); chartInst = null; }

    // Collect all periods (union)
    const allPeriods = [...new Set(
      lastSeries.flatMap(s => s.data.map(d => d.period))
    )].sort();

    const series = lastSeries.map((s, i) => {
      const color   = SERIES_COLORS[i] || '#999';
      const byPeriod = Object.fromEntries(s.data.map(d => [d.period, d.value]));

      let values;
      if (yMode === 'indexed') {
        // Find first non-null value
        let base = null;
        for (const p of allPeriods) {
          const v = byPeriod[p];
          if (v !== null && v !== undefined) { base = v; break; }
        }
        values = allPeriods.map(p => {
          const v = byPeriod[p];
          if (v === null || v === undefined || base === null || base === 0) return null;
          return Math.round(v / base * 1000) / 10; // 1 decimal
        });
      } else {
        values = allPeriods.map(p => {
          const v = byPeriod[p];
          return (v !== null && v !== undefined) ? v : null;
        });
      }

      const yAxisIndex = yMode === 'dual'
        ? (units.indexOf(s.unit) === 1 ? 1 : 0)
        : 0;

      return SWD.lineSeries(s.label, values, color, {
        width: 2.5,
        endLabel: s.label.length < 25 ? s.label : s.label.slice(0, 22) + '…',
      });
    }).map((s, i) => ({
      ...s,
      connectNulls: false,
      yAxisIndex: yMode === 'dual' ? (units.indexOf(lastSeries[i].unit) === 1 ? 1 : 0) : 0,
    }));

    const yAxes = [];
    if (yMode === 'single') {
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: units[0] || '', nameLocation: 'end', nameTextStyle: { fontSize: 10, color: '#888' } });
    } else if (yMode === 'dual') {
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: units[0], nameLocation: 'end', nameTextStyle: { fontSize: 10, color: SERIES_COLORS[0] } });
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: units[1], nameLocation: 'end', nameTextStyle: { fontSize: 10, color: SERIES_COLORS[1] }, position: 'right' });
    } else {
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: 'Index (início=100)', nameLocation: 'end', nameTextStyle: { fontSize: 10, color: '#888' } });
    }

    const baseOpts = SWD.baseOptions();
    // Enable legend for multi-series
    baseOpts.legend = {
      show: true,
      bottom: 0,
      left: 'center',
      type: 'scroll',
      textStyle: { fontSize: 11, fontFamily: 'Inter, system-ui, sans-serif', color: '#555' },
      itemWidth: 16,
      itemHeight: 3,
    };
    // Adjust grid bottom for legend; right:120 gives room for end labels (m2 fix: was 20/80, labels clipped)
    baseOpts.grid = { ...baseOpts.grid, bottom: 48, right: 120 };

    const opts = {
      ...baseOpts,
      color: SERIES_COLORS,
      xAxis: SWD.timeAxis(allPeriods),
      yAxis: yAxes,
      series,
      tooltip: {
        ...baseOpts.tooltip,
        formatter: params => {
          const period = params[0]?.axisValue || '';
          let html = `<div style="font-weight:600;margin-bottom:4px">${period}</div>`;
          params.forEach(p => {
            if (p.value !== null && p.value !== undefined) {
              const unit = lastSeries[p.seriesIndex]?.unit || '';
              html += `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px"></span>${p.seriesName}: <strong>${typeof p.value === 'number' ? p.value.toLocaleString('pt-PT') : p.value}</strong> ${unit}</div>`;
            }
          });
          return html;
        },
      },
    };

    chartInst = SWD.createSWDChart(chartEl, opts);
    // Ensure ECharts respects container size after it becomes visible
    setTimeout(() => { if (chartInst) chartInst.resize(); }, 50);
  }

  // ── Table rendering ───────────────────────────────────────────
  function renderTable() {
    elTableWrap.classList.remove('hidden');

    const allPeriods = [...new Set(
      lastSeries.flatMap(s => s.data.map(d => d.period))
    )].sort().reverse();

    const headers = ['Período', ...lastSeries.map(s => `${s.source} — ${s.label}`)];
    const byPeriod = lastSeries.map(s =>
      Object.fromEntries(s.data.map(d => [d.period, d.value]))
    );

    const rows = allPeriods
      .filter(p => lastSeries.some((_, i) => byPeriod[i][p] !== undefined))
      .map(p => [p, ...lastSeries.map((_, i) => {
        const v = byPeriod[i][p];
        return v !== null && v !== undefined ? v : '—';
      })]);

    let html = `<thead><tr>${headers.map((h, i) => `<th${i ? ' style="text-align:right"' : ''}>${h}</th>`).join('')}</tr></thead>`;
    html += `<tbody>${rows.map(row =>
      `<tr>${row.map((cell, i) => `<td${i ? ' style="text-align:right"' : ''}>${typeof cell === 'number' ? cell.toLocaleString('pt-PT', { maximumFractionDigits: 3 }) : cell}</td>`).join('')}</tr>`
    ).join('')}</tbody>`;

    elTable.innerHTML = html;
  }

  // ── View mode toggle ──────────────────────────────────────────
  elBtnChart.addEventListener('click', () => {
    viewMode = 'chart';
    elBtnChart.classList.add('active');
    elBtnTable.classList.remove('active');
    elChartWrap.classList.remove('hidden');
    elTableWrap.classList.add('hidden');
    if (lastSeries.length) {
      const units = [...new Set(lastSeries.map(s => s.unit).filter(Boolean))];
      const yMode = units.length <= 1 ? 'single' : units.length === 2 ? 'dual' : 'indexed';
      renderChart(yMode, units);
    }
  });

  elBtnTable.addEventListener('click', () => {
    viewMode = 'table';
    elBtnTable.classList.add('active');
    elBtnChart.classList.remove('active');
    elChartWrap.classList.add('hidden');
    if (lastSeries.length) renderTable();
    else elTableWrap.classList.add('hidden');
  });

  // ── CSV Export ────────────────────────────────────────────────
  elBtnCSV.addEventListener('click', () => {
    if (!selected.length) { App.showToast('Selecciona indicadores primeiro'); return; }
    const srcParam = selected.map(s => s.source).join(',');
    const indParam = selected.map(s => s.indicator).join(',');
    let url = `${BASE}/api/export?sources=${encodeURIComponent(srcParam)}&indicators=${encodeURIComponent(indParam)}`;
    const fromV = elFrom.value;
    const toV   = elTo.value;
    if (fromV) url += `&from=${fromV}`;
    if (toV)   url += `&to=${toV}`;
    window.location.href = url;
  });

  // ── Share ─────────────────────────────────────────────────────
  elBtnShare.addEventListener('click', () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      App.showToast('Link copiado!');
    }).catch(() => {
      App.showToast('Copia o URL manualmente');
    });
  });

  // ── URL state ─────────────────────────────────────────────────
  function updateURL() {
    if (!selected.length) {
      history.replaceState(null, '', '#explorador');
      return;
    }
    const s = selected.map(sel => `${sel.source}/${sel.indicator}`).join(',');
    const params = [`s=${encodeURIComponent(s)}`];
    if (elFrom.value) params.push(`from=${elFrom.value}`);
    if (elTo.value)   params.push(`to=${elTo.value}`);
    history.replaceState(null, '', `#explorador?${params.join('&')}`);
  }

  function restoreFromURL() {
    const hash = window.location.hash;
    if (!hash.includes('?s=')) return;
    try {
      const qs   = hash.split('?')[1] || '';
      const map  = Object.fromEntries(qs.split('&').map(p => p.split('=')));
      const sStr = decodeURIComponent(map.s || '');
      const fromV = map.from || '';
      const toV   = map.to   || '';

      if (fromV) elFrom.value = fromV;
      if (toV)   elTo.value   = toV;

      const pairs = sStr.split(',').filter(Boolean);
      pairs.forEach(pair => {
        const slash = pair.indexOf('/');
        if (slash < 0) return;
        const src = pair.slice(0, slash);
        const ind = pair.slice(slash + 1);
        const srcInfo = catalog[src];
        if (!srcInfo) return;
        const indInfo = srcInfo.indicators?.[ind];
        if (!indInfo) return;
        selected.push({ source: src, indicator: ind, label: indInfo.label || ind, unit: indInfo.unit || '' });
      });

      if (selected.length) {
        renderChips();
        renderFicha();
        render();
      }
    } catch (e) {
      console.warn('[explorador] URL restore error:', e);
    }
  }

  // ── WP-9: handle deep-link re-entry from Painel cards ─────────────
  window.addEventListener('hashchange', () => {
    const hash = window.location.hash;
    if (hash.startsWith('#explorador?')) {
      selected = [];
      renderChips();
      renderFicha();
      restoreFromURL();
    }
  });

  // ── Init ──────────────────────────────────────────────────────
  restoreFromURL();
});
