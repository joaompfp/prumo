# Quality review - home CMS and backoffice UI

Scope: `f493045..edef45e`, exact HEAD `edef45e`, read-only. I read the application diff and the
templates and ran one focused schema probe. I did not rerun the pytest suite (the controller's
full run was in flight), did not write to either database, and did not touch production. This is
not a screen-reader test: any accessibility statement below comes from markup inspection, not a
human or automated AX run.

Verdict: **REQUEST_CHANGES**

The frozen homepage content itself is sound: the 17-block document (hero, heading, 12 cards,
themes, verification, sources) fits every writer bound I checked, renders one hero, and the public
fallback states fail closed. The block is one invariant gap in the new hero block model. No
security, authorisation or data-integrity defect was found.

## 1. Blocking: the hero block has no single-`h1` invariant

Evidence:

- `app/templates/_cms_blocks.html` renders one `<h1 id="cms-hero-...">` per hero block.
- `app/templates/cms_page.html` always renders its own `<h1>{{ page.title }}</h1>` in the page
  header and then calls `render_blocks(page.blocks)`. `cms_home.html` is the only template that
  guards its shell heading, via `page.has_hero`.
- Nothing restricts a hero to `inicio` or to one instance: `ingest/cms.py` accepts any number of
  `HeroBlock`s, and `Cms._page_problem` (`backoffice/cms.py`, the card/theme/chart checks) has no
  hero rule. Probe against the real parser:

  ```
  body = {"title":"T","introduction":"","section":"general","blocks":[
      {"type":"hero","title":"Um"},{"type":"hero","title":"Dois"},
      {"type":"sources","title":"Fontes"}]}
  cms.parse_body("page", body)  ->  TWO_HERO_ACCEPTED 3
  ```

Reproduction, normal UI only:

1. `/cms/page/<any-page>` (or `/cms/page/inicio`), Add block, choose "cabeçalho de abertura".
2. Fill the title, Save, Publish.
3. Non-home page: the rendered page now has two `h1` elements (the page header and the hero).
   Home: add a second hero, publish, two or more `h1` elements.

Impact: duplicate top-level headings on a published page. This is a correctness defect in the new
block model, not a style preference, and it is reachable through the supported editor action on
the primary screen.

Fix: make exactly one `h1` an enforced document invariant. The smallest change is to mirror the
home guard in `cms_page.html` (`{% if not page.has_hero %}` around the header `h1`) and reject a
second `HeroBlock` in `_page_problem` with a reader-facing reason. If heroes are intended only for
`inicio`, reject them on other slugs instead. Add one regression test for both cases.

## 2. Important: publishing does not account for unsaved edits

`cms_editor.html` keeps the publish form separate from the draft form. `admin.js` shows a
"Alterações por guardar." note when the draft form is dirty, but the publish submit only attaches
the generic `data-confirm` message ("Publicar este rascunho e substituir a versão em direto?").
The server publishes the stored draft revision; visible unsaved fields are not part of it.

Reproduction: edit a hero title or a card label without saving, then click "Publicar este
rascunho" and confirm. The operation succeeds, the live page keeps the old content, and the
unsaved text is left only in a page that the redirect replaces. The beforeunload guard does fire
on the navigation, but its message is browser-generic and does not explain that it is guarding a
publish.

Impact: an operator who has just edited the page can publish a stale draft and lose the edits.
This is not silent data corruption (the browser prompt exists), but it is the main editorial
workflow and the confirmation text is misleading in that state.

Fix: on the publish submit, if the draft form is dirty, confirm that the saved draft, not the
visible edits, will go live, or disable publish until a successful save. Server logic should not
change.

## 3. Moderate: the transport cap is smaller than the schema ceiling

`backoffice/cms_routes.py` caps the whole editor form at `CMS_FORM_MAX_BYTES = 131_072` and raises
`HTTPException(413)` while reading the body, before any field is preserved. `MAX_BLOCKS` is 20 and
`MAX_TEXT` is 4000; a page of long text/note blocks is valid per `ingest/cms.py` but can exceed
128 KiB once form-encoded, because a non-ASCII byte becomes `%XX`. At roughly 10 percent accented
characters, 20 long blocks plus headings and notes cross the cap. The `413` re-raises in `mutate`,
so the operator gets an error page and the typed content is gone (there are no parsed fields to
re-render).

The real homepage is nowhere near this ceiling, so this is not part of the frozen content. It is
a bound mismatch in the new 20-block surface, and the comment on `CMS_FORM_MAX_BYTES` mentions
field-count headroom but not byte headroom.

Fix: either raise the cap to cover `MAX_BLOCKS x (MAX_TEXT + MAX_TEXT)` with UTF-8 expansion, or
lower the per-field/block maxima to match the cap, and keep the submitted values on a 413 by
reading with a larger bounded limit before rejecting.

## Verified, no finding

- Writer bounds for the real form: 17 blocks is under `MAX_BLOCKS = 20`; the rendered form emits
  about 37 names per block, roughly 740 names total with controls and the add panel, under
  `MAX_FIELDS = 1000`. The `block_*_slot` regex limits (`MAX_ACTIONS`, `MAX_THEME_REFS`,
  `MAX_STEPS`) match the model maxima and the editor names.
- `canonical_body(..., exclude_unset=True)`: reasoned through the upgrade path. Every pre-change
  stored body was produced by the old full `model_dump`, so all old-schema fields are present and
  therefore set on re-parse; new optional fields (`label`) are absent and stay absent. Old
  revisions remain canonical and restorable. Not exercised at runtime in this review.
- Home state machine: `legacy` only before the first publication, `unpublished` after an
  unpublish, `unusable` (503) when a published pointer cannot be parsed, with no resurrection of
  the legacy list. `/paginas/inicio` redirects to `/` only when the pointer is published and
  otherwise 404s; the reserved slug is excluded from page listings.
- Publication eligibility runs inside the publish transaction (`cms_publish`'s `check` hook) and
  re-evaluates cards, chart contents and themes on the same snapshot. Draft preparation never
  moves the public pointer.
- Authored links: `_validate_href` rejects schemes, `//`, backslashes, whitespace and control
  characters, and the templates render them only under the mount prefix. The probe accepted
  `/temas/%2e%2e/%2e%2e/admin` and `/%2F%2Fevil.example`; both stay same-origin in a browser and
  neither is an open redirect, so this is hardening only (dot segments are not normalized away).
  Authors are authenticated editors, so there is no untrusted input path here.
- Backoffice CSP: `style-src 'self'` and `script-src 'self'` are safe for the current templates
  (no inline `style=` or `<style>` remains), `admin.js` is referenced only where needed, and the
  icon font is local and addressed relative to the stylesheet, so it survives the mount prefix.
- Stale edits: a 409 keeps the submitted fields and the submitted version for a re-render; the
  operator must reload to advance, which is the documented conflict-recovery behaviour.
- Legacy editor lock: the redirect and the pre-mutation 409 both key off the reserved slug and the
  prepared draft; no path was found that serves a legacy edit as the CMS home.

## Residual risks (non-blocking)

- `cms_reads.home_state` documents "one read-only snapshot" but issues `cms_get` and
  `cms_published_once` as separate SELECTs. A publish committing between them can briefly classify
  a live home as `unpublished`. It self-heals on the next request and no state is written.
- `home_is_published` checks only that a pointer exists. If the published revision is
  unparseable, `/paginas/inicio` still 301s to `/`, which then serves the 503 unavailable page
  rather than a 404. The fail-closed outcome is correct, only the status path is indirect.
- When a page has a hero, `cms_home.html` drops `page.introduction` entirely. Expected from the
  shell guard, but an author who fills both will not see the introduction.

Test note: the full pytest run was left to the controller. These findings come from source
inspection and one parser probe; the two UI findings need a browser or template-level regression
test to close.
