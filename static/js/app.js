/* ═══════════════════════════════════════════════════════════════
   app.js — Hash Router + Lazy Section Init
   CAE Dashboard V7
   ═══════════════════════════════════════════════════════════════ */

const App = (() => {
  const SECTIONS = ['painel', 'europa', 'mundo', 'explorador', 'ficha'];
  const _initialized = {};
  const _loaders = {};

  // Legacy hash redirects — old V5/V6 section names
  const REDIRECTS = {
    'resumo':        'painel',
    'industria':     'explorador',
    'energia':       'explorador',
    'emprego':       'explorador',
    'macro':         'explorador',
    'analise':       'explorador',
    'fosso':         'painel',
    'produtividade': 'painel',
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

    // Lazy init
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

    // Update URL (preserve query params for sections that use them)
    const currentHash = window.location.hash;
    const currentBase = currentHash.split('?')[0].replace('#', '');
    if (currentBase !== sectionId) {
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
});
