/* ═══════════════════════════════════════════════════════════════
   painel.js — KPI cards + sparklines (v7 — Painel V2)
   Uses /api/painel (sections) with fallback to /api/resumo (flat).
   Full redesign: M2 (Criativo)
   ═══════════════════════════════════════════════════════════════ */

App.registerSection('painel', async () => {
  const container = document.getElementById('painel');
  const body = container.querySelector('.section-body');

  try {
    // Skeleton KPI cards durante loading
    const _skeletonCard = `
      <div class="kpi-card kpi-card-skeleton">
        <div class="kpi-card-header">
          <div class="skeleton" style="width:62%;height:11px"></div>
          <div class="skeleton" style="width:30px;height:11px"></div>
        </div>
        <div class="kpi-value-row">
          <div class="skeleton" style="width:45%;height:26px;margin-top:8px"></div>
        </div>
        <div class="kpi-trend-row">
          <div class="skeleton" style="width:55%;height:10px;margin-top:10px"></div>
        </div>
      </div>`;
    body.innerHTML = `<div class="kpi-grid">${Array.from({length: 10}, () => _skeletonCard).join('')}</div>`;

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
        return yoy >= 0 ? i18n.t('painel.phrase.ipi_up', {pct: yoy.toFixed(1)}) : i18n.t('painel.phrase.ipi_down', {pct: Math.abs(yoy).toFixed(1)});
      if (k.id === 'unemployment')
        return i18n.t('painel.phrase.unemployment', {val: val.toFixed(1)});
      if (k.id === 'employment_rate')
        return i18n.t('painel.phrase.employment', {val: val.toFixed(1)});
      if (k.id === 'confidence')
        return yoy >= 0 ? i18n.t('painel.phrase.confidence_up', {pp: yoy.toFixed(1)}) : i18n.t('painel.phrase.confidence_down', {pp: Math.abs(yoy).toFixed(1)});
      if (k.id === 'inflation')
        return i18n.t('painel.phrase.inflation', {val: val.toFixed(1)});
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
      titleMsg = i18n.t('painel.title_fallback');
    }

    const titleEl = container.querySelector('.section-title');
    const subEl = container.querySelector('.section-subtitle');
    // Title and subtitle start empty while AI headline loads.
    // Rule-based fallback only in .catch() or if API returns no headline.

    // Fetch headline from Opus (non-blocking — fallback to rule-based)
    // NOTE: _fetchHeadline is called early (before currentLens is declared),
    // so it must always receive an explicit lens param here.
    function _fetchHeadline(lens) {
      const lensParam = lens || localStorage.getItem('prumo-lens') || 'cae';
      const langParam = getOutputLanguage();
      let headlineUrl = `/api/painel-headline?lens=${encodeURIComponent(lensParam)}&output_language=${encodeURIComponent(langParam)}`;
      if (lensParam === 'custom') {
        const customText = localStorage.getItem('prumo-custom-ideology') || (typeof CUSTOM_LENS_DEFAULT !== 'undefined' ? CUSTOM_LENS_DEFAULT : '');
        if (customText) headlineUrl += `&custom_ideology=${encodeURIComponent(customText)}`;
      }
      API.get(headlineUrl).then(h => {
        if (!h?.headline) {
          // API responded but no headline — apply rule-based fallback
          if (titleEl && !titleEl.textContent) titleEl.textContent = titleMsg;
          if (subEl && !subEl.textContent) subEl.textContent = `${i18n.t('painel.subtitle_updated', {date: updated})} · ${allKpis.length} KPIs · ${i18n.t('painel.subtitle_sources')}`;
          return;
        }
        const lines = h.headline.split('\n').map(l => l.trim()).filter(Boolean);
        if (titleEl && lines[0]) {
          titleEl.classList.add('ia-dissolve-out');
          setTimeout(() => {
            titleEl.textContent = lines[0];
            titleEl.classList.remove('ia-dissolve-out');
            titleEl.classList.add('ia-dissolve-in');
            setTimeout(() => titleEl.classList.remove('ia-dissolve-in'), 400);
          }, 300);
        }
        if (subEl && lines.length > 1) {
          subEl.innerHTML = lines.slice(1).map(l => `<p style="margin:0.3em 0">${l}</p>`).join('')
            + `<p style="margin:0.3em 0;opacity:.6;font-size:.9em">${updated} · ${allKpis.length} KPIs</p>`;
        } else if (subEl && !subEl.innerHTML) {
          subEl.textContent = `${i18n.t('painel.subtitle_updated', {date: updated})} · ${allKpis.length} KPIs · ${i18n.t('painel.subtitle_sources')}`;
        }
      }).catch(() => {
        // Network/API failure — apply rule-based fallback (only if still empty)
        if (titleEl && !titleEl.textContent) titleEl.textContent = titleMsg;
        if (subEl && !subEl.textContent) subEl.textContent = `${i18n.t('painel.subtitle_updated', {date: updated})} · ${allKpis.length} KPIs · ${i18n.t('painel.subtitle_sources')}`;
      });
    }
    _fetchHeadline(localStorage.getItem('prumo-lens') || 'cae');

    // Re-fetch headline when language changes
    window.addEventListener('language-change', () => {
      _fetchHeadline(localStorage.getItem('prumo-lens') || 'cae');
    });

    // Source label map — uses i18n with fallback to code
    function getSourceLabel(code) {
      return i18n.t('sources.' + code) || code;
    }

    // ── Translate context strings for non-PT languages ──────────────
    // The backend generates context strings in Portuguese. This function
    // does pattern-based replacements using i18n keys when lang !== 'pt'.
    function _translateContext(text, kpi) {
      if (!text || i18n.lang() === 'pt') return text;

      // Annual data vintage: "Dados de YYYY (última actualização disponível)"
      const annualMatch = text.match(/^Dados de (\d{4}) \(última actualização disponível\)$/);
      if (annualMatch) return i18n.t('kpi.data_from_year', {year: annualMatch[1]});

      // Industrial production base comparison: "X.X% abaixo/acima do nível base (2021=100)"
      const baseMatch = text.match(/^([\d.]+)% (abaixo|acima) do nível base \(2021=100\)$/);
      if (baseMatch) return baseMatch[1] + '% ' + i18n.t(baseMatch[2] === 'abaixo' ? 'kpi.below_base' : 'kpi.above_base');

      // Saldo/pp change: "+X.X pp face ao ano anterior" or "+X.X pp face ao ano anterior (ainda negativo)"
      const ppMatch = text.match(/^([+-]?[\d.]+) pp face ao ano anterior(\s*\(ainda negativo\))?$/);
      if (ppMatch) {
        let result = ppMatch[1] + ' ' + i18n.t('kpi.pp_vs_prev_year');
        if (ppMatch[2]) result += ' (' + i18n.t('kpi.still_negative') + ')';
        return result;
      }

      // Euribor direction: "descida/subida de X.XX pp desde MONTH YEAR"
      const euriborMatch = text.match(/^(descida|subida) de ([\d.]+) pp desde (.+)$/);
      if (euriborMatch) {
        const dirKey = euriborMatch[1] === 'descida' ? 'kpi.drop_of' : 'kpi.rise_of';
        // Translate month name if present
        const monthsPt = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
        const monthsEn = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        let since = euriborMatch[3];
        for (let mi = 0; mi < 12; mi++) {
          if (since.includes(monthsPt[mi])) { since = since.replace(monthsPt[mi], monthsEn[mi]); break; }
        }
        return i18n.t(dirKey) + ' ' + euriborMatch[2] + ' ' + i18n.t('kpi.pp_since') + ' ' + since;
      }

      // Conflict pattern: "Desceu X.X% face ao ano anterior (tendência recente: subida/descida)"
      const conflictMatch = text.match(/^Desceu ([\d.]+)% face ao ano anterior \(tendência recente: (subida|descida)\)$/);
      if (conflictMatch) {
        const trendKey = conflictMatch[2] === 'subida' ? 'kpi.recent_trend_up' : 'kpi.recent_trend_down';
        return i18n.t('kpi.fell') + ' ' + conflictMatch[1] + '% ' + i18n.t('kpi.vs_prev_year_pct') + ' (' + i18n.t(trendKey) + ')';
      }

      // Consecutive months: "X.º mês consecutivo em subida/queda/estável"
      const consecMatch = text.match(/^(\d+)\.º mês consecutivo em (subida|queda|estável)$/);
      if (consecMatch) {
        const n = consecMatch[1];
        const dirMap = {'subida': 'kpi.consecutive_months_up', 'queda': 'kpi.consecutive_months_down', 'estável': 'kpi.consecutive_months_stable'};
        return n + (n === '1' ? 'st' : n === '2' ? 'nd' : n === '3' ? 'rd' : 'th') + ' ' + i18n.t(dirMap[consecMatch[2]]);
      }

      // Simple YoY: "Subiu/Desceu X.X% face ao ano anterior"
      const yoyMatch = text.match(/^(Subiu|Desceu) ([\d.]+)% face ao ano anterior$/);
      if (yoyMatch) {
        const verb = yoyMatch[1] === 'Subiu' ? i18n.t('kpi.rose') : i18n.t('kpi.fell');
        return verb + ' ' + yoyMatch[2] + '% ' + i18n.t('kpi.vs_prev_year_pct');
      }

      return text;
    }

    // ── Translate annotation strings for non-PT languages ───────────
    // Annotations are value-dependent strings from the backend. We map
    // them to structured i18n keys based on the KPI id and value range.
    function _translateAnnotation(kpi) {
      const ann = kpi.annotation;
      if (!ann || i18n.lang() === 'pt') return ann || '';
      const v = kpi.value;
      const id = kpi.id;
      // Map KPI id + value to annotation sub-key
      const key = _annotationKey(id, v);
      if (key) {
        const translated = i18n.t('kpi_annotations.' + id + '.' + key);
        if (translated !== 'kpi_annotations.' + id + '.' + key) return translated;
      }
      return ann; // fallback to raw backend string
    }

    function _annotationKey(id, v) {
      if (v === null || v === undefined) return null;
      switch(id) {
        case 'inflation': return v < 0 ? 'deflation' : v < 1 ? 'stable' : v < 2 ? 'on_target' : v < 4 ? 'above_target' : 'high';
        case 'diesel': return v < 1.30 ? 'cheap' : v < 1.55 ? 'moderate' : v < 1.80 ? 'expensive' : 'very_expensive';
        case 'gasoline_95': return v < 1.40 ? 'cheap' : v < 1.65 ? 'moderate' : v < 1.90 ? 'expensive' : 'very_expensive';
        case 'euribor_3m': return v < 0 ? 'negative' : v < 1 ? 'low' : v < 2.5 ? 'moderate' : v < 4 ? 'high' : 'very_high';
        case 'unemployment': return v < 5 ? 'full_employment' : v < 7 ? 'low' : v < 10 ? 'moderate' : 'high';
        case 'employment_rate': return v > 78 ? 'high' : v > 73 ? 'reasonable' : v > 68 ? 'below_avg' : 'low';
        case 'cli': return v > 101 ? 'strong_expansion' : v > 100 ? 'expansion' : v > 99 ? 'slowdown' : 'contraction';
        case 'confidence': return v > 5 ? 'high' : v > 0 ? 'positive' : v > -10 ? 'mild_pessimism' : 'deep_pessimism';
        case 'order_books': return v > 0 ? 'above_normal' : v > -15 ? 'slightly_below' : v > -30 ? 'weak' : 'very_weak';
        case 'renewable_share': return v > 70 ? 'excellent' : v > 50 ? 'good' : v > 30 ? 'moderate' : 'low';
        case 'energy_dependence': return v < 60 ? 'low' : v < 75 ? 'moderate' : v < 85 ? 'high' : 'very_high';
        case 'natural_gas': return v < 2 ? 'cheap' : v < 4 ? 'moderate' : v < 7 ? 'expensive' : 'very_expensive';
        case 'spread_pt_de': return v < 0.5 ? 'very_low' : v < 1.0 ? 'contained' : v < 2.0 ? 'moderate' : 'high';
        case 'brent': return v < 50 ? 'cheap' : v < 75 ? 'moderate' : v < 100 ? 'expensive' : 'very_expensive';
        case 'eur_usd': return v > 1.20 ? 'strong_euro' : v > 1.05 ? 'equilibrium' : v > 0.95 ? 'weak_euro' : 'very_weak_euro';
        case 'ipi_total': return v > 105 ? 'expansion' : v > 95 ? 'stable' : v > 85 ? 'moderate_contraction' : 'strong_contraction';
        case 'gdp_per_capita': return v > 30000 ? 'converging' : v > 23000 ? 'below_avg' : 'significant_gap';
        case 'rnd_pct_gdp': return v > 2.5 ? 'strong' : v > 1.5 ? 'moderate' : 'low';
        default: return null;
      }
    }

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

      // i18n: override description from translations if available
      const descKey = 'kpi_descriptions.' + kpi.id;
      const description = (i18n.t(descKey) !== descKey) ? i18n.t(descKey) : (kpi.description || '');

      // i18n: override explain from translations if available
      const explainKey = 'kpi_explains.' + kpi.id;
      const explain = (i18n.t(explainKey) !== explainKey) ? i18n.t(explainKey) : (kpi.explain || '');

      // i18n: translate context string
      const context = _translateContext(kpi.context || '', kpi);

      // i18n: translate annotation string
      const annotation = _translateAnnotation(kpi);

      const label = i18n.t('kpi_labels.' + kpi.id) !== ('kpi_labels.' + kpi.id) ? i18n.t('kpi_labels.' + kpi.id) : (kpi.label || kpi.id);
      const hasSpark = kpi.spark && kpi.spark.length > 0;
      const sourceLabel = kpi.source ? getSourceLabel(kpi.source) : '';

      // Base period clarity: show "Fev 2026 vs Fev 2025" instead of "vs ano anterior"
      const period = kpi.period || '';
      let yoyLabel = i18n.t('painel.yoy_label');
      if (period && period.length >= 7) {
        const months = i18n.months();
        const m = parseInt(period.slice(5, 7), 10);
        const y = parseInt(period.slice(0, 4), 10);
        if (m >= 1 && m <= 12 && y > 2000) {
          yoyLabel = `${months[m-1]} ${y} vs ${months[m-1]} ${y-1}`;
        }
      } else if (period && period.length === 4) {
        yoyLabel = `${period} vs ${parseInt(period, 10) - 1}`;
      }

      const dataAttrs = kpi.source && kpi.indicator
        ? ` data-source="${kpi.source}" data-indicator="${kpi.indicator}" title="${i18n.t('painel.view_in_explorador', {label: label})}"`
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
          <span class="kpi-label" style="font-size:11px;letter-spacing:0.5px;">${yoyLabel}</span>
        </div>
        ${description ? `<div class="kpi-description">${description}</div>` : ''}
        ${context ? `<div class="kpi-context">${context}</div>` : ''}
        ${annotation ? `<div class="kpi-annotation">${annotation}</div>` : ''}
        ${explain ? `<button class="kpi-explain-trigger" aria-label="Explain">?</button><div class="kpi-explain hidden"><strong>${label}</strong> — ${explain}</div>` : ''}
        ${hasSpark ? `<div class="spark-container" id="spark-${kpi.id}"></div>` : ''}
        ${period ? `<div class="kpi-freshness" style="font-size:10px;opacity:.5;margin-top:4px;font-style:italic">${i18n.t('painel.data_prefix')}: ${period}</div>` : ''}
      </div>`;
    }

    // ── Render ───────────────────────────────────────────────────────
    // IA button in section header
    const headerEl = container.querySelector('.section-header');
    if (headerEl && !headerEl.querySelector('#painel-ia-btn')) {
      const iaBtn = document.createElement('button');
      iaBtn.id = 'painel-ia-btn';
      iaBtn.className = 'time-preset-btn painel-ia-toggle';
      iaBtn.title = i18n.t('painel.ia.btn_title');
      iaBtn.textContent = '✦ ' + i18n.t('painel.ia.btn_label');
      iaBtn.classList.add('active');
      headerEl.appendChild(iaBtn);
    }

    // ── Ideology lens state ─────────────────────────────────────────
    let currentLens = localStorage.getItem('prumo-lens') || 'cae';
    let availableLenses = [];

    // Fetch lenses from backend
    try {
      availableLenses = await API.get('/api/lenses');
    } catch(e) { console.warn('[painel] failed to load lenses:', e); }

    function getLensParam() { return currentLens || 'cae'; }
    function getCustomIdeology() {
      if (currentLens !== 'custom') return null;
      // Prefer the live textarea value (may not be saved yet)
      const el = document.getElementById('custom-ideology-text');
      if (el && el.value.trim()) return el.value.trim();
      return localStorage.getItem('prumo-custom-ideology') || null;
    }

    function renderLensPills() {
      // Update header lens label
      const lensNameEl = document.getElementById('painel-ia-lens-name');
      if (lensNameEl) lensNameEl.textContent = currentLensLabel();
      const bar = document.getElementById('lens-selector');
      if (!bar || !availableLenses.length) return;
      bar.innerHTML = availableLenses.map(l => {
        const active = l.id === currentLens ? 'active' : '';
        const style = l.id === currentLens ? `style="border-color:${l.color};color:${l.color}"` : '';
        const icon = _lensIcon(l.icon || l.id);
        const isParty = !!PARTY_LOGOS[l.icon || l.id];
        const label = isParty ? '' : l.short;
        return `<button class="lens-pill ${active} ${isParty ? 'lens-pill-logo' : ''}" data-lens="${l.id}" ${style} title="${l.label}${l.source ? '\n' + i18n.t('painel.ia.lens_source') + ': ' + l.source : ''}">${icon}${label}</button>`;
      }).join('');
      // Show/hide custom ideology textarea
      const existing = document.getElementById('custom-ideology-wrap');
      if (currentLens === 'custom') {
        if (!existing) {
          const wrap = document.createElement('div');
          wrap.id = 'custom-ideology-wrap';
          wrap.className = 'custom-ideology-wrap';
          wrap.innerHTML = `<textarea id="custom-ideology-text" class="custom-ideology-textarea"
            placeholder="${i18n.t('painel.ia.custom_placeholder')}"
            rows="4">${localStorage.getItem('prumo-custom-ideology') || CUSTOM_LENS_DEFAULT}</textarea>
            <div class="custom-ideology-footer">
              <span class="custom-ideology-hint">${i18n.t('painel.ia.custom_hint')}</span>
              <button id="custom-ideology-save" class="lens-pill" style="border-color:#9C27B0;color:#9C27B0;font-size:10px">${i18n.t('painel.ia.custom_save')}</button>
            </div>`;
          bar.parentNode.insertBefore(wrap, bar.nextSibling);
          wrap.querySelector('#custom-ideology-save').addEventListener('click', () => {
            const txt = wrap.querySelector('#custom-ideology-text').value.trim();
            if (txt) {
              localStorage.setItem('prumo-custom-ideology', txt);
              App.showToast(i18n.t('painel.ia.custom_saved'));
            }
          });
          // Auto-save on blur
          wrap.querySelector('#custom-ideology-text').addEventListener('blur', () => {
            const txt = wrap.querySelector('#custom-ideology-text').value.trim();
            if (txt) localStorage.setItem('prumo-custom-ideology', txt);
          });
        }
      } else if (existing) {
        existing.remove();
      }
    }

    // Find label for current lens (full name for header display)
    function currentLensLabel() {
      if (currentLens === 'custom') return i18n.t('painel.ia.lens_custom');
      const l = availableLenses.find(x => x.id === currentLens);
      return l ? l.label : currentLens.toUpperCase();
    }

    // Update disclaimer text based on current lens
    // Portuguese article for each party (gender-correct)
    const _PARTY_ARTICLE = {
      'Partido Comunista Português': 'do',
      'Bloco de Esquerda': 'do',
      'Livre': 'do',
      'Pessoas-Animais-Natureza': 'do',
      'Partido Socialista': 'do',
      'Aliança Democrática (PSD + CDS-PP)': 'da',
      'Iniciativa Liberal': 'da',
      'Chega': 'do',
    };
    function updateDisclaimer() {
      const el = document.getElementById('painel-ia-disclaimer');
      if (!el) return;
      const l = availableLenses.find(x => x.id === currentLens);
      const partyName = l?.party;
      if (partyName) {
        const art = _PARTY_ARTICLE[partyName] || 'do';
        el.textContent = i18n.t('painel.ia.disclaimer_party', {article: art, party: partyName});
      } else if (currentLens === 'cae') {
        el.textContent = i18n.t('painel.ia.disclaimer_cae');
      } else if (currentLens === 'custom') {
        el.textContent = i18n.t('painel.ia.disclaimer_custom');
      } else {
        el.textContent = i18n.t('painel.ia.disclaimer_generic');
      }
    }

    // Persistent IA panel placeholder (injected at top of body)
    const iaPanelHtml = `<div id="painel-ia-panel" class="ia-collapsed">
      <div class="painel-ia-header">
        <span class="painel-ia-label">✦ ${i18n.t('painel.ia.panel_label')} · ${i18n.t('painel.ia.lens_prefix')}: <span id="painel-ia-lens-name">${currentLensLabel()}</span></span>
        <span class="painel-ia-tagline">${i18n.t('painel.ia.tagline')}</span>
        <div class="lens-selector" id="lens-selector"></div>
      </div>
      <div class="painel-ia-actions">
        <span class="painel-ia-meta" id="painel-ia-meta"></span>
        ${window.__IS_ADMIN__ ? `<button class="painel-ia-regen" id="painel-ia-regen" title="${i18n.t('painel.ia.regen_title')}">↺ ${i18n.t('painel.ia.regen')}</button>` : ''}
      </div>
      <div id="painel-ia-text" class="painel-ia-text"></div>
      <div id="painel-ia-links" class="painel-ia-links" style="display:none"></div>
      <div id="painel-ia-disclaimer" class="painel-ia-disclaimer"></div>
    </div>`;

    // ── PT vs Europa placeholder (no topo antes das KPI sections) ────────
    const ptEuropaPlaceholder = '<div class="pt-mundo-top-container" id="pt-mundo-top-container"></div>';

    // ── Theme quick-nav pills ─────────────────────────────────────────
    const themeNavHtml = useSections
      ? `<nav class="painel-theme-nav" id="painel-theme-nav">
          <button class="theme-pill active" data-target="pt-mundo-top-container">${i18n.t('painel.theme.pt_vs_europe')}</button>
          ${data.sections.map(s => { const tl = i18n.t('painel_sections.' + s.id); const lbl = (tl !== 'painel_sections.' + s.id) ? tl : (s.label || s.title || s.id); return `<button class="theme-pill" data-target="section-${s.id}">${lbl}</button>`; }).join('')}
        </nav>`
      : '';

    if (useSections) {
      body.innerHTML = iaPanelHtml + themeNavHtml + ptEuropaPlaceholder + '<div class="painel-sections">' +
        data.sections.map(section => {
          const kpis = section.kpis || [];
          return `
          <div class="painel-section" id="section-${section.id}" data-section-id="${section.id}">
            <div class="section-label" style="cursor:pointer;user-select:none;display:flex;align-items:center;justify-content:space-between">
              <span>${(i18n.t('painel_sections.' + section.id) !== 'painel_sections.' + section.id) ? i18n.t('painel_sections.' + section.id) : section.label}</span>
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
      // ── Theme quick-nav pill click logic ────────────────────────────
      const themeNav = body.querySelector('#painel-theme-nav');
      if (themeNav) {
        themeNav.addEventListener('click', e => {
          const pill = e.target.closest('.theme-pill');
          if (!pill) return;
          themeNav.querySelectorAll('.theme-pill').forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          const target = document.getElementById(pill.dataset.target);
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        });

        // Highlight active pill on scroll (IntersectionObserver)
        const sections = body.querySelectorAll('.painel-section, #pt-mundo-top-container');
        const observer = new IntersectionObserver(entries => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              const id = entry.target.id;
              themeNav.querySelectorAll('.theme-pill').forEach(p => {
                p.classList.toggle('active', p.dataset.target === id);
              });
            }
          }
        }, { rootMargin: '-120px 0px -60% 0px', threshold: 0 });
        sections.forEach(s => observer.observe(s));
      }

    } else {
      const kpis = allKpis;
      body.innerHTML = iaPanelHtml + ptEuropaPlaceholder + '<div class="kpi-grid">' + kpis.map(renderKpiCard).join('') + '</div>';
    }

    // ── Render lens pills + handler ────────────────────────────────
    renderLensPills();
    updateDisclaimer();
    const lensBar = document.getElementById('lens-selector');
    if (lensBar) {
      lensBar.addEventListener('click', e => {
        const pill = e.target.closest('.lens-pill');
        if (!pill) return;
        const newLens = pill.dataset.lens;
        if (newLens === currentLens) return;
        currentLens = newLens;
        localStorage.setItem('prumo-lens', newLens);
        renderLensPills();
        updateDisclaimer();
        // Dispatch global lens change event (syncs other sections)
        window.dispatchEvent(new CustomEvent('lens-change', {detail: {lens: newLens, source: 'painel'}}));
        // Dissolve + re-fetch analysis
        _dissolveFetchAnalysis(newLens);
      });
    }
    // Listen for lens changes from OTHER sections (metodologia, etc)
    window.addEventListener('lens-change', e => {
      if (e.detail.source === 'painel') return; // ignore own events
      const newLens = e.detail.lens;
      if (newLens === currentLens) return;
      currentLens = newLens;
      renderLensPills();
      updateDisclaimer();
      _dissolveFetchAnalysis(newLens);
    });

    // Listen for output language changes — re-fetch analysis
    window.addEventListener('language-change', () => {
      _dissolveFetchAnalysis(currentLens);
    });

    // Dissolve current IA text and re-fetch with new lens
    function _dissolveFetchAnalysis(newLens) {
      // Re-fetch headline with new lens (non-blocking)
      _fetchHeadline(newLens);
      const textEl = document.getElementById('painel-ia-text');
      const panel = document.getElementById('painel-ia-panel');
      // For custom lens without text, show notice
      if (newLens === 'custom' && !localStorage.getItem('prumo-custom-ideology') && !CUSTOM_LENS_DEFAULT) {
        if (textEl) textEl.innerHTML = `<p style="color:var(--c-muted);font-style:italic">${i18n.t('painel.ia.custom_notice')}</p>`;
        return;
      }
      // Dissolve out, then re-fetch
      if (textEl && textEl.innerHTML.trim()) {
        textEl.classList.add('ia-dissolve-out');
        textEl.addEventListener('transitionend', function _dissolveEnd() {
          textEl.removeEventListener('transitionend', _dissolveEnd);
          textEl.classList.remove('ia-dissolve-out');
          textEl.innerHTML = '';
          if (panel && !panel.classList.contains('ia-collapsed')) {
            toggleIAPanel(); // close
            toggleIAPanel(); // reopen → triggers re-fetch
          }
        }, {once: true});
        // Safety timeout in case transitionend doesn't fire
        setTimeout(() => {
          textEl.classList.remove('ia-dissolve-out');
          if (!textEl.innerHTML.trim() || textEl.classList.contains('ia-dissolve-out')) {
            textEl.innerHTML = '';
            if (panel && !panel.classList.contains('ia-collapsed')) {
              toggleIAPanel(); toggleIAPanel();
            }
          }
        }, 500);
      } else {
        if (panel && !panel.classList.contains('ia-collapsed')) {
          toggleIAPanel(); toggleIAPanel();
        }
      }
    }

    // ── Render PT vs Europa no topo (antes das restantes secções) ──────────
    const ptEuropaTop = body.querySelector('#pt-mundo-top-container');
    if (ptEuropaTop) renderPTvsMundo(ptEuropaTop);

    // ── IA button toggle logic ─────────────────────────────────────
    let iaLoading = false;
    function _renderMiniSparkline(container, data, yoy, refData, unit, label) {
    if (!window.echarts || !data?.length) {
      container.style.cssText = 'display:flex;align-items:center;justify-content:center;color:var(--c-muted);font-size:12px';
      container.textContent = i18n.t('painel.no_data');
      return;
    }
    const chart = window.echarts.init(container, null, { renderer: 'svg' });
    const vals  = data.map(d => d.value ?? d.v ?? d);
    const color = yoy >= 0 ? '#2E7D32' : '#C62828';
    // Abbreviate long units for mini chart y-axis label
    const _UNIT_SHORT = {
      'Índice (2021=100)': 'Índ.',
      'EUR/litro': '€/L',
      'milhares': 'mil',
    };
    const unitStr = _UNIT_SHORT[unit] || unit || '';
    const series = [
      { name: 'PT', type: 'line', data: vals, smooth: true,
        lineStyle: { color, width: 2.5 },
        areaStyle: { color: color, opacity: 0.06 },
        symbol: 'none' },
    ];
    if (refData?.length) {
      const refVals = refData.map(d => d.value ?? d.v ?? d);
      series.push({
        name: 'EU', type: 'line', data: refVals, smooth: true,
        lineStyle: { color: '#1565C0', width: 1.5, type: 'dashed' },
        symbol: 'none',
      });
    }
    chart.setOption({
      grid: { top: 8, right: 16, bottom: 40, left: 44, containLabel: true },
      xAxis: { type: 'category', data: data.map(d => d.period || d.p || ''),
               axisLabel: { fontSize: 9, color: '#888',
                 interval: 'auto',
                 formatter: (v, i) => {
                   const n = data.length;
                   const MO = i18n.months();
                   const fmt = (s) => {
                     const parts = s.split('-');
                     if (parts.length >= 2) {
                       const mi = parseInt(parts[1], 10) - 1;
                       return MO[mi] || s.slice(5,7);
                     }
                     return s;
                   };
                   // Always show first + last; show ~3 evenly spaced in between
                   if (i === 0) return v.slice(0, 7);
                   if (i === n - 1) return fmt(v);
                   const step = Math.max(1, Math.round((n - 1) / 4));
                   return i % step === 0 ? fmt(v) : '';
                 }
               },
               axisLine: { lineStyle: { color: '#ddd' } }, axisTick: { show: false } },
      yAxis: { type: 'value', scale: true,
               name: unitStr, nameLocation: 'end',
               nameTextStyle: { fontSize: 9, color: '#999', fontFamily: 'Inter, system-ui, sans-serif' },
               axisLabel: { fontSize: 9, color: '#888',
                 formatter: v => {
                   if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + 'B';
                   if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M';
                   if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'k';
                   return v % 1 === 0 ? v : v.toFixed(1);
                 }
               },
               splitLine: { lineStyle: { color: '#f0f0f0' } } },
      series,
      tooltip: { trigger: 'axis', textStyle: { fontSize: 11 },
        formatter: params => {
          const period = params[0]?.axisValue || '';
          const lines = params.map(p => `${p.marker} ${p.seriesName}: <b>${p.value}</b> ${unitStr}`);
          return `${period}<br>${lines.join('<br>')}`;
        }
      },
      ...(refData?.length ? { legend: { data: ['PT','EU'], top: 0, right: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 9 } } } : {}),
    });
  }

    async function _loadDeferredCardLinks(container, existingLinks) {
    // For each card without links, fetch deferred from /api/painel-card-links
    const cards = container.querySelectorAll('.ai-analysis-card');
    const BASE = window.__BASE_PATH__ || '';
    cards.forEach(async (card) => {
      const titleEl = card.querySelector('.ai-card-title');
      if (!titleEl) return;
      const topic = titleEl.textContent.trim();
      // Already has links from Sonnet?
      if (existingLinks[topic]?.length) return;
      try {
        const body = card.querySelector('.ai-card-body')?.textContent?.slice(0, 200) || '';
        const r = await fetch(`${BASE}/api/painel-card-links?topic=${encodeURIComponent(topic)}&context=${encodeURIComponent(body)}&lens=${encodeURIComponent(currentLens)}`);
        const d = await r.json();
        if (!d.links?.length) return;
        // Add ↗ icon to card header
        if (!card.querySelector('.ai-card-link')) {
          const head = card.querySelector('.ai-card-head');
          if (head) {
            const a = document.createElement('a');
            a.href = d.links[0].url;
            a.target = '_blank';
            a.className = 'ai-card-link';
            a.title = d.links[0].title || i18n.t('painel.ia.read_more');
            a.textContent = '↗';
            head.appendChild(a);
          }
        }
        // Build full "Leituras Relacionadas" section if card doesn't have one
        if (!card.querySelector('.ai-card-links')) {
          const linksDiv = document.createElement('div');
          linksDiv.className = 'ai-card-links';
          linksDiv.innerHTML = `<div class="ai-card-links-label">${i18n.t('painel.ia.related_reading')}</div>` +
            d.links.map((l, li) => {
              const url = typeof l === 'string' ? l : l.url;
              const domain = url.replace(/https?:\/\/(www\.)?/, '').split('/')[0];
              const linkTitleId = `ai-def-lnkt-${topic.replace(/\W/g,'')}-${li}`;
              // Async fetch real title
              fetch(`${BASE}/api/link-title?url=${encodeURIComponent(url)}`)
                .then(r2 => r2.json()).then(dt => {
                  const el = document.getElementById(linkTitleId);
                  if (!el) return;
                  const clean = (dt.title || '')
                    .replace(/\s*[|—\-]\s*(Público|Observador|RTP|DN|SAPO|PCP|Avante|Expresso)[^|—\-]*$/i, '')
                    .trim();
                  if (clean) el.textContent = clean;
                }).catch(() => {});
              return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="ai-card-extlink" title="${url}"><span class="ai-link-source">${domain}</span> ↗ <span id="${linkTitleId}" class="ai-link-title">…</span></a>`;
            }).join('');
          card.appendChild(linksDiv);
        }
      } catch(e) { /* silent */ }
    });
  }

    function _renderAnalysisCards(text, links) {
    // Normalize: convert ### headings to **Title:** format (model sometimes outputs markdown headings)
    const normalized = text.replace(/^#{1,3}\s+(.+)$/gm, (_, title) => `**${title.trim()}:**`);

    // Split by **Title:** pattern into cards
    const parts = normalized.split(/(?=\*\*[^*]+:\*\*)/);
    const cards = parts.map(part => {
      const hm = part.match(/^\*\*([^*]+):\*\*(.+)$/s);
      if (hm) return { title: hm[1].trim(), body: hm[2].trim() };
      const trimmed = part.trim();
      return trimmed ? { title: null, body: trimmed } : null;
    }).filter(Boolean);

    if (!cards.length) return _renderMd(text); // fallback

    // Section link icons
    const ICONS = {
      'Custo de Vida': '🛒', 'Poder de Compra': '💰', 'Energia': '⚡',
      'Emprego': '👷', 'Indústria': '🏭', 'Produção': '🏭',
      'Habitação': '🏠', 'Exportações': '📦', 'Comércio': '📦',
      'Fiscal': '📊', 'Dívida': '📊', 'Convergência': '🇪🇺',
      'Turismo': '✈️', 'Agricultura': '🌾', 'Construção': '🏗️',
    };
    const icon = t => {
      if (!t) return '📌';
      for (const [k, v] of Object.entries(ICONS)) if (t.includes(k)) return v;
      return '📍';
    };

    const cardHtml = cards.map((c, i) => {
      // Fix: links[section] is an array [{url,title},...], pick first URL
      // links entries can be plain URL strings OR {url,title} objects
      const _normLink = l => typeof l === 'string' ? {url: l, title: ''} : l;
      const sectionLinks = (links[c.title] || []).map(_normLink).filter(l => l.url);
      const firstUrl  = sectionLinks[0]?.url || null;
      const lnk = firstUrl ? `<a href="${firstUrl}" target="_blank" rel="noopener noreferrer" class="ai-card-link" title="${i18n.t('painel.ia.read_more')}">↗</a>` : '';
      // Links: show domain initially, lazy-fetch real title
      const allLinkHtml = sectionLinks.length
        ? sectionLinks.map((l, li) => {
            const domain = (l.url.replace(/https?:\/\/(www\.)?/, '').split('/')[0] || l.url);
            const linkId = `ai-lnk-${i}-${li}`;
            const linkTitleId = `ai-lnkt-${i}-${li}`;
            // Kick off async title fetch
            const BASE2 = window.__BASE_PATH__ || '';
            fetch(`${BASE2}/api/link-title?url=${encodeURIComponent(l.url)}`)
              .then(r => r.json()).then(d => {
                const el = document.getElementById(linkTitleId);
                if (!el) return;
                const clean = (d.title || '')
                  .replace(/\s*[|—\-]\s*(Público|Observador|RTP|DN|SAPO|PCP|Avante|Expresso)[^|—\-]*$/i, '')
                  .trim();
                if (clean) el.textContent = clean;
              }).catch(() => {});
            // Format: "source ↗ title-placeholder"
            return `<a id="${linkId}" href="${l.url}" target="_blank" rel="noopener noreferrer" class="ai-card-extlink" title="${l.url}"><span class="ai-link-source">${domain}</span> ↗ <span id="${linkTitleId}" class="ai-link-title">…</span></a>`;
          }).join('')
        : '';

      return `<div class="ai-analysis-card ${i === 0 ? 'active' : ''}" data-section="${c.title || ''}">
        ${c.title ? `<div class="ai-card-head"><span class="ai-card-icon">${icon(c.title)}</span><span class="ai-card-title">${c.title}</span>${lnk}</div>` : ''}
        <div class="ai-card-content">
          <div class="ai-card-body">${_renderMd(c.body || '')}</div>
          <div class="ai-card-chart-col">
            <div class="ai-card-chart-title" id="ai-cct-${i}"></div>
            <div class="ai-card-chart-box" id="ai-card-chart-${i}"></div>
            <div class="ai-card-chart-comment" id="ai-ccm-${i}"></div>
          </div>
        </div>
        ${allLinkHtml ? `<div class="ai-card-links"><div class="ai-card-links-label">${i18n.t('painel.ia.related_reading')}</div>${allLinkHtml}</div>` : ''}
      </div>`;
    }).join('');

    const dots = cards.map((_, i) =>
      `<button class="ai-dot ${i === 0 ? 'active' : ''}" data-idx="${i}"></button>`
    ).join('');

    return `<div class="ai-cards-wrap">
      <div class="ai-cards-track" id="ai-cards-track">${cardHtml}</div>
      <div class="ai-cards-nav">
        <button class="ai-nav-btn" id="ai-prev">‹</button>
        <div class="ai-dots" id="ai-dots">${dots}</div>
        <button class="ai-nav-btn" id="ai-next">›</button>
      </div>
    </div>`;
  }

  function _initAnalysisCardsNav(container, kpiPerCard) {
    const track = container.querySelector('#ai-cards-track');
    const dots  = container.querySelectorAll('.ai-dot');
    const cards = container.querySelectorAll('.ai-analysis-card');
    const prev  = container.querySelector('#ai-prev');
    const next  = container.querySelector('#ai-next');
    if (!track || !cards.length) return;

    // Render chart for each card upfront (they're hidden so no perf issue)
    const EU_SOURCES = new Set(['EUROSTAT','WORLDBANK']);
    const EU_REF_MAP = { 'EUROSTAT': 'EU27_2020', 'WORLDBANK': 'EU' };
    const BASE = window.__BASE_PATH__ || '';

    const renderCard = (i, kpi, refSpark) => {
      const chartEl   = document.getElementById(`ai-card-chart-${i}`);
      const titleEl   = document.getElementById(`ai-cct-${i}`);
      const commentEl = document.getElementById(`ai-ccm-${i}`);
      if (!chartEl || !kpi?.spark?.length) return;

      if (titleEl) {
        const indUrl = `#explorador?s=${encodeURIComponent((kpi.source || '') + '/' + (kpi.id || ''))}`;
        const chartLabel = (i18n.t('kpi_labels.' + kpi.id) !== 'kpi_labels.' + kpi.id) ? i18n.t('kpi_labels.' + kpi.id) : (kpi.label || '');
        titleEl.innerHTML = `<a href="${indUrl}" class="ai-card-chart-title-link" title="${i18n.t('painel.view_in_explorador', {label: chartLabel})}">${chartLabel} ↗</a>`;
      }
      if (commentEl) {
        const period = kpi.spark?.at(-1)?.period || kpi.spark?.at(-1)?.p || '';
        const yoy = kpi.yoy ?? 0;
        const abs = Math.abs(yoy).toFixed(1);
        const val = kpi.value;
        const unit = kpi.unit || '%';
        // Family-focused insight templates by indicator
        const id = kpi.id || '';
        const ind = kpi.indicator || '';
        let msg = '';
        if (ind === 'hicp_yoy' || id === 'inflation') {
          msg = yoy > 0 ? i18n.t('painel.insight.inflation_up', {pct: abs}) : i18n.t('painel.insight.inflation_down', {pct: abs});
        } else if (ind === 'unemp_m' || id === 'unemployment') {
          msg = yoy < 0 ? i18n.t('painel.insight.unemployment_down', {pp: abs}) : i18n.t('painel.insight.unemployment_up', {pp: abs});
        } else if (ind === 'electricity_price_mibel' || id === 'energy_cost') {
          msg = yoy < 0 ? i18n.t('painel.insight.energy_down', {pct: abs}) : i18n.t('painel.insight.energy_up', {pct: abs});
        } else if (/btn|electricity/i.test(ind)) {
          msg = yoy > 0 ? i18n.t('painel.insight.tariff_up', {pct: abs}) : i18n.t('painel.insight.tariff_down', {pct: abs});
        } else if (/euribor/i.test(ind)) {
          msg = yoy > 0 ? i18n.t('painel.insight.euribor_up', {pp: abs}) : i18n.t('painel.insight.euribor_down', {pp: abs});
        } else if (/wage|salar/i.test(ind) || id === 'wages_industry') {
          msg = yoy > 0 ? i18n.t('painel.insight.wages_up', {pct: abs}) : i18n.t('painel.insight.wages_down', {pct: abs});
        } else if (ind === 'rnd_pct_gdp') {
          msg = i18n.t('painel.insight.rnd', {val: val});
        } else {
          // Generic fallback with direction sentiment
          const dir = yoy >= 0 ? i18n.t('painel.insight.rise') : i18n.t('painel.insight.fall');
          msg = `${dir} ${abs}${kpi.yoy_unit || '%'} — ${val} ${unit} ${period}`;
        }
        commentEl.textContent = msg;
      }
      const sparkLabel = (i18n.t('kpi_labels.' + kpi.id) !== 'kpi_labels.' + kpi.id) ? i18n.t('kpi_labels.' + kpi.id) : (kpi.label || '');
      _renderMiniSparkline(chartEl, kpi.spark, kpi.yoy, refSpark || null, kpi.unit || kpi.yoy_unit || '', sparkLabel);
    };

    // First pass: render all cards immediately (no EU ref)
    (kpiPerCard || []).forEach((kpi, i) => renderCard(i, kpi, null));

    // Second pass: async fetch EU ref series for EUROSTAT/WORLDBANK indicators
    (kpiPerCard || []).forEach(async (kpi, i) => {
      if (!kpi?.spark?.length || !EU_SOURCES.has(kpi.source)) return;
      const ref = EU_REF_MAP[kpi.source] || 'EU27_2020';
      try {
        const url = `/api/mundo?indicator=${encodeURIComponent(kpi.indicator)}&source=${kpi.source}&countries=${encodeURIComponent('PT,' + ref)}&since=2015`;
        const data = await API.get(url);
        const refSeries = (data.series || []).find(s => s.country === ref || s.country === 'EU27_2020' || s.country === 'EU');
        if (refSeries?.data?.length) {
          const chartEl = document.getElementById(`ai-card-chart-${i}`);
          if (chartEl) {
            // Destroy & re-render with EU ref
            try { window.echarts.getInstanceByDom(chartEl)?.dispose(); } catch(e) {}
            _renderMiniSparkline(chartEl, kpi.spark, kpi.yoy, refSeries.data, kpi.unit || kpi.yoy_unit || '', sparkLabel);
          }
        }
      } catch(e) { /* silent — EU ref is optional enhancement */ }
    });

    let current = 0;
    const go = (idx) => {
      // Wrap around
      const len = cards.length;
      current = ((idx % len) + len) % len;
      cards.forEach((c, i) => {
        if (i === current) {
          c.classList.add('active');
          c.classList.add('card-entering');
          requestAnimationFrame(() => {
            c.classList.remove('card-entering');
            // Resize all ECharts instances in this card (were hidden at init)
            c.querySelectorAll('[id^="ai-card-chart-"]').forEach(el => {
              try { window.echarts?.getInstanceByDom(el)?.resize(); } catch(e) {}
            });
            // Second resize after DOM settling (SVG renderer needs extra tick)
            setTimeout(() => {
              c.querySelectorAll('[id^="ai-card-chart-"]').forEach(el => {
                try { window.echarts?.getInstanceByDom(el)?.resize(); } catch(e) {}
              });
            }, 50);
          });
        } else {
          c.classList.remove('active');
        }
      });
      dots.forEach((d, i) => d.classList.toggle('active', i === current));
    };
    prev?.addEventListener('click', () => go(current - 1));
    next?.addEventListener('click', () => go(current + 1));
    dots.forEach(d => d.addEventListener('click', () => go(+d.dataset.idx)));
    let sx = 0;
    track.addEventListener('touchstart', e => { sx = e.touches[0].clientX; }, { passive: true });
    track.addEventListener('touchend',   e => {
      const dx = e.changedTouches[0].clientX - sx;
      if (Math.abs(dx) > 40) go(dx < 0 ? current + 1 : current - 1);
    }, { passive: true });
  }

  function _renderMd(text) {
      // Minimal markdown: headings, **bold**, *italic*, paragraphs; strip --- separators
      return text
        .replace(/^---+\s*$/gm, '')          // strip horizontal rules
        .replace(/^#{1,3}\s+(.+)$/gm, '<strong>$1</strong>')  // ### headings → bold
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

      if (!panel.classList.contains('ia-collapsed')) {
        panel.classList.add('ia-collapsed');
        if (btn) btn.classList.remove('active');
        return;
      }
      panel.classList.remove('ia-collapsed');
      if (btn) btn.classList.add('active');

      // If already has content, just show
      if (textEl && textEl.innerHTML.trim() && !textEl.querySelector('.ai-loading') && !panel.classList.contains('ia-collapsed')) return;

      // Load analysis
      if (iaLoading) return;
      iaLoading = true;
      if (textEl) textEl.innerHTML = `<span class="ai-loading">${i18n.t('painel.ia.loading')}</span>`;

      try {
        const BASE = window.__BASE_PATH__ || '';
        const lensParam = getLensParam();
        const customIdeology = getCustomIdeology();
        const langParam = getOutputLanguage();
        console.log('[painel-ia] Fetching analysis, lens:', lensParam, 'lang:', langParam);

        // Helper: fetch analysis (with short timeout for cache hits)
        async function _fetchAnalysis(timeoutMs) {
          const ac = new AbortController();
          const timer = setTimeout(() => ac.abort(), timeoutMs);
          try {
            let r;
            if (lensParam === 'custom' && customIdeology) {
              r = await fetch(`${BASE}/api/painel-analysis?lens=custom&output_language=${encodeURIComponent(langParam)}`, {
                method: 'POST', signal: ac.signal,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({custom_ideology: customIdeology}),
              });
            } else {
              r = await fetch(`${BASE}/api/painel-analysis?lens=${encodeURIComponent(lensParam)}&output_language=${encodeURIComponent(langParam)}`, {signal: ac.signal});
            }
            clearTimeout(timer);
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return await r.json();
          } catch(e) { clearTimeout(timer); throw e; }
        }

        // Helper: fire background generation
        function _fireBg() {
          if (lensParam === 'custom' && customIdeology) {
            fetch(`${BASE}/api/painel-analysis?bg=1&force=1&lens=custom&output_language=${encodeURIComponent(langParam)}`, {
              method: 'POST', headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({custom_ideology: customIdeology}),
            }).catch(() => {});
          } else {
            fetch(`${BASE}/api/painel-analysis?bg=1&force=1&lens=${encodeURIComponent(lensParam)}&output_language=${encodeURIComponent(langParam)}`).catch(() => {});
          }
        }

        // Try quick fetch first (15s — enough for cached results)
        let result;
        try {
          result = await _fetchAnalysis(15000);
        } catch(quickErr) {
          // Cache miss or timeout — fire background generation and poll
          console.log('[painel-ia] Quick fetch failed, starting bg generation:', quickErr.message);
          _fireBg();
          if (textEl) textEl.innerHTML = `<span class="ai-loading">${i18n.t('painel.ia.generating', {time: '~90s'})}</span>`;
          // Poll every 8s for up to 3 minutes
          const maxPolls = 22;
          for (let p = 0; p < maxPolls; p++) {
            await new Promise(r => setTimeout(r, 8000));
            try {
              result = await _fetchAnalysis(10000);
              if (result?.text) break;
            } catch(_) { /* still generating */ }
            if (textEl) {
              const elapsed = (p + 1) * 8;
              textEl.innerHTML = `<span class="ai-loading">${i18n.t('painel.ia.generating', {time: elapsed + 's'})}</span>`;
            }
          }
          if (!result?.text) throw new Error(i18n.t('painel.ia.timeout'));
        }
        console.log('[painel-ia] Data received, chart_pick:', result.chart_pick);
        console.log('[painel-ia] Data received, chart_pick:', result.chart_pick);
        if (result.text) {
          if (textEl) {
            textEl.innerHTML = _renderAnalysisCards(result.text, result.section_links || {});
            textEl.classList.add('ia-dissolve-in');
            setTimeout(() => textEl.classList.remove('ia-dissolve-in'), 500);

            // Use headline from analysis response (same language as analysis)
            if (result.headline) {
              const titleEl = container.querySelector('.section-title');
              const subEl = container.querySelector('.section-subtitle');
              if (titleEl) {
                titleEl.classList.add('ia-dissolve-out');
                setTimeout(() => {
                  titleEl.textContent = result.headline;
                  titleEl.classList.remove('ia-dissolve-out');
                  titleEl.classList.add('ia-dissolve-in');
                  setTimeout(() => titleEl.classList.remove('ia-dissolve-in'), 400);
                }, 200);
              }
              if (subEl && result.subheadline) {
                subEl.innerHTML = `<span>${_renderMd(result.subheadline)}</span>` +
                  ` <span style="opacity:.6;font-size:.9em">· ${updated} · ${allKpis.length} KPIs</span>`;
              }
            }

            // Build kpiPerCard: Sonnet specifies indicator per section via section_charts
            // Fallback: highest abs YoY when no match
            const sectionCharts = result.section_charts || {};
            const cardSections = textEl.querySelectorAll('.ai-analysis-card');
            const kpiPerCard = Array.from(cardSections).map((cardEl, i) => {
              const sectionTitle = cardEl.dataset.section || '';
              // Sonnet may return string or array — always use first
              const raw = sectionCharts[sectionTitle];
              const indicatorId = Array.isArray(raw) ? raw[0] : raw;
              let kpiMatch = null;

              if (indicatorId) {
                kpiMatch = allKpis.find(k => k.id === indicatorId)
                        || allKpis.find(k => k.indicator === indicatorId)
                        || allKpis.find(k => k.id?.includes(indicatorId) || indicatorId.includes(k.id || ''))
                        || allKpis.find(k => k.indicator?.includes(indicatorId) || indicatorId.includes(k.indicator || ''));
              }
              if (!kpiMatch?.spark?.length) {
                // Fallback: rotate through top-YoY KPIs
                const ranked = allKpis
                  .filter(k => k.spark?.length > 3 && k.yoy != null)
                  .sort((a, b) => Math.abs(b.yoy) - Math.abs(a.yoy));
                kpiMatch = ranked[i % Math.max(1, ranked.length)] || null;
              }
              return kpiMatch || null;
            });

            _initAnalysisCardsNav(textEl, kpiPerCard);
            _loadDeferredCardLinks(textEl, result.section_links || {});

            // chart_pick from Sonnet: override comment for the matching card
            if (result.chart_pick?.indicator) {
              const pick = result.chart_pick;
              kpiPerCard.forEach((kpi, i) => {
                if (kpi && (kpi.id === pick.indicator || kpi.indicator === pick.indicator ||
                    kpi.label?.toLowerCase() === (pick.label || '').toLowerCase())) {
                  const commentEl = document.getElementById(`ai-ccm-${i}`);
                  if (commentEl && pick.title) commentEl.textContent = pick.title;
                }
              });
            }
          }
          if (metaEl) {
            const ts = result.generated_at ? new Date(result.generated_at).toLocaleDateString('pt-PT') : '';
            const genTime = result.generation_ms ? ` · ${Math.round(result.generation_ms / 1000)}s` : '';
            const metaInfo = (result.cached ? 'cache' : `${i18n.t('painel.ia.generated_now')}${genTime}`) + (ts ? ` · ${ts}` : '') + ` · ${i18n.t('painel.data_prefix')}: ${result.data_period || ''}`;
            metaEl.innerHTML = `<span class="ia-meta-icon" title="${metaInfo}">ℹ</span>`;
          }
          // Global links list removed — links are shown inline per card
        } else {
          if (textEl) textEl.innerHTML = `<em style="color:var(--c-muted)">${i18n.t('painel.ia.unavailable')}</em>`;
        }
      } catch(e) {
        if (textEl) textEl.innerHTML = `<em style="color:var(--c-muted)">${i18n.t('painel.error_loading')}: ${e.message}</em>`;
      } finally {
        iaLoading = false;
      }
    }

    // Bind button (may have been re-rendered)
    const iaBtnEl = container.querySelector('#painel-ia-btn');
    if (iaBtnEl) iaBtnEl.addEventListener('click', toggleIAPanel);

    // Regenerar button — triggers bg generation + reloads after 75s
    const regenBtn = container.querySelector('#painel-ia-regen');
    if (regenBtn) {
      regenBtn.addEventListener('click', async () => {
        regenBtn.textContent = '↺';
        regenBtn.disabled = true;
        regenBtn.title = i18n.t('painel.ia.regen_generating');
        const metaEl = document.getElementById('painel-ia-meta');
        if (metaEl) metaEl.textContent = i18n.t('painel.ia.regen_generating');
        const BASE = window.__BASE_PATH__ || '';
        const _regenLens = getLensParam();
        const _regenCustom = getCustomIdeology();
        const _regenLang = getOutputLanguage();
        if (_regenLens === 'custom' && _regenCustom) {
          try { await fetch(`${BASE}/api/painel-analysis?bg=1&force=1&lens=custom&output_language=${encodeURIComponent(_regenLang)}`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({custom_ideology: _regenCustom}),
          }); } catch(e) {}
        } else {
          try { await fetch(`${BASE}/api/painel-analysis?bg=1&force=1&lens=${encodeURIComponent(_regenLens)}&output_language=${encodeURIComponent(_regenLang)}`); } catch(e) {}
        }
        // Reload after 75s
        setTimeout(() => {
          regenBtn.disabled = false;
          regenBtn.title = i18n.t('painel.ia.regen_title');
          // Re-trigger analysis panel load
          const textEl = document.getElementById('painel-ia-text');
          if (textEl) textEl.innerHTML = '';
          toggleIAPanel(); toggleIAPanel(); // close & reopen to reload
        }, 75000);
      });
    }
    // Auto-open on first render
    if (!document.getElementById('painel-ia-panel')?.querySelector('.ai-analysis-card')) {
      toggleIAPanel();
    }

    // ── Track B: PT vs Mundo subsection ────────────────────────────
    async function renderPTvsMundo(parentEl) {
      const COMPARISONS = [
        // higherIsBetter: false = PT acima da média é MAU (vermelho)
        //                 true  = PT acima da média é BOM (verde)
        //                 null  = neutro (cinzento)
        { label: i18n.t('painel.pt_vs_europe.inflation'),       indicator: 'hicp',                   source: 'EUROSTAT',  ref: 'EU27', refLabel: i18n.t('painel.pt_vs_europe.eu27_ref'), unit: '%',    decimals: 1, higherIsBetter: false },
        { label: i18n.t('painel.pt_vs_europe.unemployment'),     indicator: 'unemployment',           source: 'EUROSTAT',  ref: 'EU27', refLabel: i18n.t('painel.pt_vs_europe.eu27_ref'), unit: '%',    decimals: 1, higherIsBetter: false },
        { label: i18n.t('painel.pt_vs_europe.gdp_growth'),       indicator: 'gdp_growth',             source: 'WORLDBANK', ref: 'EU',   refLabel: i18n.t('painel.pt_vs_europe.eu_ref'),    unit: '%',    decimals: 2, higherIsBetter: true  },
        { label: i18n.t('painel.pt_vs_europe.gdp_ppp'),          indicator: 'gdp_per_capita_ppp',     source: 'WORLDBANK', ref: 'EU',   refLabel: i18n.t('painel.pt_vs_europe.eu_ref'),    unit: '$',    decimals: 0, higherIsBetter: true  },
        { label: i18n.t('painel.pt_vs_europe.electricity'),      indicator: 'electricity_price_household', source: 'EUROSTAT',  ref: 'EU27', refLabel: i18n.t('painel.pt_vs_europe.eu27_ref'), unit: '€/kWh', decimals: 3, higherIsBetter: false, note: i18n.t('painel.pt_vs_europe.electricity_note') },
        { label: i18n.t('painel.pt_vs_europe.hourly_earnings'),  indicator: 'earn_ses_pub2s',         source: 'EUROSTAT',  ref: 'EU27', refLabel: i18n.t('painel.pt_vs_europe.eu27_ref'), unit: '€/h',  decimals: 2, higherIsBetter: true,  note: i18n.t('painel.pt_vs_europe.hourly_note') },
        { label: i18n.t('painel.pt_vs_europe.monthly_earnings'), indicator: 'earn_ses_pub2s',         source: 'EUROSTAT',  ref: 'EU27', refLabel: i18n.t('painel.pt_vs_europe.eu27_ref'), unit: '€/' + i18n.t('painel.pt_vs_europe.month_unit'),decimals: 0, higherIsBetter: true,  note: i18n.t('painel.pt_vs_europe.monthly_note'), transform: v => v * 176 },
        { label: i18n.t('painel.pt_vs_europe.price_level'),      indicator: 'price_level_index',      source: 'EUROSTAT',  ref: 'EU27', refLabel: i18n.t('painel.pt_vs_europe.eu27_ref'), unit: '',     decimals: 1, higherIsBetter: false, note: 'EU27=100 · 2020' },
        { label: i18n.t('painel.pt_vs_europe.life_expectancy'),  indicator: 'life_expectancy',        source: 'WORLDBANK', ref: 'EU',   refLabel: i18n.t('painel.pt_vs_europe.eu_ref'),    unit: i18n.t('painel.pt_vs_europe.years_unit'), decimals: 1, higherIsBetter: true  },
        { label: i18n.t('painel.pt_vs_europe.employment_rate'),  indicator: 'employment_rate',        source: 'WORLDBANK', ref: 'EU',   refLabel: i18n.t('painel.pt_vs_europe.eu_ref'),    unit: '%',    decimals: 1, higherIsBetter: true  },
        { label: i18n.t('painel.pt_vs_europe.health'),           indicator: 'health_expenditure',     source: 'WORLDBANK', ref: 'EU',   refLabel: i18n.t('painel.pt_vs_europe.eu_ref'),    unit: '%',    decimals: 1, higherIsBetter: null  },
        { label: i18n.t('painel.pt_vs_europe.tertiary'),         indicator: 'tertiary_enrollment',    source: 'WORLDBANK', ref: 'EU',   refLabel: i18n.t('painel.pt_vs_europe.eu_ref'),    unit: '%',    decimals: 1, higherIsBetter: true  },
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
          ${i18n.t('painel.pt_vs_europe.title')}
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
          const url = `/api/mundo?indicator=${encodeURIComponent(cmp.indicator)}&source=${cmp.source}&countries=${encodeURIComponent('PT,' + cmp.ref)}&since=${since}`;
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
            const dir = pctDiff > 0 ? i18n.t('painel.pt_vs_europe.above') : i18n.t('painel.pt_vs_europe.below');
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
            deltaHtml = `<div class="pt-mundo-delta ${cls}">PT ${sign}${pctStr}% ${dir} ${i18n.t('painel.pt_vs_europe.eu_average')}</div>`;
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
            ${period ? `<div class="pt-mundo-col-period">${i18n.t('painel.pt_vs_europe.last_data')}: ${period}</div>` : ''}
            ${cmp.note ? `<div class="pt-mundo-note">${cmp.note}</div>` : ''}`;
        } catch(e) {
          if (cardEl) cardEl.innerHTML = `<div class="pt-mundo-card-title">${cmp.label}</div><div class="error-state" style="height:60px">${i18n.t('painel.error_loading')}</div>`;
        }
      }));
    }

    // ── WP-9: Painel card → Explorador deep-link ────────────────────
    body.addEventListener('click', (e) => {
      if (e.target.closest('.kpi-explain-trigger') || e.target.closest('.kpi-explain')) return;
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


    // ── Re-render on language change ────────────────────────────────
    window.addEventListener('i18n-change', () => {
      // Full page reload is the most reliable way to re-render all sections
      // since section init state is private to App and API data is cached
      window.location.reload();
    });

  } catch(e) {
    console.error('[painel] init error:', e);
    body.innerHTML = App.errorHTML(e.message);
  }
});
