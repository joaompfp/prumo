# Homepage as a CMS page: implementation report

Baseline: `f493045` on `pipeline-rebuild`. This slice is code and tests only: no migration,
no merge, no deploy, no push. The next free migration remains 0020.

## Delivered

- Reserved CMS page `inicio` is selected as the public homepage. Before the first CMS
  publication, `/` remains the existing legacy home (including its editorial composition).
  After the first `published` audit event, the CMS owns `/`.
- Public selection lives in `app/home.py` with the read model in `app/cms_reads.py`:
  `legacy`, `published`, `unpublished` and `unusable` are distinct states. Draft creation
  alone does not switch the home; unpublishing shows a neutral page with site navigation;
  a published revision that cannot be parsed answers 503 and never falls back to the old
  list. All card eligibility is revalidated per render, and an all-invalid page renders its
  empty state plus the generic availability note.
- `Cms.prepare_home(actor, note)` imports the effective legacy/default card slots, keeps
  each calculated companion when it is still eligible, and otherwise degrades that card to
  its base. It imports the catalogued home title and introduction. It writes one private
  draft and one `created` audit event through `Db.cms_create`; an existing `inicio` document
  raises `CmsConflict` before anything is written.
- `Cms.create` and `Cms.duplicate` refuse the reserved page slug, so the homepage can only be
  prepared through the explicit path (or edited afterwards).
- Routes: `GET /cms/home` (preparation page, or redirect to the editor once prepared),
  `POST /cms/home/prepare` (authenticated, same-origin, bounded form, required reason,
  303 to the editor). The dashboard receives `home` as a head summary with `title`,
  `version`, `published` and the raw head fields, or `None`. The editor receives
  `is_home`.
- `/paginas` excludes `inicio`; `/paginas/inicio` redirects 301 to the canonical mount
  root only while the home is published, and is 404 for a draft-only or unpublished
  document.
- Shared CMS block renderer `app/templates/_cms_blocks.html` is used by `cms_page.html` and
  the new `cms_home.html`. Contiguous card blocks share one `.cards` grid and keep order.
  Text stays autoescaped; charts render static SVG unless the template's published payload
  decision enables the local chart script. The preview uses the same home shell and static
  chart markup, and never enables the script.
- `Db.cms_published_once(kind, slug)` is a narrow read of the append-only audit trail. No
  table, column or migration was added.

## Files

Owned implementation:

- `app/main.py`, `app/cms_routes.py`, `app/cms_reads.py`, `app/home.py`
- `app/templates/cms_page.html`, `app/templates/cms_home.html`,
  `app/templates/_cms_blocks.html`, `app/templates/home_unpublished.html`,
  `app/templates/home_unavailable.html`
- `backoffice/cms.py`, `backoffice/cms_routes.py`, `backoffice/templates/cms_home.html`
- `ingest/db.py` (one read method)
- `tests/app/test_cms_home.py`, `tests/backoffice/test_cms_home.py`
- `tests/backoffice/test_app_overview.py` (allowlist gains `/cms/home/prepare`)

`app/templates/home.html` and `backoffice/app.py` were not modified. The parallel UI
implementer owns the shared chrome, other backoffice templates and assets.

## Controller integration for the legacy editor

The retired fixed-home editor is already labelled `legado` by the parallel UI template, but
writes are not gated yet. The exact helper to call from `backoffice/app.py` is:

```python
app.state.cms.legacy_home_locked(slug)  # True only for page slug "inicio" once prepared
```

Recommended minimal patch, after `register_cms(...)` has set `app.state.cms`:

1. In `editor_page`, compute `legacy_locked = app.state.cms.legacy_home_locked(slug)` and
   pass it to `editorial_page.html` (disable the form/buttons and show the existing legacy
   label).
2. At the start of `apply(slug, action, fields)`, return a refusal before any mutation:

```python
if app.state.cms.legacy_home_locked(slug):
    return 409, ("O editor antigo da página inicial está bloqueado. "
                 "Use o CMS em /cms/home para editar a página inicial.")
```

`Cms.home_prepared()` is also available when only the existence check is needed.

## Verification actually run

Focused contract suite, after the final code change:

```text
.venv-ci/bin/python -m pytest tests/app/test_cms_home.py tests/app/test_cms_reads.py \
  tests/app/test_routes.py tests/backoffice/test_cms_home.py \
  tests/backoffice/test_cms_routes.py tests/backoffice/test_app_overview.py -q
127 passed, 1 warning in 230.44 s
```

CMS storage regression suite:

```text
.venv-ci/bin/python -m pytest tests/ingest/test_cms.py tests/ingest/test_cms_storage.py \
  tests/ingest/test_cms_pragma_bypass.py tests/ingest/test_cms_replace_bypass.py -q
114 passed in 64.36 s
```

Ruff on every owned Python file: clean. The new tests cover preparation/no-overwrite/audit,
legacy-until-publication, private drafts, restore as draft, neutral unpublish, unusable
published revision 503, all-invalid eligibility, canonical redirect, both Admin prefixes,
same-origin/auth refusals, stale forms, reserved-slug refusal, source/editorial row
preservation, shared card grouping and the chart script decision.

## Parallel-work tree notes

Two scoped failures observed against the current shared working tree are not from this slice
and were left untouched:

- `tests/app/test_home_composition.py::test_empty_composition_home_is_byte_identical` and
  `::test_a_page_row_for_an_unknown_slug_is_inert`: the golden differs only by the parallel
  UI's new `icons.css` link in `app/templates/base.html`; the legacy home render itself is
  unchanged.
- `tests/backoffice/test_boundaries.py::test_backoffice_package_contains_no_sql`: the SQL
  scanner matches the word `select` in a prose comment added to `backoffice/app.py` by the
  parallel UI work. The owned modules contain no SQL, and `app/` remains free of statements
  and `.execute(`.

The full suite, browser QA and production-copy acceptance remain the controller's scope.
