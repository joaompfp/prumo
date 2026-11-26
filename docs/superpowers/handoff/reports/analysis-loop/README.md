# Finding, collecting and inspecting indicators

## Scope

L1-L3 of [the analysis-loop roadmap](../../../plans/2026-11-26-analysis-loop-roadmap.md) implement the first owner-authorized online iteration after the independent Ollama design critiques. The reviewed baseline is main `3b29735`. This is a reader-only public web and static-preview Admin release, with no migration, worker restart, source write, live CMS publication or shared-edge/authentication change.

The range and selected-point rows now follow the plot directly, before the compact legend and a native `Séries, eixos e fontes` disclosure. Multi-series rows reuse prepared styles, axis membership, periods and four-significant-figure value strings. A value carries its unit once. Sparse mixed-frequency rows preserve their own observed periods and explicit missing cells. The shared fallback keeps source links accessible without JavaScript and exposes disclosure contents when printed, including metadata outside an enhancement shell.

The complete catalogue has native multi-selection. One GET form owns query, filters, selected results and pagination. It preserves selected references across searches and pages and passes the set into Caderno in one action. Previous-order metadata prevents hidden off-page fields from swapping existing card order and chart styles; it cannot restore an unchecked reference. Native removal and recovery remain available without JavaScript. The server retains up to 48 raw bounded references for recovery, refuses more before database work, and refuses a notebook handoff above twelve rather than truncating. Twelve cards and six drawn series remain separate limits.

`Energia` now matches the resolved theme title in the complete discovery catalogue. The separate bounded quick-suggestion phrase/cap contract is unchanged. Editorial comparisons remain authored and published through the authenticated CMS; selection does not publish content. The homepage document and all published drafts/revisions/events remain untouched.

## Review disposition

Independent specification review found missing primary/derived/single-CMS source disclosures and print selectors that missed fallback disclosures outside the interactive shell. Both were corrected, with route-level no-payload regressions, and specification re-review approved.

Independent quality review found repeated units and a real native-form pagination ordering defect. The fixes remove the duplicated unit decoration and preserve retained selection order through bounded `ordem` metadata. Clearing the selection also resets a previous chart-off configuration. Targeted quality re-review approved these fixes, including an independently reproduced bundle build and native order handoff. Raw reviewer receipts are preserved losslessly under `reviews/`; they are not rewritten to erase earlier findings.

Final visual QA also exposed browser-default 13.3333 px text in the query input and native auxiliary buttons. Discovery controls now inherit the approved functional type. The compact selection action precedes the results; checkboxes precede each result title so the first mobile view shows both a selectable result and a real value, without reducing text. The selection count describes the last submitted address, not unsubmitted live checks.

## Evidence and verification

The controller's initial whole-suite development run finished with 3,420 passed and two obsolete expectations: shared list markup before explicit catalogue checkboxes, and the earlier generated-bundle hash. Those were corrected and separately exercised; this run is not described as an all-green run or as verification of later changes.

The post-review focused gate passed 84 tests, including actual chart interactions, all fallback routes and typography. The final discovery surface passed 52 focused tests and broader ruff. Earlier browser receipts retain their original scope; the first geometry checker mistook browser scrolling for a changed document coordinate, and the second treated an explicitly missing sparse cell as a display-string error. Both checker issues were corrected without changing statistical behavior.

`browser_check.py` exercises populated chart pages at 320, 390, 768, 1440 and 1920 pixels on both public prefixes. It covers adjacent controls, exact keyboard point strings, native missing cells, preserved fonts, metadata, print, blocked/no-JavaScript fallbacks, actual compiled asset bytes and native selection/search/pager journeys with and without JavaScript. Neutral captures clear the tooltip before capture and assert scrollY=0; earlier active screenshots are not neutral geometry evidence. Public source CSV and original coordinates are outside the behavioral delta.

Final release, clean-commit/hosted gates, installed checks and recovery will be recorded in `installed.md` after execution. Human screen-reader acceptance and the separate source/worker operating gates remain open.

## Next product slice

L4 is a compact, data-first entry using the existing authored homepage and its CMS lifecycle. It must preserve the operator's composition and drafts and prove published values with units/periods above the fold. Comparable-country grouping and related published comparisons follow; focus mode and dated/human-approved AI writing have separate designs. No live content edit is included in this release.
