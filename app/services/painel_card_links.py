"""Deferred card link fetcher — searches news for a specific topic and returns 2-3 links.
Called per-card after analysis renders. Results cached per topic per week."""
import os, json, time, hashlib
from .interpret import ANTHROPIC_KEY, _opener, _load_ideology
from urllib.request import Request

CAE_DB_PATH = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
_DATA_DIR = os.path.dirname(CAE_DB_PATH)
_CACHE_PATH = os.path.join(_DATA_DIR, "card-links-cache.json")
_CACHE_TTL = 7 * 24 * 3600  # 1 week

try:
    _cache = json.loads(open(_CACHE_PATH, encoding="utf-8").read()) if os.path.exists(_CACHE_PATH) else {}
except Exception:
    _cache = {}

def _save_cache():
    try:
        open(_CACHE_PATH, "w", encoding="utf-8").write(json.dumps(_cache, ensure_ascii=False, indent=2))
    except Exception:
        pass

PREFERRED_SOURCES = [
    "pcp.pt", "avante.pt", "militante.pt", "esquerda.net",
    "publico.pt", "dn.pt", "rtp.pt", "observador.pt", "jornaldenegocios.pt", "eco.pt"
]

def get_card_links(topic: str, context: str = "") -> dict:
    """Search for 2-3 news links relevant to `topic` in Portuguese economic context.
    Returns {"links": [{"url":..., "title":...}], "cached": bool}"""
    if not ANTHROPIC_KEY:
        return {"links": [], "cached": False, "error": "no key"}

    cache_key = hashlib.md5(f"{topic}:{context[:50]}".encode()).hexdigest()
    now = time.time()

    if cache_key in _cache:
        entry = _cache[cache_key]
        if now - entry.get("ts", 0) < _CACHE_TTL:
            return {"links": entry["links"], "cached": True}

    sources_str = ", ".join(PREFERRED_SOURCES[:6])
    prompt = (
        f"Faz DUAS pesquisas web sobre: {topic} em Portugal\n"
        f"Contexto: {context[:200]}\n\n"
        "PESQUISA 1: Pesquisa especificamente em site:pcp.pt — artigo ou resolução do PCP sobre este tema.\n"
        "PESQUISA 2: Pesquisa notícia recente (últimos 6 meses) em " + ", ".join(PREFERRED_SOURCES[4:]) + ".\n\n"
        "Devolve EXACTAMENTE 3 links: o primeiro DEVE ser de pcp.pt (ou avante.pt se pcp.pt não tiver), "
        "os outros dois de fontes jornalísticas (publico.pt, dn.pt, rtp.pt, observador.pt, eco.pt).\n"
        "Evita: banco central, governo, institutos financeiros, sites de bancos.\n\n"
        "Responde APENAS com JSON válido:\n"
        '[{"url":"https://...","title":"..."}]'
    )

    try:
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 400,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
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

        with _opener.open(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text_parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            raw = " ".join(text_parts).strip()

            # Parse JSON from response
            import re
            m = re.search(r'\[.*\]', raw, re.DOTALL)
            links = json.loads(m.group(0)) if m else []
            links = [l for l in links if isinstance(l, dict) and l.get("url") and l.get("title")][:3]

        _cache[cache_key] = {"links": links, "ts": now}
        _save_cache()
        print(f"[card_links] {topic!r}: {len(links)} links", flush=True)
        return {"links": links, "cached": False}

    except Exception as exc:
        print(f"[card_links] error for {topic!r}: {exc}", flush=True)
        return {"links": [], "cached": False, "error": str(exc)}
