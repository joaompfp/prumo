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


def _build_headline_prompt(sections: list, lens: str = None, custom_ideology: str = None, output_language: str = "pt") -> str | None:
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

    # Language-specific headline instructions
    lang_instructions = {
        "pt": "Com base nos dados acima, escreve uma manchete jornalística em português europeu (PT-PT):\nLINHA 1 (título): máx. 12 palavras — os factos mais marcantes com números\nLINHA 2 (subtítulo): máx. 10 palavras — contexto ou contraste relevante\nLINHA 3 (2º subtítulo, opcional): máx. 10 palavras — se houver tensão adicional\n\nSem aspas, sem ponto final, sem prefixos como 'Título:', 'Linha 1:' etc.\nSepara as linhas com \\n apenas. Âncora tudo nos números. Começa directamente.",
        "cv": "Baseadu na datus aba, scriva un tituláu jornalistiku em kriolu di São Vicente (barlavento):\nLINHA 1 (tituláu): máx. 12 palavras — es factu mais merkanti ku numeru\nLINHA 2 (subtituláu): máx. 10 palavras — kontestu u kontras relevanti\nLINHA 3 (2º subtituláu, opsionál): máx. 10 palavras — se tê tensãu adisionál\n\nSem aspa, sem pontu finál, sem prefixa kumá 'Tituláu:', 'Linha 1:' etc.\nSepara na linhas ku \\n só. Ancra tudo na numeru. Kumesa direktamenti.",
        "fr": "Sur la base des données ci-dessus, écrivez un titre journalistique en français (France):\nLIGNE 1 (titre): max. 12 mots — les faits les plus marquants avec chiffres\nLIGNE 2 (sous-titre): max. 10 mots — contexte ou contraste pertinent\nLIGNE 3 (2e sous-titre, optionnel): max. 10 mots — s'il y a tension supplémentaire\n\nSans guillemets, sans point final, sans préfixes comme 'Titre:', 'Ligne 1:' etc.\nSéparez les lignes par \\n seulement. Ancrez tout aux chiffres. Commencez directement.",
        "es": "En función de los datos anteriores, escriba un titular periodístico en español (castellano):\nLÍNEA 1 (titular): máx. 12 palabras — los hechos más relevantes con números\nLÍNEA 2 (subtítulo): máx. 10 palabras — contexto o contraste relevante\nLÍNEA 3 (2º subtítulo, opcional): máx. 10 palabras — si hay tensión adicional\n\nSin comillas, sin punto final, sin prefijos como 'Titular:', 'Línea 1:' etc.\nSepare las líneas con \\n únicamente. Ancle todo en números. Comience directamente.",
        "en": "Based on the data above, write a journalistic headline in English (British):\nLINE 1 (headline): max. 12 words — the most striking facts with numbers\nLINE 2 (subheadline): max. 10 words — relevant context or contrast\nLINE 3 (2nd subheadline, optional): max. 10 words — if there's additional tension\n\nNo quotes, no full stop, no prefixes like 'Headline:', 'Line 1:' etc.\nSeparate lines with \\n only. Anchor everything to numbers. Start directly.",
    }

    instructions = lang_instructions.get(output_language, lang_instructions["pt"])

    return (
        f"{ideology}\n\n"
        "---\n\n"
        f"{instructions}\n\n"
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


def get_painel_headline(sections: list, updated: str, force: bool = False, lens: str = None, custom_ideology: str = None, output_language: str = "pt") -> dict:
    """
    Return Claude Opus headline derived from Sonnet analysis.
    Disk-cached per data period + lens + language, TTL 6h.
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
    cache_key = f"headline:v4:{updated}:{lens_key}:{output_language}"
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

    # Language-specific analysis headline instructions
    analysis_instructions = {
        "pt": "Com base nesta análise económica sobre Portugal, escreve uma manchete jornalística em português europeu (PT-PT):\nLINHA 1 (título): máx. 12 palavras — os factos mais marcantes com números\nLINHA 2 (subtítulo): máx. 10 palavras — contexto ou contraste relevante\nLINHA 3 (2º subtítulo, opcional): máx. 10 palavras — se houver tensão adicional\n\nSem aspas, sem ponto final, sem prefixos. Separa as linhas com \\n. Âncora tudo nos números. Começa directamente com a manchete.",
        "cv": "Baseadu neta analizu ekonomiku sôbri Portugál, scriva un tituláu jornalistiku em kriolu:\nLINHA 1 (tituláu): máx. 12 palavras — es factu mais merkanti ku numeru\nLINHA 2 (subtituláu): máx. 10 palavras — kontestu u kontras relevanti\nLINHA 3 (2º subtituláu, opsionál): máx. 10 palavras — se tê tensãu adisionál\n\nSem aspa, sem prefixu, sem ponto finál. Separa na linhas ku \\n. Ancra tudo na numeru. Kumesa direktamenti.",
        "fr": "En fonction de cette analyse économique sur le Portugal, écrivez un titre journalistique en français (France):\nLIGNE 1 (titre): max. 12 mots — les faits les plus marquants avec chiffres\nLIGNE 2 (sous-titre): max. 10 mots — contexte ou contraste pertinent\nLIGNE 3 (2e sous-titre, optionnel): max. 10 mots — s'il y a tension supplémentaire\n\nSans guillemets, sans point final, sans préfixes. Séparez les lignes par \\n. Ancrez tout aux chiffres. Commencez directement.",
        "es": "En función de este análisis económico sobre Portugal, escriba un titular periodístico en español (castellano):\nLÍNEA 1 (titular): máx. 12 palabras — los hechos más relevantes con números\nLÍNEA 2 (subtítulo): máx. 10 palabras — contexto o contraste relevante\nLÍNEA 3 (2º subtítulo, opcional): máx. 10 palabras — si hay tensión adicional\n\nSin comillas, sin punto final, sin prefijos. Separe las líneas con \\n. Ancle todo en números. Comience directamente.",
        "en": "Based on this economic analysis of Portugal, write a journalistic headline in English (British):\nLINE 1 (headline): max. 12 words — the most striking facts with numbers\nLINE 2 (subheadline): max. 10 words — relevant context or contrast\nLINE 3 (2nd subheadline, optional): max. 10 words — if there's additional tension\n\nNo quotes, no full stop, no prefixes. Separate lines with \\n. Anchor everything to numbers. Start directly."
    }
    analysis_instruction = analysis_instructions.get(output_language, analysis_instructions["pt"])

    if sonnet_text:
        # Ask Opus to distil the analysis into a headline
        user_msg = (
            f"{ideology}\n\n---\n\n"
            f"{analysis_instruction}\n\n"
            f"ANÁLISE:\n{sonnet_text[:3000]}"
        )
    else:
        # Fallback: use raw KPI data with ideology framing
        user_msg = _build_headline_prompt(sections, lens=lens, custom_ideology=custom_ideology, output_language=output_language)
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


def generate_all_headlines(sections: list, updated: str, lenses: list = None, languages: list = None) -> dict:
    """
    Generate headlines for all lenses × languages combinations.
    Returns dict with results: {cache_key: {headline, generated_at, cached}, ...}
    Use this for batch pre-generation (called during painel rebuild).
    """
    if not lenses:
        lenses = ["cae", "pcp", "ps", "be", "livre", "pan", "ad", "il", "chega", "neutro"]
    if not languages:
        languages = ["pt", "cv", "fr", "es", "en"]

    results = {}
    total = len(lenses) * len(languages)
    count = 0

    print(f"[painel_headline] batch generating {total} headlines ({len(lenses)} lenses × {len(languages)} languages)...", flush=True)

    for lens in lenses:
        for lang in languages:
            count += 1
            try:
                result = get_painel_headline(sections, updated, force=True, lens=lens, output_language=lang)
                cache_key = f"headline:v4:{updated}:{lens}:{lang}"
                results[cache_key] = result
                status = "✓" if result.get("headline") else "✗"
                print(f"[painel_headline] [{count}/{total}] {status} {lens:8s} {lang} — {result.get('headline', '')[:60]}", flush=True)
            except Exception as e:
                print(f"[painel_headline] [{count}/{total}] ✗ {lens:8s} {lang} — ERROR: {e}", flush=True)
                results[f"headline:v4:{updated}:{lens}:{lang}"] = {"headline": None, "error": str(e)}

    print(f"[painel_headline] batch complete: {sum(1 for r in results.values() if r.get('headline'))} succeeded, {sum(1 for r in results.values() if not r.get('headline'))} failed", flush=True)
    return results
