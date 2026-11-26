# Responsive chart inspection

## Contract

Mobile charts must remain unobstructed while a point is inspected. Narrow viewports and coarse pointers use the existing full-width period/series/value readout immediately below the plot, before the range. Fine hovering desktop pointers retain the floating tooltip. Hybrid touch/pen input selects inline reading until mouse input returns. Responsive changes retain the point. Touch scrolling does not select a different observation. Every reader string comes from the server-prepared four-significant-figure model; geometry, source tokens, CSV, CMS content, schema and ingestion are unchanged.

The shared adapter covers series, calculated details, Caderno, authored comparisons and inline CMS chart blocks. Admin previews remain static, private and script-free. No CDN, changed CSP, public composition editor or duplicated below-plot tooltip was added.

## Verification before release

Controller runtime checks passed 78 chart/engine/typography tests after the hybrid refinement; an additional 22 typography/architecture checks and broader ruff passed. The rebuilt bundle reproduced twice with SHA-256 `9ee9f891083e93e22a25872a37bb212e5f901f133a2065064cbf463bc032992e`, 512971 raw bytes and 174992 locally gzipped bytes. This is not an installed transfer measurement.

Real production-copy acceptance passed 1046 assertions over 36 route/viewport/input cases, including 320/390/844 coarse touch, 599/600 boundary and 1440 desktop, native keyboard endpoints, prepared per-series values and no-JavaScript fallback. The isolated database hash is `72044db83620d3458259bd2c725213f63442bba5ae5b2312e1b478c6a9c1795c`; source backup used read-only SQLite backup API including WAL, never a main-file copy.

A separate live baseline reproduced the covering tooltip at the plot midpoint. The first baseline helper expected an overlay even in canvas padding, where the old renderer did not paint one; its failed receipt is retained rather than attributed to a new application defect. Candidate padding/endpoints remain covered by exact readout and native endpoint regressions. The synthetic hybrid-pointer test is explicitly labelled; it is not a hardware acceptance claim.

Independent specification/quality review approved the fix after hybrid-input and marker/title alignment refinements. A screenshot critique alleged left-edge clipping in an element-cropped screenshot; actual page overflow and complete row geometry checks pass, so no unrelated page-padding change was made. Human screen-reader acceptance remains separate and open.

## Release boundary

A schema-unchanged release changes only public web and the shared static-preview Admin consumer. Existing owner authorization for the online UI iteration applies. Never restart ingestion or shared edge, edit live CMS documents, refresh sources or change rights/ownership for this fix. The adapted `release/` helpers preserve immediate preactivation worker/schema/CMS and unrelated infrastructure state, prebuild from a detached pushed SHA, require exact-main hosted CI, then recreate readers through existing aliases. Dated helpers are receipts; do not rerun them blindly.

Installed status, exact CI and recovery will be recorded in `installed.md` after public readback and the real reader observation interval. L4 CMS-authored compact entry remains the next product phase, not part of this correction.
