"""One-shot headline generation via Claude Opus — cached 6h."""
import os
import json
import time
from .interpret import ANTHROPIC_KEY, _opener, _load_ideology
from urllib.request import Request

CAE_DB_PATH = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
_DATA_DIR = os.path.dirname(CAE_DB_PATH)
_CACHE_PATH = os.path.join(_DATA_DIR, "painel-headline-cache.json")
_CACHE_TTL_SECONDS = 6 * 3600  # 6 hours


def _build_headline_prompt(sections: list, lens: str = None, custom_ideology: str = None) -> str | None:
    if lens:
        from .ideology_lenses import get_lens_prompt
        ideology = get_lens_prompt(lens, custom_ideology=custom_ideology)
    else:
        ideology = _load_ideology()
    lines = []
    for section in sections:
        title = section.get("title", "Indicadores")
        for k in section.get("kpis", []):
            if k.get("value") is None:
                continue
            yoy_str = f", var. anual: {k['yoy']:+.1f}{k.get('yoy_unit') or '%'}" if k.get("yoy") is not None else ""
            lines.append(f"  - {k['label']} ({title}): {k['value']} {k.get('unit', '')}{yoy_str}")

    if not lines:
        return None

    kpi_block = "\n".join(lines)
    return (
        f"{ideology}\n\n"
        "---\n\n"
        "Com base nos dados acima, escreve uma manchete jornalística em PT-PT:\n"
        "LINHA 1 (título): máx. 12 palavras — os factos mais marcantes com números\n"
        "LINHA 2 (subtítulo): máx. 10 palavras — contexto ou contraste relevante\n"
        "LINHA 3 (2º subtítulo, opcional): máx. 10 palavras — se houver tensão adicional\n\n"
        "Sem aspas, sem ponto final, sem prefixos como 'Título:', 'Linha 1:' etc.\n"
        "Separa as linhas com \\n apenas. Âncora tudo nos números. Começa directamente.\n\n"
        f"{kpi_block}"
    )


def _get_sonnet_analysis_text(lens_key: str = None, updated: str = None) -> str | None:
    """Load the Sonnet analysis from its cache, optionally for a specific lens+period."""
    import os, json
    analysis_cache_path = os.path.join(_DATA_DIR, "painel-analysis-cache.json")
    try:
        cache = json.loads(open(analysis_cache_path, encoding="utf-8").read())
        # Try to find exact match for this lens+period
        if lens_key and updated:
            for version in ("v21", "v20", "v19"):
                key = f"painel:{version}:{updated}:{lens_key}"
                if key in cache and cache[key].get("text"):
                    return cache[key]["text"]
        # Fallback: find most recent entry
        entries = [(k, v) for k, v in cache.items() if v.get("text")]
        if not entries:
            return None
        latest = max(entries, key=lambda x: x[1].get("generated_at", ""))
        return latest[1]["text"]
    except Exception:
        return None


def get_painel_headline(sections: list, updated: str, force: bool = False, lens: str = None, custom_ideology: str = None) -> dict:
    """
    Return Claude Opus headline derived from Sonnet analysis.
    Disk-cached per data period + lens, TTL 6h.
    Returns None headline on failure — JS falls back to rule-based title.
    """
    if not ANTHROPIC_KEY:
        return {"headline": None, "cached": False, "error": "API key not configured"}

    # Load cache
    cache = {}
    try:
        if os.path.exists(_CACHE_PATH):
            cache = json.loads(open(_CACHE_PATH, encoding="utf-8").read())
    except Exception:
        cache = {}

    import hashlib as _hl
    lens_key = lens or "default"
    if lens == "custom" and custom_ideology:
        lens_key = "custom:" + _hl.md5(custom_ideology.encode()).hexdigest()[:8]
    cache_key = f"headline:v3:{updated}:{lens_key}"
    now = time.time()

    if not force and cache_key in cache:
        entry = cache[cache_key]
        age = now - entry.get("ts", 0)
        if age < _CACHE_TTL_SECONDS:
            return {
                "headline": entry["headline"],
                "generated_at": entry["generated_at"],
                "cached": True,
            }

    # Build ideology context for the headline
    if lens:
        from .ideology_lenses import get_lens_prompt
        ideology = get_lens_prompt(lens, custom_ideology=custom_ideology)
    else:
        ideology = _load_ideology()

    # Try to use existing analysis (for this lens) as context
    sonnet_text = _get_sonnet_analysis_text(lens_key=lens_key, updated=updated)

    if sonnet_text:
        # Ask Opus to distil the analysis into a headline
        user_msg = (
            f"{ideology}\n\n---\n\n"
            "Com base nesta análise económica sobre Portugal, escreve uma manchete jornalística em PT-PT:\n"
            "LINHA 1 (título): máx. 12 palavras — os factos mais marcantes com números\n"
            "LINHA 2 (subtítulo): máx. 10 palavras — contexto ou contraste relevante\n"
            "LINHA 3 (2º subtítulo, opcional): máx. 10 palavras — se houver tensão adicional\n\n"
            "Sem aspas, sem ponto final, sem prefixos. Separa as linhas com \\n. "
            "Âncora tudo nos números. Começa directamente com a manchete.\n\n"
            f"ANÁLISE:\n{sonnet_text[:3000]}"
        )
    else:
        # Fallback: use raw KPI data with ideology framing
        user_msg = _build_headline_prompt(sections, lens=lens, custom_ideology=custom_ideology)
        if not user_msg:
            return {"headline": None, "cached": False, "error": "No data available"}

    try:
        body = json.dumps({
            "model": "claude-opus-4-6",
            "max_tokens": 120,
            "messages": [{"role": "user", "content": user_msg}],
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

        with _opener.open(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text_parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            headline = "\n".join(text_parts).strip().strip('"').strip("'").replace("\\n", "\n")

        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cache[cache_key] = {
            "headline": headline,
            "generated_at": generated_at,
            "ts": now,
        }
        source = "sonnet-analysis" if sonnet_text else "raw-kpis"
        print(f"[painel_headline] generated from {source}: {headline!r}", flush=True)

        try:
            open(_CACHE_PATH, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[painel_headline] cache write error: {e}", flush=True)

        return {"headline": headline, "generated_at": generated_at, "cached": False}

    except Exception as exc:
        print(f"[painel_headline] error: {exc}", flush=True)
        return {"headline": None, "cached": False, "error": str(exc)}
