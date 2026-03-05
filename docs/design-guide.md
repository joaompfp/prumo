# Prumo Design Guide

Quick reference for design standards and visual patterns used across Prumo.

## Quick Links

- **[Design Resources](/design/)** — Design inspired by *Storytelling with Data* (Cole Nussbaumer Knaflic, Wiley, 2015), plus open-source implementations (Python, R, JavaScript)
- **SWD Principles** — See [docs/design/README.md](/design/README.md) for how we apply them

## Visual Standards

### Colors & Sentiment

Prumo uses **sentiment-based coloring** for KPI cards:

- **🟢 Green (positive)** — Good news indicators
  - Growth metrics (employment ↑, production ↑)
  - Price decreases (inflation ↓, unemployment ↓)
- **🔴 Red (negative)** — Concerning indicators
  - Declines (GDP ↓, employment ↓)
  - Price increases (inflation ↑, unemployment ↑)
- **⚪ Neutral (gray)** — Stable or mixed signals

**Note:** Many indicators use `invert_sentiment=True` because lower is better (inflation, unemployment).

### KPI Card Anatomy

```
┌──────────────────────┐
│ Label                │ ← Title (Portuguese)
│ Value  Period        │ ← Main metric + date
│ YoY% ↑  Trend →      │ ← Year-over-year change
│ ▌▄▅▆▇█             │ ← Sparkline (12-month history)
│ Source: INE          │ ← Data provenance
└──────────────────────┘
```

### Typography

- **Section headers:** Bold, large (24px+)
- **KPI labels:** Regular, medium (16px)
- **Values:** Bold-or-monospace, large (32px+)
- **Metadata:** Light gray, small (12px)

All in **Portuguese (pt-PT)** for primary audience.

### Charts

Prumo uses **ECharts** with SWD principles:

- **Line charts** — Trends over time (line thickness 2-3px)
- **Bar charts** — Horizontal bar for comparisons (avoid 3D)
- **Sparklines** — Tiny 60px-wide inline trends (no axis labels)
- **No unnecessary decorations** — Minimal gridlines, clear legends

See `static/js/swd-charts.js` for chart factory.

---

## Implementation Guide

### Adding a New KPI

1. **Pick a metric** from [`app/constants/catalog.py`](../app/constants/catalog.py)
2. **Create card** in service file using `painel_kpi()` helper:
   ```python
   painel_kpi(
       kpi_id="my_metric",
       label="My Metric Name",
       source="INE",
       indicator="my_db_code",
       decimals=1,
       invert_sentiment=True  # if lower is better
   )
   ```
3. **Test visually** using browser:
   ```bash
   pw https://joao.date/dados
   pw-snap https://joao.date/dados painel
   ```

### Adding a New Chart

1. **Design first** — Sketch or reference SWD example
2. **Use ECharts** — Template in `static/js/swd-charts.js`
3. **Include title + annotation** — Tell the story, not just data
4. **Test responsiveness** — Works on mobile + large screens

### Color References

See `swd-python-matplotlib/images/colors/` for palette studies.

Prumo primary colors:
- **Accent:** Blue (data highlight)
- **Positive:** Green (#2ecc71 or similar)
- **Negative:** Red (#e74c3c or similar)
- **Light:** Gray (#ecf0f1 for neutral/background)

---

## Resources

- **Inspiration source:** *Storytelling with Data: A Data Visualization Guide for Business Professionals* — Cole Nussbaumer Knaflic (Wiley, 2015)
- **Author website:** https://www.storytellingwithdata.com/
- **Project references:** `docs/design/` notes and open-source implementations only
- **Python examples:** `docs/design/swd-python-matplotlib/`
- **R examples:** `docs/design/swd-r-ggplot/`
- **React examples:** `docs/design/swd-highcharts-nextjs/`

---

## Key Principles (from SWD)

1. **Eliminate clutter** — Remove everything that doesn't support insight
2. **Focus attention** — Use color, size, position to direct the eye
3. **Think like a designer** — Whitespace, typography, hierarchy matter
4. **Tell a story** — Data alone ≠ insight; context + narrative required
5. **Use preattentive attributes** — Color, size, position process faster than text

---

See also:
- [Prumo README](../README.md) — Architecture & features
- [Prumo Dashboard](https://joao.date/dados) — Live example
