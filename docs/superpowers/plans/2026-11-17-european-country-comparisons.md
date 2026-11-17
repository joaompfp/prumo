# European country comparisons implementation plan

> For Hermes: use subagent-driven-development task by task with independent specification and then quality review.

Goal: add electricity and economic comparisons of Portugal, Spain, France, Germany and Italy without changing observations or ingestion.

Architecture: first extend the authoritative comparison preparation/rendering boundary, retaining all pair/CMS behavior. Then add a curated country read service, routes and templates consuming that boundary.

Tech stack: existing Python/FastAPI/Jinja/SQLite, inline SVG, local pinned ECharts, Carmim/paper identity and local Lato/Schola fonts.

Authority: docs/superpowers/specs/2026-11-17-european-country-comparisons-design.md.

## Task 1: Shared multi-series preparation and rendering

Ownership: app/chart_model.py, app/charts.py, app/interactive.py, tools/charts/src/adapter.js, generated chart bundle/manifest/notice, static/css/prumo.css chart styles, focused chart tests. Leave app/reads.py, main.py, catalogues and CMS untouched.

Write regression assertions for existing comparison SVG and payload, run them against baseline. Refactor comparison internals into an ordered, bounded series/value representation with compatibility access for current pair consumers, one shared or the existing dual axis. Commit passing refactor before adding multi-series behavior. Then add a shared-axis factory for three-to-six series from period/values tuples and short labels; same domains/ticks/break helper, exact value tokens, no overlapping last marks. Renderer loops across ordered values; a group style carries Carmim Portugal, distinct other colours plus patterns. Pair output remains identical. Adapter must honor series style and explicit axis mapping without changing existing line/pair payloads; rebuild deterministically using tools/charts. Add focused N=3/5/6, invalid count/mismatched shape/nonfinite, gaps, one point and hostile-label tests.

Commands: .venv-ci/bin/python -m pytest tests/app/test_chart_model.py tests/app/test_interactive.py tests/app/test_comparisons.py -q plus the relevant new tests; scoped ruff; pinned chart build. Report actual red/green receipts. Only commit owned paths; do not push. Independent spec then quality approval before Task2.

## Task 2: Curated country pages

Ownership: new app/country_comparisons.py and template, app/reads.py shared preparation wrapper only if required, app/main.py route registration, comparison index/template integration, presentation/__init__.py, presentation/catalog/pt.py, catalogue tests and new tests/app/test_country_comparisons.py. Reuse the Task1 engine; no copied scale or formatting logic. Never add SQL in app/.

Catalogue defines the three families and five fixed countries with reviewed meaning/caveats and short geography labels. Use current public Db methods to read one snapshot; all sides required, matching dimensions and family. Expose period alignment, dropped counts, exact values/statuses, full table, latest common summary, series links and per-side provenance. Index groups must not require preparing a whole graph; use a bounded read model. Add notebook link for selected series via existing helper. Unknown slug404, malformed authored definition503, every URL prefix safe. Keep operational ids only in links.

Start with failing tests for index and route plus eligibility/mismatch/provenance regressions. Cover all15 registry identities and native-dimension equality. Run group+pair+CMS affected tests and ruff. Commit only owned paths, no push or deployment. Independent spec then quality approval.

## Task 3: Real-data and browser acceptance

Controller owns the consistent snapshot, server lifecycle, evidence and final run. Starting snapshot: /home/joao/.hermes/cache/scratch/prumo-eu-comparisons/production-copy.sqlite3 (online backup from read-only URI, schema0019, quick_check ok and zero FK violations). Use a development server bound to localhost. Exercise all three groups and the existing pairs, both prefixes, exact pointer/touch/keyboard and fallback, four widths, light/dark/print as applicable; inspect screenshots through vision. Fingerprint all tables before and after. Preserve failures and corrective receipts. Run full .venv-ci/bin/python -m pytest tests -q and ruff app/ ingest/ presentation/ backoffice/ tests/. Require independent integration review on frozen runtime. No production writes.

## Task 4: Delivery and roadmap

Document usage, comparison scope and installation boundary. Update technical HANDOFF and /home/joao/vaults/projects/prumo/roadmap-e-implementacao.md without rewriting historical plans. Commit checked task-owned evidence, including ignored images explicitly. Verify code/templates/compiled assets from an unused detached committed checkout, then push pipeline-rebuild and read back remote exact SHA. Do not merge main or install without release authorization; previous larger-type/Caderno candidate remains part of the branch release.
