"""One-shot headline generation via Claude Opus — cached 6h."""
import os
import json
import time
from .interpret import ANTHROPIC_KEY, _load_ideology

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

    from .prompt_loader import load_prompt
    instructions = load_prompt(f"headline_{output_language}") or load_prompt("headline_pt")

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
        with open(analysis_cache_path, encoding="utf-8") as _f:
            cache = json.load(_f)
        # Try to find exact match for this lens+period
        if lens_key and updated:
            for version in ("v23", "v21", "v20", "v19"):
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
    Return Ollama-generated headline derived from Painel analysis.
    Disk-cached per data period + lens + language, TTL 6h.
    Returns None headline on failure — JS falls back to rule-based title.
    """

    # Load cache
    cache = {}
    try:
        if os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, encoding="utf-8") as _f:
                cache = json.load(_f)
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

    from .prompt_loader import load_prompt
    analysis_instruction = load_prompt(f"headline_from_analysis_{output_language}") or load_prompt("headline_from_analysis_pt")

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
        from .claude_client import call_ollama
        raw = call_ollama(user_msg, num_predict=2048, timeout=120)
        headline = raw.strip().strip('"').strip("'").replace("\\n", "\n")

        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cache[cache_key] = {
            "headline": headline,
            "generated_at": generated_at,
            "ts": now,
            "model": "kimi-k2.5:cloud",
            "lens": lens_key,
            "output_language": output_language,
            "source_type": "sonnet-analysis" if sonnet_text else "raw-kpis",
        }
        source = "sonnet-analysis" if sonnet_text else "raw-kpis"
        print(f"[painel_headline] generated from {source}: {headline!r}", flush=True)

        try:
            with open(_CACHE_PATH, "w", encoding="utf-8") as _f:
                json.dump(cache, _f, ensure_ascii=False, indent=2)
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
