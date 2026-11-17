# Independent specification review: homepage as CMS content and restrained UI

Decision: **CHANGES_REQUIRED**

Reviewed `f493045..cfccdf7` (`ebe42c5`, `ccffedf`, `cfccdf7`) plus the unstaged
`backoffice/app.py` legacy lock and `tests/backoffice/test_home_legacy_lock.py`. I read the
plan, the actual implementation, templates, CSS/JS/font assets and tests. No migration, source
data write, commit, deployment or browser/production-copy run was performed here; that remains
the controller's scope.

## Verification observed

- `pytest -q tests/backoffice/test_cms_home.py::test_the_seed_fits_the_full_twelve_card_current_homepage tests/app/test_cms_home.py::test_prepared_and_published_home_renders_every_current_section`
  → **2 passed, 1 warning in 4.48s**.
- `node --check static/js/admin.js` → passed.
- Two bounded `TestClient` reproductions (not pytest tests) for the findings below.
- Full suite, real browser, no-JS browser, screen reader and production-copy acceptance were
  not run here.

## Blocking findings

### B1. The Admin dashboard says the CMS owns `/` before the first CMS publication

`backoffice/templates/cms_list.html:30-36` renders the home panel whenever a CMS document
exists, and always ends with:

> `O CMS gere o que aparece em /`

That is false in the prepared-but-never-published state required by the plan: the public `/`
must still be the legacy homepage. The panel has only `published` (`backoffice/cms.py:104-117`)
and `backoffice/cms_routes.py:553-558` passes only that summary, so it cannot distinguish
"never published" from "published and later unpublished" either. After an unpublish the panel
still says "Rascunho privado ... O CMS gere o que aparece em `/`", with no "despublicada"
state.

Bounded reproduction (fresh `tests.backoffice.test_cms_home.Env`):

1. `POST /cms/home/prepare` with `Origin` → 303.
2. `GET /cms` → home panel text `Página inicial Início Rascunho privado versão 1 O CMS gere o
   que aparece em / .`
3. Public `app.main.create_app(db_path).get("/")` → 200 and still contains
   `Estatísticas oficiais, com a proveniência à vista.` (the legacy home).
4. Publish then unpublish the home; public `/` → 200 with `A página inicial está por publicar.`
   The dashboard still shows `Rascunho privado` and the same "CMS gere" sentence.

Requirement: plan lines 8-9 ("Keep the existing home public until the first CMS publication";
"Unpublication shows a neutral unpublished-home state") and line 13 ("meaningful
empty/status/error states"). This is a status-state defect, not a public render defect.

Fix direction: expose `published_once` (or a three-state `legacy` / `published` / `unpublished`)
from `Cms.home()` and render the correct sentence/badge for each state. Add a test for the
prepared-only and unpublished cases.

### B2. Server-side validation errors discard every submitted editor value

`backoffice/cms_routes.py:685-694` starts with `doc = None`; if `_document_from_fields` raises
`FormError` (unknown/blank block type, missing action label or href, duplicate theme, empty
step, etc.), the assignment never completes. The error path passes `doc=None` to
`editor_page`, and `backoffice/cms_routes.py:517-522` then replaces it with the **stored draft**.
The visible error is shown, but all other edits in the submitted form are gone.

Bounded reproduction with the real route:

1. Prepare the home.
2. Post a save with a hero title `TÍTULO ESCRITO PELO OPERADOR`, a note, and one action whose
   `href` is empty (a normal `FormError` from `_link`).
3. Response is 422 and includes the expected "endereço" error, but the re-rendered form contains
   the seed title `Estatísticas oficiais, com a proveniência à vista.` and does **not** contain
   `TÍTULO ESCRITO PELO OPERADOR`.

Requirement: plan line 14, "Do not silently discard user input". The error is not silent, but
the input is discarded, which is the behavior the requirement is intended to prevent. This is
especially costly on a 17-block home.

Fix direction: on `FormError` from `_document_from_fields`, pass the raw field/block values (or a
best-effort document plus the original values) to the editor so the form re-renders what the
operator typed; add a regression for the missing-href hero action.

### B3. Two reorder controls are icon-only, so a blocked font removes the visible action

`backoffice/templates/editorial_page.html:83` and `:89` are the only action controls in the
Admin with no visible text:

```html
<button ...><i class="icon icon-arrow-up" aria-hidden="true"></i><span class="sr-only">Subir</span></button>
<button ...><i class="icon icon-arrow-down" aria-hidden="true"></i><span class="sr-only">Descer</span></button>
```

`.sr-only` is clipped by `static/css/admin.css:82-85`. If the local icon font is blocked or
fails, the button has no visible content. This contradicts plan line 13 ("Icons supplement
text") and the acceptance requirement "accessible text survives blocked icons". The UI report's
claim that every action keeps a visible Portuguese label (`ui-implementation.md:39-40`) is not
true for these two controls.

Fix direction: add a visible `Subir` / `Descer` label (or replace the icon-only controls with
text buttons). Keep the icon aria-hidden.

## Minor specification deviation

The icon font contains **10 unused glyphs**. `static/css/icons.css` defines 37 classes, while
`backoffice/templates` and `app/templates` reference 27. The unused classes are
`icon-activity` (line 28), `icon-calendar` (37), `icon-database` (43), `icon-flag` (47),
`icon-hourglass` (50), `icon-info` (53), `icon-layers` (55), `icon-list-task` (57),
`icon-audit` (61) and `icon-table` (62). The plan asks for a self-hosted font "with only needed
glyphs"; the README already describes a 37-glyph subset. Re-subset to the 27 used glyphs (or
document an explicit reserved set) while touching the asset.

## Parity and quality notes (not blocking this specification review)

- **`<title>` changes after the first publication.** The legacy home uses
  `Prumo - estatísticas oficiais com proveniência` (`app/templates/home.html:2`), while the CMS
  home renders `{{ page.title }} - Prumo` (`app/templates/cms_home.html:3`) with the seed title
  `Início` (`backoffice/cms.py:405`, `presentation/catalog/pt.py:353`). If the document title is
  part of "current homepage parity", seed a title that preserves the legacy `<title>`; otherwise
  confirm the change is intended.
- **The highlights note is frozen at preparation.** `backoffice/cms.py:379-381` chooses
  `note_all_pt` or `note_mixed` once and stores it, while the legacy home computes
  `page.note` per render (`app/templates/home.html:15`, `app/reads.py:home`). Adding a non-PT
  card after preparation leaves "Portugal ..." on the page. The plan's "live counts/source
  facts" wording arguably does not require this note to be live, but it is a visible parity
  drift.
- **The highlights landmark is lost.** The legacy cards are wrapped in
  `<section aria-labelledby="destaques">` (`app/templates/home.html:12-22`); the shared renderer
  emits the heading and `.cards` as siblings (`app/templates/_cms_blocks.html:36-40`). The
  heading still labels the cards visually, but the section association is gone.
- **Ordinary CMS pages can get two `<h1>`s.** `cms_page.html:15-19` always renders the page
  header, and `_cms_blocks.html:21-35` renders an authored `hero` block. The editor offers the
  hero type on every page. Either suppress the generic header when `page.has_hero` (as the home
  shell does) or restrict hero blocks to the home.
- **The home appears twice on `/cms`.** The home panel (`cms_list.html:27-46`) and the pages
  table (`cms_list.html:57` loops `pages`, which includes `inicio`) both show it. Not a
  correctness bug, but it weakens the "clear home entry" hierarchy.
- **The legacy-editor notice is premature/inaccurate.** `editorial_list.html:17-22` says the
  home "passou a ser gerida em CMS" and is kept for reversal while the CMS home is not
  published. Before preparation the legacy editor is still the active home editor; after
  preparation it is blocked by `backoffice/app.py:393-395` and `461-466`. The copy should be
  state-dependent.
- **Admin CSP is broad across all pages.** `backoffice/app.py:63` grants `script-src 'self'`
  on every Admin page, although only the CMS dashboard/editor load `admin.js`. There is no
  inline execution or eval, so this is a hardening opportunity rather than a functional defect.

## What passed inspection

- **Complete seed and current-home parity:** `backoffice/cms.py:_home_body` builds the current
  hero, highlights heading, twelve curated cards with their labels/derived keys, theme
  directory, verification chain and published-institutions section. It uses live flags for the
  series/source counts and freshness, theme codes and catalogue facts for the directory, and
  live `public_sources()` for the institution list. The full 12-card test passed and confirmed
  the 17-block draft, one `.cards` grid and the expected labels. Source/observation/editorial
  rows are not written.
- **Lifecycle:** `cms_reads.home_state` distinguishes legacy, published, unpublished and
  unusable; a draft alone does not switch `/`; restore creates a draft; unpublish gives the
  neutral page; a missing/invalid published revision answers 503 and never falls back to the
  legacy list. `/paginas` excludes `inicio`; `/paginas/inicio` is 404 before publication and a
  prefix-aware 301 to `/` after it.
- **Eligibility:** card slots and chart blocks are revalidated at render; ineligible blocks are
  dropped with one generic note; an all-invalid page renders no legacy cards. Chart script
  loading is tied to an eligible payload.
- **Canonical revisions:** `canonical_body(..., exclude_unset=True)` keeps older stored bodies
  canonical and restorable; the regression for the pre-label card body is present.
- **Links and prefixes:** authored actions are constrained to bounded site-relative paths;
  rendering uses the validated `base`; the old-slug redirect uses the validated mount prefix.
- **No-JS and assets:** the editor fields are all server-rendered (JS only hides irrelevant
  groups), the forms are server-validated, the CSS/JS/font are local, icons are aria-hidden
  except B3, reduced-motion rules exist, and the Admin/public CSPs avoid inline execution and
  eval. Active navigation and the one local Admin script are covered by tests.
- **Legacy lock:** `backoffice/app.py:393-395` redirects the old page and `:461-466` refuses
  every old write once the CMS draft exists. `tests/backoffice/test_home_legacy_lock.py`
  asserts the redirect, 409s and unchanged legacy rows; I read it but did not rerun it because
  the review budget was two focused pytest tests.

## Scope boundary

The core homepage-as-content behavior, seed, renderer, lifecycle, eligibility, canonical
revision handling and prefix/link safety are in good shape. B1-B3 (with the minor font-subset
cleanup) should be fixed and re-tested before the quality/integration review and the controller's
browser/production-copy acceptance.
