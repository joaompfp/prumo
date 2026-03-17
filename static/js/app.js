/* ═══════════════════════════════════════════════════════════════
   app.js — Hash Router + Lazy Section Init
   CAE Dashboard V7
   ═══════════════════════════════════════════════════════════════ */

// ── Theme toggle — dark/light mode ──────────────────────────────────
(function() {
  const THEME_KEY = 'prumo-theme';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.querySelector('.theme-icon').textContent = theme === 'dark' ? '☀️' : '🌙';
    // Re-render ECharts with updated theme colors
    try {
      const isDark = theme === 'dark';
      const textColor  = isDark ? '#e8e8f0' : '#1A1A1A';
      const subColor   = isDark ? '#a0a0b8' : '#666666';
      const tooltipBg  = isDark ? '#1e1e2a' : '#FFFFFF';
      const tooltipBdr = isDark ? '#2a2a3a' : '#EBEBEB';
      const splitLine  = isDark ? '#252535' : '#F5F5F5';
      const chartList  = window.__prumoCharts || (window.SWD && SWD._getCharts ? SWD._getCharts() : []);
      chartList.forEach(function(chart) {
        if (chart && !chart.isDisposed()) {
          chart.setOption({
            backgroundColor: 'transparent',
            textStyle:  { color: textColor },
            tooltip:    { backgroundColor: tooltipBg, borderColor: tooltipBdr, textStyle: { color: textColor } },
            xAxis:      [{ axisLabel: { color: subColor } }],
            yAxis:      [{ axisLabel: { color: subColor }, splitLine: { lineStyle: { color: splitLine } } }],
          }, { notMerge: false });
        }
      });
    } catch(e) {}
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    const preferred = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    applyTheme(saved || preferred);
  }

  document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', function() {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        localStorage.setItem(THEME_KEY, next);
      });
    }
  });
})();

// ── Lens logos — all lenses use image files ──────────────────────────
// Pills use <img> tags pointing to /static/images/parties/<id>_48.png
const PARTY_LOGOS = {
  cae: 'cae_48.png', pcp: 'pcp_48.png', ps: 'ps_48.png', ad: 'ad_48.png', il: 'il_48.png',
  be: 'be_48.png', chega: 'chega_48.png', livre: 'livre_48.png', pan: 'pan_48.png',
  neutro: 'neutro_48.png', custom: 'custom_48.png',
};
const PARTY_ICONS = {};
const CUSTOM_LENS_DEFAULT = window.__CUSTOM_LENS_DEFAULT__ || '';
const OUTPUT_LANGUAGES = window.__OUTPUT_LANGUAGES__ || { pt: 'português europeu' };
const DEFAULT_OUTPUT_LANGUAGE = window.__DEFAULT_OUTPUT_LANGUAGE__ || 'pt';

// ── Global output language state ─────────────────────────────────────
function getOutputLanguage() {
  return localStorage.getItem('prumo-output-language') || DEFAULT_OUTPUT_LANGUAGE;
}
// Flag images via flagcdn.com — key is lang code from site.json, value is ISO 3166-1 alpha-2
const LANG_ISO = { pt: 'pt', cv: 'cv', en: 'gb', es: 'es', fr: 'fr', de: 'de', it: 'it' };
function _flagImg(langKey, w = 20) {
  const iso = LANG_ISO[langKey] || langKey;
  return `<img src="https://flagcdn.com/w40/${iso}.png" width="${w}" height="${Math.round(w*0.7)}" alt="${iso.toUpperCase()}" style="border-radius:1px;vertical-align:middle;display:block">`;
}
const LANG_LABELS = { pt: 'PT', cv: 'CV', en: 'EN', es: 'ES', fr: 'FR', de: 'DE', it: 'IT' };
const LANG_NAMES = { pt: 'Português', cv: 'Kriolu', en: 'English', es: 'Español', fr: 'Français', de: 'Deutsch', it: 'Italiano' };

// ── UI Messages (localized for each language) ──────────────────────────────
const UI_MESSAGES = {
  pt: {
    lens_saved: 'Lente personalizada guardada',
    choose_language: 'Escolhe o teu idioma de saída',
    copy_copied: 'Copiado para a área de transferência',
  },
  cv: {
    lens_saved: 'Lenti personalizada guardadu',
    choose_language: 'Eskoji ku idioma di saída',
    copy_copied: 'Kopiadu pa klipi',
  },
  fr: {
    lens_saved: 'Lens personnalisé enregistré',
    choose_language: 'Choisissez votre langue de sortie',
    copy_copied: 'Copié dans le presse-papiers',
  },
  es: {
    lens_saved: 'Lente personalizada guardado',
    choose_language: 'Elige tu idioma de salida',
    copy_copied: 'Copiado al portapapeles',
  },
  en: {
    lens_saved: 'Custom lens saved',
    choose_language: 'Choose your output language',
    copy_copied: 'Copied to clipboard',
  },
};

function _getMessage(key) {
  const lang = getOutputLanguage();
  return (UI_MESSAGES[lang] && UI_MESSAGES[lang][key]) || (UI_MESSAGES.pt && UI_MESSAGES.pt[key]) || key;
}

function _lensIcon(lensId) {
  const BASE = window.__BASE_PATH__ || '';
  if (PARTY_LOGOS[lensId]) return `<img class="lens-logo" src="${BASE}/static/images/parties/${PARTY_LOGOS[lensId]}" alt="${lensId}">`;
  if (PARTY_ICONS[lensId]) return `<span class="lens-icon">${PARTY_ICONS[lensId]}</span>`;
  return '';
}

// ── Global lens change event bus ────────────────────────────────────
// Dispatch: window.dispatchEvent(new CustomEvent('lens-change', {detail: {lens, source}}))
// Listen:   window.addEventListener('lens-change', e => { ... })

// ── Global lens hint bar — shows active ideology below nav ─────────
const _PARTY_ARTICLE = {
  'Partido Comunista Português': 'do', 'Bloco de Esquerda': 'do',
  'Livre': 'do', 'Pessoas-Animais-Natureza': 'do', 'Partido Socialista': 'do',
  'Aliança Democrática (PSD + CDS-PP)': 'da', 'Iniciativa Liberal': 'da', 'Chega': 'do',
};
function _updateLensHintBar(lenses) {
  const bar = document.getElementById('lens-hint-bar');
  if (!bar) return;
  const lensId = localStorage.getItem('prumo-lens') || 'cae';
  const lens = (lenses || []).find(l => l.id === lensId);
  const icon = _lensIcon(lens?.icon || lensId);
  let disclaimer;
  const party = lens?.party;
  if (party) {
    const art = _PARTY_ARTICLE[party] || 'do';
    disclaimer = typeof i18n !== 'undefined' ? i18n.t('lens.disclaimer_party', { article: art, party: party }) : `Análise simulada — não constitui posição oficial ${art} ${party}`;
  } else if (lensId === 'cae') {
    disclaimer = typeof i18n !== 'undefined' ? i18n.t('lens.disclaimer_cae') : 'Análise simulada — perspectiva editorial do operador desta instância';
  } else if (lensId === 'custom') {
    disclaimer = typeof i18n !== 'undefined' ? i18n.t('lens.disclaimer_custom') : 'Análise simulada — lente personalizada pelo utilizador';
  } else {
    disclaimer = typeof i18n !== 'undefined' ? i18n.t('lens.disclaimer_default') : 'Análise gerada por IA — meramente indicativa';
  }
  // Preserve the dropdown if it's currently inside the bar (avoid destroying it on re-render)
  const dropdown = document.getElementById('lens-dropdown');
  const dropdownInBar = dropdown && dropdown.parentNode === bar;
  if (dropdownInBar) bar.removeChild(dropdown);

  bar.innerHTML = `<span class="lens-hint-prefix">${typeof i18n !== 'undefined' ? i18n.t('lens.label') : 'Lente'}:</span><span class="lens-hint-icon">${icon}</span><span class="lens-hint-label">${lens?.short || lensId}</span><span class="lens-hint-sep">·</span><span class="lens-hint-disclaimer">${disclaimer}</span>`;

  // Re-attach dropdown if it was here before
  if (dropdownInBar && dropdown) {
    bar.appendChild(dropdown);
  }

  // Make the hint bar clickable → open a lens dropdown anchored to the hint bar
  bar.style.cursor = 'pointer';
  bar.onclick = (e) => {
    e.stopPropagation();
    const dd = document.getElementById('lens-dropdown');
    if (!dd) return;
    // Move dropdown into hint bar so it opens near the click
    if (dd.parentNode !== bar) {
      bar.style.position = 'relative';
      bar.appendChild(dd);
      dd.style.bottom = 'auto';
      dd.style.top = '100%';
      dd.style.right = 'auto';
      dd.style.left = '50%';
      dd.style.transform = 'translateX(-50%)';
      dd.style.marginBottom = '0';
      dd.style.marginTop = '2px';
    }
    dd.classList.toggle('hidden');
  };
}
// Update on lens change
window.addEventListener('lens-change', () => _updateLensHintBar(window.__prumoLenses || []));

const App = (() => {
  const SECTIONS = ['painel', 'comparativos', 'explorador', 'metodologia', 'ajuda'];
  const _initialized = {};
  const _loaders = {};

  // Legacy hash redirects — old V5/V6/V7 section names
  const REDIRECTS = {
    'resumo':        'painel',
    'industria':     'explorador',
    'energia':       'explorador',
    'emprego':       'explorador',
    'macro':         'explorador',
    'analise':       'explorador',
    'fosso':         'painel',
    'produtividade': 'painel',
    'europa':        'comparativos',
    'mundo':         'comparativos',
    'ficha':         'metodologia',
    'manifesto':     'metodologia',
  };

  function registerSection(id, initFn) {
    _loaders[id] = initFn;
  }

  function currentSection() {
    const raw = window.location.hash.replace('#', '').split('?')[0] || 'painel';
    // Handle legacy redirects
    if (REDIRECTS[raw]) return REDIRECTS[raw];
    return SECTIONS.includes(raw) ? raw : 'painel';
  }

  async function navigate(sectionId) {
    // Resolve redirects
    if (REDIRECTS[sectionId]) sectionId = REDIRECTS[sectionId];
    if (!SECTIONS.includes(sectionId)) sectionId = 'painel';

    // Hide all sections
    SECTIONS.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });

    // Activate nav tab
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.section === sectionId);
    });

    // Show section
    const section = document.getElementById(sectionId);
    if (section) section.classList.add('active');

    // Lazy init — also re-init if navigating with query params (deep link)
    const incomingHash = window.location.hash;
    const hasIncomingParams = incomingHash.startsWith('#' + sectionId + '?');
    if (hasIncomingParams) _initialized[sectionId] = false;
    if (!_initialized[sectionId] && _loaders[sectionId]) {
      _initialized[sectionId] = true;
      try {
        await _loaders[sectionId]();
      } catch(e) {
        console.error(`[app] Erro ao inicializar #${sectionId}:`, e);
      }
    }

    // Resize all charts in section (fix ECharts zero-width bug)
    setTimeout(() => SWD.resizeAll(), 50);

    // Update URL — preserve query params when navigating TO this section
    const currentHash = window.location.hash;
    const currentBase = currentHash.split('?')[0].replace('#', '');
    const hasQueryForThisSection = currentHash.startsWith('#' + sectionId + '?');
    if (currentBase !== sectionId && !hasQueryForThisSection) {
      history.replaceState(null, '', '#' + sectionId);
    }
  }

  function init() {
    // Tab clicks
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        navigate(tab.dataset.section);
      });
    });

    // Hash change (back/forward)
    window.addEventListener('hashchange', () => {
      navigate(currentSection());
    });

    // Navigate to initial section
    navigate(currentSection());
  }

  function errorHTML(msg) {
    return `<div class="error-state" style="flex-direction:column;gap:12px;height:auto;padding:40px 20px">
      <span style="font-size:28px">⚠️</span>
      <p style="margin:0;font-size:14px;font-weight:600;color:#333">Não foi possível carregar os dados</p>
      <p style="margin:0;font-size:12px;color:#888">${msg}</p>
      <button onclick="location.reload()" style="margin-top:4px;padding:8px 20px;background:#CC0000;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-family:inherit">
        Tentar novamente
      </button>
    </div>`;
  }

  function showToast(msg, duration = 2500) {
    let toast = document.getElementById('app-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'app-toast';
      toast.className = 'toast-notification';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('show'), duration);
  }

  return { init, registerSection, navigate, errorHTML, showToast };
})();

window.App = App;

document.addEventListener('DOMContentLoaded', () => {
  App.init();

  // ── Global lens selector (nav bar) ───────────────────────────────
  const lensContainer = document.getElementById('nav-lens-selector');
  if (lensContainer) {
    const BASE = window.__BASE_PATH__ || '';
    fetch(`${BASE}/api/lenses`).then(r => r.json()).then(lenses => {
      if (!Array.isArray(lenses) || !lenses.length) return;
      const current = localStorage.getItem('prumo-lens') || 'cae';
      const currentLens = lenses.find(l => l.id === current) || lenses[0];
      const currentIcon = _lensIcon(currentLens.icon || currentLens.id);
      lensContainer.innerHTML = `<button class="lens-toggle" id="lens-toggle" title="Lente ideológica">${currentIcon}</button>
        <div class="lens-dropdown hidden" id="lens-dropdown">
          ${lenses.map(l => {
            const active = l.id === current ? ' active' : '';
            const icon = _lensIcon(l.icon || l.id);
            const isParty = !!PARTY_LOGOS[l.icon || l.id];
            const label = l.short || l.id;
            return `<button class="lens-option${active}" data-lens="${l.id}" title="${l.label}">${icon}<span class="lens-option-label">${label}</span></button>`;
          }).join('')}
        </div>`;
      const toggle = lensContainer.querySelector('#lens-toggle');
      const dropdown = lensContainer.querySelector('#lens-dropdown');
      function _returnDropdownToNav() {
        if (dropdown.parentNode !== lensContainer) {
          lensContainer.appendChild(dropdown);
          dropdown.style.bottom = ''; dropdown.style.top = '';
          dropdown.style.left = ''; dropdown.style.right = '';
          dropdown.style.transform = '';
          dropdown.style.marginBottom = ''; dropdown.style.marginTop = '';
        }
      }
      toggle.addEventListener('click', e => { e.stopPropagation(); _returnDropdownToNav(); dropdown.classList.toggle('hidden'); });
      document.addEventListener('click', () => dropdown.classList.add('hidden'));
      dropdown.addEventListener('click', e => {
        const opt = e.target.closest('.lens-option');
        if (!opt) return;
        const lensId = opt.dataset.lens;
        const lens = lenses.find(l => l.id === lensId);
        localStorage.setItem('prumo-lens', lensId);
        toggle.innerHTML = _lensIcon(lens.icon || lens.id);
        dropdown.querySelectorAll('.lens-option').forEach(o => o.classList.toggle('active', o.dataset.lens === lensId));
        dropdown.classList.add('hidden');
        window.dispatchEvent(new CustomEvent('lens-change', { detail: { lens: lensId, source: 'global' } }));
      });
      // Sync with lens changes from other sources (painel, metodologia)
      window.addEventListener('lens-change', e => {
        if (e.detail.source === 'global') return;
        const lens = lenses.find(l => l.id === e.detail.lens);
        if (lens) toggle.innerHTML = _lensIcon(lens.icon || lens.id);
        dropdown.querySelectorAll('.lens-option').forEach(o => o.classList.toggle('active', o.dataset.lens === e.detail.lens));
      });
      // Store lenses globally for hint bar updates
      window.__prumoLenses = lenses;
      _updateLensHintBar(lenses);
    }).catch(() => { lensContainer.style.display = 'none'; });
  }

  // ── Global language selector (nav bar) ────────────────────────────
  const langContainer = document.getElementById('nav-lang-selector');
  if (langContainer) {
    // Only show languages with available i18n translation files
    const READY_LANGUAGES = new Set(['pt', 'en']);
    const langKeys = Object.keys(OUTPUT_LANGUAGES).filter(k => READY_LANGUAGES.has(k));
    if (langKeys.length > 1) {
      const current = getOutputLanguage();
      langContainer.innerHTML = `<button class="lang-toggle" id="lang-toggle" title="Língua / Language / Langue">${_flagImg(current)}</button>
        <div class="lang-dropdown hidden" id="lang-dropdown">
          ${langKeys.map(k => {
            const lbl = LANG_LABELS[k] || k.toUpperCase();
            const name = LANG_NAMES[k] || k;
            const active = k === current ? ' active' : '';
            return `<button class="lang-option${active}" data-lang="${k}" title="${name}">${_flagImg(k)}<span class="lang-option-label">${lbl}</span></button>`;
          }).join('')}
        </div>`;
      const toggle = langContainer.querySelector('#lang-toggle');
      const dropdown = langContainer.querySelector('#lang-dropdown');
      toggle.addEventListener('click', e => { e.stopPropagation(); dropdown.classList.toggle('hidden'); });
      document.addEventListener('click', () => dropdown.classList.add('hidden'));
      dropdown.addEventListener('click', e => {
        const opt = e.target.closest('.lang-option');
        if (!opt) return;
        const lang = opt.dataset.lang;
        localStorage.setItem('prumo-output-language', lang);
        toggle.innerHTML = _flagImg(lang);
        dropdown.querySelectorAll('.lang-option').forEach(o => o.classList.toggle('active', o.dataset.lang === lang));
        dropdown.classList.add('hidden');
        window.dispatchEvent(new CustomEvent('language-change', { detail: { language: lang } }));
        if (typeof i18n !== 'undefined') i18n.setLang(lang);
      });
    } else {
      langContainer.style.display = 'none';
    }
  }

  // ── Hero onboarding — full on first visit, compact for returning users ──
  const hero = document.getElementById('hero-onboarding');
  if (hero) {
    const _dismissed = localStorage.getItem('prumo-hero-dismissed');
    if (_dismissed) {
      // Returning user: show compact banner instead of hiding entirely
      hero.classList.add('compact');
      // Inject compact bar if not already present
      if (!hero.querySelector('.hero-compact-bar')) {
        const bar = document.createElement('div');
        bar.className = 'hero-compact-bar';
        bar.innerHTML = `
          <span class="hero-compact-title">${typeof i18n !== 'undefined' ? i18n.t('hero.compact_title') : 'Economia portuguesa, verificada.'}</span>
          <span class="hero-compact-snapshot" id="hero-compact-snapshot"></span>
          <button class="hero-compact-expand" title="${typeof i18n !== 'undefined' ? i18n.t('hero.expand_label') : 'About Prumo'}">↓ ${typeof i18n !== 'undefined' ? i18n.t('hero.expand_label') : 'About Prumo'}</button>`;
        hero.insertBefore(bar, hero.firstChild);
        bar.querySelector('.hero-compact-expand').addEventListener('click', () => {
          hero.classList.remove('compact', 'hidden');
          bar.style.display = 'none';
          localStorage.removeItem('prumo-hero-dismissed');
        });
      }
    }
    const dismiss = () => {
      hero.classList.add('hidden');
      hero.classList.remove('compact');
      localStorage.setItem('prumo-hero-dismissed', '1');
    };
    document.getElementById('hero-dismiss')?.addEventListener('click', dismiss);
    document.getElementById('hero-cta-explore')?.addEventListener('click', dismiss);

    // ── Snapshot: fetch and render data highlights in hero ──────────
    (function _fetchAndRenderSnapshot() {
    const BASE = window.__BASE_PATH__ || '';
    const container = document.getElementById('hero-snapshot');
    const compactEl = document.getElementById('hero-compact-snapshot');

    // Show loading state in full hero
    if (container) {
      container.innerHTML = '<div class="snapshot-loading"><div class="loading-spinner"></div><span>A carregar destaques\u2026</span></div>';
    }

    const snapshotLang = (typeof i18n !== 'undefined') ? i18n.lang() : 'pt';
    fetch(`${BASE}/api/snapshot?lang=${snapshotLang}`)
      .then(r => r.json())
      .then(data => {
        if (!data || !data.highlights || !data.highlights.length) {
          if (container) container.innerHTML = '';
          return;
        }

        // ── Render full hero snapshot ──────────────────────────────
        if (container) {
          const mood = data.mood || 'mixed';
          const moodLabel = data.mood_label || 'Sinais mistos';
          const icons = { positive: '+', negative: '\u2013' }; // + and – (endash)

          // Split into positive and negative groups
          const posItems = data.highlights.filter(h => h.sentiment === 'positive');
          const negItems = data.highlights.filter(h => h.sentiment !== 'positive');

          let html = '<div class="snapshot-fade-in">';
          html += '<div class="snapshot-columns">';

          // Positive column
          html += '<div class="snapshot-col snapshot-col--positive">';
          html += `<div class="snapshot-col-heading snapshot-col-heading--positive">${typeof i18n !== 'undefined' ? i18n.t('snapshot.positive_heading') : 'Sinais positivos'}</div>`;
          posItems.forEach(h => {
            html += `<div class="snapshot-item snapshot-item--positive">`;
            html += `<span class="snapshot-icon">+</span>`;
            html += `<span class="snapshot-sentence">${_escapeHtml(h.sentence)}</span>`;
            html += '</div>';
          });
          html += '</div>';

          // Negative column
          html += '<div class="snapshot-col snapshot-col--negative">';
          html += `<div class="snapshot-col-heading snapshot-col-heading--negative">${typeof i18n !== 'undefined' ? i18n.t('snapshot.negative_heading') : 'Sinais negativos'}</div>`;
          negItems.forEach(h => {
            html += `<div class="snapshot-item snapshot-item--negative">`;
            html += `<span class="snapshot-icon">\u2013</span>`;
            html += `<span class="snapshot-sentence">${_escapeHtml(h.sentence)}</span>`;
            html += '</div>';
          });
          html += '</div>';

          html += '</div>'; // close columns
          html += '</div>';
          const ref = data.reference || 'Variação face ao ano anterior';
          html += `<div class="snapshot-meta">Dados: ${_escapeHtml(data.updated_label || data.updated)} · ${_escapeHtml(ref)}</div>`;
          html += '</div>';
          container.innerHTML = html;
        }

        // ── Render compact hero teaser (first highlight) ──────────
        if (compactEl && data.highlights.length > 0) {
          const first = data.highlights[0];
          const mood = data.mood || 'mixed';
          compactEl.innerHTML = `<span class="compact-mood-dot compact-mood-dot--${mood}"></span>${_escapeHtml(first.sentence)}`;
        }
      })
      .catch(err => {
        console.warn('[snapshot] fetch error:', err);
        if (container) container.innerHTML = '';
      });
    })();
  }

  /** Minimal HTML escaping to prevent XSS in template-filled sentences. */
  function _escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Language selector prompt — show only on first visit ──────────────────
  if (!localStorage.getItem('prumo-language-selected')) {
    const langContainer = document.getElementById('nav-lang-selector');
    if (langContainer) {
      const prompt = document.createElement('div');
      prompt.className = 'lang-selector-prompt';
      prompt.style.cssText = `
        position: fixed; top: 60px; right: 10px; z-index: 9998;
        background: #fff; border: 1px solid #ddd; border-radius: 8px;
        padding: 12px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        font-size: 12px; font-weight: 600; color: #374151;
        display: flex; align-items: center; gap: 8px;
      `;
      const msgLang = getOutputLanguage();
      const prompts = {
        pt: 'Escolha o seu idioma de saída',
        cv: 'Eskoji ku idioma di saída',
        fr: 'Choisissez votre langue de sortie',
        es: 'Elige tu idioma de salida',
        en: 'Choose your output language',
      };
      prompt.textContent = prompts[msgLang] || prompts.pt;
      document.body.appendChild(prompt);
      setTimeout(() => prompt.remove(), 5000);
      localStorage.setItem('prumo-language-selected', '1');
    }
  }

  // ── Metodologia lens bar — populate from /api/lenses ──────────────
  const mfLensBar = document.getElementById('mf-lens-bar');
  if (mfLensBar) {
    const BASE = window.__BASE_PATH__ || '';
    fetch(`${BASE}/api/lenses`).then(r => r.json()).then(lenses => {
      if (!Array.isArray(lenses) || !lenses.length) return;
      const current = localStorage.getItem('prumo-lens') || 'cae';
      mfLensBar.innerHTML = lenses.map(l => {
        const active = l.id === current ? 'active' : '';
        const style = l.id === current ? `style="border-color:${l.color};color:${l.color}"` : '';
        const icon = _lensIcon(l.icon || l.id);
        const isParty = !!PARTY_LOGOS[l.icon || l.id];
        const label = isParty ? '' : l.short;
        return `<button class="lens-pill ${active} ${isParty ? 'lens-pill-logo' : ''}" data-lens="${l.id}" ${style} title="${l.label}${l.source ? '\nFonte: '+l.source : ''}">${icon}${label}</button>`;
      }).join('');

      // Show source for active lens
      const activeLens = lenses.find(l => l.id === current);
      const srcEl = document.getElementById('mf-lens-source');
      if (srcEl && activeLens?.source) {
        srcEl.textContent = `Fonte: ${activeLens.source}`;
      }

      // Show/hide custom ideology textarea in metodologia
      function toggleMfCustomTextarea(lensId) {
        let wrap = document.getElementById('mf-custom-ideology-wrap');
        if (lensId === 'custom') {
          if (!wrap) {
            wrap = document.createElement('div');
            wrap.id = 'mf-custom-ideology-wrap';
            wrap.className = 'custom-ideology-wrap';
            wrap.innerHTML = `<textarea id="mf-custom-ideology-text" class="custom-ideology-textarea"
              placeholder="Escreve aqui o teu enquadramento ideológico personalizado…"
              rows="5">${localStorage.getItem('prumo-custom-ideology') || CUSTOM_LENS_DEFAULT}</textarea>
              <div class="custom-ideology-footer">
                <span class="custom-ideology-hint">Texto enviado como contexto ao modelo de IA. Guardado no browser.</span>
                <button id="mf-custom-save" class="lens-pill" style="border-color:#9C27B0;color:#9C27B0;font-size:10px">Guardar</button>
              </div>`;
            const ideologyText = document.getElementById('mf-ideology-text');
            if (ideologyText) ideologyText.parentNode.insertBefore(wrap, ideologyText);
            wrap.querySelector('#mf-custom-save').addEventListener('click', () => {
              const txt = wrap.querySelector('#mf-custom-ideology-text').value.trim();
              if (txt) {
                localStorage.setItem('prumo-custom-ideology', txt);
                App.showToast(_getMessage('lens_saved'));
                const textEl = document.getElementById('mf-ideology-text');
                if (textEl) textEl.textContent = txt;
              }
            });
            wrap.querySelector('#mf-custom-ideology-text').addEventListener('blur', () => {
              const txt = wrap.querySelector('#mf-custom-ideology-text').value.trim();
              if (txt) localStorage.setItem('prumo-custom-ideology', txt);
            });
          }
          // Show custom text in ideology display
          const textEl = document.getElementById('mf-ideology-text');
          const customText = localStorage.getItem('prumo-custom-ideology') || CUSTOM_LENS_DEFAULT;
          if (textEl) textEl.textContent = customText;
        } else if (wrap) {
          wrap.remove();
        }
      }

      // Shared function to update metodologia pills + text
      function _mfSwitchLens(lensId) {
        mfLensBar.querySelectorAll('.lens-pill').forEach(p => {
          const l = lenses.find(x => x.id === p.dataset.lens);
          if (p.dataset.lens === lensId) {
            p.classList.add('active');
            if (l) p.style.cssText = `border-color:${l.color};color:${l.color}`;
          } else {
            p.classList.remove('active');
            p.style.cssText = '';
          }
        });
        toggleMfCustomTextarea(lensId);
        if (lensId === 'custom') {
          if (srcEl) srcEl.textContent = 'Fonte: Texto definido pelo utilizador';
          return;
        }
        // Dissolve ideology text, then fetch new
        const textEl = document.getElementById('mf-ideology-text');
        if (textEl) {
          textEl.classList.add('ia-dissolve-out');
          textEl.addEventListener('transitionend', function _dEnd() {
            textEl.removeEventListener('transitionend', _dEnd);
            textEl.classList.remove('ia-dissolve-out');
            _mfFetchIdeology(lensId);
          }, {once: true});
          setTimeout(() => { textEl.classList.remove('ia-dissolve-out'); _mfFetchIdeology(lensId); }, 500);
        } else {
          _mfFetchIdeology(lensId);
        }
      }

      async function _mfFetchIdeology(lensId) {
        try {
          const resp = await fetch(`${BASE}/api/metodologia?lens=${encodeURIComponent(lensId)}`);
          const data = await resp.json();
          const textEl = document.getElementById('mf-ideology-text');
          if (textEl && data.ideology) { textEl.textContent = data.ideology; textEl.classList.add('ia-dissolve-in'); setTimeout(() => textEl.classList.remove('ia-dissolve-in'), 400); }
          if (srcEl && data.lens?.source) srcEl.textContent = `Fonte: ${data.lens.source}`;
          else if (srcEl) srcEl.textContent = '';
        } catch(err) { console.warn('[metodologia] lens switch error:', err); }
      }

      // Click handler — switch ideology text
      mfLensBar.addEventListener('click', e => {
        const pill = e.target.closest('.lens-pill');
        if (!pill) return;
        const lensId = pill.dataset.lens;
        localStorage.setItem('prumo-lens', lensId);
        // Dispatch global lens change event
        window.dispatchEvent(new CustomEvent('lens-change', {detail: {lens: lensId, source: 'metodologia'}}));
        _mfSwitchLens(lensId);
      });

      // Listen for lens changes from other sections
      window.addEventListener('lens-change', e => {
        if (e.detail.source === 'metodologia') return;
        _mfSwitchLens(e.detail.lens);
      });

      // Init custom textarea if custom lens is active
      toggleMfCustomTextarea(current);
    }).catch(() => {});
  }
});
