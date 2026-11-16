/* Prumo chart adapter: local, dependency-free except the pinned ECharts build.
 *
 * Reads the inert JSON block the server rendered from the same prepared model as the SVG
 * fallback. Values are server-formatted strings; this file never formats a number back into a
 * reader-facing value. The SVG stays in the document (in flow, accessible) and the canvas is
 * overlayed only after setOption succeeds.
 */
import { init, use } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

const VIEW_W = 880;
const VIEW_H = 340;

function css(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function finite(value) {
  return typeof value === 'number' && isFinite(value);
}

function valid(payload) {
  if (!payload || payload.version !== 1) return false;
  if (!Array.isArray(payload.x) || !Array.isArray(payload.periods)) return false;
  if (!Array.isArray(payload.y) || !Array.isArray(payload.display)) return false;
  if (!Array.isArray(payload.series) || !Array.isArray(payload.axes)) return false;
  if (!payload.series.length || !payload.axes.length) return false;
  if (payload.x.length !== payload.periods.length || payload.x.length !== payload.y.length) {
    return false;
  }
  if (!payload.x.length) return false;
  for (let i = 0; i < payload.x.length; i += 1) {
    if (!finite(payload.x[i])) return false;
    if (!Array.isArray(payload.y[i]) || payload.y[i].length !== payload.series.length) return false;
    if (!payload.y[i].every(finite)) return false;
  }
  return finite(payload.x_min) && finite(payload.x_max);
}

function tickText(ticks, value) {
  let best = null;
  let bestDistance = Infinity;
  for (let i = 0; i < ticks.length; i += 1) {
    const distance = Math.abs(ticks[i].value - value);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = ticks[i];
    }
  }
  const tolerance = Math.max(Math.abs(value) * 1e-9, 1e-6);
  return best && bestDistance <= tolerance ? best.text : '';
}

function xText(ticks, value) {
  let best = null;
  let bestDistance = Infinity;
  for (let i = 0; i < ticks.length; i += 1) {
    const distance = Math.abs(ticks[i].x - value);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = ticks[i];
    }
  }
  const tolerance = Math.max(Math.abs(value) * 1e-9, 1e-6);
  return best && bestDistance <= tolerance ? best.text : '';
}

function dataFor(payload, seriesIndex) {
  const breaks = new Set(payload.breaks || []);
  const data = [];
  for (let i = 0; i < payload.x.length; i += 1) {
    if (breaks.has(i)) data.push(null);
    data.push([payload.x[i], payload.y[i][seriesIndex]]);
  }
  return data;
}

function indexMap(payload) {
  const breaks = new Set(payload.breaks || []);
  const map = [];
  for (let i = 0; i < payload.x.length; i += 1) {
    if (breaks.has(i)) map.push(-1);
    map.push(i);
  }
  return map;
}

function nearest(xs, value) {
  let lo = 0;
  let hi = xs.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (xs[mid] < value) lo = mid + 1;
    else hi = mid;
  }
  if (lo > 0 && Math.abs(xs[lo - 1] - value) <= Math.abs(xs[lo] - value)) return lo - 1;
  return lo;
}

function optionFor(payload, width, height) {
  const ink = css('--ink', '#1a1a1a');
  const red = css('--red', '#cc0000');
  const muted = css('--muted', '#524d48');
  const rule = css('--rule', '#e2ded9');
  const sans = css('--sans', 'system-ui, sans-serif');
  const scale = width / VIEW_W;
  const right = payload.axes.length > 1 ? 104 : 20;

  const yAxis = payload.axes.map((axis, index) => ({
    type: 'value',
    min: axis.min,
    max: axis.max,
    interval: axis.interval,
    position: index === 0 ? 'left' : 'right',
    name: axis.unit,
    nameLocation: 'end',
    nameGap: 8 * scale,
    nameTextStyle: {
      color: muted,
      fontFamily: sans,
      fontSize: 11,
      align: index === 0 ? 'right' : 'left',
    },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: {
      show: index === 0,
      lineStyle: { color: rule, width: 1 },
    },
    axisLabel: {
      color: muted,
      fontFamily: sans,
      fontSize: 11,
      customValues: axis.ticks.map((tick) => tick.value),
      formatter: (value) => tickText(axis.ticks, value),
    },
  }));

  const xAxis = {
    type: 'value',
    min: payload.x_min,
    max: payload.x_max,
    boundaryGap: false,
    axisLine: { show: true, lineStyle: { color: rule, width: 1 } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: {
      color: muted,
      fontFamily: sans,
      fontSize: 11,
      hideOverlap: true,
      customValues: payload.x_ticks.map((tick) => tick.x),
      formatter: (value) => xText(payload.x_ticks, value),
    },
  };

  const many = payload.x.length > 200;
  const series = payload.series.map((entry, index) => ({
    type: 'line',
    name: entry.title,
    data: dataFor(payload, index),
    yAxisIndex: index < payload.axes.length ? index : 0,
    connectNulls: payload.kind === 'line',
    showSymbol: true,
    symbol: 'circle',
    symbolSize: many ? 3 : 6,
    lineStyle: {
      color: index === 0 ? ink : red,
      width: 1.6,
      type: index === 0 ? 'solid' : 'dashed',
    },
    itemStyle: { color: index === 0 ? ink : red },
    emphasis: { focus: 'none' },
    animation: false,
  }));

  const map = indexMap(payload);
  const formatter = (params) => {
    if (!params || !params.length) return '';
    const point = map[params[0].dataIndex];
    if (point === undefined || point < 0) return '';
    const lines = [];
    if (payload.series[0].badge) lines.push(payload.series[0].badge);
    lines.push(payload.periods[point]);
    for (let i = 0; i < payload.series.length; i += 1) {
      lines.push(payload.series[i].title + ': ' + payload.display[point][i]);
    }
    return lines.join('\n');
  };

  return {
    animation: false,
    grid: {
      left: 68 * scale,
      right: right * scale,
      top: 18 * scale,
      bottom: 44 * scale,
      containLabel: false,
    },
    xAxis,
    yAxis,
    series,
    tooltip: {
      trigger: 'axis',
      renderMode: 'richText',
      confine: true,
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: rule,
      borderWidth: 1,
      padding: [6, 8],
      textStyle: { color: ink, fontFamily: sans, fontSize: 12, lineHeight: 18 },
      axisPointer: {
        type: 'line',
        lineStyle: { color: rule, width: 1 },
        label: { show: false },
      },
      formatter,
    },
  };
}

function readoutText(payload, point) {
  const period = payload.periods[point];
  if (payload.series.length === 1) return period + ': ' + payload.display[point][0];
  const parts = [];
  for (let i = 0; i < payload.series.length; i += 1) {
    parts.push(payload.series[i].title + ': ' + payload.display[point][i]);
  }
  return period + ' - ' + parts.join('; ');
}

function enhance(root) {
  const data = root.querySelector('script.chart-data');
  const stage = root.querySelector('.chart-canvas');
  const range = root.querySelector('.chart-range');
  const readout = root.querySelector('.chart-readout');
  const live = root.querySelector('.chart-live');
  const hint = root.querySelector('.chart-hint');
  if (!data || !stage || !range || !readout || !live) return;

  let payload;
  try {
    payload = JSON.parse(data.textContent);
  } catch (error) {
    return;
  }
  if (!valid(payload)) return;

  const width = stage.clientWidth;
  const height = stage.clientHeight;
  if (!width || !height) return;

  let chart;
  try {
    chart = init(stage, null, { renderer: 'canvas', width, height });
    chart.setOption(optionFor(payload, width, height), true);
  } catch (error) {
    if (chart) {
      try { chart.dispose(); } catch (ignored) { /* fallback stays usable */ }
    }
    stage.textContent = '';
    return;
  }

  const xs = payload.x;
  const map = indexMap(payload);
  let current = xs.length - 1;

  function show(point, announce) {
    current = point;
    range.value = String(point);
    range.setAttribute('aria-valuetext', payload.periods[point]);
    readout.textContent = readoutText(payload, point);
    if (announce) {
      live.textContent = readout.textContent;
      try {
        chart.dispatchAction({ type: 'showTip', seriesIndex: 0,
                               dataIndex: dataIndex(point) });
      } catch (ignored) { /* the readout is already correct */ }
    }
  }

  function dataIndex(point) {
    for (let i = 0; i < map.length; i += 1) {
      if (map[i] === point) return i;
    }
    return point;
  }

  if (width && height) {
    root.classList.add('chart-enhanced');
    if (xs.length > 1) {
      range.hidden = false;
      range.max = String(xs.length - 1);
    } else {
      range.hidden = true;
    }
    if (hint) hint.hidden = false;
    show(xs.length - 1, false);
  }

  chart.on('updateAxisPointer', (event) => {
    const info = event.axesInfo && event.axesInfo[0];
    if (!info || !finite(info.value)) return;
    show(nearest(xs, info.value), false);
  });

  // Native pointer/touch selection keeps the persistent readout in step even when the
  // library's axis-pointer event does not fire for a synthetic or touch event.
  const locate = (event) => {
    const rect = stage.getBoundingClientRect();
    const px = event.clientX - rect.left;
    const py = event.clientY - rect.top;
    if (px < 0 || py < 0 || px > rect.width || py > rect.height) return;
    let value;
    try {
      const converted = chart.convertFromPixel({ xAxisIndex: 0 }, [px, py]);
      value = Array.isArray(converted) ? converted[0] : converted;
    } catch (ignored) {
      return;
    }
    if (!finite(value)) return;
    show(nearest(xs, value), false);
  };
  // Capture phase: zrender may stop propagation at the canvas, and the readout must still
  // follow the same pointer/touch position the tooltip uses.
  stage.addEventListener('pointermove', locate, true);
  stage.addEventListener('pointerdown', locate, true);

  range.addEventListener('input', () => show(Number(range.value), true));
  range.addEventListener('focus', () => {
    live.textContent = readoutText(payload, current);
  });

  const onResize = () => {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    if (!w || !h) return;
    chart.resize({ width: w, height: h });
    chart.setOption({ grid: optionFor(payload, w, h).grid });
  };
  if (window.ResizeObserver) {
    const observer = new ResizeObserver(onResize);
    observer.observe(stage);
  }
}

function start() {
  const roots = document.querySelectorAll('[data-chart]');
  for (let i = 0; i < roots.length; i += 1) enhance(roots[i]);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}
