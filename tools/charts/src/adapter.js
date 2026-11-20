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

function validBreaks(breaks, length) {
  if (!Array.isArray(breaks)) return false;
  let previous = -1;
  for (let i = 0; i < breaks.length; i += 1) {
    const value = breaks[i];
    if (!Number.isInteger(value) || value < 0 || value >= length) return false;
    if (value <= previous) return false;
    previous = value;
  }
  return true;
}

function validTicks(ticks) {
  if (!Array.isArray(ticks) || !ticks.length) return false;
  for (let i = 0; i < ticks.length; i += 1) {
    const tick = ticks[i];
    if (!tick || !finite(tick.x) || typeof tick.text !== 'string') return false;
  }
  return true;
}

function validAxis(axis) {
  if (!axis || typeof axis !== 'object' || typeof axis.unit !== 'string') return false;
  if (!finite(axis.min) || !finite(axis.max) || !finite(axis.interval)) return false;
  if (!Array.isArray(axis.ticks) || !axis.ticks.length) return false;
  for (let i = 0; i < axis.ticks.length; i += 1) {
    const tick = axis.ticks[i];
    if (!tick || !finite(tick.value) || typeof tick.text !== 'string') return false;
  }
  return true;
}

function validV1(payload) {
  if (!Array.isArray(payload.x) || !Array.isArray(payload.periods)) return false;
  if (!Array.isArray(payload.y) || !Array.isArray(payload.display)) return false;
  if (!Array.isArray(payload.series) || !Array.isArray(payload.axes)) return false;
  if (!payload.series.length || !payload.axes.length) return false;
  // A pair may use at most two scales; a country group declares exactly one shared axis.
  if (payload.axes.length > 2) return false;
  if (payload.kind === 'group' && payload.axes.length !== 1) return false;
  if (payload.x.length !== payload.periods.length || payload.x.length !== payload.y.length) {
    return false;
  }
  if (!payload.x.length || !validTicks(payload.x_ticks)) return false;
  for (let i = 0; i < payload.axes.length; i += 1) {
    if (!validAxis(payload.axes[i])) return false;
  }
  for (let i = 0; i < payload.series.length; i += 1) {
    const entry = payload.series[i];
    if (!entry || typeof entry.title !== 'string' || typeof entry.style !== 'string') return false;
    if (entry.axis !== undefined
        && (!Number.isInteger(entry.axis) || entry.axis < 0 || entry.axis >= payload.axes.length)) {
      return false;
    }
  }
  if (payload.breaks !== undefined && !validBreaks(payload.breaks, payload.x.length)) return false;
  if (!Array.isArray(payload.display) || payload.display.length !== payload.x.length) return false;
  for (let i = 0; i < payload.x.length; i += 1) {
    if (!finite(payload.x[i])) return false;
    if (!Array.isArray(payload.y[i]) || payload.y[i].length !== payload.series.length) return false;
    if (!payload.y[i].every(finite)) return false;
    if (!Array.isArray(payload.display[i])
        || payload.display[i].length !== payload.series.length) return false;
    if (!payload.display[i].every((value) => typeof value === 'string')) return false;
  }
  return finite(payload.x_min) && finite(payload.x_max);
}

function validV2(payload) {
  // Version 2 is reserved for the sparse calendar. Anything else keeps the SVG fallback.
  if (payload.kind !== 'calendar') return false;
  if (!Array.isArray(payload.x) || !payload.x.length) return false;
  if (!Array.isArray(payload.periods) || payload.periods.length !== payload.x.length) return false;
  if (!Array.isArray(payload.y) || payload.y.length !== payload.x.length) return false;
  if (!Array.isArray(payload.display) || payload.display.length !== payload.x.length) return false;
  if (!Array.isArray(payload.cell_periods) || payload.cell_periods.length !== payload.x.length) {
    return false;
  }
  if (!Array.isArray(payload.series) || !payload.series.length) return false;
  if (!Array.isArray(payload.axes) || !payload.axes.length || payload.axes.length > 2) return false;
  if (typeof payload.missing !== 'string' || !payload.missing) return false;
  if (!validTicks(payload.x_ticks)) return false;
  if (!finite(payload.x_min) || !finite(payload.x_max) || payload.x_min >= payload.x_max) {
    return false;
  }

  let previous = null;
  for (let i = 0; i < payload.x.length; i += 1) {
    if (!Number.isInteger(payload.x[i])) return false;
    if (previous !== null && payload.x[i] <= previous) return false;
    previous = payload.x[i];
    if (typeof payload.periods[i] !== 'string') return false;
  }
  if (payload.x_min > payload.x[0] || payload.x_max < payload.x[payload.x.length - 1]) {
    return false;
  }

  for (let i = 0; i < payload.axes.length; i += 1) {
    if (!validAxis(payload.axes[i])) return false;
  }
  for (let i = 0; i < payload.series.length; i += 1) {
    const entry = payload.series[i];
    if (!entry || typeof entry !== 'object') return false;
    if (typeof entry.title !== 'string' || typeof entry.unit !== 'string') return false;
    if (typeof entry.style !== 'string' || typeof entry.badge !== 'string') return false;
    if (typeof entry.frequency !== 'string' || !entry.frequency) return false;
    if (!Number.isInteger(entry.axis) || entry.axis < 0 || entry.axis >= payload.axes.length) {
      return false;
    }
    if (!validBreaks(entry.breaks, payload.x.length)) return false;
  }

  for (let i = 0; i < payload.x.length; i += 1) {
    if (!Array.isArray(payload.y[i]) || payload.y[i].length !== payload.series.length) return false;
    if (!Array.isArray(payload.display[i])
        || payload.display[i].length !== payload.series.length) return false;
    if (!Array.isArray(payload.cell_periods[i])
        || payload.cell_periods[i].length !== payload.series.length) return false;
    let present = 0;
    for (let side = 0; side < payload.series.length; side += 1) {
      const value = payload.y[i][side];
      const display = payload.display[i][side];
      const period = payload.cell_periods[i][side];
      if (value === null) {
        // All three columns are one observation: a null side is never half-present.
        if (display !== null || period !== null) return false;
        continue;
      }
      if (!finite(value)) return false;
      if (typeof display !== 'string' || typeof period !== 'string') return false;
      present += 1;
    }
    if (!present) return false;
  }
  return true;
}

function valid(payload) {
  if (!payload || typeof payload !== 'object') return false;
  if (payload.version === 1) return validV1(payload);
  if (payload.version === 2) return validV2(payload);
  return false;
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

function seriesData(payload, seriesIndex) {
  // A sparse side skips its own null cells entirely. Other frequencies' rows are not gaps in
  // this line; only the side's own `breaks` insert a null sentinel so ECharts does not join
  // across a missing native period. Version 1 keeps its shared row/sentinel contract.
  const calendar = payload.version === 2;
  const breaks = new Set(calendar ? payload.series[seriesIndex].breaks : (payload.breaks || []));
  const data = [];
  const map = [];
  for (let i = 0; i < payload.x.length; i += 1) {
    if (calendar && payload.y[i][seriesIndex] === null) continue;
    if (breaks.has(i)) {
      data.push(null);
      map.push(-1);
    }
    data.push([payload.x[i], payload.y[i][seriesIndex]]);
    map.push(i);
  }
  return { data, map };
}

function dataFor(payload, seriesIndex) {
  return seriesData(payload, seriesIndex).data;
}

function indexMap(payload, seriesIndex) {
  return seriesData(payload, seriesIndex).map;
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

/* One reader row per series. Version 2 names that side's own native period; a null side gets
 * the server's explicit missing string, never the previous value, "null" or "undefined". */
function seriesLine(payload, point, index) {
  if (payload.version === 2) {
    const period = payload.cell_periods[point][index];
    const display = payload.display[point][index];
    if (period === null || display === null) {
      return payload.series[index].title + ' - ' + payload.missing;
    }
    return payload.series[index].title + ' - ' + period + ': ' + display;
  }
  return payload.series[index].title + ': ' + payload.display[point][index];
}

/* One block per line, filled with textContent so a publisher title can never become markup.
 * The browser wraps the text inside the box; values keep their U+00A0 thousands groups. */
function tooltipNode(payload, point) {
  const box = document.createElement('div');
  const lines = [];
  if (payload.series[0].badge) lines.push(payload.series[0].badge);
  lines.push(payload.periods[point]);
  for (let i = 0; i < payload.series.length; i += 1) {
    lines.push(seriesLine(payload, point, i));
  }
  for (let i = 0; i < lines.length; i += 1) {
    const row = document.createElement('div');
    row.className = 'chart-tip-line';
    row.textContent = lines[i];
    box.appendChild(row);
  }
  return box;
}

function optionFor(payload, width, activePoint) {
  const ink = css('--ink', '#1a1a1a');
  const red = css('--red', '#c0392b');
  const muted = css('--muted', '#524d48');
  const rule = css('--rule', '#e2ded9');
  const sans = css('--sans', 'system-ui, sans-serif');
  const seriesStyles = {
    ink: { color: ink, type: 'solid' },
    red: { color: red, type: 'dashed' },
    a: { color: ink, type: 'solid' },
    b: { color: red, type: 'dashed' },
    g0: { color: css('--accent', '#9b1c2e'), type: 'solid' },
    g1: { color: css('--chart-series-2', '#2f5d8a'), type: [6, 3] },
    g2: { color: css('--chart-series-3', '#8a5a00'), type: [2, 3] },
    g3: { color: css('--chart-series-4', '#2e7d32'), type: [8, 3, 2, 3] },
    g4: { color: css('--chart-series-5', '#6b3fa0'), type: [12, 4] },
    g5: { color: css('--chart-series-6', '#0b6b6b'), type: [1, 4] },
  };
  const scale = width / VIEW_W;
  const right = payload.axes.length > 1 ? 172 : 33;
  // The axis name and gap are fixed CSS pixels, so the top gutter cannot keep shrinking with
  // the stage. At 320/480px the scaled 31/13 values would put the 19.8px unit name above the
  // canvas. The floor preserves the designed gutter from the full 880px view.
  const top = Math.max(31 * scale, 31);
  const nameGap = Math.max(13 * scale, 13);

  const yAxis = payload.axes.map((axis, index) => ({
    type: 'value',
    min: axis.min,
    max: axis.max,
    interval: axis.interval,
    position: index === 0 ? 'left' : 'right',
    name: axis.unit,
    nameLocation: 'end',
    nameGap,
    nameTextStyle: {
      color: muted,
      fontFamily: sans,
      fontSize: 19.8,
      // Both names end on their axis. A name that starts at the right axis has to fit inside
      // `grid.right`, and ECharts 6 shrinks the whole plot when it cannot: at 390px the long
      // "milhões de euros" would take a quarter of the canvas and move every point under the
      // cursor. Ending the name at the axis keeps the plot at its designed width.
      align: 'right',
    },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: {
      show: index === 0,
      lineStyle: { color: rule, width: 1.35 },
    },
    axisLabel: {
      color: muted,
      fontFamily: sans,
      fontSize: 18.15,
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
      fontSize: 18.15,
      hideOverlap: true,
      customValues: payload.x_ticks.map((tick) => tick.x),
      formatter: (value) => xText(payload.x_ticks, value),
    },
  };

  const many = payload.x.length > 200;
  const series = payload.series.map((entry, index) => {
    const style = seriesStyles[entry.style] || seriesStyles.ink;
    // A pair infers its axis from the series order; a group declares axis 0 explicitly.
    const axis = Number.isInteger(entry.axis) ? entry.axis
      : (index < payload.axes.length ? index : 0);
    return {
      type: 'line',
      name: entry.title,
      data: dataFor(payload, index),
      yAxisIndex: axis,
      connectNulls: payload.kind === 'line',
      showSymbol: true,
      symbol: 'circle',
      symbolSize: many ? 3 : 6,
      lineStyle: {
        color: style.color,
        width: 2.2,
        type: style.type,
      },
      itemStyle: { color: style.color },
      emphasis: { focus: 'none' },
      animation: false,
    };
  });

  const maps = payload.series.map((entry, index) => indexMap(payload, index));
  const formatter = (params) => {
    // The readout snaps to a union row before ECharts renders the tooltip. Prefer that same
    // row: at the extreme plot edges ECharts can pass empty or edge-clamped params, and a
    // touch must never open a tooltip for a different period than the live readout.
    let point = activePoint();
    if (point === undefined || point < 0) {
      const first = params && params.length ? params[0] : null;
      if (first) {
        // Version 2 data indices differ per side because each side skips its own null cells.
        const seriesIndex = Number.isInteger(first.seriesIndex) ? first.seriesIndex : 0;
        const map = maps[seriesIndex] || maps[0];
        if (map) point = map[first.dataIndex];
      }
    }
    if (point === undefined || point < 0) return '';
    return tooltipNode(payload, point);
  };

  return {
    animation: false,
    grid: {
      left: 97 * scale,
      right: right * scale,
      top,
      bottom: 68 * scale,
      containLabel: true,
    },
    xAxis,
    yAxis,
    series,
    tooltip: {
      trigger: 'axis',
      renderMode: 'html',
      className: 'chart-tooltip',
      confine: true,
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: rule,
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: ink, fontFamily: sans, fontSize: 19.8, lineHeight: 29.7 },
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
  if (payload.version === 2) {
    const parts = [];
    for (let i = 0; i < payload.series.length; i += 1) {
      parts.push(seriesLine(payload, point, i));
    }
    return period + ' - ' + parts.join('; ');
  }
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
  let activePoint = payload.x.length - 1;
  try {
    chart = init(stage, null, { renderer: 'canvas', width, height });
    chart.setOption(optionFor(payload, width, () => activePoint), true);
  } catch (error) {
    if (chart) {
      try { chart.dispose(); } catch (ignored) { /* fallback stays usable */ }
    }
    stage.textContent = '';
    return;
  }

  const xs = payload.x;
  const low = Math.min(xs[0], xs[xs.length - 1]);
  const high = Math.max(xs[0], xs[xs.length - 1]);
  let current = xs.length - 1;

  function showTip(point) {
    try {
      // Axis-trigger tooltips are positioned by a canvas coordinate, not by dataIndex.
      // dataIndex works for item trigger only; using it here left the visible tooltip on the
      // previous period after a touch at the other end of the plot.
      const x = chart.convertToPixel({ xAxisIndex: 0 }, payload.x[point]);
      if (!finite(x)) return;
      chart.dispatchAction({ type: 'hideTip' });
      chart.dispatchAction({ type: 'showTip', x, y: chart.getHeight() / 2 });
    } catch (ignored) { /* the readout is already correct */ }
  }

  function show(point, announce) {
    current = point;
    activePoint = point;
    range.value = String(point);
    range.setAttribute('aria-valuetext', payload.periods[point]);
    readout.textContent = readoutText(payload, point);
    if (announce) {
      live.textContent = readout.textContent;
      showTip(point);
    }
  }

  root.classList.add('chart-enhanced');
  if (xs.length > 1) {
    range.hidden = false;
    range.max = String(xs.length - 1);
  } else {
    range.hidden = true;
  }
  // The hint explains arrow-key stepping, which only exists with more than one period.
  if (hint) hint.hidden = xs.length < 2;
  show(xs.length - 1, false);

  chart.on('updateAxisPointer', (event) => {
    const info = event.axesInfo && event.axesInfo[0];
    if (!info || !finite(info.value)) return;
    show(nearest(xs, info.value), false);
  });

  // The readout follows the same cartesian conversion the series are drawn with. The finder
  // must name the grid (or both axes): `{xAxisIndex}` alone resolves to the x axis and then
  // `toLocalCoord` receives a point where it expects one scalar, yielding NaN. Clamping to the
  // data domain keeps the first and last period reachable at the plot edges and makes the
  // padding around the plot select that edge instead of a stale period.
  const locate = (event) => {
    const rect = stage.getBoundingClientRect();
    const px = event.clientX - rect.left;
    const py = event.clientY - rect.top;
    if (px < 0 || py < 0 || px > rect.width || py > rect.height) return;
    let value;
    try {
      const converted = chart.convertFromPixel({ gridIndex: 0 }, [px, py]);
      value = Array.isArray(converted) ? converted[0] : converted;
    } catch (ignored) {
      return;
    }
    if (!finite(value)) return;
    show(nearest(xs, Math.min(Math.max(value, low), high)), false);
  };

  // Capture phase: zrender may stop propagation at the canvas, and the readout must still
  // follow the same pointer/touch position the tooltip uses. A touch only selects on release
  // and only when it did not turn into a scroll, so panning the page over the chart stays inert.
  let touchStart = null;
  stage.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'touch') locate(event);
  }, true);
  stage.addEventListener('pointerdown', (event) => {
    if (event.pointerType === 'touch') {
      touchStart = [event.clientX, event.clientY];
    } else {
      locate(event);
    }
  }, true);
  stage.addEventListener('pointerup', (event) => {
    if (event.pointerType !== 'touch') return;
    const start = touchStart;
    touchStart = null;
    if (!start) return;
    if (Math.abs(event.clientX - start[0]) > 10 || Math.abs(event.clientY - start[1]) > 10) return;
    locate(event);
    showTip(current);
  }, true);
  stage.addEventListener('pointercancel', () => { touchStart = null; }, true);
  stage.addEventListener('pointerleave', () => {
    try { chart.dispatchAction({ type: 'hideTip' }); } catch (ignored) { /* nothing shown */ }
  }, true);

  range.addEventListener('input', () => show(Number(range.value), true));
  range.addEventListener('focus', () => {
    live.textContent = readoutText(payload, current);
  });

  const onResize = () => {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    if (!w || !h) return;
    chart.resize({ width: w, height: h });
    chart.setOption({ grid: optionFor(payload, w, () => activePoint).grid });
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
