### Task 1: Tag the legacy UI, delete it, serve "Em manutenção"

**Files:**
- Delete: `app/routes/`, `app/services/`, `app/constants/`, `app/analytics.py`, `app/database.py`, `templates/`, `prompts/`, `stats_lib/`, `tests/routes/`, `tests/services/`, `tests/db/`, `tests/browser/`, `scripts/ai/`, `warm_cache.py`, `test_all_indicators.py`
- Modify: `app/main.py`, `Dockerfile`, `requirements.txt`, `CLAUDE.md`, `AGENTS.md`, delete `SETUP_NOTES.md`
- Create: `app/maintenance.py`, `tests/test_maintenance.py`
- Keep: `static/` (the apex `/static` route serves it), `collectors/` and `scripts/` until replaced by later tasks

**Interfaces:**
- Produces: `app.main.app` (FastAPI) answering `GET /healthz` → 200 `{"status":"ok"}` and every other `GET` path → 200 HTML containing `Em manutenção` (also under the `/dados` prefix, which Traefik strips).

- [ ] **Step 1:** `git tag legacy-ui-final` on current `main` (recoverable reference; do not push tags unless asked).
- [ ] **Step 2: Write failing test** `tests/test_maintenance.py`: `test_root_is_maintenance` (`GET /` → 200, `"Em manutenção" in text`), `test_deep_path_is_maintenance` (`GET /painel/xyz` → 200, same text), `test_healthz` (`GET /healthz` → 200 json `status == "ok"`), `test_no_claude_references` (walk the repo excluding `.git`, `venv`, `docs`, `tests`: no file contains `claude-max-proxy`, `ANTHROPIC`, `anthropic`).
- [ ] **Step 3: Run** `pytest tests/test_maintenance.py -v` → FAIL.
- [ ] **Step 4:** Delete the listed paths; rewrite `app/main.py` to create `app` with `/healthz` and a catch-all route returning `app.maintenance.PAGE` (static HTML string, `lang="pt-PT"`, uses `/static` favicon/CSS already present, no JS, no external requests). Remove `duckdb`, `pandas`, `pyarrow`, `Pillow`, `pytest-asyncio` from `requirements.txt` only if nothing left imports them (check `collectors/` first; leave them until Task 17 if still used).
- [ ] **Step 5:** Rewrite `CLAUDE.md`/`AGENTS.md` deploy sections: aliases are `dc-web-*` (not `dc-jarbas`), host is f0nix, remove token env var rows and `cae-dashboard` mentions; delete `SETUP_NOTES.md`.
- [ ] **Step 6: Run** `pytest tests/test_maintenance.py -v` → PASS; `grep -rIl -i "anthropic\|claude-max" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=docs` → empty.
- [ ] **Step 7:** On f0nix: `git pull` in `stacks/web/images/prumo`, `bash -lic "dc-web-up prumo"`; verify `curl -s https://cae.joao.date/ | grep "Em manutenção"` and `curl -s -o /dev/null -w "%{http_code}" https://joao.date/dados/` → 200.
- [ ] **Step 8: Commit** (`prumo: legacy UI removed, maintenance page`).

---

