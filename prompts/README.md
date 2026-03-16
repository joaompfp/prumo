# Prumo — Prompt Templates

All LLM prompts are externalized here for easy editing without touching Python code.

## Files

| File | Used by | Model | Purpose |
|------|---------|-------|---------|
| `headline_<lang>.txt` | `painel_headline.py` | Opus | KPI-based headline (fallback when no Sonnet analysis) |
| `headline_from_analysis_<lang>.txt` | `painel_headline.py` | Opus | Headline from Sonnet analysis text |
| `painel_analysis.txt` | `painel_analysis.py` | Sonnet | Full Painel section analysis + META_JSON |
| `interpret.txt` | `interpret.py` | Haiku | Explorador/Análise tab chart interpretation |

Languages: `pt` (default), `cv` (kriolu), `fr`, `es`, `en`

## Placeholders

Templates use Python `str.format_map()`. Use `{placeholder}` for substitution, `{{` / `}}` for literal braces.

### headline_*.txt
No placeholders — used as-is.

### headline_from_analysis_*.txt
No placeholders — used as-is.

### painel_analysis.txt
| Placeholder | Description |
|-------------|-------------|
| `{lang_rule}` | Language enforcement rule (built per-language in Python) |
| `{token_budget}` | Max tokens for analysis (~200/section + 600) |
| `{search_hint}` | Party-specific search terms |
| `{updated}` | Data period (e.g. "2026-02") |
| `{lang_name}` | Language name (e.g. "português europeu (PT-PT)") |
| `{lang_code}` | Language code (e.g. "pt") |
| `{sections_list}` | Comma-separated section names |
| `{link_sources}` | Allowed news domains for this lens |
| `{ids_str}` | Indicator IDs available for section_charts |

### interpret.txt
| Placeholder | Description |
|-------------|-------------|
| `{indicator_labels}` | Quoted indicator names (e.g. `"Inflação", "Euribor"`) |
| `{lang_desc}` | Output language description |
| `{focus}` | Time horizon focus (e.g. "evolução conjuntural recente") |
| `{period_str}` | Period range (e.g. "2020-01 a 2026-12") |

## Ideology Prompts

Party/lens ideology prompts are separate — loaded from `/data/ideologies/<id>.txt` at runtime.
See `ideology_lenses.py` for the full lens registry.

## Editing

1. Edit the `.txt` file
2. Rebuild: `dc-jarbas-up`
3. Prompts are cached in memory — restart clears cache

For hot-reload without rebuild, mount `prompts/` as a volume and call the `/api/admin/reload-prompts` endpoint (if implemented).
