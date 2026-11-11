# Task 1 report
Status: DONE_WITH_CONCERNS
Commits: prumo 031eb3b (branch pipeline-rebuild, pushed); infra repo (f0nix branch) 63b0af1. Tag legacy-ui-final -> a18a58a (local, not pushed).

## TDD
RED: `pytest tests/test_maintenance.py` -> collection error `ModuleNotFoundError: duckdb` (app.main imported legacy routes).
GREEN: `.venv-ci/bin/python -m pytest tests` -> 4 passed.
Intermediate: no_claude_references failed on .github/workflows/ci.yml (ANTHROPIC_API_KEY env) -> removed.

## Changes
Deleted: app/routes, services, constants, analytics.py, database.py, templates, prompts, stats_lib, tests/{routes,services,db,browser}, scripts/ai, scripts/enrich_new_indicators.py (ruling B), warm_cache.py, test_all_indicators.py, SETUP_NOTES.md.
Added: app/maintenance.py (PAGE), rewritten app/main.py (/healthz + catch-all), tests/test_maintenance.py.
Modified: Dockerfile (dropped COPY prompts/templates/stats_lib), requirements.txt (removed pandas, Pillow, pytest-asyncio, jinja2; kept duckdb, pyarrow (collectors/base.py), requests), app/config.py (dropped TEMPLATES_DIR), ci.yml (dropped ANTHROPIC_API_KEY), CLAUDE.md, AGENTS.md rewritten.

## Deploy (f0nix)
- infra compose: dropped templates mount, commit 63b0af1 (only that file committed; infra repo has other unrelated dirty files, untouched).
- pushed pipeline-rebuild; checked out on f0nix; dc-web-up prumo OK; container healthy.
- `curl https://cae.joao.date/ | grep "Em manutenção"` -> matches; `https://joao.date/dados/` -> 200; `/healthz` -> {"status":"ok"}.

## Concerns
- scripts/audit_nightly.py imports deleted app.services.quality and is still in the entrypoint.sh cron block (kept per ruling); it will fail nightly until a later task removes it. Likewise scripts/collect_scheduled.py etc. untouched.
- CI workflow still runs create_seed_db.py and `--cov=app`; may need a later update.
- f0nix images/prumo submodule pointer now on pipeline-rebuild (shows modified in infra repo status, was already ' M' before).
- static/i18n JSON still mention "anthropic" (excluded from scan per ruling); tests/README.md and OPENSOURCE.md too.
