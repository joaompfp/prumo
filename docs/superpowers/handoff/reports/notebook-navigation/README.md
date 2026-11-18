# Notebook charts and public navigation: delivery evidence

## State

Implemented and independently reviewed on `pipeline-rebuild`, runtime `7baa127`; the follow-up
`a42324b` only updates the old navigation-selector regression. Not merged or installed.
Installed production remains the prior runtime `42c581f`, with main at `24a3dc7` when work began.
Code was pushed to `pipeline-rebuild` at `a42324b` and its exact remote SHA read back.
The fresh exhaustive controller gate passed2835/2835 selected tests; seven network tests were
excluded by the existing marker policy. No skipped selected tests, failures or errors.

No migration, source collection, production content write, ownership change, worker restart,
authentication or routing operation belongs to this change. Public presentation templates are
also used by the CMS's static preview, so a future authorized installation should update web
and backoffice together, preserving the worker and CMS contents. Existing bind-mount-aware
prebuild/activation and image-retention rules in `docs/data/operations.md` still apply.

## Implemented contract

The public shell now prepares navigation independently from HTTP rendering and templates.
Brand/search share a masthead; destinations occupy a consistent rail. Native theme/support
disclosures preserve current-section context. Compact menus stay in normal flow and work
without JavaScript. The joined search remains aligned at320px without reducing reading type;
only its visible submit text becomes a locally drawn icon, retaining its accessible name.
Carmim, paper/charcoal, local Lato/Schola and the approved plumb-bob remain.

The Caderno retains twelve ordered cards and adds an explicit chart subset of up to six.
Shared scales validate frequency, native unit, multiplier and index base; deliberate dual
scales require exactly two sides. Defaults use the complete finite intersection over a
rolling ten-year display window, with five-year/full-history alternatives. Interval values
are read only for the common selected UTC day. No rebasing, interpolation or aggregation.

Addressed selection, explicit group, scale/window/day and disabled/empty state are shareable
without accounts, storage, cookies or writes. Eligibility loss never silently changes an
explicit chart group. Exact values, source flags, complete table and last-common-period
provenance come from one read-only snapshot. SVG/no-JavaScript/print and the existing local
ECharts adapter share the same prepared chart. Empty/incompatible/error pages do not enable
scripts; all Caderno responses remain noindex.

## Review and correction trail

The initial design review required explicit empty state, eligibility-preserving share links,
correct rolling-window codes, deterministic common day, stale dual-mode behavior, N-way
exclusion counts, label uniqueness, size budget, narrow search treatment, noindex policy and
visible current-theme context. Binding resolutions in the spec close those requirements.

Independent implementation specification review found true older-common history excluded by
an initial min-latest read, a non-finite newest-period anchor, missing native daily geometry,
right-edge support-menu overflow and block padding erased by a later wrap shorthand. All were
fixed with regressions. Scoped specification re-review returned APPROVED_SPEC. Independent
quality/integration review returned APPROVED with no critical/important issue.

Non-blocking quality follow-ups are retained honestly: raw multiplier is validated but not
separately printed in the definitions, both day and year-window controls are always visible
(their frequency-specific behavior is labelled), and single-series copy still uses plural
comparison wording. Some unused compatibility/copy fields can be removed later. None changes
source values or the eligibility/write boundary. Human screen-reader acceptance remains open.

Parent's fresh focused run passed139 tests. A detached committed checkout at `7baa127` passed
123 focused tests, importing the new navigation/notebook providers and the actual app entrypoint
from that checkout. No untracked workspace provider is needed. The initial complete canonical
suite ran to completion:2834 passed,1 failed,7 network deselected,3 warnings in1542.16s. Its sole
failure was the old `.site-nav a` literal guard; actual grouped nav uses `.site-nav > a` at the
same large size. The exact one-line assertion was corrected, and25 legibility/typography tests
passed. Runtime files remain byte-identical to that run. The fresh exhaustive controller gate
then passed all2835 selected tests in isolated module-preserving workers:946/944/945 passed,
zero failures/errors/skips, seven network exclusions established at collection. The manifest
proves unique and complete coverage. The slowest worker took921.24s. All610 frozen files match
the detached committed checkout at a42324b; only the documented source assertion changed from
the initial run. This is a fresh complete selected-scope result, not a relabelling of the
earlier failed run. Raw population/JUnit/logs are losslessly archived under `receipts/`;
`final-summary.json`, `final-gates.json` and `archive-manifest.json` pin counts and raw hashes.

## Real browser acceptance

The online backup was taken through a read-only SQLite source URI and backup API on f0nix,
including WAL contents, then copied into local scratch.217755648 bytes, integrity ok, zero FK
violations. The browser server serves the same app at root and a real `/dados` ASGI mount.

`browser_acceptance.py` final run passed2180/2180 assertions at320/390/768/900/901/1024/1440 on
both mounts: native open/closed menus, large loaded fonts, equal-height joined search, actual
compiled bundle digest, one/two/multiple series, explicit dual units, incompatibility states,
interval day, all plotted table rows, opened definitions/table/provenance, subset form and
share state, deliberate empty chart, painted first/interior/last pointer/touch/keyboard exact
readouts, fallback/no-JavaScript/blocked bundle/print, no page/console errors and no off-origin
requests. All23 table row counts and content fingerprints match before/after; quick_check ok
and zero foreign-key violations. The separate actual AX-tree/focus probe passed on desktop/mobile with one named
chart image, one named period slider and16 immediately visible keyboard outlines. The boundary
probe passed137 additional assertions for one/six series at maximum history and seven requiring
a choice, including all table columns and keyboard-reachable local scrolling. Combined browser
checks:2317. These probes are not human screen-reader use.

Initial failing receipts remain distinguishable. `browser-initial` found search-result table
overflow at901; `browser-refined` found a long active support label; `browser-layout` found an
existing theme table escaping its container. Corrected layout preserves exact large values with
local scroll/stacked results. `browser-accepted` passed the full viewport matrix, then its
helper timed out because an nth locator was based on a shrinking `:checked` set; the stable
checkbox locator fixes only that helper. `browser-final` is the complete passed acceptance.
The boundary probe initially used the multi-series readout shape for a single line. Its expected
string was corrected to the established period/value shape; application code did not change.
Historical goldens were retained byte-for-byte; their comparison excludes only the deliberately
changed shared header, with content below main still compared.

## Measured cost and explicit budget exception

`performance.py` uses20 HTTP requests after two warm-ups per sampled route on the isolated copy,
concurrent with the controller suite. This is not an exhaustive worst-case claim or production
network/compression result. The bundle is unchanged; sizes below are HTML, not library totals.

| Workload | Drawn periods | HTML bytes | Local gzip bytes | Median ms | p95 ms |
|---|---|---|---|---|---|
| Homepage | none |19093|4418|93.956|117.839|
| Six BP series, initial ten-year window |121|197201|26351|66.507|75.522|
| Same six, all shared history |322|471389|57914|106.134|171.114|
| INE inflation/unemployment, ten years |121|78744|12049|81.825|85.042|
| Two E-REDES series, common UTC day |96|80478|13747|225.456|242.297|

The sampled default six-series page meets the250kB HTML target. The optional full-history page
exceeds it. This delivery explicitly accepts471389 bytes for that measured full-history choice
rather than truncating values or pretending all history fits the default budget. The initial
window stays ten years, full table is collapsed but complete, and the reader deliberately
chooses maximum history. Larger future populations require fresh measurement; no universal
500kB upper bound is asserted. Non-interval histories are read before the finite shared anchor
can be determined correctly; interval value reads remain day-bounded.

## Reproduction and receipts

Use the project's `.venv-ci/bin/python`. Start the public app against an online acceptance copy,
mounted at root and `/dados` (the small dual-mount wrapper is optional test infrastructure).
Run with `PRUMO_QA_DB` pointing to the isolated scratch copy, `PRUMO_QA_URL` to localhost, and
`PRUMO_QA_OUT` to a new report directory:

```bash
PRUMO_QA_DB=/absolute/scratch/copy.sqlite3 PRUMO_QA_URL=http://127.0.0.1:8107 \
PRUMO_QA_OUT=/absolute/report/browser .venv-ci/bin/python \
docs/superpowers/handoff/reports/notebook-navigation/browser_acceptance.py
```

`full_gate.py` first collects exactly `tests -q --collect-only` without overriding markers. Its
versioned population receipt proves every selected node runs exactly once; three isolated
workers keep modules together and use separate temporary/cache directories. Network exclusions
come from the existing pytest configuration. JUnit counts must equal the complete population.

Reader operation and URL fields: `docs/data/notebook.md`. Design and plan:
`docs/superpowers/specs/2026-11-18-notebook-chart-and-navigation-design.md`.
