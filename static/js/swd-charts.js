/* ═══════════════════════════════════════════════════════════════
   swd-charts.js — ECharts factory com defaults SWD
   "Storytelling with Data" visual standards
   CAE Dashboard V5
   ═══════════════════════════════════════════════════════════════ */

const SWD = (() => {
  // Registo de todos os charts para resize global
  const _charts = [];

  // Paleta padrão SWD
  const COLORS = {
    pt:     '#CC0000',
    eu:     '#4A90D9',
    es:     '#999999',
    de:     '#AAAAAA',
    fr:     '#BBBBBB',
    other:  '#CCCCCC',
    base:   '#E0E0E0',
    positive: '#2E7D32',
    negative: '#C62828',
  };

  const COUNTRY_COLORS = {
    // Portugal — destaque vermelho
    PT:        '#CC0000',
    // Agregado UE
    EU:        '#4A90D9',
    EU27:      '#4A90D9',
    EU27_2020: '#4A90D9',
    // Grandes economias ocidentais
    DE: '#2c3e50',
    FR: '#8e44ad',
    IT: '#27ae60',
    ES: '#e67e22',
    NL: '#16a085',
    BE: '#2980b9',
    AT: '#c0392b',
    LU: '#9c27b0',
    // Nórdicos
    SE: '#9b59b6',
    DK: '#e91e63',
    FI: '#00bcd4',
    // Mediterrâneo / Ibérica
    EL: '#ff5722',   // código Eurostat para Grécia
    GR: '#ff5722',   // alias ISO — mantido para compatibilidade
    IE: '#4caf50',
    CY: '#009688',
    MT: '#8bc34a',
    // Alargamento Leste
    PL: '#1abc9c',
    CZ: '#d35400',
    SK: '#e74c3c',
    HU: '#7f8c8d',
    RO: '#f39c12',
    BG: '#95a5a6',
    HR: '#3498db',
    SI: '#2ecc71',
    EE: '#607d8b',
    LV: '#795548',
    LT: '#ff9800',
  };

  // Base options — zero clutter
  function baseOptions(title = '', subtitle = '') {
    return {
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 600,
      animationEasing: 'cubicOut',
      color: [COLORS.pt, COLORS.eu, COLORS.es, COLORS.de, COLORS.fr, COLORS.other],
      textStyle: {
        fontFamily: 'Inter, system-ui, sans-serif',
        color: '#1A1A1A',
      },
      title: title ? {
        text: title,
        subtext: subtitle,
        left: 'left',
        top: 0,
        textStyle: {
          fontSize: 14,
          fontWeight: 600,
          color: '#1A1A1A',
          fontFamily: 'Inter, system-ui, sans-serif',
          lineHeight: 20,
        },
        subtextStyle: {
          fontSize: 12,
          color: '#888888',
          fontFamily: 'Inter, system-ui, sans-serif',
        },
      } : undefined,
      grid: {
        containLabel: true,
        left: 40,
        right: 20,
        top: title ? 56 : 16,
        bottom: 30,
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#FFFFFF',
        borderColor: '#EBEBEB',
        borderWidth: 1,
        padding: [8, 12],
        textStyle: {
          fontSize: 12,
          color: '#1A1A1A',
          fontFamily: 'Inter, system-ui, sans-serif',
        },
        extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.12); border-radius: 6px;',
        axisPointer: {
          type: 'line',
          lineStyle: { color: '#E0E0E0', width: 1 },
        },
      },
      legend: { show: false }, // Labels directos — sem legend separada
    };
  }

  // xAxis padrão (categorias temporais)
  function timeAxis(data = [], opts = {}) {
    // Intervalo: nunca mais de 8 labels. Se opts.interval fornecido, usar; caso contrário calcular.
    const defaultInterval = data.length > 0
      ? Math.max(0, Math.floor(data.length / 8) - 1)
      : 'auto';
    return {
      type: 'category',
      data,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        fontSize: 10,
        color: '#888888',
        fontFamily: 'Inter, system-ui, sans-serif',
        interval: opts.interval ?? defaultInterval,
        rotate: opts.rotate ?? 0,
        hideOverlap: true,
        // Permite override via opts.axisLabel
        ...(opts.axisLabel || {}),
      },
      boundaryGap: opts.boundaryGap ?? false,
    };
  }

  // yAxis padrão
  function valueAxis(opts = {}) {
    return {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: {
        show: true,
        lineStyle: { color: '#F0F0F0', width: 1 },
      },
      axisLabel: {
        fontSize: 11,
        color: '#888888',
        fontFamily: 'Inter, system-ui, sans-serif',
        formatter: opts.formatter || null,
      },
      min: opts.min,
      max: opts.max,
      scale: opts.scale ?? false,
    };
  }

  // Marca linha horizontal (índice 100, baseline, etc.)
  function markLine(value, label = '', color = '#CCCCCC') {
    return {
      silent: true,
      symbol: ['none', 'none'],
      lineStyle: { color, type: 'solid', width: 1 },
      label: {
        show: !!label,
        position: 'end',
        fontSize: 10,
        color,
        fontFamily: 'Inter, system-ui, sans-serif',
        formatter: label,
      },
      data: [{ yAxis: value }],
    };
  }

  // Marca linha vertical (anotação de evento)
  function markLineVertical(xValue, label = '', color = '#CCCCCC') {
    return {
      xAxis: xValue,
      lineStyle: { type: 'dashed', color, width: 1 },
      label: {
        show: true,
        position: 'start',
        formatter: label,
        fontSize: 10,
        color,
        fontFamily: 'Inter, system-ui, sans-serif',
        rotate: 90,
      },
    };
  }

  /* ── Factory principal ─────────────────────────────────────────── */
  function createSWDChart(container, options = {}) {
    if (!container) return null;
    // Destroy se já existia
    const existing = echarts.getInstanceByDom(container);
    if (existing) existing.dispose();

    const chart = echarts.init(container, null, { renderer: 'canvas' });
    chart.setOption(options);

    // Force resize after layout settles (fix sizing on first render)
    setTimeout(() => { try { chart.resize(); } catch(e) {} }, 150);

    // Resize automático
    const resizeFn = () => chart.resize();
    window.addEventListener('resize', resizeFn);
    chart._swdResizeFn = resizeFn;

    _charts.push(chart);
    return chart;
  }

  function destroyChart(chart) {
    if (!chart) return;
    if (chart._swdResizeFn) window.removeEventListener('resize', chart._swdResizeFn);
    chart.dispose();
    const idx = _charts.indexOf(chart);
    if (idx > -1) _charts.splice(idx, 1);
  }

  function resizeAll() {
    _charts.forEach(c => { try { c.resize(); } catch(e){} });
  }

  /* ── Sparkline (micro gráfico KPI) ────────────────────────────── */
  function createSparkline(container, data, color = '#CC0000') {
    if (!container || !data || !data.length) return null;
    const chart = createSWDChart(container, {
      backgroundColor: 'transparent',
      animation: false,
      grid: { left: 0, right: 0, top: 0, bottom: 0 },
      xAxis: {
        type: 'category',
        show: false,
        data: data.map((_, i) => i),
        boundaryGap: false,
      },
      yAxis: { type: 'value', show: false, scale: true },
      series: [{
        type: 'line',
        data,
        smooth: true,
        symbol: 'none',
        lineStyle: { color, width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: color + '33' },
              { offset: 1, color: color + '00' },
            ],
          },
        },
      }],
      tooltip: { show: false },
    });
    return chart;
  }

  /* ── Helper: gera série linha padrão ──────────────────────────── */
  function lineSeries(name, data, color, opts = {}) {
    return {
      name,
      type: 'line',
      data,
      smooth: opts.smooth ?? false,
      symbol: opts.symbol ?? 'none',
      symbolSize: opts.symbolSize ?? 4,
      lineStyle: {
        color: color || COLORS.pt,
        width: opts.width ?? 2,
        type: opts.type ?? 'solid',
      },
      itemStyle: { color: color || COLORS.pt },
      markLine: opts.markLine,
      markArea: opts.markArea,
      endLabel: opts.endLabel ? {
        show: true,
        formatter: opts.endLabel,
        fontSize: 11,
        color,
        fontFamily: 'Inter, system-ui, sans-serif',
      } : undefined,
    };
  }

  return {
    COLORS,
    COUNTRY_COLORS,
    baseOptions,
    timeAxis,
    valueAxis,
    markLine,
    markLineVertical,
    createSWDChart,
    createSparkline,
    destroyChart,
    resizeAll,
    lineSeries,
  };
})();

window.SWD = SWD;
