/* ═══════════════════════════════════════════════════════════════
   api.js — Fetch wrappers com cache simples (5 min TTL)
   CAE Dashboard V7
   ═══════════════════════════════════════════════════════════════ */

const API = (() => {
  const _cache = {};
  const TTL = 5 * 60 * 1000; // 5 minutes
  const BASE = window.__BASE_PATH__ || '';

  async function get(path) {
    const url = BASE + path;
    const now = Date.now();
    if (_cache[url] && now - _cache[url].ts < TTL) {
      return _cache[url].data;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const resp = await fetch(url, { signal: controller.signal });
      clearTimeout(timer);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _cache[url] = { data, ts: now };
      return data;
    } catch (e) {
      clearTimeout(timer);
      if (e.name === 'AbortError') throw new Error('Tempo limite excedido — servidor não respondeu em 10s');
      throw e;
    }
  }

  async function post(path, body) {
    const url = BASE + path;
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn('[api] POST error:', path, e);
      return null;
    }
  }

  // Convenience shortcuts for active endpoints
  return {
    get,
    post,
    resumo:    () => get('/api/resumo'),
    painel:    () => get('/api/painel'),
    catalog:   () => get('/api/catalog'),
    events:    () => get('/api/events'),
    compare:   (params) => get(`/api/compare?${new URLSearchParams(params)}`),
    track:     (data) => post('/api/track', data),
    invalidate:    (path) => { delete _cache[BASE + path]; },
    invalidateAll: () => { Object.keys(_cache).forEach(k => delete _cache[k]); },
  };
})();

/* Formatting utilities */
const fmt = {
  num: (v, decimals) => {
    if (v === null || v === undefined || isNaN(v)) return 'n/d';
    const n = Number(v);
    if (decimals !== undefined) return n.toFixed(decimals);
    const abs = Math.abs(n);
    const d = abs >= 100 ? 0 : abs >= 10 ? 1 : 3;  // <10 (combustíveis, elect., euribor) → 3 casas
    return n.toFixed(d);
  },
  pct: (v, decimals = 1) => {
    if (v === null || v === undefined || isNaN(v)) return 'n/d';
    const n = Number(v).toFixed(decimals);
    return (v > 0 ? '+' : '') + n + '%';
  },
  signed: (v, decimals = 1) => {
    if (v === null || v === undefined || isNaN(v)) return 'n/d';
    const n = Number(v).toFixed(decimals);
    return (v > 0 ? '+' : '') + n;
  },
  sentimentClass: (v) => {
    if (v === null || v === undefined || isNaN(v)) return 'neutral';
    return v > 0 ? 'positive' : v < 0 ? 'negative' : 'neutral';
  },
  arrow: (v) => {
    if (v === null || v === undefined || isNaN(v)) return '→';
    return v > 0.5 ? '↑' : v < -0.5 ? '↓' : '→';
  },
  period: (p) => {
    if (!p || !p.includes('-')) return p;
    const [y, m] = p.split('-');
    const months = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
    return `${months[parseInt(m,10)-1]} ${y.slice(2)}`;
  },
};

window.API = API;
window.fmt = fmt;
