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
    if (subEl) subEl.textContent = `Dados actualizados: ${updated} · ${allKpis.length} KPIs · Fonte: INE, Eurostat, WorldBank`;

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
    // IA button in section header
    const headerEl = container.querySelector('.section-header');
    if (headerEl && !headerEl.querySelector('#painel-ia-btn')) {
      const iaBtn = document.createElement('button');
      iaBtn.id = 'painel-ia-btn';
      iaBtn.className = 'time-preset-btn painel-ia-toggle';
      iaBtn.title = 'Análise interpretativa com Claude Sonnet';
      iaBtn.textContent = '✦ Análise IA';
      headerEl.appendChild(iaBtn);
    }

    // Persistent IA panel placeholder (injected at top of body)
    const iaPanelHtml = `<div id="painel-ia-panel" style="display:none">
      <div class="painel-ia-header">
        <span class="painel-ia-label">✦ Análise CAE — Claude Sonnet</span>
        <span class="painel-ia-meta" id="painel-ia-meta"></span>
      </div>
      <div id="painel-ia-text" class="painel-ia-text"></div>
      <div id="painel-ia-links" class="painel-ia-links" style="display:none"></div>
    </div>`;

    // ── PT vs Europa placeholder (no topo antes das KPI sections) ────────
    const ptEuropaPlaceholder = '<div class="pt-mundo-top-container" id="pt-mundo-top-container"></div>';

    if (useSections) {
      body.innerHTML = iaPanelHtml + ptEuropaPlaceholder + '<div class="painel-sections">' +
        data.sections.map(section => {
          const kpis = section.kpis || [];
          return `
          <div class="painel-section" data-section-id="${section.id}">
            <div class="section-label" style="cursor:pointer;user-select:none;display:flex;align-items:center;justify-content:space-between">
              <span>${section.label}</span>
              <span class="section-collapse-arrow" style="font-size:16px;line-height:1;transition:transform .2s">&#9660;</span>
            </div>
            <div class="kpi-grid">
              ${kpis.map(renderKpiCard).join('')}
            </div>
          </div>`;
        }).join('') +
        '</div>';

      // ── Collapsible sections (Feature 1) ─────────────────────────────
      body.querySelectorAll('.painel-section').forEach(sec => {
        const sectionId = sec.dataset.sectionId;
        const label = sec.querySelector('.section-label');
        const grid  = sec.querySelector('.kpi-grid');
        const arrow = sec.querySelector('.section-collapse-arrow');
        if (!label || !grid || !arrow) return;

        const storageKey = `painel-collapsed-${sectionId}`;
        // Restore persisted state
        if (sessionStorage.getItem(storageKey) === '1') {
          grid.style.display = 'none';
          arrow.style.transform = 'rotate(-90deg)';
        }

        label.addEventListener('click', () => {
          const isCollapsed = grid.style.display === 'none';
          grid.style.display = isCollapsed ? '' : 'none';
          arrow.style.transform = isCollapsed ? '' : 'rotate(-90deg)';
          sessionStorage.setItem(storageKey, isCollapsed ? '0' : '1');
        });
      });
    } else {
      const kpis = allKpis;
      body.innerHTML = iaPanelHtml + ptEuropaPlaceholder + '<div class="kpi-grid">' + kpis.map(renderKpiCard).join('') + '</div>';
    }

    // ── Render PT vs Europa no topo (antes das restantes secções) ──────────
    const ptEuropaTop = body.querySelector('#pt-mundo-top-container');
    if (ptEuropaTop) renderPTvsMundo(ptEuropaTop);

    // ── IA button toggle logic ─────────────────────────────────────
    let iaLoading = false;
    function _renderMd(text) {
      // Minimal markdown: **bold**, *italic*, paragraphs; strip --- separators
      return text
        .replace(/^---+\s*$/gm, '')          // strip horizontal rules
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/gs, m => `<ul>${m}</ul>`)
        .split(/\n\n+/)
        .map(p => p.trim())
        .filter(Boolean)
        .map(p => p.startsWith('<ul>') ? p : `<p>${p.replace(/\n/g, ' ')}</p>`)
        .join('');
    }

    async function toggleIAPanel() {
      const panel   = document.getElementById('painel-ia-panel');
      const btn     = document.getElementById('painel-ia-btn');
      const textEl  = document.getElementById('painel-ia-text');
      const metaEl  = document.getElementById('painel-ia-meta');
      const linksEl = document.getElementById('painel-ia-links');
      if (!panel) return;

      if (panel.style.display !== 'none') {
        panel.style.display = 'none';
        if (btn) btn.classList.remove('active');
        return;
      }

      // Show panel
      panel.style.display = '';
      if (btn) btn.classList.add('active');

      // If already has content, just show
      if (textEl && textEl.innerHTML.trim() && !textEl.querySelector('.ai-loading')) return;

      // Load analysis
      if (iaLoading) return;
      iaLoading = true;
      if (textEl) textEl.innerHTML = '<span class="ai-loading">A gerar análise com Claude Sonnet…</span>';

      try {
        const BASE = window.__BASE_PATH__ || '';
        const resp = await fetch(`${BASE}/api/painel-analysis`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const result = await resp.json();
        if (result.text) {
          if (textEl) textEl.innerHTML = _renderMd(result.text);
          if (metaEl) {
            const ts = result.generated_at ? new Date(result.generated_at).toLocaleDateString('pt-PT') : '';
            const genTime = result.generation_ms ? ` · ${Math.round(result.generation_ms / 1000)}s` : '';
            metaEl.textContent = (result.cached ? 'cache' : `gerado agora${genTime}`) + (ts ? ` · ${ts}` : '') + ` · dados: ${result.data_period || ''}`;
          }
          // Render per-section links
          const sectionLinks = result.section_links || {};
          const linkEntries = Object.entries(sectionLinks).filter(([, links]) => links && links.length);
          if (linksEl && linkEntries.length) {
            linksEl.innerHTML = '<span class="ai-links-label">🔗 Leitura relacionada por secção:</span>' +
              linkEntries.map(([section, links]) =>
                `<div class="painel-ia-links-section"><strong>${section}</strong>` +
                links.map(l => `<a href="${l.url}" target="_blank" rel="noopener noreferrer">${l.title || l.url}</a>`).join('') +
                '</div>'
              ).join('');
            linksEl.style.display = '';
          } else if (linksEl) {
            linksEl.style.display = 'none';
          }
        } else {
          if (textEl) textEl.innerHTML = '<em style="color:var(--c-muted)">Análise indisponível — token Sonnet não configurado.</em>';
        }
      } catch(e) {
        if (textEl) textEl.innerHTML = `<em style="color:var(--c-muted)">Erro: ${e.message}</em>`;
      } finally {
        iaLoading = false;
      }
    }

    // Bind button (may have been re-rendered)
    const iaBtnEl = container.querySelector('#painel-ia-btn');
    if (iaBtnEl) iaBtnEl.addEventListener('click', toggleIAPanel);

    // ── Track B: PT vs Mundo subsection ────────────────────────────
    async function renderPTvsMundo(parentEl) {
      const COMPARISONS = [
        // higherIsBetter: false = PT acima da média é MAU (vermelho)
        //                 true  = PT acima da média é BOM (verde)
        //                 null  = neutro (cinzento)
        { label: 'Inflação (HICP)',        indicator: 'hicp',                   source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27', unit: '%',    decimals: 1, higherIsBetter: false },
        { label: 'Desemprego',             indicator: 'unemployment',           source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27', unit: '%',    decimals: 1, higherIsBetter: false },
        { label: 'Crescimento PIB',        indicator: 'gdp_growth',             source: 'WORLDBANK', ref: 'EU',   refLabel: 'UE',    unit: '%',    decimals: 2, higherIsBetter: true  },
        { label: 'PIB per Capita PPP',     indicator: 'gdp_per_capita_ppp',     source: 'WORLDBANK', ref: 'EU',   refLabel: 'UE',    unit: '$',    decimals: 0, higherIsBetter: true  },
        { label: 'Electricidade (Dom.)',   indicator: 'electricity_price_household', source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27', unit: '€/kWh', decimals: 3, higherIsBetter: false, note: 'Fonte: Eurostat nrg_pc_204 · Semestral' },
        { label: 'Rendimento Hora Med.',   indicator: 'earn_ses_pub2s',         source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27', unit: '€/h',  decimals: 2, higherIsBetter: true,  note: 'Fonte: Eurostat SES · Dados de 4 em 4 anos' },
        { label: 'Rendimento Mensal Est.', indicator: 'earn_ses_pub2s',         source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27', unit: '€/mês',decimals: 0, higherIsBetter: true,  note: 'Estimado: €/h × 176h (22dias×8h)', transform: v => v * 176 },
        { label: 'Nível de Preços (PLI)',  indicator: 'price_level_index',      source: 'EUROSTAT',  ref: 'EU27', refLabel: 'UE-27', unit: '',     decimals: 1, higherIsBetter: false, note: 'EU27=100 · 2020' },
        { label: 'Esperança de Vida',      indicator: 'life_expectancy',        source: 'WORLDBANK', ref: 'EU',   refLabel: 'UE',    unit: 'anos', decimals: 1, higherIsBetter: true  },
        { label: 'Taxa de Emprego',        indicator: 'employment_rate',        source: 'WORLDBANK', ref: 'EU',   refLabel: 'UE',    unit: '%',    decimals: 1, higherIsBetter: true  },
        { label: 'Saúde (% PIB)',          indicator: 'health_expenditure',     source: 'WORLDBANK', ref: 'EU',   refLabel: 'UE',    unit: '%',    decimals: 1, higherIsBetter: null  },
        { label: 'Ensino Superior',        indicator: 'tertiary_enrollment',    source: 'WORLDBANK', ref: 'EU',   refLabel: 'UE',    unit: '%',    decimals: 1, higherIsBetter: true  },
      ];

      // ── Mapping to COMPARATIVOS_CATALOG ids (Feature 2) ─────────────
      const CATALOG_MAP = {
        'EUROSTAT/hicp':               'eu_hicp',
        'EUROSTAT/unemployment':       'cmp_unemployment',
        'WORLDBANK/gdp_growth':        'wb_gdp_growth',
        'WORLDBANK/gdp_per_capita_ppp':'wb_gdp_per_capita_ppp',
        'WORLDBANK/life_expectancy':   'wb_life_expectancy',
        'WORLDBANK/employment_rate':   'cmp_employment_rate',
        'WORLDBANK/health_expenditure':'wb_health_exp',
        'WORLDBANK/tertiary_enrollment':'wb_tertiary',
      };

      const section = document.createElement('div');
      section.className = 'pt-mundo-section';
      section.innerHTML = `
        <div class="section-label pt-mundo-toggle" id="pt-mundo-label" style="cursor:pointer;user-select:none">
          Portugal vs Europa · Comparação de Referência
          <span class="pt-mundo-chevron" id="pt-mundo-chevron" style="float:right;transition:transform .2s;font-size:16px;line-height:1">&#9660;</span>
        </div>
        <div class="pt-mundo-grid" id="pt-mundo-grid">
          ${COMPARISONS.map((cmp, i) => {
            const catalogId = CATALOG_MAP[`${cmp.source}/${cmp.indicator}`];
            const dataAttrs = catalogId
              ? ` data-catalog-id="${catalogId}" style="cursor:pointer"`
              : '';
            return `<div class="pt-mundo-card"${dataAttrs} id="pt-mundo-card-${i}">
              <div class="loading-state" style="height:80px"><div class="loading-spinner"></div></div>
            </div>`;
          }).join('')}
        </div>`;
      parentEl.appendChild(section);
      // Collapsible toggle
      const toggleLabel = section.querySelector('#pt-mundo-label');
      const grid = section.querySelector('#pt-mundo-grid');
      const chevron = section.querySelector('#pt-mundo-chevron');
      let collapsed = false;
      toggleLabel.addEventListener('click', () => {
        collapsed = !collapsed;
        grid.style.display = collapsed ? 'none' : '';
        chevron.style.transform = collapsed ? 'rotate(-90deg)' : '';
      });

      // ── Deep link to Comparativos (Feature 2) ────────────────────────
      section.addEventListener('click', e => {
        const card = e.target.closest('.pt-mundo-card[data-catalog-id]');
        if (!card) return;
        const catalogId = card.dataset.catalogId;
        window.location.hash = `#comparativos?ind=${encodeURIComponent(catalogId)}&countries=PT,ES,EU27_2020`;
      });

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
          const tf = cmp.transform || (v => v);
          const ptRaw  = ptLast?.value  != null ? tf(Number(ptLast.value))  : null;
          const refRaw = refLast?.value != null ? tf(Number(refLast.value)) : null;
          const ptVal  = ptRaw  != null ? (dec === 0 ? Math.round(ptRaw).toLocaleString('pt-PT')  : ptRaw.toFixed(dec))  : 'n/d';
          const refVal = refRaw != null ? (dec === 0 ? Math.round(refRaw).toLocaleString('pt-PT') : refRaw.toFixed(dec)) : 'n/d';
          const period = (ptLast?.period || '').replace(/-00$/, '');

          let deltaHtml = '';
          if (ptRaw != null && refRaw != null && refRaw !== 0) {
            const pctDiff = ((ptRaw - refRaw) / Math.abs(refRaw)) * 100;
            const sign = pctDiff > 0 ? '+' : '';
            const pctStr = Math.abs(pctDiff) < 1 ? pctDiff.toFixed(1) : Math.round(pctDiff).toString();
            const dir = pctDiff > 0 ? 'acima' : 'abaixo';
            // Sentimento depende de higherIsBetter:
            //   null  → neutro (cinzento, sem conotação)
            //   true  → PT acima=verde, abaixo=vermelho
            //   false → PT acima=vermelho, abaixo=verde
            let cls = '';
            if (cmp.higherIsBetter === null || cmp.higherIsBetter === undefined) {
              cls = '';  // neutro
            } else if (cmp.higherIsBetter) {
              cls = pctDiff > 0 ? 'positive' : (pctDiff < 0 ? 'negative' : '');
            } else {
              cls = pctDiff > 0 ? 'negative' : (pctDiff < 0 ? 'positive' : '');
            }
            deltaHtml = `<div class="pt-mundo-delta ${cls}">PT ${sign}${pctStr}% ${dir} da média europeia</div>`;
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
            ${period ? `<div class="pt-mundo-col-period">Último dado: ${period}</div>` : ''}
            ${cmp.note ? `<div class="pt-mundo-note">${cmp.note}</div>` : ''}`;
        } catch(e) {
          if (cardEl) cardEl.innerHTML = `<div class="pt-mundo-card-title">${cmp.label}</div><div class="error-state" style="height:60px">Erro ao carregar</div>`;
        }
      }));
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


  } catch(e) {
    console.error('[painel] init error:', e);
    body.innerHTML = App.errorHTML(e.message);
  }
});
