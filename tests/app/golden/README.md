# Home page golden (pre-editorial)

`home_before_editorial.html` is the home page rendered by commit `7e563b2` (the deployed public
site, before the editorial composition existed), against a database built by
`tests/app/conftest.py::build` with its fixed timestamps.

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
Path('/tmp/home.html').write_text(TestClient(create_app('/tmp/golden.db')).get('/').text)
"
```

Do not regenerate it after the composition lands: the new code renders the same bytes only
because the composition is empty, and a fresh capture would make the test compare the new
render with itself.
