# Design Resources — Storytelling with Data

This folder contains **Storytelling with Data** (SWD) reference materials, exercises, and implementations that inspire Prumo's visual design and charting patterns.

## Contents

### 📖 Book & Exercises

- **`Storytelling with Data - Cole Nussbaumer Knaflic.epub`** — Complete EPUB of the book
- **`swd-exercises/`** — Chapter-by-chapter exercises
  - CHAPTER 1-7 folders with notebooks and workbooks
  - `CHAPTER 2/2.2 PYTHON.ipynb` — Python exercises with Jupyter

### 💻 Implementations

Prumo draws inspiration from these reference implementations:

**`swd-python-matplotlib/`** — Python + Matplotlib examples
- Horizontal bar charts (figures 3-14, 4-9)
- Line charts (figure 5-10)
- Scatterplots (figure 5-6)
- Simple text visualizations (figure 9-29)
- Slopegraphs (figure 9-32, academic papers)
- Talks & winter school materials

**`swd-r-ggplot/`** — R + ggplot2 implementations
- Complete R scripts for all SWD figures (FIG0203-FIG0932)
- CSV datasets for each figure
- Theme: `theme/theme_swd.R` — SWD-style ggplot theme
- Helper functions for consistent styling
- Comparison examples and original data sources

**`swd-highcharts-nextjs/`** — React/Next.js + Highcharts
- Modern JavaScript/TypeScript implementation
- Reusable chart components:
  - `components/Scatterplot/`
  - `components/SimpleText/`
  - `components/Graph/` (line charts)
  - `components/ReactTable/`, `ReactTableHeatmap/`
  - `components/Figure0201/` (chapter examples)
- Storybook setup for component development
- Cypress tests for UI validation
- Next.js pages and theming

---

## Key SWD Principles Applied in Prumo

### 1. **Eliminate Clutter**
- Minimal gridlines, axis labels
- Focus on data, not decoration
- See: `static/css/swd-theme.css`

### 2. **Direct the Audience**
- Highlight important insights with color
- Use annotations (trend lines, value callouts)
- Sentiment coloring in KPI cards

### 3. **Think Like a Designer**
- Consistent color palette (see `swd-python-matplotlib/images/colors/`)
- Typography hierarchy
- Whitespace as design element

### 4. **Tell a Data Story**
- KPI cards -> Trend indication -> YoY context
- Sparklines for historical context
- Section narratives via AI-generated summaries

---

## How Prumo Uses These References

| Prumo Feature | SWD Inspiration |
|---------------|-----------------|
| KPI card layout | Figure 2.1 (effective visual hierarchy) |
| Sparklines in cards | Chapter 5 (line charts for context) |
| Trend direction (↑/→/↓) | Chapter 4 (pre-attentive processing) |
| Color sentiment (red/green) | Chapter 2 (color discrimination) |
| Section organization | Chapter 3 (choosing effective graph types) |
| Accessibility | Chapter 9 (inclusive design) |

---

## Using These Materials

### For Frontend Development
- Reference `swd-highcharts-nextjs/` for React chart patterns
- Study `swd-python-matplotlib/` for static chart examples
- Review `swd-r-ggplot/theme/theme_swd.R` for consistent styling

### For Learning
- Work through exercises in `swd-exercises/`
- Study figure references in the book EPUB
- Implement figures yourself (great learning exercise!)

### For Design Decisions
- When adding new chart types, check SWD examples first
- Use `swd-r-ggplot/data/` as reference datasets
- Apply SWD principles from book to justify design choices

---

## References

- **Book:** Cole Nussbaumer Knaflic — *Storytelling with Data: A Data Visualization Guide for Business Professionals*
- **Author Website:** [storytellingwithdata.com](https://www.storytellingwithdata.com/)
- **GitHub Repos:** 
  - Python: [swd-python-matplotlib](https://github.com/Cole-Nussbaumer-Knaflic/Storytelling-with-data)
  - R: [swd-r-ggplot](https://github.com/Cole-Nussbaumer-Knaflic/Storytelling-with-data)
  - JavaScript: [swd-highcharts-nextjs](https://github.com/Cole-Nussbaumer-Knaflic/Storytelling-with-data)

---

**How This Folder Helps Prumo Developers:**
- Quick reference for chart patterns
- Reproducible examples in multiple languages
- Consistent SWD styling to maintain brand
- Learning resource for data visualization principles
