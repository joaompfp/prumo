# Tabler UI - independent spec review

Date: 2026-11-17
Baseline: `7a35f47` · Commit reviewed: `16f9772` (branch `pipeline-rebuild`) + uncommitted controller files
Plan: `docs/superpowers/plans/2026-11-17-tabler-ui.md`
Review type: read-only specification compliance. No runtime edits, no full suite, no network, no browser.

## Verdict

**PASS** on the specification for the reviewed diff. Two release-hygiene items must be closed
before the commit/push slice; neither requires a design change.

## Verified against the plan

| Plan requirement | Evidence |
| --- | --- |
| Pinned, local Tabler; no CDN | `backoffice/templates/base.html:9` links `/static/vendor/tabler/1.7.5/tabler.min.css`; `static/vendor/tabler/1.7.5/manifest.json` pins version, npm tarball URL, `sha512-` integrity, per-file bytes+sha256; `sha256sum` of the vendored CSS matches the manifest (4421622c…32ce3). |
| No external browser requests / CSP relaxation | App diffstat contains no `app/main.py`; `SECURITY_HEADERS` CSP unchanged (`default-src 'none'; style-src 'self'; img-src 'self' data:`); vendor CSS has zero `@import`, zero `sourceMappingURL`, and every `url()` is `data:`. |
| No inline scripts / arbitrary execution | No `<style>` or `style=` added to backoffice templates (`tests/backoffice/test_admin_ui.py` also pins this); script blocks remain only `admin.js` on CMS list/editor and `chart_js` on chart pages. |
| Real Tabler controls, handcrafted control layer removed | Editor/list templates now use `form-control`, `form-select`, `form-check-input`, `btn btn-*`, `card`, `table`, `nav-link`; `admin.css` redefines no native controls (only `input[type="date"] { max-width }`) and no longer ships `.button-primary`/`.button-danger`. |
| Form contract preserved (routes, method/action/name/value, CAS, actor/reason, previews, no-JS) | Programmatic multiset diff of every `name=`, `method=`, `action=` attribute in all changed `backoffice/templates/**` files against `7a35f47`: **no removed or added occurrences**. Changes are class attributes only. |
| Public summaries stay script-free, no admin toolkit | No `vendor/tabler` reference anywhere under `app/templates`; `/` renders no `<script>` (`tests/app/test_visual_identity.py::test_public_summaries_do_not_load_admin_toolkit`). |
| SVG summaries and ECharts roles kept | `_chart.html`, `cms_page.html`, `series.html`, `derived.html`, `compare.html` unchanged in the diff; chart adapter compatibility token preserved (`--red: var(--series-b)`). |
| Danger semantically distinct from green brand | `--danger: #b42318` vs `--primary: #1b514b` (dark: `#ff9b8f` / `#8ac4b8`); public `var(--red)` is now used **only** for chart series (`.spark-end`, `.chart-last*`, `.chart-line-b`, `.swatch-b`), never for error UI; 404/503 use `.error-page`, not `--red`. |
| Palette matches the approved brand set | `admin.css` `:root` and `prumo.css` `:root` carry `#f6f5f0 / #ffffff / #18322f / #1b514b / #123d38 / #99672d / #52645f / #dbe2dd`, with `light-dark()` + `prefers-color-scheme` equivalents and `prefers-reduced-motion` handling. |
| Plumb-bob brand mark | `static/images/prumo/favicon.svg` is a 32×32 vector with `plumb-line` and `plumb-weight` paths, no `<text>`; `test_brand_is_a_vector_plumb_bob_not_font_text` asserts both. |
| Reproducible, reviewed preparation | `tools/ui/vendor_tabler.py` verifies the tarball sha512 before reading named members, pins the licence by sha256, refuses `@import`/non-`data:` `url()`, strips source-map refs, and records the exact upstream→local delta in the manifest. No archive member is executed/extracted to disk. |
| Scope: no ingestion/access/persistence/schema change | Diffstat touches only `backoffice/templates`, `static/{css,js,images}`, `tests/backoffice`, plus untracked `static/vendor`, `tools/ui`, `tests/app/test_visual_identity.py`, and report artifacts. Main/prod untouched. |

## Actionable items

**F1 - Commit the proof before claiming the pinned layer (release blocker for slice 5/6).**
`static/vendor/` (Tabler CSS + LICENSE + manifest), `tools/ui/vendor_tabler.py`, and
`tests/app/test_visual_identity.py` are still untracked (`git ls-files --others`). Until they are
committed, `16f9772` alone cannot reproduce the stylesheet the templates link, and the receipt
tests do not exist for a clean checkout.

**F2 - Remove the conditional guard on the vendor serving assertion (test-honesty).**
`tests/backoffice/test_admin_ui.py` wraps the check in `if tabler.exists():  # the controller owns
the pinned vendor copy`. If the vendor directory is ever missing from a checkout, the test passes
silently while `base.html` still advertises the link - exactly the failure the assertion exists to
catch. Make it an unconditional `assert c.get(TABLER).status_code == 200` once F1 lands.
The same file's relaxed selectors (`class="nav-link[^"]*is-legacy..."`, `class="[^"]*tag-legacy..."`)
are required by the added Tabler classes and do not weaken the contract.

**F3 - Public-front breadth is CSS-only; confirm it is intended.**
Plan slice 4 asks for "restrained search/filter/buttons/table/surface refinements" on the public
side. `app/templates/**` is untouched; the public pass is entirely `static/css/prumo.css` (palette,
search field/button radii, nav states, focus ring, brand sizing) plus the new favicon. That is
consistent with keeping public summaries script-free and adds no risk, but the table/surface part of
slice 4 has no template or test evidence - accept it explicitly or extend the CSS pass.

## Not verified here (left to the parent's browser/runtime pass)

- 320/390/768/1440 rendering, stacked `cms-table` `data-label` behaviour, light/dark contrast.
- Label association for the checkboxes converted from wrapping `<label>` to `form-check-input` with
  explicit `id`s (diff shows the `id`s added; the `<label for=…>` pairing was not inspected).
- Dirty/save/publish/CAS reason round-trips and the real-data CMS exercise.
- 16/24/32 px favicon legibility is structurally plausible (integer paths, high contrast fill) but
  is a visual judgement.

## Out of scope / untouched (confirmed)

`app/main.py`, access, persistence, schema, ingestion, `docs` roadmap, and any main/prod state.
No staging, commit, push, or deployment was performed by this review.
