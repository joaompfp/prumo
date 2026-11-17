# Admin and public shell UI implementation

Baseline: `f493045` on `pipeline-rebuild`, integrated on top of the homepage CMS slice. This
report covers the UI-owned slice only: no deploy, merge, push, migration or release. The
public home template and CMS behaviour belong to the homepage slice; this slice consumes its
`home` dashboard summary, `is_home` editor flag and `/cms/home` entry.

## Design decisions

- **Shell and navigation.** The Admin is now a compact two-column shell: a sticky paper
  sidebar and a bounded reading column. Navigation is grouped by work, content first
  (`Página inicial`, `Páginas e gráficos`, `Editorial`) and data operation second (`Visão
  geral`, `Fila de revisão`, `Séries`, `Calculadas`). The home entry is the first item and
  links to `/cms/home`. The retired fixed-home editor is visibly de-emphasised and carries a
  `legado` tag. Each item uses the validated path below the Admin mount for a single
  `aria-current="page"`, including `/cms/page/inicio` when the editor receives `is_home`.
- **Editorial identity.** Cream paper, ink, one red accent and inherited hairline rules.
  Headings use the existing Prumo serif stack; controls use the system sans stack. Corners
  are 2 px, there are no shadows, no gradients and no decorative motion. Dark mode keeps
  the same token structure. Compact spacing replaces the previous one-size-fits-all page.
- **Page structure.** Every Admin page now has a breadcrumb, a page heading with a short
  explanation, and labelled actions. The overview replaces the bare totals table with a
  compact metric strip while preserving every `id="t-*"` and source row id. Queue, series,
  derivadas, replay, error and editorial pages use the same headings, panels, table shell
  and empty-state language. CMS pages carry the home panel, explicit preview/edit actions,
  and empty states that point at the create forms.
- **Forms and action hierarchy.** CMS forms use fieldsets and a two-column field grid that
  collapses to one column. `Guardar rascunho` is the primary filled action; preview is
  secondary; publishing is a separate deliberate red action with an optional browser
  confirmation; unpublish, restore and reset are visually distinct. Existing field names,
  hidden `version`/`block_count` values, actions and server validation are unchanged.
- **Progressive JavaScript.** `static/js/admin.js` is loaded only by the CMS dashboard and
  editor. It does three optional things: hide irrelevant block fields according to the type
  select (fields are hidden, never disabled), filter the options already present in a long
  `<select>` with a local search box (the select keeps its name and value), and show a
  quiet unsaved-change note plus the browser's leave confirmation. Destructive forms may
  ask for confirmation. With the script blocked, every form still submits exactly as before.
- **Icons.** Admin uses a pinned self-hosted subset of Bootstrap Icons 1.11.3. Icons are
  decorative (`aria-hidden="true"`) and every action keeps its visible Portuguese label, so a
  blocked font removes no meaning. The public search affordance is a local inline vector
  background, not a font, so public summary and preview pages need no font source at all.
- **CSP.** The inline Admin stylesheet was removed. The Admin policy is now
  `default-src 'none'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self'
  data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`. There is no
  `unsafe-inline`, `unsafe-eval`, CDN, analytics or new UI runtime. The preview and public
  policies are untouched and remain script-free.
- **Responsive behaviour.** At 960 px the sidebar becomes a top bar with horizontally
  scrollable grouped navigation; at 600 px the metrics become two columns, forms one column,
  and touch targets are at least 40-44 px. Tables already scroll inside their own container,
  so the page itself does not pan. `prefers-reduced-motion` removes transitions and pressed
  transforms.
- **Safe public link.** The Admin "Ver site público" link is derived from the validated mount,
  never from an arbitrary forwarded URL. Proxy mode uses the configured canonical origin
  (`https://joao.date/dados/`); local root mode links `/`; a local development prefix omits
  the guessed link rather than inventing one.

## Assets and provenance

- `static/fonts/icons/prumo-icons.woff2`: subset of Bootstrap Icons 1.11.3 (npm package
  `bootstrap-icons@1.11.3`, upstream https://github.com/twbs/icons). MIT licence. Reduced
  with `pyftsubset --flavor=woff2 --layout-features='' --no-hinting --desubroutinize` to 37
  glyphs, 3.6 kB. Glyph map and full provenance: `static/fonts/icons/README.md`.
- `static/fonts/icons/LICENSE.bootstrap-icons.txt`: upstream MIT licence text.
- `static/css/icons.css`: the single local `@font-face` and class map.
- No CDN, remote font, remote script or new build step.

## Files

Modified:

- `backoffice/app.py` (presentation context, validated path, public link, CSP)
- `backoffice/templates/base.html`
- `backoffice/templates/overview.html`
- `backoffice/templates/queue.html`
- `backoffice/templates/series_list.html`
- `backoffice/templates/series_detail.html`
- `backoffice/templates/derived_list.html`
- `backoffice/templates/derived_detail.html`
- `backoffice/templates/editorial_list.html`
- `backoffice/templates/editorial_page.html`
- `backoffice/templates/cms_list.html`
- `backoffice/templates/cms_editor.html`
- `backoffice/templates/item.html`
- `backoffice/templates/error.html`
- `static/css/prumo.css` (public transitions, focus/pressed states, touch targets, local
  search icon, reduced motion)
- `tests/backoffice/test_review_minors.py` (exact CSP expectation changed to the tighter
  policy; the test still asserts the exact restrictive header)

Added:

- `static/css/admin.css`
- `static/css/icons.css`
- `static/js/admin.js`
- `static/fonts/icons/prumo-icons.woff2`
- `static/fonts/icons/LICENSE.bootstrap-icons.txt`
- `static/fonts/icons/README.md`
- `tests/backoffice/test_admin_ui.py`
- `tests/app/test_public_ui.py`
- this report

Not touched: `app/main.py`, `app/cms_routes.py`, `app/cms_reads.py`, `app/templates/*`
except the public stylesheet, `backoffice/cms.py`, `backoffice/cms_routes.py`,
`backoffice/templates/cms_home.html`, `ingest/`, existing boundary tests, deploy docs,
HANDOFF or roadmap.

## Verification actually run

Using `.venv-ci/bin/python` in this checkout, after the homepage slice was committed:

```text
pytest tests/backoffice -q
262 passed

pytest tests/app/test_routes.py tests/app/test_cms_home.py tests/app/test_cms_reads.py \
       tests/app/test_public_ui.py tests/app/test_home_composition.py -q
92 passed

ruff check backoffice/app.py tests/backoffice/test_admin_ui.py \
           tests/app/test_public_ui.py tests/backoffice/test_review_minors.py
All checks passed
```

The focused UI tests cover local CSS/font assets, prefixed Admin links, one active navigation
item, the content-first order and legacy label, the derived public link under a hostile
prefix and in proxy mode, the prepared-home dashboard state, CMS script usage only on CMS
pages, script-free editorial pages, icon accessibility attributes, strict CSP, the
no-gradient identity and reduced motion. The golden byte comparison for the legacy home
still passes because the public HTML was not changed.

## Controller dependencies and follow-ups

- Legacy write gating is still the controller's integration item, exactly as documented by
  the homepage slice: call `app.state.cms.legacy_home_locked(slug)` in the editorial read and
  write paths in `backoffice/app.py`. The templates already label the editor `legado` and
  link to `/cms/home`; this slice deliberately did not add write behaviour outside its
  presentation scope.
- No new route, migration, worker change or preview CSP change is required. The Admin icon
  font is covered by `font-src 'self'` in the Admin policy. Public and preview pages use no
  icon font, so their existing policies stay valid.
- Browser QA, real screen-reader acceptance, responsive screenshots at 320/390/768/1440,
  no-JS workflow and production-copy checks remain for the controller's integrated run.
