/**
 * CAE Dashboard — Embed Script (M6)
 * Self-contained IIFE. Drop into any page with:
 *   <script src="https://joao.date/dados/embed.js" data-base="https://joao.date/dados"></script>
 * Then use <div class="cae-embed" data-indicators="SOURCE/indicator" ...></div>
 */
(function () {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* Config                                                               */
  /* ------------------------------------------------------------------ */
  const CAE_BASE =
    (document.currentScript && document.currentScript.dataset.base) ||
    'https://joao.date/dados';

  const FETCH_TIMEOUT_MS = 8000;

  /* SWD colour palette — inline, no dependency on swd-charts.js */
  const COLORS = {
    primary:  '#CC0000',
    positive: '#2E7D32',
    negative: '#CC0000',
    neutral:  '#555555',
    series:   ['#CC0000', '#4A90D9', '#2E7D32', '#E67E22', '#9B59B6', '#00838F'],
  };

  /* ------------------------------------------------------------------ */
  /* Utilities                                                            */
  /* ------------------------------------------------------------------ */

  /** Load ECharts from CDN if not already present. */
  function loadECharts(cb) {
    if (window.echarts) return cb();
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js';
    s.onload = cb;
    s.onerror = function () {
      console.error('[cae-embed] Failed to load ECharts from CDN');
    };
    document.head.appendChild(s);
  }

  /** Fetch with a hard timeout. Returns a Promise<Response>. */
  function fetchWithTimeout(url, opts) {
    opts = opts || {};
    return new Promise(function (resolve, reject) {
      const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timer = setTimeout(function () {
        if (ctrl) ctrl.abort();
        reject(new Error('timeout'));
      }, FETCH_TIMEOUT_MS);

      fetch(url, ctrl ? Object.assign({}, opts, { signal: ctrl.signal }) : opts)
        .then(function (r) { clearTimeout(timer); resolve(r); })
        .catch(function (e) { clearTimeout(timer); reject(e); });
    });
  }

  /** Parse "SOURCE/indicator" into { source, indicator }. */
  function parseIndicator(str) {
    const idx = str.indexOf('/');
    if (idx < 0) return { source: '', indicator: str.trim() };
    return {
      source:    str.slice(0, idx).trim(),
      indicator: str.slice(idx + 1).trim(),
    };
  }

  /* ------------------------------------------------------------------ */
  /* Data fetching                                                        */
  /* ------------------------------------------------------------------ */

  /**
   * Fetch a single series (no countries).
   * GET /api/series?source=&indicator=&from=&to=
   */
  function fetchSeries(source, indicator, from, to) {
    let url = CAE_BASE + '/api/series?source=' + encodeURIComponent(source) +
              '&indicator=' + encodeURIComponent(indicator);
    if (from) url += '&from=' + encodeURIComponent(from);
    if (to)   url += '&to='   + encodeURIComponent(to);

    return fetchWithTimeout(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
  }

  /**
   * Fetch compare mode (multiple countries for one indicator).
   * GET /api/compare?indicator=&source=&countries=&since=
   */
  function fetchCompare(source, indicator, countries, since) {
    let url = CAE_BASE + '/api/compare?indicator=' + encodeURIComponent(indicator) +
              '&source=' + encodeURIComponent(source) +
              '&countries=' + encodeURIComponent(countries);
    if (since) url += '&since=' + encodeURIComponent(since);

    return fetchWithTimeout(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
  }

  /* ------------------------------------------------------------------ */
  /* Analytics                                                            */
  /* ------------------------------------------------------------------ */

  function trackEmbed(indicatorsStr) {
    fetch(CAE_BASE + '/api/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event:      'embed_load',
        host:       window.location.hostname,
        path:       window.location.pathname,
        indicators: indicatorsStr,
      }),
    }).catch(function () {}); /* silencioso */
  }

  /* ------------------------------------------------------------------ */
  /* Rendering                                                            */
  /* ------------------------------------------------------------------ */

  /** Build attribution HTML below chart. */
  function buildAttribution(indicatorsStr) {
    const explorerHash = 'explorador?s=' + encodeURIComponent(indicatorsStr);
    const div = document.createElement('div');
    div.style.cssText = 'text-align:right;font-size:11px;color:#888;margin-top:4px;font-family:sans-serif';
    div.innerHTML =
      'Dados: <a href="' + CAE_BASE + '#' + explorerHash +
      '" target="_blank" rel="noopener" style="color:#CC0000;text-decoration:none">CAE Dashboard ↗</a>';
    return div;
  }

  /** Show an error fallback inside the container div. */
  function showError(container, height) {
    container.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;' +
      'height:' + height + 'px;background:#f9f9f9;border:1px solid #eee;' +
      'border-radius:4px;color:#888;font-size:13px;font-family:sans-serif">' +
      'Dados indisponíveis — ' +
      '<a href="' + CAE_BASE + '" target="_blank" rel="noopener" ' +
      'style="color:#CC0000;margin-left:4px;text-decoration:none">ver no dashboard ↗</a>' +
      '</div>';
  }

  /**
   * Convert raw API response into { periods: string[], series: [{name, data}] }.
   * Handles both series and compare response shapes from the CAE API.
   */
  function normaliseData(raw, mode) {
    /* Compare mode: API returns { series: [{country, label, data: [{period, value}]}], ... } */
    if (mode === 'compare') {
      if (raw.series && Array.isArray(raw.series) && raw.series.length) {
        var periods = raw.series[0].data.map(function (d) { return d.period; });
        var series = raw.series.map(function (s) {
          return { name: s.label || s.country, data: s.data.map(function (d) { return d.value; }) };
        });
        return { periods: periods, series: series };
      }
      return null;
    }

    /* Series mode: API returns [{source, indicator, label, unit, data: [{period, value}]}] */
    /* Unwrap array if needed */
    if (Array.isArray(raw)) raw = raw[0];
    if (!raw) return null;

    if (raw.data && Array.isArray(raw.data)) {
      return {
        periods: raw.data.map(function (d) { return d.period || d.date || ''; }),
        series:  [{ name: raw.label || raw.indicator || 'Série',
                    data: raw.data.map(function (d) { return d.value; }) }],
      };
    }

    return null;
  }

  /** Render ECharts line chart into chartEl. */
  function renderChart(chartEl, normalised, title) {
    const chart = window.echarts.init(chartEl);

    const option = {
      animation: false,
      grid:  { top: title ? 48 : 20, right: 20, bottom: 40, left: 55, containLabel: false },
      xAxis: {
        type: 'category',
        data: normalised.periods,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { fontSize: 10, color: '#666', fontFamily: 'Inter, system-ui, sans-serif', hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#F0F0F0', width: 1 } },
        axisLabel: { fontSize: 10, color: '#666' },
      },
      series: normalised.series.map(function (s, i) {
        return {
          name:      s.name,
          type:      'line',
          data:      s.data,
          smooth:    false,
          symbol:    'none',
          lineStyle: { width: 2, color: COLORS.series[i % COLORS.series.length] },
          itemStyle: { color: COLORS.series[i % COLORS.series.length] },
          endLabel: normalised.series.length === 1 ? undefined : {
            show: true,
            formatter: function(p) { return s.name; },
            fontSize: 10,
            color: COLORS.series[i % COLORS.series.length],
            fontFamily: 'Inter, system-ui, sans-serif',
          },
        };
      }),
      tooltip: {
        trigger:   'axis',
        textStyle: { fontSize: 12 },
      },
    };

    if (title) {
      option.title = { text: title, textStyle: { fontSize: 13, color: '#333', fontWeight: 'bold' } };
    }

    if (normalised.series.length > 1) {
      option.legend = {
        bottom: 0,
        textStyle: { fontSize: 11 },
        itemWidth: 14,
        itemHeight: 10,
      };
      option.grid.bottom = 56; /* make room for legend */
    }

    chart.setOption(option);
    return chart;
  }

  /** Attach ResizeObserver to keep chart responsive. */
  function attachResize(chartEl, chart) {
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(function () { chart.resize(); });
    ro.observe(chartEl);
  }

  /* ------------------------------------------------------------------ */
  /* Main embed logic                                                     */
  /* ------------------------------------------------------------------ */

  function processEmbed(container) {
    const indicatorsStr = (container.dataset.indicators || '').trim();
    if (!indicatorsStr) {
      console.warn('[cae-embed] Missing data-indicators on', container);
      return;
    }

    const countriesStr = (container.dataset.countries || '').trim();
    const from         = (container.dataset.from  || '').trim();
    const to           = (container.dataset.to    || '').trim();
    const height       = parseInt(container.dataset.height || '400', 10);
    const title        = (container.dataset.title || '').trim();

    /* Set container height early so layout doesn't jump */
    container.style.minHeight = height + 'px';

    const indicators = indicatorsStr.split(',').map(function (s) { return s.trim(); }).filter(Boolean);

    /* Analytics — fire and forget */
    trackEmbed(indicatorsStr);

    /* Build an array of fetch promises */
    let promises;
    let mode;

    if (countriesStr) {
      /* Compare mode: one indicator + multiple countries */
      mode = 'compare';
      const parsed = parseIndicator(indicators[0]);
      promises = [fetchCompare(parsed.source, parsed.indicator, countriesStr, from)];
    } else {
      /* Series mode: one or more indicators */
      mode = 'series';
      promises = indicators.map(function (ind) {
        const parsed = parseIndicator(ind);
        return fetchSeries(parsed.source, parsed.indicator, from, to);
      });
    }

    Promise.all(promises)
      .then(function (results) {
        let normalised;

        if (mode === 'compare') {
          normalised = normaliseData(results[0], 'compare');
        } else {
          /* Merge multiple series results into one dataset */
          var allPeriods = null;
          var allSeries  = [];

          results.forEach(function (raw, i) {
            const n = normaliseData(raw, 'series');
            if (!n) return;
            if (!allPeriods) allPeriods = n.periods;
            n.series.forEach(function (s) {
              /* Use indicator as name if label is generic */
              if (s.name === 'Série' && indicators[i]) {
                s.name = parseIndicator(indicators[i]).indicator.replace(/_/g, ' ');
              }
              allSeries.push(s);
            });
          });

          normalised = allPeriods ? { periods: allPeriods, series: allSeries } : null;
        }

        if (!normalised || !normalised.series.length) {
          throw new Error('empty data');
        }

        /* Build inner layout: chart div + attribution */
        container.innerHTML = '';

        const chartEl = document.createElement('div');
        chartEl.style.cssText = 'width:100%;height:' + height + 'px';
        container.appendChild(chartEl);
        container.appendChild(buildAttribution(indicatorsStr));

        const chart = renderChart(chartEl, normalised, title || null);
        attachResize(chartEl, chart);
      })
      .catch(function (err) {
        console.warn('[cae-embed] Failed to load data:', err);
        showError(container, height);
      });
  }

  /* ------------------------------------------------------------------ */
  /* Init                                                                 */
  /* ------------------------------------------------------------------ */

  function init() {
    const embeds = document.querySelectorAll('.cae-embed');
    if (!embeds.length) return;

    loadECharts(function () {
      embeds.forEach(function (el) { processEmbed(el); });
    });
  }

  /* Boot */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
