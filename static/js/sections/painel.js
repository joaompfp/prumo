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
    body.innerHTML = `<div class="kpi-grid">${Array.from({length: 10}, () => PrumoLib.skeletonCard).join('')}</div>`;

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
          if (subEl && !subEl.textContent) subEl.textContent = `Dados actualizados: ${updated} · ${allKpis.length} KPIs · Fonte: INE, Eurostat, WorldBank`;
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
          subEl.textContent = `Dados actualizados: ${updated} · ${allKpis.length} KPIs · Fonte: INE, Eurostat, WorldBank`;
        }
      }).catch(() => {
        // Network/API failure — apply rule-based fallback (only if still empty)
        if (titleEl && !titleEl.textContent) titleEl.textContent = titleMsg;
        if (subEl && !subEl.textContent) subEl.textContent = `Dados actualizados: ${updated} · ${allKpis.length} KPIs · Fonte: INE, Eurostat, WorldBank`;
      });
    }
    _fetchHeadline(localStorage.getItem('prumo-lens') || 'cae');

    // Re-fetch headline when language changes
    window.addEventListener('language-change', () => {
      _fetchHeadline(localStorage.getItem('prumo-lens') || 'cae');
    });

    // ── KPI card template (from shared lib) ──────────────────────────
    const renderKpiCard = PrumoLib.renderKpiCard;

    // ── Render ───────────────────────────────────────────────────────
    // IA button in section header
    const headerEl = container.querySelector('.section-header');
    if (headerEl && !headerEl.querySelector('#painel-ia-btn')) {
      const iaBtn = document.createElement('button');
      iaBtn.id = 'painel-ia-btn';
      iaBtn.className = 'time-preset-btn painel-ia-toggle';
      iaBtn.title = 'Análise política interpretativa com IA';
      iaBtn.textContent = '✦ Análise IA';
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
        return `<button class="lens-pill ${active} ${isParty ? 'lens-pill-logo' : ''}" data-lens="${l.id}" ${style} title="${l.label}${l.source ? '\nFonte: '+l.source : ''}">${icon}${label}</button>`;
      }).join('');
      // Show/hide custom ideology textarea
      const existing = document.getElementById('custom-ideology-wrap');
      if (currentLens === 'custom') {
        if (!existing) {
          const wrap = document.createElement('div');
          wrap.id = 'custom-ideology-wrap';
          wrap.className = 'custom-ideology-wrap';
          wrap.innerHTML = `<textarea id="custom-ideology-text" class="custom-ideology-textarea"
            placeholder="Escreve aqui o teu enquadramento ideológico. Ex: 'És um analista que privilegia a sustentabilidade ambiental e a economia circular…'"
            rows="4">${localStorage.getItem('prumo-custom-ideology') || CUSTOM_LENS_DEFAULT}</textarea>
            <div class="custom-ideology-footer">
              <span class="custom-ideology-hint">Este texto é enviado como contexto ao modelo de IA. Guardado localmente no browser.</span>
              <button id="custom-ideology-save" class="lens-pill" style="border-color:#9C27B0;color:#9C27B0;font-size:10px">Guardar</button>
            </div>`;
          bar.parentNode.insertBefore(wrap, bar.nextSibling);
          wrap.querySelector('#custom-ideology-save').addEventListener('click', () => {
            const txt = wrap.querySelector('#custom-ideology-text').value.trim();
            if (txt) {
              localStorage.setItem('prumo-custom-ideology', txt);
              App.showToast('Lente personalizada guardada');
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
      if (currentLens === 'custom') return 'Personalizada';
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
        el.textContent = `Análise simulada — não constitui posição oficial ${art} ${partyName}`;
      } else if (currentLens === 'cae') {
        el.textContent = 'Análise simulada — perspectiva editorial do operador desta instância';
      } else if (currentLens === 'custom') {
        el.textContent = 'Análise simulada — lente personalizada pelo utilizador';
      } else {
        el.textContent = 'Análise gerada por IA — meramente indicativa';
      }
    }

    // Persistent IA panel placeholder (injected at top of body)
    const iaPanelHtml = `<div id="painel-ia-panel" class="ia-collapsed">
      <div class="painel-ia-header">
        <span class="painel-ia-label">✦ Análise Política · Lente: <span id="painel-ia-lens-name">${currentLensLabel()}</span></span>
        <span class="painel-ia-tagline">(quase) instantânea, só juntar electricidade</span>
        <div class="lens-selector" id="lens-selector"></div>
      </div>
      <div class="painel-ia-actions">
        <span class="painel-ia-meta" id="painel-ia-meta"></span>
        ${window.__IS_ADMIN__ ? '<button class="painel-ia-regen" id="painel-ia-regen" title="Forçar nova análise">↺ regenerar</button>' : ''}
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
          <button class="theme-pill active" data-target="pt-mundo-top-container">PT vs Europa</button>
          ${data.sections.map(s => `<button class="theme-pill" data-target="section-${s.id}">${s.label || s.title || s.id}</button>`).join('')}
        </nav>`
      : '';

    if (useSections) {
      body.innerHTML = iaPanelHtml + themeNavHtml + ptEuropaPlaceholder + '<div class="painel-sections">' +
        data.sections.map(section => {
          const kpis = section.kpis || [];
          return `
          <div class="painel-section" id="section-${section.id}" data-section-id="${section.id}">
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
        if (textEl) textEl.innerHTML = '<p style="color:var(--c-muted);font-style:italic">Escreve o teu enquadramento no campo acima e gera a análise.</p>';
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
    // Use shared sparkline renderer from lib
    const _renderMiniSparkline = PrumoLib.renderMiniSparkline;

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
            a.title = d.links[0].title || 'Leia mais';
            a.textContent = '↗';
            head.appendChild(a);
          }
        }
        // Build full "Leituras Relacionadas" section if card doesn't have one
        if (!card.querySelector('.ai-card-links')) {
          const linksDiv = document.createElement('div');
          linksDiv.className = 'ai-card-links';
          linksDiv.innerHTML = `<div class="ai-card-links-label">Leituras relacionadas</div>` +
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
      const lnk = firstUrl ? `<a href="${firstUrl}" target="_blank" rel="noopener noreferrer" class="ai-card-link" title="Leia mais">↗</a>` : '';
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
        ${allLinkHtml ? `<div class="ai-card-links"><div class="ai-card-links-label">Leituras relacionadas</div>${allLinkHtml}</div>` : ''}
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
        titleEl.innerHTML = `<a href="${indUrl}" class="ai-card-chart-title-link" title="Ver no Explorador de Análise">${kpi.label || ''} ↗</a>`;
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
          msg = yoy > 0 ? `Preços ${abs}% acima do ano passado — poder de compra das famílias continua sob pressão` : `Inflação desce ${abs}% — algum alívio no orçamento familiar`;
        } else if (ind === 'unemp_m' || id === 'unemployment') {
          msg = yoy < 0 ? `Desemprego caiu ${abs}pp — mais famílias com rendimento de trabalho` : `Desemprego subiu ${abs}pp — mais famílias em situação vulnerável`;
        } else if (ind === 'electricity_price_mibel' || id === 'energy_cost') {
          msg = yoy < 0 ? `Grossista caiu ${abs}% — mas a factura doméstica ainda não reflecte a queda` : `Electricidade grossista sobe ${abs}% — custo energético das famílias em risco`;
        } else if (/btn|electricity/i.test(ind)) {
          msg = yoy > 0 ? `Tarifa sobe ${abs}% — mais peso na factura das famílias` : `Tarifa desce ${abs}% — algum alívio nas despesas fixas`;
        } else if (/euribor/i.test(ind)) {
          msg = yoy > 0 ? `Euribor sobe ${abs}pp — prestações de crédito habitação sobem` : `Euribor desce ${abs}pp — alívio para famílias com crédito variável`;
        } else if (/wage|salar/i.test(ind) || id === 'wages_industry') {
          msg = yoy > 0 ? `Salários industriais crescem ${abs}% — ganho real de poder de compra` : `Salários industriais caem ${abs}% — famílias operárias sob pressão`;
        } else if (ind === 'rnd_pct_gdp') {
          msg = `I&D em ${val}% do PIB — longe dos 3% da meta europeia; menos inovação = menos empregos qualificados`;
        } else {
          // Generic fallback with direction sentiment
          const dir = yoy >= 0 ? 'Subida' : 'Descida';
          msg = `${dir} de ${abs}${kpi.yoy_unit || '%'} — ${val} ${unit} em ${period}`;
        }
        commentEl.textContent = msg;
      }
      _renderMiniSparkline(chartEl, kpi.spark, kpi.yoy, refSpark || null, kpi.unit || kpi.yoy_unit || '', kpi.label || '');
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
            _renderMiniSparkline(chartEl, kpi.spark, kpi.yoy, refSeries.data, kpi.unit || kpi.yoy_unit || '', kpi.label || '');
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

  // Use shared markdown renderer from lib
  const _renderMd = PrumoLib.renderMd;

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
      if (textEl) textEl.innerHTML = '<span class="ai-loading">A carregar análise IA…</span>';

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
          if (textEl) textEl.innerHTML = '<span class="ai-loading">A gerar análise IA (~90s)…</span>';
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
              textEl.innerHTML = `<span class="ai-loading">A gerar análise IA… ${elapsed}s</span>`;
            }
          }
          if (!result?.text) throw new Error('Timeout — análise não gerada. Tente recarregar.');
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
            const metaInfo = (result.cached ? 'cache' : `gerado agora${genTime}`) + (ts ? ` · ${ts}` : '') + ` · dados: ${result.data_period || ''}`;
            metaEl.innerHTML = `<span class="ia-meta-icon" title="${metaInfo}">ℹ</span>`;
          }
          // Global links list removed — links are shown inline per card
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

    // Regenerar button — triggers bg generation + reloads after 75s
    const regenBtn = container.querySelector('#painel-ia-regen');
    if (regenBtn) {
      regenBtn.addEventListener('click', async () => {
        regenBtn.textContent = '↺';
        regenBtn.disabled = true;
        regenBtn.title = 'A gerar nova análise…';
        const metaEl = document.getElementById('painel-ia-meta');
        if (metaEl) metaEl.textContent = 'A gerar nova análise (~60s)…';
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
          regenBtn.title = 'Forçar nova análise';
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
