/* ═══════════════════════════════════════════════════════════════
   painel.js — KPI cards + sparklines (v7 — Painel V2)
   Uses /api/painel (sections) with fallback to /api/resumo (flat).
   Full redesign: M2 (Criativo)
   ═══════════════════════════════════════════════════════════════ */

App.registerSection('painel', async () => {
  const container = document.getElementById('painel');
  const body = container.querySelector('.section-body');

  try {
    body.innerHTML = `
      <div class="loading-state">
        <div class="loading-spinner"></div>
        <span>A carregar indicadores…</span>
      </div>`;

    // ── Try /api/painel (sections), fallback to /api/resumo (flat) ──
    let data;
    let useSections = false;
    try {
      data = await API.painel();
      if (data && Array.isArray(data.sections) && data.sections.length > 0) {
        useSections = true;
      }
    } catch (e) {
      console.warn('[painel] /api/painel failed, falling back to /api/resumo:', e.message);
      data = await API.resumo();
    }

    const updated = data.updated || new Date().toISOString().slice(0, 10);

    // ── Flatten all KPIs for title logic ────────────────────────────
    let allKpis;
    if (useSections) {
      allKpis = data.sections.flatMap(s => s.kpis || []);
    } else {
      allKpis = data.kpis || [];
    }

    // Dynamic title: top 2 KPIs by absolute YoY change
    function kpiPhrase(k) {
      if (!k) return '';
      const yoy = Number(k.yoy);
      const val = Number(k.value);
      if (k.id === 'industrial_production')
        return yoy >= 0 ? `produção industrial sobe ${yoy.toFixed(1)}%` : `produção industrial recua ${Math.abs(yoy).toFixed(1)}%`;
      if (k.id === 'unemployment')
        return `desemprego em ${val.toFixed(1)}%`;
      if (k.id === 'employment_rate')
        return `taxa de emprego em ${val.toFixed(1)}%`;
      if (k.id === 'confidence')
        return yoy >= 0 ? `confiança melhora ${yoy.toFixed(1)} pp` : `confiança cede ${Math.abs(yoy).toFixed(1)} pp`;
      if (k.id === 'inflation')
        return `inflação em ${val.toFixed(1)}%`;
      return `${k.label} ${yoy >= 0 ? '+' : ''}${yoy.toFixed(1)}${k.yoy_unit || '%'}`;
    }

    // Exclude technical/non-citizen indicators from headline
    const HEADLINE_BLACKLIST = new Set(['spread_pt_de', 'cli', 'order_books', 'industrial_employment', 'industrial_production', 'ipi_total', 'energy_dependence', 'wages_industry', 'gdp_per_capita', 'rnd_pct_gdp', 'employment_rate', 'copper', 'aluminum', 'natural_gas']);
    const kpisWithYoY = allKpis.filter(k => k.yoy !== null && k.yoy !== undefined && !HEADLINE_BLACKLIST.has(k.id));
    const byAbsYoY = kpisWithYoY.slice().sort((a, b) => Math.abs(b.yoy) - Math.abs(a.yoy));
    const top1 = byAbsYoY[0];
    const top2 = byAbsYoY[1];
    let titleMsg;
    if (top1 && top2) {
      const p1 = kpiPhrase(top1);
      const p2 = kpiPhrase(top2);
      titleMsg = p1.charAt(0).toUpperCase() + p1.slice(1) + ' · ' + p2;
    } else {
      titleMsg = 'Panorama dos indicadores económicos';
    }

    const titleEl = container.querySelector('.section-title');
    const subEl = container.querySelector('.section-subtitle');
    if (titleEl) titleEl.textContent = titleMsg;
    if (subEl) subEl.textContent = `Dados actualizados: ${updated} · ${allKpis.length} indicadores · Fonte: INE, Eurostat, WorldBank`;

    // Source label map
    const SOURCE_LABELS = {
      'INE': 'INE', 'EUROSTAT': 'Eurostat', 'FRED': 'FRED',
      'BPORTUGAL': 'Banco de Portugal', 'OECD': 'OCDE',
      'WORLDBANK': 'Banco Mundial', 'REN': 'REN',
      'ERSE': 'ERSE', 'DGEG': 'DGEG',
    };

    // ── KPI card template (shared) ───────────────────────────────────
    function renderKpiCard(kpi) {
      const sentiment = kpi.sentiment || 'neutral';
      const yoy = kpi.yoy;
      const yoyUnit = kpi.yoy_unit || '%';
      const yoyText = yoy !== null && yoy !== undefined
        ? (yoy > 0 ? '+' : '') + Number(yoy).toFixed(1) + yoyUnit
        : 'n/d';
      const arrow = fmt.arrow(yoy);
      const value = kpi.value !== null && kpi.value !== undefined ? fmt.num(kpi.value) : 'n/d';
      const unit = kpi.unit || '';
      const context = kpi.context || '';
      const description = kpi.description || '';
      const label = kpi.label || kpi.id;
      const hasSpark = kpi.spark && kpi.spark.length > 0;
      const sourceLabel = kpi.source ? (SOURCE_LABELS[kpi.source] || kpi.source) : '';

      const dataAttrs = kpi.source && kpi.indicator
        ? ` data-source="${kpi.source}" data-indicator="${kpi.indicator}" title="Ver ${label} no Explorador"`
        : '';
      return `
      <div class="kpi-card ${sentiment}"${dataAttrs}>
        <div class="kpi-card-header">
          <div class="kpi-label">${label}</div>
          ${sourceLabel ? `<span class="kpi-source-tag">${sourceLabel}</span>` : ''}
        </div>
        <div class="kpi-value-row">
          <span class="kpi-value">${value}</span>
          <span class="kpi-unit">${unit}</span>
        </div>
        <div class="kpi-trend-row">
          <span class="kpi-yoy ${sentiment}">${yoyText}</span>
          <span class="kpi-arrow ${sentiment}">${arrow}</span>
          <span class="kpi-label" style="font-size:11px;letter-spacing:0.5px;">vs ano anterior</span>
        </div>
        ${description ? `<div class="kpi-description">${description}</div>` : ''}
        ${context ? `<div class="kpi-context">${context}</div>` : ''}
        ${hasSpark ? `<div class="spark-container" id="spark-${kpi.id}"></div>` : ''}
      </div>`;
    }

    // ── Render ───────────────────────────────────────────────────────
    if (useSections) {
      // Section-based rendering (Painel V2)
      body.innerHTML = '<div class="painel-sections">' +
        data.sections.map(section => {
          const kpis = section.kpis || [];
          return `
          <div class="painel-section" data-section-id="${section.id}">
            <div class="section-label">${section.label}</div>
            <div class="kpi-grid">
              ${kpis.map(renderKpiCard).join('')}
            </div>
          </div>`;
        }).join('') +
        '</div>';
    } else {
      // Flat grid fallback (legacy /api/resumo)
      const kpis = allKpis;
      body.innerHTML = '<div class="kpi-grid">' + kpis.map(renderKpiCard).join('') + '</div>';
    }

    // ── Track B: PT vs Mundo subsection ────────────────────────────
    async function renderPTvsMundo(parentEl) {
      const COMPARISONS = [
        { label: 'Inflação (HICP)',   indicator: 'hicp',            source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27',  unit: '%',  decimals: 1 },
        { label: 'Desemprego',        indicator: 'unemployment',    source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27',  unit: '%',  decimals: 1 },
        { label: 'Crescimento PIB',   indicator: 'gdp_growth',      source: 'WORLDBANK', ref: 'EU',  refLabel: 'UE',     unit: '%',  decimals: 2 },
        { label: 'PIB per Capita PPP',indicator: 'gdp_per_capita_ppp',source:'WORLDBANK',ref: 'EU',  refLabel: 'UE',     unit: '$',  decimals: 0 },
      ];

      const section = document.createElement('div');
      section.className = 'pt-mundo-section';
      section.innerHTML = `
        <div class="section-label">Portugal vs Mundo · Comparação de Referência</div>
        <div class="pt-mundo-grid" id="pt-mundo-grid">
          ${COMPARISONS.map((_, i) => `<div class="pt-mundo-card" id="pt-mundo-card-${i}">
            <div class="loading-state" style="height:80px"><div class="loading-spinner"></div></div>
          </div>`).join('')}
        </div>`;
      parentEl.appendChild(section);

      // Fetch all comparisons in parallel
      await Promise.allSettled(COMPARISONS.map(async (cmp, i) => {
        const cardEl = document.getElementById(`pt-mundo-card-${i}`);
        try {
          const since = '2018';
          const url = `/api/mundo?indicator=${encodeURIComponent(cmp.indicator)}&source=${cmp.source}&countries=PT,${cmp.ref}&since=${since}`;
          const data = await API.get(url);
          const series = data.series || [];
          const ptSeries  = series.find(s => s.country === 'PT');
          const refSeries = series.find(s => s.country === cmp.ref);

          const ptLast  = ptSeries?.data?.at(-1);
          const refLast = refSeries?.data?.at(-1);

          const dec = cmp.decimals ?? 1;
          const ptVal  = ptLast?.value  != null ? Number(ptLast.value).toFixed(dec) : 'n/d';
          const refVal = refLast?.value != null ? Number(refLast.value).toFixed(dec) : 'n/d';
          const period = ptLast?.period || '';

          let deltaHtml = '';
          if (ptLast?.value != null && refLast?.value != null) {
            const delta = ptLast.value - refLast.value;
            const sign  = delta > 0 ? '+' : '';
            const cls   = delta > 0 ? 'positive' : (delta < 0 ? 'negative' : '');
            const dStr  = cmp.decimals === 0 ? Math.round(delta).toLocaleString('pt-PT') : delta.toFixed(cmp.decimals ?? 1);
            deltaHtml = `<div class="pt-mundo-delta ${cls}">PT ${sign}${dStr}${cmp.unit} vs ${cmp.refLabel}</div>`;
          }

          const unitDisp = cmp.unit === '€' ? '€' : cmp.unit;
          cardEl.innerHTML = `
            <div class="pt-mundo-card-title">${cmp.label}</div>
            <div class="pt-mundo-compare-row">
              <div class="pt-mundo-col pt-col">
                <div class="pt-mundo-col-label">🇵🇹 Portugal</div>
                <div class="pt-mundo-col-value">${ptVal}<span class="pt-mundo-col-unit"> ${unitDisp}</span></div>
              </div>
              <div class="pt-mundo-col ref-col">
                <div class="pt-mundo-col-label">🇪🇺 ${cmp.refLabel}</div>
                <div class="pt-mundo-col-value">${refVal}<span class="pt-mundo-col-unit"> ${unitDisp}</span></div>
              </div>
            </div>
            ${deltaHtml}
            ${period ? `<div class="pt-mundo-col-period">Último dado: ${period}</div>` : ''}`;
        } catch(e) {
          if (cardEl) cardEl.innerHTML = `<div class="pt-mundo-card-title">${cmp.label}</div><div class="error-state" style="height:60px">Erro ao carregar</div>`;
        }
      }));
    }

    // ── Track C: Haiku analysis card ─────────────────────────────────
    async function renderHaikuAnalysis(parentEl, kpis) {
      const topKpis = kpis
        .filter(k => k.spark && k.spark.length > 0 && k.value != null)
        .slice(0, 5);

      if (!topKpis.length) return;

      const section = document.createElement('div');
      section.className = 'haiku-analysis-section';
      section.innerHTML = `
        <div class="haiku-card" id="haiku-analysis-card">
          <div class="haiku-card-header">
            <span class="haiku-badge">Análise IA</span>
            <span class="haiku-model-tag">Claude Haiku · Interpretação automática</span>
          </div>
          <div class="haiku-loading" id="haiku-loading">
            <div class="loading-spinner" style="width:14px;height:14px"></div>
            <span>A gerar análise interpretativa…</span>
          </div>
          <div class="haiku-text" id="haiku-text" style="display:none"></div>
        </div>`;
      parentEl.appendChild(section);

      try {
        const seriesPayload = topKpis.map(k => ({
          source: k.source || 'INE',
          indicator: k.id || k.indicator,
          label: k.label,
          unit: k.unit || '',
          data: (k.spark || []).map((v, i) => ({ period: `T-${topKpis[0].spark.length - i}`, value: v })),
        }));

        const resp = await fetch('/api/interpret', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ series: seriesPayload, from: '', to: '' }),
        });
        const result = await resp.json();

        const loadEl = document.getElementById('haiku-loading');
        const textEl = document.getElementById('haiku-text');
        if (loadEl) loadEl.style.display = 'none';
        if (textEl) {
          if (result.text) {
            textEl.textContent = result.text;
            textEl.style.display = 'block';
          } else {
            textEl.textContent = 'Análise não disponível (token Haiku não configurado).';
            textEl.style.display = 'block';
            textEl.style.color = 'var(--c-muted)';
          }
        }
      } catch(e) {
        const loadEl = document.getElementById('haiku-loading');
        const textEl = document.getElementById('haiku-text');
        if (loadEl) loadEl.style.display = 'none';
        if (textEl) {
          textEl.textContent = 'Análise indisponível.';
          textEl.style.display = 'block';
          textEl.style.color = 'var(--c-muted)';
        }
      }
    }

    // ── WP-9: Painel card → Explorador deep-link ────────────────────
    body.addEventListener('click', (e) => {
      const card = e.target.closest('.kpi-card[data-source][data-indicator]');
      if (!card || !card.dataset.source || !card.dataset.indicator) return;
      window.location.hash = `#explorador?s=${encodeURIComponent(card.dataset.source + '/' + card.dataset.indicator)}`;
    });

    // ── Sparklines (all KPIs regardless of render mode) ─────────────
    allKpis.forEach(kpi => {
      if (!kpi.spark || !kpi.spark.length) return;
      const sparkEl = document.getElementById(`spark-${kpi.id}`);
      if (sparkEl) {
        try {
          SWD.createSparkline(sparkEl, kpi.spark,
            kpi.sentiment === 'positive' ? SWD.COLORS.positive :
            kpi.sentiment === 'negative' ? SWD.COLORS.negative : SWD.COLORS.other
          );
        } catch(e) { console.warn('[painel] sparkline error:', kpi.id, e); }
      }
    });

    // ── Render PT vs Mundo + Haiku sections ──────────────────────────
    const pSection = body.querySelector('.painel-sections') || body;
    renderPTvsMundo(pSection);
    renderHaikuAnalysis(pSection, allKpis);

  } catch(e) {
    console.error('[painel] init error:', e);
    body.innerHTML = App.errorHTML(e.message);
  }
});
