# Home page golden (pre-editorial)

`home_before_editorial.html` is the home page rendered by commit `7e563b2` (the deployed public
site, before the editorial composition existed), against a database built by
`tests/app/conftest.py::build` with its fixed timestamps. It stays the historical reference and
is never edited. `home_code_list.html` started as a copy of it and has two audited deltas: the
Comparações navigation item added by the comparisons release, and the single absolute
`<a href="https://joao.date/dados/admin/">Admin</a>` footer anchor added by the Admin-entry
slice (both public hosts use the same absolute URL; no `X-Forwarded-Prefix` applies to it).

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
