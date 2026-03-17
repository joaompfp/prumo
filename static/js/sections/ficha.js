/* ═══════════════════════════════════════════════════════════════
   ficha.js — Ficha Técnica completa
   CAE Dashboard V7 — M5 (Analyst)
   Implementação: header + source cards + metodologia + dashboard info + disclaimer
   ═══════════════════════════════════════════════════════════════ */

// Ficha loads inside metodologia — triggered when <details> is opened
(() => {
  let _fichaLoaded = false;
  const details = document.getElementById('ficha-container');
  if (!details) return;
  details.addEventListener('toggle', async () => {
    if (!details.open || _fichaLoaded) return;
    _fichaLoaded = true;
    await _loadFicha();
  });

  async function _loadFicha() {
  const body = document.querySelector('#ficha');
  if (!body) return;

  try {
    body.innerHTML = `<div class="loading-state"><div class="loading-spinner"></div><span>${i18n.t('ficha.loading')}</span></div>`;

    // Fetch catalog + explorador (real DB stats) + resumo in parallel
    const [catalog, explorador, resumo] = await Promise.all([
      API.catalog(),
      API.get('/api/explorador').catch(() => ({ items: [], total: 0 })),
      API.get('/api/resumo').catch(() => ({ updated: '—' })),
    ]);

    // ── Compute totals from real DB data (explorador) ──────────────────
    const expItems = explorador.items || [];
    const totalIndicators = explorador.total || expItems.length;
    const totalRows       = expItems.reduce((s, i) => s + (i.rows || 0), 0);
    let earliest = expItems.reduce((m, i) => i.since && i.since < m ? i.since : m, '9999');
    let latest   = expItems.reduce((m, i) => i.until && i.until > m ? i.until : m, '0000');
    if (earliest === '9999') earliest = '—';
    if (latest   === '0000') latest   = '—';

    // Group all DB indicators by source (all 377 combinations)
    const expBySrc = {};
    expItems.forEach(item => {
      if (!expBySrc[item.source]) expBySrc[item.source] = [];
      expBySrc[item.source].push(item);
    });

    // Display sources in catalog order first, then any extra from DB
    const catalogOrder = Object.keys(catalog);
    const allSrcs = [...new Set([...catalogOrder, ...Object.keys(expBySrc)])];

    const updated   = resumo.updated || '—';
    const totalSrcs = Object.keys(expBySrc).length || catalogOrder.length;

    // Update ficha summary with stats
    const summaryEl = document.querySelector('.mf-ficha-summary .mf-heading');
    if (summaryEl) summaryEl.textContent = i18n.t('ficha.summary_heading', {sources: totalSrcs, indicators: totalIndicators});

    // ── Frequency label helper ──────────────────────────────────────
    function freqLabel(rawFreq) {
      if (!rawFreq) return '—';
      const map = {
        'monthly':   i18n.t('ficha.freq.monthly'),
        'quarterly': i18n.t('ficha.freq.quarterly'),
        'annual':    i18n.t('ficha.freq.annual'),
        'weekly':    i18n.t('ficha.freq.weekly'),
        'semester':  i18n.t('ficha.freq.semester'),
      };
      return map[rawFreq] || rawFreq;
    }

    // ── Source card HTML generator (all DB indicators + catalog metadata) ──
    function renderSourceCard(src, idx = 0) {
      const expInds = expBySrc[src] || [];
      if (!expInds.length) return '';

      const catSrc  = catalog[src] || {};
      const srcLabel = catSrc.label       || src;
      const srcUrl   = catSrc.url         || null;
      const srcDesc  = catSrc.description || '';
      const catInds  = catSrc.indicators  || {};

      const rows = expInds.map(expInd => {
        const code    = expInd.indicator;
        const catInd  = catInds[code] || {};
        const label   = catInd.label || expInd.label || code;
        const unit    = catInd.unit  || expInd.unit  || '—';
        const rawFreq = catInd.frequency || expInd.frequency || '';
        const freq    = freqLabel(rawFreq);
        const since     = expInd.since    || catInd.since || '—';
        const until     = expInd.until    || catInd.until || '—';
        const rowsCount = expInd.rows;
        const regCount  = expInd.region_count || 1;

        // Single-region → Explorador link; multi-region → Comparativos
        const linkHref  = regCount > 1 ? '#comparativos' : `#explorador?s=${src}/${code}`;
        const linkTitle = regCount > 1
          ? i18n.t('ficha.link_comparativos', {count: regCount})
          : i18n.t('ficha.link_explorador');
        const regBadge  = regCount > 1
          ? ` <span class="ficha-reg-badge" title="${i18n.t('ficha.countries_count', {count: regCount})}">${regCount}p</span>`
          : '';

        return `<tr id="ficha-row-${src}-${code}">
          <td><a href="${linkHref}" class="indicator-link" title="${linkTitle}">${code}</a>${regBadge}</td>
          <td>${label}</td>
          <td>${unit}</td>
          <td>${freq}</td>
          <td>${since}</td>
          <td>${until}</td>
          <td>${rowsCount != null ? rowsCount.toLocaleString('pt-PT') : '—'}</td>
        </tr>`;
      }).join('');

      const tableHTML = expInds.length > 0 ? `
        <div class="table-scroll-wrap">
          <table class="indicator-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>${i18n.t('ficha.table.indicator')}</th>
                <th>${i18n.t('ficha.table.unit')}</th>
                <th>${i18n.t('ficha.table.freq')}</th>
                <th>${i18n.t('ficha.table.since')}</th>
                <th>${i18n.t('ficha.table.until')}</th>
                <th>${i18n.t('ficha.table.obs')}</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>` : `<p style="color:var(--c-muted);font-size:var(--fs-sm)">${i18n.t('ficha.no_indicators')}</p>`;

      const urlHTML = srcUrl
        ? `<a href="${srcUrl}" target="_blank" rel="noopener" class="source-url-link">${i18n.t('ficha.official_site')} ↗</a>`
        : '';

      const isOpen = idx === 0;
      return `
        <details class="source-card"${isOpen ? ' open' : ''}>
          <summary class="source-header">
            <div class="source-header-meta">
              <h3 class="source-title">${srcLabel}</h3>
              ${srcDesc ? `<p class="source-desc">${srcDesc}</p>` : ''}
            </div>
            <div class="source-header-right">
              <span class="source-badge" data-source="${src}">${i18n.t('ficha.n_indicators', {count: expInds.length})}</span>
              ${urlHTML}
              <span class="source-collapse-hint">
                <span class="source-collapse-closed">▶ ${i18n.t('ficha.show_indicators')}</span>
                <span class="source-collapse-open">▼ ${i18n.t('ficha.hide')}</span>
              </span>
            </div>
          </summary>
          <div class="source-card-body">${tableHTML}</div>
        </details>`;
    }

    // ── Methodology section ───────────────────────────────────────────
    const methodologyHTML = `
      <div class="methodology-section" id="metodologia">
        <h3>${i18n.t('ficha.methodology.title')}</h3>
        <div class="methodology-content">

          <details class="method-accordion">
            <summary>${i18n.t('ficha.methodology.seasonal.title')}</summary>
            <p>${i18n.t('ficha.methodology.seasonal.body')}</p>
          </details>

          <details class="method-accordion">
            <summary>${i18n.t('ficha.methodology.base_index.title')}</summary>
            <p>${i18n.t('ficha.methodology.base_index.body')}</p>
          </details>

          <details class="method-accordion">
            <summary>${i18n.t('ficha.methodology.comparability.title')}</summary>
            <p>${i18n.t('ficha.methodology.comparability.body')}</p>
          </details>

          <details class="method-accordion">
            <summary>${i18n.t('ficha.methodology.gdp_differential.title')}</summary>
            <p>${i18n.t('ficha.methodology.gdp_differential.body')}</p>
          </details>

          <details class="method-accordion">
            <summary>${i18n.t('ficha.methodology.eu27.title')}</summary>
            <p>${i18n.t('ficha.methodology.eu27.body')}</p>
          </details>

          <details class="method-accordion" open>
            <summary>${i18n.t('ficha.methodology.update_freq.title')}</summary>
            <div class="table-scroll-wrap"><table class="methodology-table">
              <thead><tr><th>${i18n.t('ficha.methodology.update_freq.col_source')}</th><th>${i18n.t('ficha.methodology.update_freq.col_indicators')}</th><th>${i18n.t('ficha.methodology.update_freq.col_freq')}</th><th>${i18n.t('ficha.methodology.update_freq.col_lag')}</th></tr></thead>
              <tbody>
                <tr><td><strong>INE</strong></td><td>${i18n.t('ficha.methodology.update_freq.ine_desc')}</td><td>${i18n.t('ficha.freq.monthly')}</td><td>${i18n.t('ficha.methodology.update_freq.ine_lag')}</td></tr>
                <tr><td><strong>Eurostat</strong></td><td>${i18n.t('ficha.methodology.update_freq.eurostat_desc')}</td><td>${i18n.t('ficha.methodology.update_freq.eurostat_freq')}</td><td>${i18n.t('ficha.methodology.update_freq.eurostat_lag')}</td></tr>
                <tr><td><strong>FRED</strong></td><td>${i18n.t('ficha.methodology.update_freq.fred_desc')}</td><td>${i18n.t('ficha.freq.monthly')}</td><td>${i18n.t('ficha.methodology.update_freq.fred_lag')}</td></tr>
                <tr><td><strong>${i18n.t('sources.BPORTUGAL')}</strong></td><td>${i18n.t('ficha.methodology.update_freq.bportugal_desc')}</td><td>${i18n.t('ficha.freq.monthly')}</td><td>${i18n.t('ficha.methodology.update_freq.bportugal_lag')}</td></tr>
                <tr><td><strong>${i18n.t('sources.OECD')}</strong></td><td>${i18n.t('ficha.methodology.update_freq.oecd_desc')}</td><td>${i18n.t('ficha.freq.monthly')}</td><td>${i18n.t('ficha.methodology.update_freq.oecd_lag')}</td></tr>
                <tr><td><strong>REN</strong></td><td>${i18n.t('ficha.methodology.update_freq.ren_desc')}</td><td>${i18n.t('ficha.freq.monthly')}</td><td>${i18n.t('ficha.methodology.update_freq.ren_lag')}</td></tr>
                <tr><td><strong>DGEG</strong></td><td>${i18n.t('ficha.methodology.update_freq.dgeg_desc')}</td><td>${i18n.t('ficha.methodology.update_freq.dgeg_freq')}</td><td>${i18n.t('ficha.methodology.update_freq.dgeg_lag')}</td></tr>
                <tr><td><strong>ERSE</strong></td><td>${i18n.t('ficha.methodology.update_freq.erse_desc')}</td><td>${i18n.t('ficha.freq.annual')}</td><td>${i18n.t('ficha.methodology.update_freq.erse_lag')}</td></tr>
                <tr><td><strong>World Bank</strong></td><td>${i18n.t('ficha.methodology.update_freq.worldbank_desc')}</td><td>${i18n.t('ficha.freq.annual')}</td><td>${i18n.t('ficha.methodology.update_freq.worldbank_lag')}</td></tr>
              </tbody>
            </table></div>
          </details>

          <details class="method-accordion">
            <summary>${i18n.t('ficha.methodology.disclaimer.title')}</summary>
            <p>${i18n.t('ficha.methodology.disclaimer.body')}</p>
          </details>

          <details class="method-accordion">
            <summary>${i18n.t('ficha.methodology.interpretation.title')}</summary>
            <ul>
              <li>${i18n.t('ficha.methodology.interpretation.ipi')}</li>
              <li>${i18n.t('ficha.methodology.interpretation.eu27_avg')}</li>
              <li>${i18n.t('ficha.methodology.interpretation.employment')}</li>
              <li>${i18n.t('ficha.methodology.interpretation.long_series')}</li>
              <li>${i18n.t('ficha.methodology.interpretation.nominal')}</li>
              <li>${i18n.t('ficha.methodology.interpretation.worldbank_lag')}</li>
            </ul>
          </details>

        </div>
      </div>`;

    // ── Dashboard info ────────────────────────────────────────────────
    const _appUrl = 'https://joao.date/dados';
    const dashboardHTML = `
      <div class="dashboard-info">
        <h3>${i18n.t('ficha.about.title')}</h3>
        <ul>
          <li><strong>URL:</strong> <a href="${_appUrl}" target="_blank" rel="noopener" style="color:var(--c-pt)">joao.date/dados</a></li>
          <li><strong>${i18n.t('ficha.about.contact')}:</strong> <a href="mailto:joao.mpfp+prumo@gmail.com" style="color:var(--c-pt)">joao.mpfp+prumo@gmail.com</a></li>
        </ul>
        <p style="margin-top:var(--sp-md);font-size:var(--fs-xs);color:var(--c-text-sub);line-height:1.6">
          <strong>${i18n.t('ficha.about.embed')}:</strong> ${i18n.t('ficha.about.embed_desc')}
        </p>
        <pre class="dashboard-embed-code"><code>&lt;script src="${_appUrl}/static/js/embed.js" data-base="${_appUrl}" async&gt;&lt;/script&gt;
&lt;div class="cae-embed" data-indicators="INE/ipi_total"&gt;&lt;/div&gt;</code></pre>
      </div>`;

    // ── Render ────────────────────────────────────────────────────────
    body.innerHTML = `
      <!-- 1. Header -->
      <div class="ficha-header">
        <div class="ficha-meta">
          <span>${i18n.t('ficha.header.indicators_in_sources', {indicators: totalIndicators, sources: totalSrcs})}</span>
          <span>${i18n.t('ficha.header.last_update')}: <strong>${updated}</strong></span>
          <span>${i18n.t('ficha.header.total_obs')}: <strong>${totalRows > 0 ? totalRows.toLocaleString('pt-PT') : '—'}</strong></span>
          <span>${i18n.t('ficha.header.coverage')}: <strong>${earliest} → ${latest}</strong></span>
        </div>
      </div>

      <!-- 2. Source cards -->
      <div class="source-cards-list">
        ${allSrcs.map((src, i) => renderSourceCard(src, i)).join('')}
      </div>

      <!-- 3. Metodologia -->
      ${methodologyHTML}

      <!-- 4. Dashboard info -->
      ${dashboardHTML}

      <!-- 5. Disclaimer -->
      <div class="ficha-disclaimer">
        <p>${i18n.t('ficha.disclaimer')}</p>
      </div>`;

  } catch (e) {
    console.error('[ficha] error:', e);
    body.innerHTML = App.errorHTML(e.message);
  }
  } // end _loadFicha
})();
