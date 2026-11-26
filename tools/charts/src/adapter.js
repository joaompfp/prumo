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

/* Inspection presentation policy. A floating tooltip can cover the plot on a narrow phone and
 * is redundant beside the persistent in-flow readout there. Input capability and the page
 * viewport decide, never one inline chart's own width: a narrow chart inside a wide desktop
 * page keeps the desktop tooltip. Coarse pointers keep the readout even in landscape, where
 * the viewport is wide. */
const FLOATING_QUERY = '(min-width: 600px) and (hover: hover) and (pointer: fine)';

function css(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function finite(value) {
  return typeof value === 'number' && isFinite(value);
}

let measure = null;
function textWidth(text, size, family) {
  if (!measure) measure = document.createElement('canvas').getContext('2d');
  measure.font = size + 'px ' + family;
  return measure.measureText(text).width;
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
  // A chart may use at most two scales: the left and right axes.
  if (payload.axes.length > 2) return false;
  if (payload.x.length !== payload.periods.length || payload.x.length !== payload.y.length) {
    return false;
  }
  if (!payload.x.length || !validTicks(payload.x_ticks)) return false;
  for (let i = 0; i < payload.axes.length; i += 1) {
    if (!validAxis(payload.axes[i])) return false;
  }
  const usedAxes = new Set();
  for (let i = 0; i < payload.series.length; i += 1) {
    const entry = payload.series[i];
    if (!entry || typeof entry.title !== 'string' || typeof entry.style !== 'string') return false;
    let axis;
    if (entry.axis === undefined) {
      // Legacy line/pair payloads predate the explicit field. Only those one-or-two-series
      // consumers may keep their positional contract; every grouped payload declares `axis`.
      if (payload.kind === 'group' || payload.series.length > 2) return false;
      axis = i < payload.axes.length ? i : 0;
    } else {
      axis = entry.axis;
    }
    if (!Number.isInteger(axis) || axis < 0 || axis >= payload.axes.length) return false;
    usedAxes.add(axis);
  }
  // Every declared axis must own at least one series; no empty axis group.
  if (usedAxes.size !== payload.axes.length) return false;
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
  const usedAxes = new Set();
  for (let i = 0; i < payload.series.length; i += 1) {
    const entry = payload.series[i];
    if (!entry || typeof entry !== 'object') return false;
    if (typeof entry.title !== 'string' || typeof entry.unit !== 'string') return false;
    if (typeof entry.style !== 'string' || typeof entry.badge !== 'string') return false;
    if (typeof entry.frequency !== 'string' || !entry.frequency) return false;
    if (!Number.isInteger(entry.axis) || entry.axis < 0 || entry.axis >= payload.axes.length) {
      return false;
    }
    usedAxes.add(entry.axis);
    if (!validBreaks(entry.breaks, payload.x.length)) return false;
  }
  // Every declared axis must own at least one side; no empty axis group.
  if (usedAxes.size !== payload.axes.length) return false;

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

/* The prepared reader view of one inspected point. Tooltip text, the visible readout and the
 * polite announcement all come from this single boundary, so they cannot describe different
 * rows. Version 2 names each side's own native period; a null side gets the server's explicit
 * missing string, never the previous value, "null" or "undefined". */
function pointView(payload, point) {
  const rows = [];
  for (let index = 0; index < payload.series.length; index += 1) {
    const entry = payload.series[index];
    const axis = Number.isInteger(entry.axis) ? entry.axis
      : (index < payload.axes.length ? index : 0);
    // Both fields are prepared by the server. The unit is never inferred from a translated
    // series label, and the style key drives the same swatch classes as the visible legend.
    const unit = typeof entry.unit === 'string' ? entry.unit
      : (payload.axes[axis] ? payload.axes[axis].unit : '');
    if (payload.version === 2) {
      const period = payload.cell_periods[point][index];
      const display = payload.display[point][index];
      rows.push({
        title: entry.title,
        period,
        value: display,
        missing: period === null || display === null,
        axis,
        style: entry.style,
        unit,
      });
    } else {
      rows.push({
        title: entry.title,
        period: null,
        value: payload.display[point][index],
        missing: false,
        axis,
        style: entry.style,
        unit,
      });
    }
  }
  return { period: payload.periods[point], rows };
}

/* The reviewed one-line row text shared by the tooltip and the announcement. */
function rowText(payload, row) {
  if (row.missing) return row.title + ' - ' + payload.missing;
  if (row.period !== null) return row.title + ' - ' + row.period + ': ' + row.value;
  return row.title + ': ' + row.value;
}

/* One block per line, filled with textContent so a publisher title can never become markup.
 * The browser wraps the text inside the box; values keep their U+00A0 thousands groups. */
function tooltipNode(payload, point) {
  const view = pointView(payload, point);
  const box = document.createElement('div');
  const lines = [];
  if (payload.series[0].badge) lines.push(payload.series[0].badge);
  lines.push(view.period);
  for (let i = 0; i < view.rows.length; i += 1) {
    lines.push(rowText(payload, view.rows[i]));
  }
  for (let i = 0; i < lines.length; i += 1) {
    const row = document.createElement('div');
    row.className = 'chart-tip-line';
    row.textContent = lines[i];
    box.appendChild(row);
  }
  return box;
}

function optionFor(payload, width, activePoint, floatingAllowed) {
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
  // Two unit names on one row collide once the left name grows into the plot. The top gutter
  // grows by one 29.7px text row and the left name follows it, so the left name keeps the top
  // row and the right name moves one row down. Both keep the 19.8px role.
  const nameStagger = payload.axes.length > 1 ? 29.7 : 0;

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
      // The left name grows into the plot from its axis; the right name still ends on its
      // axis. Ending the left name on the axis clipped it at the left edge on every narrow
      // canvas, and starting the right name at the axis would push the plot inward.
      align: index === 0 ? 'left' : 'right',
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
  if (nameStagger) yAxis[0].nameGap += nameStagger;

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
    // Grouped and calendar payloads declare axis membership explicitly. Only the legacy
    // line/pair payload without the field keeps its reviewed positional contract.
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
    // The inline presentation owns no floating content. Returning an empty tooltip keeps the
    // axis cursor on the canvas while the complete rows stay in the persistent readout below.
    if (!floatingAllowed()) return '';
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

  const grid = {
    left: 97 * scale,
    right: right * scale,
    top,
    bottom: 68 * scale,
    containLabel: true,
  };
  if (nameStagger) {
    grid.top += nameStagger;
    // ECharts anchors a right-axis name to the plot's right edge and lays it out leftwards.
    // On a 320px canvas the scaled dual gutter plus the fixed-width tick labels left less
    // room than the 19.8px name, so it started off-canvas. Give the plot edge back only the
    // room the measured name and labels need; wider canvases keep the designed gutter.
    const labelWidth = Math.max(...payload.axes[1].ticks.map(
      (tick) => textWidth(tick.text, 18.15, sans)));
    const nameWidth = textWidth(payload.axes[1].unit, 19.8, sans);
    grid.right = Math.max(0, Math.min(grid.right, width - nameWidth - labelWidth - 20));
  }

  return {
    animation: false,
    grid,
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

/* The one-line announcement text. The visible readout is structured, but the polite live
 * region keeps the reviewed sentence so keyboard users hear the period and every exact row. */
function pointText(payload, point) {
  const view = pointView(payload, point);
  if (payload.version === 2) {
    return view.period + ' - ' + view.rows.map((row) => rowText(payload, row)).join('; ');
  }
  if (view.rows.length === 1) return view.period + ': ' + view.rows[0].value;
  return view.period + ' - ' + view.rows.map((row) => rowText(payload, row)).join('; ');
}

function appendSpan(parent, className, text) {
  const node = document.createElement('span');
  node.className = className;
  node.textContent = text;
  parent.appendChild(node);
  return node;
}

/* Structured visible readout: the period on its own line, then one row per series.
 *
 * The hidden separator spans keep `output.textContent` byte-identical to the reviewed
 * one-line sentence existing consumers already inspect. They are display:none in
 * chart-inspector.css, so the visible structure is rows while exact strings and the live
 * announcement stay unchanged. Values are inserted with textContent, never markup. */
function renderReadout(readout, payload, point) {
  const view = pointView(payload, point);
  while (readout.firstChild) readout.removeChild(readout.firstChild);
  appendSpan(readout, 'chart-readout-period', view.period);
  const multi = payload.version === 2 || view.rows.length > 1;
  appendSpan(readout, 'chart-readout-sep', multi ? ' - ' : ': ');
  for (let index = 0; index < view.rows.length; index += 1) {
    const row = view.rows[index];
    if (index) appendSpan(readout, 'chart-readout-sep', '; ');
    const line = document.createElement('span');
    line.className = 'chart-readout-row';
    line.setAttribute('data-axis', String(row.axis));
    line.setAttribute('data-unit', row.unit);
    if (row.missing) line.setAttribute('data-missing', 'true');
    if (multi) {
      if (row.style) {
        const swatch = document.createElement('span');
        swatch.className = 'legend-swatch swatch-' + row.style;
        swatch.setAttribute('aria-hidden', 'true');
        line.appendChild(swatch);
      }
      appendSpan(line, 'chart-readout-title', row.title);
      if (row.missing) {
        appendSpan(line, 'chart-readout-sep', ' - ');
        appendSpan(line, 'chart-readout-value', payload.missing);
      } else {
        if (row.period !== null) {
          appendSpan(line, 'chart-readout-sep', ' - ');
          const native = appendSpan(line, 'chart-readout-native', row.period);
          if (row.period === view.period) native.classList.add('chart-readout-native-same');
        }
        appendSpan(line, 'chart-readout-sep', ': ');
        appendSpan(line, 'chart-readout-value', row.value);
      }
    } else {
      appendSpan(line, 'chart-readout-value', row.value);
    }
    readout.appendChild(line);
  }
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

  const floatingQuery = window.matchMedia(FLOATING_QUERY);
  let touchInspection = false;
  let floating = floatingQuery.matches;
  let chart;
  let activePoint = payload.x.length - 1;
  try {
    chart = init(stage, null, { renderer: 'canvas', width, height });
    chart.setOption(optionFor(payload, width, () => activePoint, () => floating), true);
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
  // Dispatching showTip from the pointer handler keeps the visible tooltip on the same row as
  // the readout. Native axis hover does not always invoke the formatter at the final symbol:
  // the readout moved to the last period while the tooltip stayed on the previous one. Guard
  // the axis event so the action that shows the tooltip cannot feed a new point back through
  // updateAxisPointer and rewrite the row that was just chosen.
  let syncingTip = false;
  let tipTimer = 0;
  // Touch drags scroll the page. ECharts still tracks its axis cursor while a finger is down,
  // so its updateAxisPointer event must not rewrite the selected row until a real tap ends.
  let touchActive = false;
  let suppressAxisUntil = 0;

  function showTip(point) {
    if (!floating) return;
    try {
      // Axis-trigger tooltips are positioned by a canvas coordinate, not by dataIndex.
      // dataIndex works for item trigger only; using it here left the visible tooltip on the
      // previous period after a touch at the other end of the plot.
      const x = chart.convertToPixel({ xAxisIndex: 0 }, payload.x[point]);
      if (!finite(x)) return;
      // The last period converts to the plot's right edge exactly. ECharts only shows a
      // programmatic pixel point when its axis finder maps it back inside the grid, and
      // `toLocalCoord(right edge)` can land a couple of ulps past the axis extent at narrow
      // widths (390px canvas: 145.49292103160514 against 145.4929210316051). The point is
      // then treated as outside and the previous tooltip stays. Move at most one hundredth
      // of a row's pixel spacing inward: enough to clear the rounding error, far too little
      // to change the union row `nearest` selects.
      const right = chart.convertToPixel({ xAxisIndex: 0 }, payload.x_max);
      const rowPixels = chart.getWidth() / Math.max(1, payload.x.length - 1);
      const inset = Math.min(0.01, rowPixels / 100);
      const tipX = finite(right) ? Math.min(x, right - inset) : x;
      chart.dispatchAction({ type: 'hideTip' });
      chart.dispatchAction({ type: 'showTip', x: tipX, y: chart.getHeight() / 2 });
    } catch (ignored) { /* the readout is already correct */ }
  }

  function show(point, announce) {
    current = point;
    activePoint = point;
    range.value = String(point);
    range.setAttribute('aria-valuetext', payload.periods[point]);
    renderReadout(readout, payload, point);
    if (announce) {
      live.textContent = pointText(payload, point);
      showTip(point);
    }
  }

  function syncTip(point) {
    if (syncingTip || !floating) return;
    // Native pointer handling runs in the same dispatch before this deferred task. At the plot
    // edges it hides the axis tooltip even though its content was just rendered; reassert the
    // chosen point after that handler, coalescing a burst of moves into one showTip.
    if (tipTimer) clearTimeout(tipTimer);
    tipTimer = setTimeout(() => {
      tipTimer = 0;
      if (current !== point) return;
      syncingTip = true;
      try { showTip(point); } finally { syncingTip = false; }
    }, 0);
  }

  function cancelTip() {
    if (!tipTimer) return;
    clearTimeout(tipTimer);
    tipTimer = 0;
  }

  /* One policy boundary changes both the chart presentation and the layout class. Narrow,
   * coarse and resized-to-narrow transitions hide any floating tooltip but keep `current`
   * and the persistent readout untouched; widening back restores the desktop tooltip at that
   * point. The tooltip component stays enabled so its axis cursor still tracks the plot. */
  function applyPresentation(pointerType) {
    // A hybrid laptop can report a fine primary pointer while the reader touches its screen.
    // Honour that actual input until a mouse returns, without removing desktop hover support.
    if (pointerType === 'touch' || pointerType === 'pen') touchInspection = true;
    else if (pointerType === 'mouse') touchInspection = false;
    const next = floatingQuery.matches && !touchInspection;
    if (next === floating) return;
    floating = next;
    root.classList.toggle('chart-inline-readout', !floating);
    if (floating) {
      showTip(current);
    } else {
      cancelTip();
      try { chart.dispatchAction({ type: 'hideTip' }); } catch (ignored) { /* none shown */ }
    }
  }

  root.classList.add('chart-enhanced');
  root.classList.toggle('chart-inline-readout', !floating);
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
    if (syncingTip || touchActive || performance.now() < suppressAxisUntil) return;
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
    if (px < 0 || py < 0 || px > rect.width || py > rect.height) return null;
    let value;
    try {
      const converted = chart.convertFromPixel({ gridIndex: 0 }, [px, py]);
      value = Array.isArray(converted) ? converted[0] : converted;
    } catch (ignored) {
      return null;
    }
    if (!finite(value)) return null;
    const point = nearest(xs, Math.min(Math.max(value, low), high));
    show(point, false);
    return point;
  };

  // Capture phase: zrender may stop propagation at the canvas, and the readout must still
  // follow the same pointer/touch position the tooltip uses. A touch only selects on release
  // and only when it did not turn into a scroll, so panning the page over the chart stays inert.
  root.addEventListener('pointerdown', (event) => applyPresentation(event.pointerType), true);
  let touchStart = null;
  stage.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'touch') {
      applyPresentation(event.pointerType);
      const point = locate(event);
      if (point !== null) syncTip(point);
    }
  }, true);
  stage.addEventListener('pointerdown', (event) => {
    if (event.pointerType === 'touch') {
      touchStart = [event.clientX, event.clientY];
      touchActive = true;
    } else {
      const point = locate(event);
      if (point !== null) syncTip(point);
    }
  }, true);
  stage.addEventListener('pointerup', (event) => {
    if (event.pointerType !== 'touch') return;
    const start = touchStart;
    touchStart = null;
    touchActive = false;
    if (!start) return;
    if (Math.abs(event.clientX - start[0]) > 10 || Math.abs(event.clientY - start[1]) > 10) {
      // Let the axis cursor settle without letting the drag's final position select a row.
      suppressAxisUntil = performance.now() + 150;
      return;
    }
    locate(event);
    showTip(current);
  }, true);
  stage.addEventListener('pointercancel', () => {
    touchStart = null;
    suppressAxisUntil = performance.now() + 300;
  }, true);
  // A scroll gesture cancels the pointer stream, but ECharts keeps handling the raw touch
  // stream. Track that touch until it ends so axis moves cannot select during the drag.
  stage.addEventListener('touchstart', () => {
    touchActive = true;
    suppressAxisUntil = performance.now() + 300;
  }, { capture: true, passive: true });
  stage.addEventListener('touchmove', () => {
    suppressAxisUntil = performance.now() + 300;
  }, { capture: true, passive: true });
  stage.addEventListener('touchend', () => {
    touchActive = false;
    suppressAxisUntil = performance.now() + 150;
  }, { capture: true, passive: true });
  stage.addEventListener('touchcancel', () => {
    touchActive = false;
    suppressAxisUntil = performance.now() + 150;
  }, { capture: true, passive: true });
  stage.addEventListener('pointerleave', () => {
    cancelTip();
    try { chart.dispatchAction({ type: 'hideTip' }); } catch (ignored) { /* nothing shown */ }
  }, true);

  range.addEventListener('input', () => show(Number(range.value), true));
  range.addEventListener('focus', () => {
    live.textContent = pointText(payload, current);
  });

  const onResize = () => {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    if (!w || !h) return;
    chart.resize({ width: w, height: h });
    chart.setOption({ grid: optionFor(payload, w, () => activePoint, () => floating).grid });
    // A media-query change can arrive before the resize observer. Reconcile both here, using
    // the already-resized plot if the presentation changes.
    applyPresentation();
  };
  if (window.ResizeObserver) {
    const observer = new ResizeObserver(onResize);
    observer.observe(stage);
  }
  if (floatingQuery.addEventListener) {
    floatingQuery.addEventListener('change', applyPresentation);
  } else if (floatingQuery.addListener) {
    floatingQuery.addListener(applyPresentation);
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
