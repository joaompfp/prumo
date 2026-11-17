# Reviewed presentation fixtures

The 2026-11-17 typography increment deliberately recaptured `charts/*.svg` once more over
the legibility release: the axis tick role and SVG axis unit names moved from 16.5 to 18.15
user units, last-value labels from 18 to 19.8 (the canvas axis name is 19.8 CSS px), and
the plot margins from 88/30/28/62 to 97/33/31/68 (the dual right gutter from 156 to 172).
Every point, title, tick and legend text is
unchanged; only coordinate attributes differ. `home_code_list.html` and
`home_before_editorial.html` are unaffected (the home render carries no chart labels and
its CSS is external). All previous bytes stay in `pre_legibility/`; the earlier legibility
before/after hashes remain in
`docs/superpowers/handoff/reports/legibility-notebook/golden-deltas.json`, and this narrow
delta is recorded in `docs/superpowers/handoff/reports/legibility-release/type-increment.md`.

The approved 2026-11-17 legibility release deliberately recaptured `home_code_list.html`
and `charts/*.svg` against the same deterministic fixtures. Deltas: local font links,
native mobile navigation, Caderno entry, wrappable number grouping, wider SVG label margins
and inward endpoint anchors. No fixture observations, point/title/tick text or publisher
precision changed. All previous bytes are retained under `pre_legibility/`; before/after
hashes and text-comparison results are in
`docs/superpowers/handoff/reports/legibility-notebook/golden-deltas.json`.

`home_before_editorial.html` remains unchanged as the older historical reference.
Subsequent captures require another explicitly reviewed presentation delta. The historical
pre-legibility capture procedure and rationale follow below.

# Home page golden (pre-editorial)

`home_before_editorial.html` is the home page rendered by commit `7e563b2` (the deployed public
site, before the editorial composition existed), against a database built by
`tests/app/conftest.py::build` with its fixed timestamps. It stays the historical reference and
is never edited. `home_code_list.html` started as a copy of it and has three audited deltas:
the Comparações navigation item added by the comparisons release, the single absolute
`<a href="https://joao.date/dados/admin/">Admin</a>` footer anchor added by the Admin-entry
slice (both public hosts use the same absolute URL; no `X-Forwarded-Prefix` applies to it),
and the relative `<a href="/paginas">Páginas</a>` footer anchor added by the statistics CMS
(index discoverability; `NAV` is unchanged, so the anchor exists only in `footer-links`, once,
rendered from the mount base on both hosts). Each footer delta is exactly one `<a>` element
plus its ` · ` separator; the nav capture also carries the whitespace line the nav loop emits
around it. The commit diff between the golden files shows those deltas and nothing else.

Both committed captures use ASCII hyphens after the owner's repository-wide
punctuation correction. Only U+2014 was replaced with `-`; neither capture was
rendered again, and its layout, values and navigation are unchanged. Reproducing
the original capture below applies that same explicit text replacement.

It exists for one assertion: with migration 0018 applied and the three `editorial_*` tables
empty, the home must be **byte-identical** to what the site served before this feature. That is
the deploy's entire safety argument and the documented rollback (delete the rows), so it is a
test, not a note.

Reproduce it (only if the committed file is ever lost):

```bash
git worktree add --detach /tmp/prumo-pre 7e563b2
cd /tmp/prumo-pre
~/projects/prumo-pipeline/.venv-ci/bin/python -c "
from pathlib import Path
from tests.app.conftest import build
from app.main import create_app
from fastapi.testclient import TestClient
build(Path('/tmp/golden.db'))
Path('/tmp/home.html').write_text(TestClient(create_app('/tmp/golden.db')).get('/').text.replace(chr(0x2014), '-'))
"
```

Do not regenerate it after the composition lands: the new code renders the same bytes only
because the composition is empty, and a fresh capture would make the test compare the new
render with itself.
