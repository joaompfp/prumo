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
  period: (p, opts = {}) => {
    if (!p) return p;
    // Quarterly: "2025-Q3" or "2025 Q3"
    const qm = p.match(/^(\d{4})[- ]Q(\d)$/);
    if (qm) return `Q${qm[2]} ${qm[1].slice(2)}`;
    // Semi-annual: "2025 S1" or "2025-H1"
    const sm = p.match(/^(\d{4})[- ][SH](\d)$/);
    if (sm) return `S${sm[2]} ${sm[1].slice(2)}`;
    // Annual: "2025"
    if (/^\d{4}$/.test(p)) return p;
    // Monthly: "2025-03" (or annual-collapsed "YYYY-12" when opts.annualCollapsed)
    if (!p.includes('-')) return p;
    const [y, m] = p.split('-');
    // Annual period collapsed to YYYY-12 by normalisePeriod → show just the year
    if (opts.annualCollapsed && m === '12') return y;
    const months = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
    const mIdx = parseInt(m, 10) - 1;
    if (isNaN(mIdx) || mIdx < 0 || mIdx > 11) return p; // fallback
    return `${months[mIdx]} ${y.slice(2)}`;
  },
};

window.API = API;
window.fmt = fmt;

// ── Unit display normalisation ─────────────────────────────────────────────
// Call: fmt.unit(u) → canonical display string
// Call: fmt.unitFamily(u) → { base, scale, factor } for prefix-aware comparison
(function() {
  const UNIT_DISPLAY = {
    // Currency notation
    'EUR':        '€',
    'EUR/l':      '€/l',
    'EUR/L':      '€/l',
    'EUR/kWh':    '€/kWh',
    'EUR/KWH':    '€/kWh',
    'EUR/kwh':    '€/kWh',
    'EUR/MWh':    '€/MWh',
    'EUR/MWH':    '€/MWh',
    'EUR/GJ':     '€/GJ',
    'EUR/kW/mês': '€/kW/mês',
    'EUR/m3':     '€/m³',
    'EUR/m³':     '€/m³',
    // Energy
    'KWH':  'kWh',
    'MWH':  'MWh',
    'GWH':  'GWh',
    'TWH':  'TWh',
    'GJ':   'GJ',
    'TEP':  'tep',
    'KTEP': 'ktep',
    // Mass
    'T':    't',
    'KT':   'kt',
    'MT':   'Mt',
    'GT':   'Gt',
    // Other common
    'USD':  'USD',
    'USD/t':   'USD/t',
    'USD/ton': 'USD/t',
    'USD/lb':  'USD/lb',
    'USD/libra': 'USD/lb',
    'USD/bbl': 'USD/bbl',
    'USD/bushel': 'USD/bushel',
    'EUR/t':   '€/t',
    'EUR/ton': '€/t',
    'EUR/kg':  '€/kg',
    '€/ton':   '€/t',
    '€/tonelada': '€/t',
    'M EUR': 'M€',
    'M€':   'M€',
    'MtCO2e': 'MtCO₂e',
    'Mton CO2e': 'MtCO₂e',
    '%PIB': '% PIB',
    '% PIB': '% PIB',
  };

  // Families of units that share the same physical dimension but differ by SI prefix.
  // When two series are in the same family, convert the larger to the smaller for display.
  const UNIT_FAMILIES = [
    // Energy price (per energy unit)
    { base: '€/Wh',    members: { '€/kWh': 1, '€/MWh': 1e-3, '€/GWh': 1e-6 } },
    { base: 'USD/Wh',  members: { 'USD/kWh': 1, 'USD/MWh': 1e-3 } },
    { base: '€/GJ',    members: { '€/GJ': 1, '€/MJ': 1e3 } },
    // Energy volume
    { base: 'Wh',      members: { 'kWh': 1, 'MWh': 1e3, 'GWh': 1e6, 'TWh': 1e9 } },
    { base: 'J',       members: { 'GJ': 1, 'TJ': 1e3, 'PJ': 1e6 } },
    // Oil equivalent
    { base: 'tep',     members: { 'tep': 1, 'ktep': 1e3, 'Mtep': 1e6 } },
    // Mass
    { base: 'g',       members: { 'g': 1, 'kg': 1e3, 't': 1e6, 'kt': 1e9, 'Mt': 1e12 } },
    // Price per mass (commodities)
    { base: '€/g',     members: { '€/kg': 1, '€/t': 1e-3, '€/ton': 1e-3, '€/tonelada': 1e-3 } },
    { base: 'USD/g',   members: { 'USD/kg': 1, 'USD/t': 1e-3, 'USD/ton': 1e-3, 'USD/lb': 2.205, 'USD/libra': 2.205 } },
    // Price per volume (fuels)
    { base: '€/l',     members: { '€/l': 1, '€/m³': 1e-3 } },
    { base: 'USD/l',   members: { 'USD/l': 1, 'USD/bbl': 0.00629 } },  // 1 bbl ≈ 158.987 l → USD/l = USD/bbl * 0.00629
    // CO₂ mass
    { base: 'tCO2',    members: { 'tCO₂': 1, 'MtCO₂': 1e6, 'Mton CO2e': 1e6, 'ktCO₂': 1e3 } },
    // Power / capacity
    { base: 'W',       members: { 'kW': 1, 'MW': 1e3, 'GW': 1e6 } },
    // Currency scale
    { base: '€',       members: { '€': 1, 'M€': 1e6, 'G€': 1e9 } },
    { base: 'USD',     members: { 'USD': 1, 'M USD': 1e6, 'B USD': 1e9 } },
    // Volume
    { base: 'l',       members: { 'l': 1, 'm³': 1e3 } },
  ];

  fmt.unit = function(u) {
    if (!u) return u;
    const norm = UNIT_DISPLAY[u];
    if (norm) return norm;
    // Try case-insensitive
    const key = Object.keys(UNIT_DISPLAY).find(k => k.toLowerCase() === u.toLowerCase());
    return key ? UNIT_DISPLAY[key] : u;
  };

  fmt.unitFamily = function(u) {
    const disp = fmt.unit(u) || u;
    for (const fam of UNIT_FAMILIES) {
      if (disp in fam.members) return { family: fam.base, scale: fam.members[disp], unit: disp };
    }
    return null;
  };

  /**
   * Given an array of unit strings, return { units[], converters[] } where:
   * - units[] are the canonical display units (same-family units converted to the smallest)
   * - converters[] are functions value → converted value
   * If two units are in the same family, both are normalised to the finest-grained member.
   */
  fmt.resolveUnits = function(rawUnits) {
    const display = rawUnits.map(u => fmt.unit(u) || u);
    const result = display.map(u => ({ unit: u, factor: 1 }));

    for (const fam of UNIT_FAMILIES) {
      const indices = display.reduce((acc, u, i) => { if (u in fam.members) acc.push(i); return acc; }, []);
      if (indices.length > 1) {
        // Convert all to the unit with smallest scale (highest resolution)
        const scales = indices.map(i => fam.members[display[i]]);
        const minScale = Math.min(...scales);
        const targetUnit = Object.keys(fam.members).find(k => fam.members[k] === minScale);
        indices.forEach((i, j) => {
          result[i] = { unit: targetUnit, factor: scales[j] / minScale };
        });
      }
    }
    return result;
  };
})();
