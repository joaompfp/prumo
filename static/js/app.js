/* ═══════════════════════════════════════════════════════════════
   app.js — Hash Router + Lazy Section Init
   CAE Dashboard V7
   ═══════════════════════════════════════════════════════════════ */

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

function _lensIcon(lensId) {
  const BASE = window.__BASE_PATH__ || '';
  if (PARTY_LOGOS[lensId]) return `<img class="lens-logo" src="${BASE}/static/images/parties/${PARTY_LOGOS[lensId]}" alt="${lensId}">`;
  if (PARTY_ICONS[lensId]) return `<span class="lens-icon">${PARTY_ICONS[lensId]}</span>`;
  return '';
}

// ── Global lens change event bus ────────────────────────────────────
// Dispatch: window.dispatchEvent(new CustomEvent('lens-change', {detail: {lens, source}}))
// Listen:   window.addEventListener('lens-change', e => { ... })

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

  // ── Global language selector (nav bar) ────────────────────────────
  const langContainer = document.getElementById('nav-lang-selector');
  if (langContainer) {
    const langKeys = Object.keys(OUTPUT_LANGUAGES);
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
      });
    } else {
      langContainer.style.display = 'none';
    }
  }

  // ── Hero onboarding — show only on first visit ──────────────────
  const hero = document.getElementById('hero-onboarding');
  if (hero) {
    if (localStorage.getItem('prumo-hero-dismissed')) {
      hero.classList.add('hidden');
    }
    const dismiss = () => {
      hero.classList.add('hidden');
      localStorage.setItem('prumo-hero-dismissed', '1');
    };
    document.getElementById('hero-dismiss')?.addEventListener('click', dismiss);
    document.getElementById('hero-cta-explore')?.addEventListener('click', dismiss);
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
                App.showToast('Lente personalizada guardada');
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
