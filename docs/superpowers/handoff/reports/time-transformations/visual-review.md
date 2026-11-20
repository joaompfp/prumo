# Visual acceptance: time alignment and transformations

The initial visual review is retained unchanged in `failed-ea01c80/visual-review.md`. It found repeated early-year labels and clipped/merged unit titles. Those were corrected in a00f0d2/bb4b026, and the controller reran the browser matrix on the actual rebuilt asset before acceptance.

Final real-data captures show calendar tick positions spanning 2016-2026, separate unit-title rows in dual charts and a complete base100 axis title. The mobile view retains the complete plot at the approved reading scale. At 1440 the native/annual/base100/pp views have a dominant chart; legends/evidence continue below the first viewport rather than being hidden. Exact point values remain interactive and available in the complete table, not floating labels on every point.

Vision inspection was cross-checked against current time and computed geometry. The model's claim that October 2026 was future-dated was rejected: the actual runtime date is November 2026. Pixel-derived estimates of font sizes and contrast were not accepted over actual measured 18.15px ticks and 25.245px readout. A viewport crop does not establish missing metadata or a truncated document.

The base100 caption initially named the publisher unit generically while the axis named an index. The controller changed the caption to explicitly distinguish "Unidade do gráfico" from "Unidade da fonte" and added a per-side calculated mark, with a route regression. Original-series captions remain unchanged.

The final exact-value acceptance passes pointer, touch and keyboard, including the last-row mobile boundary regression. Source tokens, absent cells, native periods, all method/base inputs, no-JS/print SVG and strict local-only assets remain. Current evidence is in `receipt.json`; production proof is a separate installed record. Human screen-reader and subjective usability acceptance remain separate.
