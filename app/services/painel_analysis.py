"""Sonnet analysis for the Painel section — one-shot, disk-cached."""
import os
import re
import json
import time
from .interpret import _load_ideology, _opener, ANTHROPIC_KEY
from urllib.request import Request

CAE_DB_PATH = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
_DATA_DIR = os.path.dirname(CAE_DB_PATH)
_CACHE_PATH = os.path.join(_DATA_DIR, "painel-analysis-cache.json")


def _parse_section_links(text: str) -> tuple:
    """Extract SECTION_LINKS:{...} from text. Uses raw_decode for correct nested-JSON handling."""
    marker = '\nSECTION_LINKS:'
    idx = text.rfind(marker)
    if idx == -1:
        return text.strip(), {}
    try:
        json_start = text.index('{', idx + len(marker))
        links, _ = json.JSONDecoder().raw_decode(text, json_start)
        return text[:idx].strip(), links
    except Exception:
        return text[:idx].strip(), {}


def _build_painel_prompt(sections: list, updated: str) -> str:
    ideology = _load_ideology()

    section_blocks = []
    section_names = []
    for section in sections:
        title = section.get("title", "Indicadores")
        kpis = section.get("kpis", [])
        lines = []
        for k in kpis:
            if k.get("value") is None:
                continue
            yoy_str = f", var. anual: {k['yoy']:+.1f}{k.get('yoy_unit') or '%'}" if k.get("yoy") is not None else ""
            lines.append(
                f"  - {k['label']} ({k.get('source','?')}): {k['value']} {k.get('unit','')}{yoy_str}"
            )
        if lines:
            section_blocks.append(f"### {title}\n" + "\n".join(lines))
            section_names.append(title)

    if not section_blocks:
        return None

    sections_list = ", ".join(f'"{s}"' for s in section_names)

    n_sections = len(section_names)
    # ~120 tok/section (strictly 3 short sentences) + ~500 tok for links JSON
    token_budget = n_sections * 120 + 500

    instruction = (
        f"Tens um orçamento ESTRITO de {token_budget} tokens para análise + links.\n"
        "NÃO escrevas notas, planos, separadores (---) nem texto em inglês. Começa directamente com a análise.\n\n"
        "PASSO 1 — Pesquisa (silenciosa): para cada secção, pesquisa 2 artigos recentes (últimos 2 meses). Máx. 6 pesquisas.\n\n"
        "PASSO 2 — Análise em **português europeu** (sem brasileirismos), período: " + updated + ".\n"
        "Para cada secção (###), escreve EXACTAMENTE 3 frases curtas com **negrito** nos conceitos-chave.\n"
        "Interpreta impacto real para trabalhadores e famílias — não repitas números.\n"
        "Título inline em negrito (ex: **Custo de Vida:**). Linha em branco entre parágrafos.\n"
        "Termina com **Síntese:** (máx. 2 frases transversais). Sem listas, sem cabeçalhos.\n\n"
        "PASSO 3 — OBRIGATÓRIO: imediatamente após a última frase, na linha seguinte, escreve:\n"
        f'SECTION_LINKS:{{"secção":[{{"url":"https://...","title":"..."}}]}}\n'
        f"Inclui TODAS estas secções: {sections_list}. 2 links por secção. "
        "O SECTION_LINKS deve ser a ÚLTIMA coisa que escreves."
    )

    return f"{ideology}\n\n{instruction}\n\n" + "\n\n".join(section_blocks)


def get_painel_analysis(sections: list, updated: str, force: bool = False) -> dict:
    """
    Return Sonnet analysis of Painel sections.
    Results are cached to disk keyed by `updated`. Cache survives restarts.
    Pass force=True to regenerate even if cached.
    Cache key versioned (v3) to invalidate old entries without section_links.
    """
    if not ANTHROPIC_KEY:
        return {"text": None, "cached": False, "error": "API key not configured"}

    # Load existing cache
    cache = {}
    try:
        if os.path.exists(_CACHE_PATH):
            cache = json.loads(open(_CACHE_PATH, encoding="utf-8").read())
    except Exception:
        cache = {}

    cache_key = f"painel:v7:{updated}"
    if not force and cache_key in cache:
        entry = cache[cache_key]
        return {
            "text": entry["text"],
            "section_links": entry.get("section_links", {}),
            "generated_at": entry["generated_at"],
            "generation_ms": entry.get("generation_ms"),
            "data_period": updated,
            "cached": True,
        }

    prompt = _build_painel_prompt(sections, updated)
    if not prompt:
        return {"text": None, "cached": False, "error": "No KPI data available"}

    try:
        body = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 3200,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        req = Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

        t0 = time.time()
        with _opener.open(req, timeout=180) as resp:
            data = json.loads(resp.read())
            # Collect all text blocks (response may include web_search blocks)
            text_parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            full_text = "\n".join(text_parts).strip()
        generation_ms = round((time.time() - t0) * 1000)

        text, section_links = _parse_section_links(full_text)

        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cache[cache_key] = {
            "text": text,
            "section_links": section_links,
            "generated_at": generated_at,
            "generation_ms": generation_ms,
        }
        print(f"[painel_analysis] generated in {generation_ms}ms for period {updated}", flush=True)

        try:
            open(_CACHE_PATH, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[painel_analysis] cache write error: {e}", flush=True)

        return {
            "text": text,
            "section_links": section_links,
            "generated_at": generated_at,
            "generation_ms": generation_ms,
            "data_period": updated,
            "cached": False,
        }

    except Exception as exc:
        print(f"[painel_analysis] error: {exc}", flush=True)
        return {"text": None, "cached": False, "error": str(exc)}
