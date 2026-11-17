# Complete current homepage as CMS content

Baseline: `ccffedf` on `pipeline-rebuild` (homepage slice `ebe42c5` plus UI `ccffedf`).
Code and focused tests only: no migration, no `main`, no push, no production change, no source
table write. The next free migration remains 0020.

## What changed

The prepared `inicio` document is now the complete current homepage, not a card list. For a
database that serves all twelve curated home series it is 17 typed blocks:

`hero`, `heading`, twelve `card`, `themes`, `verification`, `sources`.

The authored copy and links are the legacy ones, moved into the revision:

- hero eyebrow, h1, lede, both calls to action and freshness line;
- "Números em destaque" with the existing all-Portugal or mixed note and curated card labels;
- "Temas" with the existing note and the three theme references;
- "A cadeia de verificação" with its three label/text steps and methodology link;
- "Instituições publicadas" with the licence link. The institution list is read live.

Live facts are typed flags or references, never frozen prose:

- `hero.counts` renders the series/institution count through `Db.public_counts()`;
- `hero.freshness` renders the last verified receipt date through the same read;
- `themes.themes` holds stable theme codes; titles, blurbs and per-theme counts come from
  `reads.catalogue` at render time;
- `sources` has no stored institution list; `Db.public_sources()` is filtered by
  redistribution permission and served series on every render.

The renderer keeps the existing `.cards` grid for contiguous card blocks. The CMS home shell
renders an authored hero instead of adding a second generic one; older CMS home revisions
without a hero block keep the previous generic shell.

## Typed contract

`ingest/cms.py` adds only blocks for the actual homepage sections:

- `hero`: eyebrow, title, note, counts flag, freshness flag, up to 4 site-relative actions;
- `heading`: title and note;
- `themes`: title, note and up to 6 unique theme-code references;
- `verification`: title, 1..6 steps (label/text) and an optional action;
- `sources`: title, note and an optional action;
- `card` gains an optional authored `label`, so curated home labels such as "Inflação (IHPC)"
  survive the migration without changing page-card behaviour when absent.

`MAX_BLOCKS` is 20. The current 17-block home fits with a small edit margin; the bounded
editor field limit is 1000 and the rendered 20-block form carries about 890 names.

Older page and card revisions stay canonical. `canonical_body` now dumps with
`exclude_unset=True`, so an optional field added later is not invented when an old stored
body is revalidated or restored. A regression constructs the pre-label card body and proves
it is accepted unchanged.

## Editor and initialization

The CMS editor has ordinary labelled fields for every new section: title/note, hero
eyebrow/actions/counts/freshness, theme selects, verification step rows, source link and the
optional card label. Existing add/move/remove controls work on all of them. The new
`data-show-for` groups use the vocabulary `admin.js` already parses; all fields are present
server-side, so the form still works with JavaScript blocked.

`Cms.initialize_home(actor, prepare_note, publish=False, publish_note="")` is the idempotent
content initializer for a future authorized deploy. It:

- creates the complete private draft when no document exists;
- publishes it as a second audited step only with `publish=True` and a reason;
- returns `already_published` and writes nothing when a published home exists;
- raises `CmsConflict` for an existing draft, because it may hold operator edits.

`scripts/init_home_content.py` is the thin CLI wrapper. It was exercised against fresh copies:
prepare created revision 1, a repeat refused, prepare+publish produced the `created` and
`published` audit events, and a repeat reported `already_published` without a write.

Operator note: a production copy that already contains the earlier card-only `inicio`
draft is refused by design. That draft must be inspected and kept, edited or discarded
deliberately; the initializer will not overwrite it.

## Verification actually run

```text
.venv-ci/bin/python -m pytest tests/app tests/backoffice/test_cms_home.py \
  tests/backoffice/test_cms_routes.py tests/backoffice/test_cms_service.py \
  tests/ingest/test_cms.py tests/ingest/test_cms_storage.py \
  tests/ingest/test_cms_pragma_bypass.py tests/ingest/test_cms_replace_bypass.py \
  tests/backoffice/test_boundaries.py -q

399 passed, 1 warning in 303.39 s
```

Ruff on every changed Python file: clean. `git diff --check`: clean.

Coverage includes: complete section copy and links; all twelve curated card refs and labels;
17 blocks published and rendered in one cards grid; live counts/date/theme/source facts
changing after database updates; source-licence revocation; private drafts; edit, reorder and
remove through service and route controls; same public prefix in preview and public HTML;
publication/prepare audits; initializer idempotence and refusals; old canonical bodies;
unknown/invalid links, duplicate themes, out-of-range block and slot indexes; max-block form
field bound.

## Files

Implementation: `ingest/cms.py`, `app/cms_reads.py`, `app/templates/cms_home.html`,
`app/templates/_cms_blocks.html`, `backoffice/cms.py`, `backoffice/cms_routes.py`,
`backoffice/templates/cms_editor.html`, `backoffice/templates/cms_home.html`,
`backoffice/templates/cms_list.html`, `scripts/init_home_content.py`.

Tests: `tests/ingest/test_cms.py`, `tests/app/test_cms_home.py`,
`tests/backoffice/test_cms_home.py`, `tests/backoffice/test_cms_routes.py`.

`app/home.py`, `backoffice/app.py`, migrations, source/observation data and shared CSS/JS
were not modified.
