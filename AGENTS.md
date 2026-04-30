# AGENTS.md

> Para guidelines completas de arquitectura, convenções e ficheiros-chave, lê:
> **[`.github/copilot-instructions.md`](.github/copilot-instructions.md)**

## Quick Start

### Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/create_seed_db.py
```

### Testes
```bash
CAE_DB_PATH=seed_data/seed.duckdb pytest tests/ -m "not integration and not slow" -v
```

### Lint
```bash
ruff check app/ collectors/
```

### App local
```bash
CAE_DB_PATH=seed_data/seed.duckdb uvicorn app.main:app --port 8080 --reload
```

## Restrições
- DuckDB **read-only** — sempre `read_only=True` (ver `app/database.py`)
- Padrão de serviços: `build_*()` aggregação, `compute_*()` cálculo, `get_*()` queries
- Erros: retornar `{"error": "no data", "id": ..., "label": ...}` — nunca raise em dados ausentes
- Testes: correr antes de abrir PRs; unit tests usam `seed_data/seed.duckdb`
- Lint: `ruff check` antes de push; CI falha em erros

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **prumo** (5639 symbols, 12363 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/prumo/context` | Codebase overview, check index freshness |
| `gitnexus://repo/prumo/clusters` | All functional areas |
| `gitnexus://repo/prumo/processes` | All execution flows |
| `gitnexus://repo/prumo/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
