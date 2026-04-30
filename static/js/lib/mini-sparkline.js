/* ═══════════════════════════════════════════════════════════════
   mini-sparkline.js — ECharts mini sparkline for AI analysis cards
   Extracted from painel.js for reuse.
   ═══════════════════════════════════════════════════════════════ */

window.PrumoLib = window.PrumoLib || {};

/**
 * Render a mini sparkline with optional EU reference line.
 * @param {HTMLElement} container - DOM element to render into
 * @param {Array} data - [{period, value}] or plain numbers
 * @param {number} yoy - Year-over-year change (determines line colour)
 * @param {Array|null} refData - Optional EU reference series
 * @param {string} unit - Unit label for axis
 * @param {string} label - Series label
 */
PrumoLib.renderMiniSparkline = function(container, data, yoy, refData, unit, label) {
  if (!window.echarts || !data?.length) {
    container.style.cssText = 'display:flex;align-items:center;justify-content:center;color:var(--c-muted);font-size:12px';
    container.textContent = 'Sem dados';
    return;
  }
  const chart = window.echarts.init(container, null, { renderer: 'svg' });
  const vals  = data.map(d => d.value ?? d.v ?? d);
  const color = yoy >= 0 ? '#2E7D32' : '#C62828';
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
                 const MO = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
                 const fmt = (s) => {
                   const parts = s.split('-');
                   if (parts.length >= 2) {
                     const mi = parseInt(parts[1], 10) - 1;
                     return MO[mi] || s.slice(5,7);
                   }
                   return s;
                 };
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
};
