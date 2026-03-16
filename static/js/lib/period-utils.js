/* ═══════════════════════════════════════════════════════════════
   period-utils.js — Period normalisation utilities (shared)
   Extracted from analise.js / explorador for reuse.
   ═══════════════════════════════════════════════════════════════ */

window.PrumoLib = window.PrumoLib || {};

/**
 * Normalise period formats to YYYY-MM so mixed-frequency series align on
 * the same X-axis.
 *   "2024"     → "2024-12"
 *   "2025-Q3"  → "2025-09"
 *   "2025 S1"  → "2025-06"
 *   "2025-03"  → "2025-03" (unchanged)
 */
PrumoLib.normalisePeriod = function(p) {
  if (!p) return p;
  if (/^\d{4}$/.test(p)) return `${p}-12`;
  const qm = p.match(/^(\d{4})[- ]Q(\d)$/);
  if (qm) return `${qm[1]}-${String(parseInt(qm[2]) * 3).padStart(2, '0')}`;
  const sm = p.match(/^(\d{4})[- ][SH](\d)$/);
  if (sm) return `${sm[1]}-${sm[2] === '1' ? '06' : '12'}`;
  return p;
};

/** Returns true if the raw period string was an annual value ("YYYY"). */
PrumoLib.isAnnualPeriod = function(p) {
  return !!p && /^\d{4}$/.test(p);
};

/** Return current date as YYYY-MM. */
PrumoLib.nowYM = function() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

/** Return date N years ago as YYYY-MM. */
PrumoLib.subtractYears = function(n) {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};
