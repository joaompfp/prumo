/* ═══════════════════════════════════════════════════════════════
   explorador.js — World Bank-style multi-indicator explorer
   CAE Dashboard V7  (M4)
   ═══════════════════════════════════════════════════════════════ */

App.registerSection('explorador', async () => {
  // ── Cleanup from previous init (re-init on deep-link) ──────────
  // The hashchange listener below captures closure state; if the section
  // re-initialises (app.js line 182 sets _initialized=false on incoming params),
  // old listeners would fire with stale/empty catalog.  AbortController
  // ensures only the latest listener survives.
  if (window.__exploradorHashAbort) window.__exploradorHashAbort.abort();
  const _hashAbort = new AbortController();
  window.__exploradorHashAbort = _hashAbort;

  const container  = document.getElementById('explorador');
  const body       = container.querySelector('.section-body');
  const BASE       = window.__BASE_PATH__ || '';

  // ── State ──────────────────────────────────────────────────────
  let catalog      = {};        // {SOURCE: {label, indicators: {IND: {...}}}}
  let selected     = [];        // [{source, indicator, label, unit}]
  let chartInst    = null;
  let viewMode     = 'chart';   // 'chart' | 'table'
  let lastSeries   = [];        // [{source, indicator, label, unit, data:[{period,value}]}]
  let aiPanelAbort = null;      // AbortController for in-flight AI panel request
  let renderVersion = 0;        // Monotonic counter — discard stale concurrent renders

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

  // ── Period normalisation (WP-E5) ──────────────────────────────
  // Normalises all period formats to YYYY-MM so mixed-frequency series
  // (e.g. annual "2024" vs monthly "2024-03") align on the same X-axis.
  function normalisePeriod(p) {
    if (!p) return p;
    // Annual: "2024" → "2024-12"
    if (/^\d{4}$/.test(p)) return `${p}-12`;
    // Quarterly: "2025-Q3" or "2025 Q3" → "2025-09"
    const qm = p.match(/^(\d{4})[- ]Q(\d)$/);
    if (qm) return `${qm[1]}-${String(parseInt(qm[2]) * 3).padStart(2, '0')}`;
    // Semi-annual: "2025 S1" or "2025-H1" → "2025-06" / "2025-12"
    const sm = p.match(/^(\d{4})[- ][SH](\d)$/);
    if (sm) return `${sm[1]}-${sm[2] === '1' ? '06' : '12'}`;
    // Monthly: "2025-03" → as-is
    return p;
  }
  // Returns true if the raw period string was an annual value ("YYYY")
  function isAnnualPeriod(p) { return !!p && /^\d{4}$/.test(p); }

  // ── Toast — usa App.showToast (WP-5 unified) ─────────────────────

  // ── Build HTML skeleton ───────────────────────────────────────
  body.innerHTML = `
    <div class="explorador-wrap">
      <!-- Guided exploration paths -->
      <div class="exp-guided-paths" id="exp-guided">
        <span class="exp-guided-label">Explorar:</span>
        <button class="exp-path-btn" data-path="custo_vida">Custo de Vida</button>
        <button class="exp-path-btn" data-path="emprego">Emprego</button>
        <button class="exp-path-btn" data-path="energia">Energia</button>
        <button class="exp-path-btn" data-path="industria">Indústria</button>
        <button class="exp-path-btn" data-path="macro">Conjuntura</button>
      </div>

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
        <button class="exp-clear-btn hidden" id="exp-clear-btn" title="Limpar todos os indicadores">Limpar</button>
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
        <button class="time-preset-btn" id="exp-render-btn">Ver →</button>
        <button class="time-preset-btn" id="exp-ai-btn" title="Análise automática com IA" disabled>✦ IA</button>
      </div>

      <div class="analise-layout">
        <div class="explorador-chart-container" id="exp-chart-wrap">
          <div class="explorador-empty-state">
            Selecciona indicadores para visualizar
          </div>
        </div>
        <details id="ai-panel-details" class="ai-panel-collapsible">
          <summary class="ai-panel-summary">✦ Análise Automática</summary>
          <div id="ai-panel">
            <div class="ai-context" id="ai-panel-context"></div>
            <div id="ai-panel-text"></div>
            <div class="ai-links" id="ai-panel-links"></div>
            <div class="ai-footer" id="ai-panel-footer"></div>
          </div>
        </details>
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
  const elAIBtn       = body.querySelector('#exp-ai-btn');

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

    // Source aliases PT-PT → inglês e vice-versa
    const SRC_ALIASES = { ocde: 'oecd', oecd: 'ocde', 'banco de portugal': 'bportugal', bportugal: 'banco de portugal', 'banco mundial': 'worldbank', worldbank: 'banco mundial', eurostat: 'eurostat', ine: 'ine', fred: 'fred', dgeg: 'dgeg', erse: 'erse', ren: 'ren' };
    const filtered = all.filter(item => {
      const matchSrc = !srcF || item.source === srcF;
      const srcLower = item.source.toLowerCase();
      const alias    = SRC_ALIASES[query] || '';
      const matchQ   = !query ||
        item.label.toLowerCase().includes(query) ||
        srcLower.includes(query) ||
        (alias && srcLower.includes(alias)) ||
        item.indicator.toLowerCase().includes(query);
      return matchSrc && matchQ;
    });
    // Sort: label substring matches first, then indicator ID matches
    if (query) {
      filtered.sort((a, b) => {
        const aLabel = a.label.toLowerCase().includes(query) ? 0 : 1;
        const bLabel = b.label.toLowerCase().includes(query) ? 0 : 1;
        return aLabel - bLabel;
      });
    }

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
        renderResults(); // always keep open after adding
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

  // ── Session persistence ───────────────────────────────────────
  const SS_KEY = 'bussola_exp_selected';
  function saveSession() {
    try { sessionStorage.setItem(SS_KEY, JSON.stringify(selected)); } catch(_) {}
  }
  function loadSession() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(SS_KEY) || '[]');
      saved.forEach(s => {
        if (selected.length < 5 && !selected.some(e => e.source === s.source && e.indicator === s.indicator)) {
          selected.push(s);
        }
      });
      if (selected.length) { renderChips(); renderFicha(); render(); }
    } catch(_) {}
  }

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
    saveSession();
  }

  function removeIndicator(source, indicator) {
    selected = selected.filter(s => !(s.source === source && s.indicator === indicator));
    renderChips();
    renderFicha();
    if (selected.length > 0) autoRender();
    else clearChart();
    saveSession();
  }

  function clearAllIndicators() {
    selected = [];
    try { sessionStorage.removeItem(SS_KEY); } catch(_) {}
    renderChips();
    renderFicha();
    clearChart();
    updateURL();
  }

  function renderChips() {
    // Remove existing chips (keep placeholder)
    elChips.querySelectorAll('.indicator-chip').forEach(c => c.remove());

    const elClear = document.getElementById('exp-clear-btn');
    if (selected.length === 0) {
      elChipPH.style.display = '';
      if (elClear) elClear.classList.add('hidden');
    } else {
      elChipPH.style.display = 'none';
      if (elClear) elClear.classList.remove('hidden');
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
      <details class="ficha-inline-details">
      <summary class="ficha-inline-title">Ficha técnica dos indicadores seleccionados</summary>
      ${selected.map((s, i) => {
        const srcData = catalog[s.source] || {};
        const indData = (srcData.indicators || {})[s.indicator] || {};
        const color = SERIES_COLORS[i % SERIES_COLORS.length];
        return `<div class="ficha-inline-card" data-source="${s.source}" data-indicator="${s.indicator}" title="Clique para ver na Ficha Técnica">
          <div class="ficha-inline-header">
            <span class="ficha-color-dot" style="background:${color}"></span>
            <strong>${s.label}</strong>
            <span class="ficha-inline-source">${srcData.label || s.source}</span>
          </div>
          <div class="ficha-inline-body">
            ${indData.description ? `<p class="ficha-inline-desc">${indData.description}</p>` : ''}
            <div class="ficha-inline-meta">
              <span>Código: <code class="indicator-shortcode">${s.indicator}</code></span>
              <span>Unidade: <strong>${s.unit || indData.unit || 'n/d'}</strong></span>
              <span>Frequência: <strong>${freqLabel(indData.frequency)}</strong></span>
              <span>Cobertura: <strong>${indData.since || '?'} — ${indData.until || '?'}</strong></span>
              <span>Observações: <strong>${indData.rows_pt || indData.rows || 'n/d'}</strong></span>
              <button class="ficha-cite-btn" data-source="${s.source}" data-indicator="${s.indicator}" data-label="${encodeURIComponent(s.label)}" data-src-label="${encodeURIComponent(srcData.label || s.source)}" title="Copiar citação">Citar</button>
            </div>
          </div>
        </div>`;
      }).join('')}
      </details>`;

    // Click card → navigate to Ficha and scroll to that indicator's row
    container.querySelectorAll('.ficha-inline-card[data-source]').forEach(card => {
      card.addEventListener('click', async (e) => {
        if (e.target.closest('.ficha-cite-btn')) return; // Don't navigate on cite click
        const src = card.dataset.source;
        const ind = card.dataset.indicator;
        await App.navigate('ficha');
        const row = document.getElementById(`ficha-row-${src}-${ind}`);
        if (row) {
          row.scrollIntoView({ behavior: 'smooth', block: 'center' });
          row.classList.add('ficha-row-highlight');
          setTimeout(() => row.classList.remove('ficha-row-highlight'), 2000);
        }
      });
    });

    // Citation copy
    container.querySelectorAll('.ficha-cite-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const label = decodeURIComponent(btn.dataset.label);
        const srcLabel = decodeURIComponent(btn.dataset.srcLabel);
        const today = new Date().toISOString().slice(0, 10);
        const citation = `${label}. Fonte: ${srcLabel}. In: Prumo PT (${window.location.origin}/dados). Acedido em ${today}.`;
        navigator.clipboard.writeText(citation).then(() => {
          App.showToast('Citação copiada!');
        });
      });
    });
  }

  // ── Time range presets ────────────────────────────────────────
  body.querySelectorAll('.time-preset-btn[data-years]').forEach(btn => {
    btn.addEventListener('click', () => {
      body.querySelectorAll('.time-preset-btn[data-years]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const years = parseInt(btn.dataset.years, 10);
      elTo.value = nowYM();
      elFrom.value = years === 0 ? '' : subtractYears(years);
      if (selected.length > 0) autoRender();
    });
  });

  // ── Period change → auto-render (chart + AI with new date range) ──
  let _periodDebounce;
  function onPeriodChange() {
    clearTimeout(_periodDebounce);
    _periodDebounce = setTimeout(() => { if (selected.length > 0) render(); }, 600);
  }
  elFrom.addEventListener('change', onPeriodChange);
  elTo.addEventListener('change', onPeriodChange);

  // ── Render button ─────────────────────────────────────────────
  elRenderBtn.addEventListener('click', () => render());

  // ── IA toggle button ──────────────────────────────────────────
  elAIBtn.addEventListener('click', () => {
    if (!lastSeries.length) return;
    const details = document.getElementById('ai-panel-details');
    if (!details) return;
    if (!details.open) {
      details.open = true;
      updateAIPanel(lastSeries, elFrom.value || '', elTo.value || nowYM());
      elAIBtn.classList.add('active');
    } else {
      if (aiPanelAbort) { aiPanelAbort.abort(); aiPanelAbort = null; }
      details.open = false;
      elAIBtn.classList.remove('active');
    }
  });

  // ── AI panel <details> toggle — trigger analysis on expand ─────
  const elAIDetails = body.querySelector('#ai-panel-details');
  if (elAIDetails) {
    elAIDetails.addEventListener('toggle', () => {
      if (elAIDetails.open && lastSeries.length) {
        updateAIPanel(lastSeries, elFrom.value || '', elTo.value || nowYM());
        if (elAIBtn) elAIBtn.classList.add('active');
      } else {
        if (aiPanelAbort) { aiPanelAbort.abort(); aiPanelAbort = null; }
        if (elAIBtn) elAIBtn.classList.remove('active');
      }
    });
  }

  // ── Auto-render on selection change ──────────────────────────
  function autoRender() {
    if (selected.length > 0) render();
  }


  // ── AI Panel (Haiku) ──────────────────────────────────────────
  function _renderMd(text) {
    // Strip preamble lines (model thinking out loud) and horizontal rules
    const lines = text.split('\n');
    const preambleRe = /^(vou |irei |vamos |let me |i'll |i will |análise\s*$|---+\s*$)/i;
    const firstContent = lines.findIndex(l => !preambleRe.test(l.trim()) && l.trim().length > 0);
    const cleaned = (firstContent > 0 ? lines.slice(firstContent) : lines).join('\n');

    return cleaned
      .replace(/^---+\s*$/gm, '')
      .replace(/^#{1,3}\s+/gm, '')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, m => `<ul>${m}</ul>`)
      .split(/\n\n+/)
      .map(p => p.trim())
      .filter(Boolean)
      .map(p => p.startsWith('<ul>') ? p : `<p style="margin:0 0 0.7rem">${p.replace(/\n/g, ' ')}</p>`)
      .join('');
  }

  async function updateAIPanel(seriesData, from, to) {
    // Cancel any in-flight request from a previous render
    if (aiPanelAbort) { aiPanelAbort.abort(); }
    const ctrl = new AbortController();
    aiPanelAbort = ctrl;

    const panel   = document.getElementById('ai-panel');
    const text    = document.getElementById('ai-panel-text');
    const ctx     = document.getElementById('ai-panel-context');
    const linksEl = document.getElementById('ai-panel-links');
    const footer  = document.getElementById('ai-panel-footer');
    if (!panel || !text) return;

    // Show context (which indicators + period)
    if (ctx) {
      const labels = seriesData.map(s => s.label).join(', ');
      const period = from && to ? `${from} → ${to}` : (from || to || '');
      ctx.textContent = period ? `${labels} · ${period}` : labels;
    }

    // Clear stale links immediately so old ones don't persist during loading
    if (linksEl) { linksEl.innerHTML = ''; linksEl.style.display = 'none'; }
    if (footer) footer.textContent = '';

    text.innerHTML = '<span class="ai-loading">A gerar análise IA…</span>';
    if (elAIBtn) { elAIBtn.classList.add('active'); elAIBtn.disabled = false; }

    try {
      const lens = localStorage.getItem('prumo-lens') || 'cae';
      const custom_ideology = lens === 'custom' ? (localStorage.getItem('prumo-custom-ideology') || CUSTOM_LENS_DEFAULT) : null;
      const output_language = getOutputLanguage();

      // sessionStorage cache to avoid redundant LLM calls for same combo
      const cacheKey = 'prumo_interpret_' + btoa(unescape(encodeURIComponent(
        JSON.stringify({ind: seriesData.map(s => `${s.source}/${s.indicator}`).sort(), from, to, lens, output_language})
      ))).slice(0, 64);
      const cached = sessionStorage.getItem(cacheKey);
      let data;
      if (cached) {
        data = JSON.parse(cached);
      } else {
        const res = await fetch(`${BASE}/api/interpret`, {
          method: 'POST',
          signal: ctrl.signal,
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({series: seriesData, from, to, lang: 'pt', context: 'economia portuguesa', lens, custom_ideology, output_language}),
        });
        if (ctrl.signal.aborted) return;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        data = await res.json();
        try { sessionStorage.setItem(cacheKey, JSON.stringify(data)); } catch(_) {}
      }
      if (ctrl.signal.aborted) return;
      if (data.text) {
        text.innerHTML = _renderMd(data.text) || data.text;
        if (elAIBtn) elAIBtn.classList.add('active');
        // Links from web search
        if (linksEl) {
          const links = data.links || [];
          if (links.length) {
            linksEl.innerHTML = `<span class="ai-links-label">🔗 Leitura relacionada:</span>` +
              links.map(l => `<a href="${l.url}" target="_blank" rel="noopener noreferrer" title="${l.url}">${l.title || l.url}</a>`).join('');
            linksEl.style.display = '';
          } else {
            linksEl.innerHTML = '';
            linksEl.style.display = 'none';
          }
        }
        // Footer with timestamp
        if (footer) footer.textContent = cached
          ? `Análise em cache (sessão)`
          : `Análise gerada: ${new Date().toLocaleTimeString('pt-PT', {hour:'2-digit',minute:'2-digit'})}`;
      } else {
        if (elAIBtn) elAIBtn.classList.remove('active');
      }
    } catch(e) {
      if (e.name === 'AbortError') return;  // cancelled by newer request — leave panel as-is
      console.warn('[ai-panel] interpret error:', e);
      if (elAIBtn) elAIBtn.classList.remove('active');
    }
  }

  // ── Clear chart ───────────────────────────────────────────────
  function clearChart() {
    if (chartInst) { SWD.destroyChart(chartInst); chartInst = null; }
    elChartWrap.innerHTML = '<div class="explorador-empty-state">Selecciona indicadores para visualizar</div>';
    elTableWrap.classList.add('hidden');
    lastSeries = [];
    const _aiDetails = document.getElementById('ai-panel-details');
    if (_aiDetails) _aiDetails.open = false;
    if (elAIBtn) { elAIBtn.classList.remove('active'); elAIBtn.disabled = true; }
    // M2: Remove unit warning banner when chart is cleared
    const banner = document.getElementById('exp-unit-warning');
    if (banner) banner.remove();
    const freqNote = document.getElementById('exp-freq-note');
    if (freqNote) freqNote.remove();
    updateURL();
  }

  // ── Main render ───────────────────────────────────────────────
  async function render() {
    if (!selected.length) return;

    // Version guard: discard results from older concurrent renders
    const myVersion = ++renderVersion;

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
      // Discard if a newer render started while we were fetching
      if (myVersion !== renderVersion) return;
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

      // ── Auto-expand date range when too few data points ─────────
      const totalPts = lastSeries.reduce((n, s) => n + s.data.length, 0);
      if (totalPts < 5 && (fromV || toV)) {
        // Re-fetch without date constraints to get all available data
        const expandedFetches = selected.map(s => {
          const url = `${BASE}/api/series?source=${encodeURIComponent(s.source)}&indicator=${encodeURIComponent(s.indicator)}`;
          return fetch(url).then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status} for ${s.source}/${s.indicator}`);
            return r.json();
          });
        });
        const expandedResults = await Promise.all(expandedFetches);
        if (myVersion !== renderVersion) return;

        lastSeries = expandedResults.map((arr, i) => {
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

        // Update date inputs to reflect the actual data range
        const allPeriods = lastSeries.flatMap(s => s.data.map(d => d.period)).filter(Boolean).sort();
        if (allPeriods.length) {
          elFrom.value = allPeriods[0].slice(0, 7);  // YYYY-MM
          elTo.value   = allPeriods[allPeriods.length - 1].slice(0, 7);
        }
      }

      // Determine Y-axis mode — normalise unit strings first (€/l === EUR/l etc.)
      // Resolve units: normalise display + convert same-family units (€/kWh + €/MWh → single axis)
      const rawUnits = lastSeries.map(s => s.unit || '');
      const resolved = fmt.resolveUnits(rawUnits);
      // Apply conversion factors to lastSeries data (mutate a copy)
      const conversions = []; // track which series were converted for UX notice
      lastSeries = lastSeries.map((s, i) => {
        const { factor, unit } = resolved[i];
        if (factor === 1) return { ...s, unit };
        const origUnit = s.unit;
        conversions.push(`${s.label}: ${fmt.unit(origUnit)||origUnit} → ${unit} (×${factor % 1 === 0 ? factor : factor.toFixed(4)})`);
        return { ...s, unit, data: s.data.map(d => ({ ...d, value: d.value != null ? d.value * factor : null })) };
      });
      const units = [...new Set(lastSeries.map(s => s.unit).filter(Boolean))];
      const yMode = units.length <= 1 ? 'single'
                  : units.length === 2 ? 'dual'
                  : 'indexed';

      // M2: Warn on incompatible units — banner goes BEFORE analise-layout, outside the flex row
      // Show conversion notice if unit scaling was applied
      if (conversions.length) {
        let convBanner = document.getElementById('exp-conv-notice');
        if (!convBanner) {
          convBanner = document.createElement('div');
          convBanner.id = 'exp-conv-notice';
          convBanner.className = 'exp-info-banner';
        }
        convBanner.textContent = `Conversão automática de unidades: ${conversions.join(' | ')}`;
        const analiseLayout = elChartWrap.parentNode;
        if (convBanner.parentNode !== analiseLayout.parentNode) {
          analiseLayout.parentNode.insertBefore(convBanner, analiseLayout);
        }
      } else {
        const cb = document.getElementById('exp-conv-notice');
        if (cb) cb.remove();
      }

      if (units.length > 1) {
        let banner = document.getElementById('exp-unit-warning');
        if (!banner) {
          banner = document.createElement('div');
          banner.id = 'exp-unit-warning';
          banner.className = 'exp-warning-banner';
        }
        if (yMode === 'dual') {
          banner.textContent = `Dois eixos verticais — esquerdo: ${units[0]} · direito: ${units[1]}`;
        } else {
          banner.textContent = `Unidades incompatíveis (${units.join(', ')}) — o gráfico pode ser enganador. Considera usar o modo Indexado.`;
        }
        const analiseLayout = elChartWrap.parentNode;
        if (banner.parentNode !== analiseLayout) {
          analiseLayout.insertBefore(banner, elChartWrap);
        }
      } else {
        const banner = document.getElementById('exp-unit-warning');
        if (banner) banner.remove();
      }

      if (viewMode === 'chart') renderChart(yMode, units);
      else                      renderTable();

      // ── Fix 5: Frequency mismatch note ──────────────────────────
      const freqs = new Set(selected.map(s => {
        const srcData = catalog[s.source] || {};
        const indData = (srcData.indicators || {})[s.indicator] || {};
        return indData.frequency || '';
      }).filter(Boolean));
      if (freqs.size > 1) {
        let freqNote = document.getElementById('exp-freq-note');
        if (!freqNote) {
          freqNote = document.createElement('div');
          freqNote.id = 'exp-freq-note';
          freqNote.className = 'exp-info-banner';
        }
        const freqLabel = f => ({ monthly: 'mensal', annual: 'anual', weekly: 'semanal', semester: 'semestral', quarterly: 'trimestral' }[f] || f);
        freqNote.textContent = `Nota: frequências diferentes (${[...freqs].map(freqLabel).join(', ')}) — dados trimestrais ligados entre pontos`;
        const analiseLayout = elChartWrap.parentNode;
        if (freqNote.parentNode !== analiseLayout) {
          analiseLayout.insertBefore(freqNote, elChartWrap);
        }
      } else {
        const fn = document.getElementById('exp-freq-note');
        if (fn) fn.remove();
      }

      // Enable IA button now that we have data
      if (elAIBtn) elAIBtn.disabled = false;

      // Only trigger AI analysis if the panel is already expanded
      const aiDetails = document.getElementById('ai-panel-details');
      if (aiDetails && aiDetails.open) {
        updateAIPanel(lastSeries, fromV, toV);
      }

      updateURL();
    } catch (e) {
      elChartWrap.innerHTML = `<div class="error-state">Erro: ${e.message}</div>`;
      console.error('[explorador] render error:', e);
    }
  }

  // ── Chart rendering ───────────────────────────────────────────
  function renderChart(yMode, units) {
    const isMobile = (elChartWrap.offsetWidth || window.innerWidth) < 640;
    const chartH = Math.max(elChartWrap.offsetHeight || 0, isMobile ? 320 : 400);
    elChartWrap.innerHTML = `<div id="exp-chart" style="width:100%;height:${chartH}px;overflow:hidden"></div>`;
    const chartEl = elChartWrap.querySelector('#exp-chart');

    if (chartInst) { SWD.destroyChart(chartInst); chartInst = null; }

    // Normalise all periods to YYYY-MM before merging series (WP-E5)
    const normPeriod = p => normalisePeriod(p);
    // Track which normalised periods were originally annual (for display via fmt.period)
    const annualNormPeriods = new Set(
      lastSeries.flatMap(s => s.data.filter(d => isAnnualPeriod(d.period)).map(d => normPeriod(d.period)))
    );
    const allPeriods = [...new Set(
      lastSeries.flatMap(s => s.data.map(d => normPeriod(d.period)))
    )].sort();

    const series = lastSeries.map((s, i) => {
      const color   = SERIES_COLORS[i] || '#999';
      const byPeriod = Object.fromEntries(s.data.map(d => [normPeriod(d.period), d.value]));

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
        endLabel: isMobile ? false : (s.label.length < 40 ? s.label : s.label.slice(0, 37) + '…'),
      });
    }).map((s, i) => ({
      ...s,
      connectNulls: s.data.filter(v => v === null || v === undefined).length / s.data.length > 0.3,
      yAxisIndex: yMode === 'dual' ? (units.indexOf(lastSeries[i].unit) === 1 ? 1 : 0) : 0,
    }));

    const yAxes = [];
    const _yNameStyle = (color) => ({
      nameLocation: 'end',
      nameTextStyle: { fontSize: 10, color, fontFamily: 'Inter, system-ui, sans-serif', padding: [0, 0, 0, -10] },
    });
    const _yNameStyleR = (color) => ({
      nameLocation: 'end',
      nameTextStyle: { fontSize: 10, color, fontFamily: 'Inter, system-ui, sans-serif', padding: [0, -10, 0, 0] },
    });
    if (yMode === 'single') {
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: units[0] || '', ..._yNameStyle('#888') });
    } else if (yMode === 'dual') {
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: units[0] || '', ..._yNameStyle(SERIES_COLORS[0]) });
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: units[1] || units[0] || '', ..._yNameStyleR(SERIES_COLORS[1]), position: 'right' });
    } else {
      yAxes.push({ ...SWD.valueAxis({ scale: true }), name: 'Index (início=100)', ..._yNameStyle('#888') });
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
      // FIX 5: truncate long names + show full name on hover
      formatter: function(name) {
        return name.length > 35 ? name.substring(0, 32) + '…' : name;
      },
      tooltip: { show: true },  // full name visible on hover
    };
    // Override grid on the base object directly (ECharts deep-merges grid)
    baseOpts.grid.top = 30;
    baseOpts.grid.bottom = 48;
    baseOpts.grid.left = isMobile ? 40 : 50;
    baseOpts.grid.right = isMobile ? (yMode === 'dual' ? 45 : 16) : (yMode === 'dual' ? 55 : 180);

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
          const dispPeriod = fmt.period(period, { annualCollapsed: annualNormPeriods.has(period) });
          let html = `<div style="font-weight:600;margin-bottom:4px">${dispPeriod}</div>`;
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

    // Normalise all periods to YYYY-MM before merging series (WP-E5)
    const normPeriod = p => normalisePeriod(p);
    const annualNormPeriods = new Set(
      lastSeries.flatMap(s => s.data.filter(d => isAnnualPeriod(d.period)).map(d => normPeriod(d.period)))
    );
    // Filter out annual aggregate rows (period="YYYY") when monthly data exists
    // — they create confusing jumps in the table
    const hasMonthly = lastSeries.some(s => s.data.some(d => d.period && d.period.length >= 7));
    const allPeriods = [...new Set(
      lastSeries.flatMap(s => s.data
        .filter(d => !(hasMonthly && isAnnualPeriod(d.period)))
        .map(d => normPeriod(d.period))
      )
    )].sort().reverse();

    const headers = ['Período', ...lastSeries.map(s => `${s.source} — ${s.label}`)];
    const byPeriod = lastSeries.map(s =>
      Object.fromEntries(s.data.map(d => [normPeriod(d.period), d.value]))
    );

    const rows = allPeriods
      .filter(p => lastSeries.some((_, i) => byPeriod[i][p] !== undefined))
      .map(p => [fmt.period(p, { annualCollapsed: annualNormPeriods.has(p) }), ...lastSeries.map((_, i) => {
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
      const units = [...new Set(lastSeries.map(s => fmt.unit(s.unit) || s.unit).filter(Boolean))];
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
    if (!hash.includes('?s=')) return false;
    try {
      const qs   = hash.split('?')[1] || '';
      const map  = Object.fromEntries(qs.split('&').map(p => p.split('=')));
      const sStr = decodeURIComponent(map.s || '');
      const fromV = map.from || '';
      const toV   = map.to   || '';

      if (fromV) elFrom.value = fromV;
      if (toV)   elTo.value   = toV;

      let added = 0;
      const pairs = sStr.split(',').filter(Boolean);
      pairs.forEach(pair => {
        const slash = pair.indexOf('/');
        if (slash < 0) return;
        let src = pair.slice(0, slash);
        const ind = pair.slice(slash + 1);
        // Alias normalisation: OCDE→OECD, Banco Mundial→WORLDBANK, etc.
        const SRC_ALIAS = { 'OCDE': 'OECD', 'BANCO MUNDIAL': 'WORLDBANK', 'BANCO DE PORTUGAL': 'BPORTUGAL' };
        src = SRC_ALIAS[src.toUpperCase()] || src;
        if (selected.length >= 5) return;
        if (selected.some(e => e.source === src && e.indicator === ind)) return;
        const srcInfo = catalog[src];
        if (!srcInfo) return;
        const indInfo = srcInfo.indicators?.[ind];
        if (!indInfo) return;
        selected.push({ source: src, indicator: ind, label: indInfo.label || ind, unit: indInfo.unit || '' });
        added++;
      });

      if (added > 0) {
        renderChips();
        renderFicha();
        render();
        saveSession();
      }
      return added > 0;
    } catch (e) {
      console.warn('[explorador] URL restore error:', e);
      return false;
    }
  }

  // ── Clear button ──────────────────────────────────────────────
  document.getElementById('exp-clear-btn')?.addEventListener('click', () => {
    clearAllIndicators();
  });

  // ── Re-generate AI when global lens changes ────────────────────
  window.addEventListener('lens-change', () => {
    const _aiDet = document.getElementById('ai-panel-details');
    if (lastSeries.length && _aiDet && _aiDet.open) {
      updateAIPanel(lastSeries, elFrom.value || '', elTo.value || nowYM());
    }
  }, { signal: _hashAbort.signal });

  // ── Handle deep-link re-entry (Painel cards, Ficha links, shared URLs) ──
  // Uses AbortController signal so old listeners are removed on re-init
  window.addEventListener('hashchange', () => {
    const hash = window.location.hash;
    if (hash.startsWith('#explorador?')) {
      // Painel cards always navigate with 1 indicator → ADD behaviour.
      // External deep-links (emails, shared URLs) have multiple → REPLACE.
      try {
        const qs  = hash.split('?')[1] || '';
        const map = Object.fromEntries(qs.split('&').map(p => p.split('=')));
        const newInds = decodeURIComponent(map.s || '').split(',').filter(Boolean);
        if (newInds.length > 1) selected = [];  // full deep-link → clear first
      } catch(_) {}
      restoreFromURL();
    }
  }, { signal: _hashAbort.signal });

  // ── Guided exploration paths ────────────────────────────────────
  const GUIDED_PATHS = {
    custo_vida: [
      { source: 'INE', indicator: 'hicp_total' },
      { source: 'EUROSTAT', indicator: 'hicp_yoy' },
      { source: 'DGEG', indicator: 'price_gasoline' },
    ],
    emprego: [
      { source: 'EUROSTAT', indicator: 'unemployment' },
      { source: 'INE', indicator: 'employment_rate' },
      { source: 'INE', indicator: 'wages_industry' },
    ],
    energia: [
      { source: 'REN', indicator: 'electricity_price_mibel' },
      { source: 'DGEG', indicator: 'price_diesel' },
      { source: 'FRED', indicator: 'brent_oil' },
    ],
    industria: [
      { source: 'INE', indicator: 'ipi_seasonal_cae_TOT' },
      { source: 'INE', indicator: 'ipi_total' },
      { source: 'OECD', indicator: 'order_books' },
    ],
    macro: [
      { source: 'INE', indicator: 'gdp_yoy' },
      { source: 'EUROSTAT', indicator: 'unemployment' },
      { source: 'INE', indicator: 'hicp_total' },
    ],
  };

  body.querySelectorAll('.exp-path-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const pathId = btn.dataset.path;
      const indicators = GUIDED_PATHS[pathId] || [];
      // Clear current selection and add path indicators
      selected = [];
      indicators.forEach(({ source, indicator }) => {
        const srcInfo = catalog[source];
        if (!srcInfo) return;
        const indInfo = srcInfo.indicators?.[indicator];
        if (!indInfo) return;
        selected.push({ source, indicator, label: indInfo.label || indicator, unit: indInfo.unit || '' });
      });
      renderChips();
      renderFicha();
      if (selected.length) render();
      saveSession();
      // Highlight active path
      body.querySelectorAll('.exp-path-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  // ── Init ──────────────────────────────────────────────────────
  if (!restoreFromURL()) {
    loadSession();  // No URL params → restore previous session
    // If still empty (no session), auto-load macro path as default
    if (selected.length === 0) {
      const defaultPath = GUIDED_PATHS.macro || [];
      defaultPath.forEach(({ source, indicator }) => {
        const srcInfo = catalog[source];
        if (!srcInfo) return;
        const indInfo = srcInfo.indicators?.[indicator];
        if (!indInfo) return;
        selected.push({ source, indicator, label: indInfo.label || indicator, unit: indInfo.unit || '' });
      });
      if (selected.length) {
        renderChips();
        renderFicha();
        render();
        body.querySelector('.exp-path-btn[data-path="macro"]')?.classList.add('active');
      }
    }
  }
});
