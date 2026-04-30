# Claude Agent: Prumo Codebase

## Role

Edit and maintain Prumo — FastAPI + DuckDB + ECharts economic dashboard for Portugal.
Repo: `joaompfp/prumo` (this directory). Live: `https://cae.joao.date`

## Path Mapping

| Location | Container Path | Notes |
|----------|---------------|-------|
| `.` (this dir) | `/app` | Code: Python, JS, CSS, templates |
| `./appdata/` | `/data` | Runtime data (symlink, see below) |

### Appdata (`./appdata/` → `../../appdata/prumo/`)

Symlink to the runtime data dir, bind-mounted as `/data` in the container. Gitignored — **never commit appdata**.

| File | Purpose |
|------|---------|
| `cae-data.duckdb` | Main DB (read-only, 422+ indicators) |
| `site.json` | Runtime config (languages, paths, defaults) |
| `ideology.txt` | Active ideology lens text |
| `ideologies/` | Political lens files (one .txt per party) |
| `interpret-cache.json` | AI interpretation cache (30d TTL) |
| `painel-analysis-cache.json` | Painel IA analysis cache |
| `painel-headline-cache.json` | Headline cache (6h TTL) |
| `analytics.db` | SQLite usage tracking |
| `audit-log.jsonl` | Nightly audit trail |

## Deploy Workflow

All `dc-*` commands require aliases:

```bash
source ~/.bash_aliases
```

| Action | Command |
|--------|---------|
| **Build + deploy** | `dc-jarbas-up` |
| **Restart only** | `dc-jarbas restart prumo` |
| **Logs** | `dc-jarbas logs -f prumo` |
| **Shell** | `dc-jarbas exec prumo sh` |
| **Status** | `dc-jarbas ps` |
| **Recreate** | `dc-jarbas-rec prumo` |

**NEVER `dc-jarbas up -d`** — skips SOPS secret decryption and injection. Always `dc-jarbas-up`.

## Live Reload vs Rebuild

`app/`, `static/`, `templates/` are bind-mounted `:ro` — restart picks up changes:
```bash
source ~/.bash_aliases && dc-jarbas restart prumo
```

**Rebuild needed** (`dc-jarbas-up`) for:
`Dockerfile`, `requirements.txt`, `prompts/`, `scripts/`, `collectors/`, `seed_data/`, `stats_lib/`

## Testing

```bash
# In-container (production DB)
source ~/.bash_aliases && dc-jarbas exec prumo python -m pytest tests/ -x -q --tb=short

# Local (seed DB)
source venv/bin/activate
CAE_DB_PATH=seed_data/seed.duckdb pytest tests/ -m "not integration and not slow" -v
```

## Key Env Vars

| Var | Purpose |
|-----|---------|
| `CAE_DB_PATH` | DuckDB path (default `/data/cae-data.duckdb`) |
| `CAE_ANTHROPIC_TOKEN` | Claude API for AI interpretations |
| `ANALYTICS_DB_PATH` | Analytics SQLite (default `/data/analytics.db`) |

## Reference

- **`AGENTS.md`** — Local dev setup, coding constraints
- **`.github/copilot-instructions.md`** — Architecture, conventions, data flow
- **`TESTS.md`** — Test coverage roadmap
- **Compose files** — `/home/joao/docker/stacks/web/compose/prumo.yml` (+ `prumo.base.yml`)

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
