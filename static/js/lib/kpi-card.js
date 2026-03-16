/* ═══════════════════════════════════════════════════════════════
   kpi-card.js — KPI card HTML renderer (shared component)
   Extracted from painel.js for reuse.
   ═══════════════════════════════════════════════════════════════ */

window.PrumoLib = window.PrumoLib || {};

/** Source label map for display. */
PrumoLib.SOURCE_LABELS = {
  'INE': 'INE', 'EUROSTAT': 'Eurostat', 'FRED': 'FRED',
  'BPORTUGAL': 'Banco de Portugal', 'OECD': 'OCDE',
  'WORLDBANK': 'Banco Mundial', 'REN': 'REN',
  'ERSE': 'ERSE', 'DGEG': 'DGEG',
};

/** Skeleton card HTML for loading state. */
PrumoLib.skeletonCard = `
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

/**
 * Render a single KPI card as HTML string.
 * @param {Object} kpi - KPI data object
 * @returns {string} HTML string
 */
PrumoLib.renderKpiCard = function(kpi) {
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
  const sourceLabel = kpi.source ? (PrumoLib.SOURCE_LABELS[kpi.source] || kpi.source) : '';

  const period = kpi.period || '';
  let yoyLabel = 'vs ano anterior';
  if (period && period.length >= 7) {
    const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
    const m = parseInt(period.slice(5, 7), 10);
    const y = parseInt(period.slice(0, 4), 10);
    if (m >= 1 && m <= 12 && y > 2000) {
      yoyLabel = `${MONTHS[m-1]} ${y} vs ${MONTHS[m-1]} ${y-1}`;
    }
  } else if (period && period.length === 4) {
    yoyLabel = `${period} vs ${parseInt(period, 10) - 1}`;
  }

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
      <span class="kpi-label" style="font-size:11px;letter-spacing:0.5px;">${yoyLabel}</span>
    </div>
    ${description ? `<div class="kpi-description">${description}</div>` : ''}
    ${context ? `<div class="kpi-context">${context}</div>` : ''}
    ${hasSpark ? `<div class="spark-container" id="spark-${kpi.id}"></div>` : ''}
    ${period ? `<div class="kpi-freshness" style="font-size:10px;opacity:.5;margin-top:4px;font-style:italic">Dados: ${period}</div>` : ''}
  </div>`;
};
