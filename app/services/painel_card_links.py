"""Deferred card link fetcher — searches news for a specific topic and returns 2-3 links.
Called per-card after analysis renders. Results cached per topic+lens per week.
Now lens-aware: includes party-specific source as first link."""
import os, json, time, hashlib
from .interpret import ANTHROPIC_KEY
from .ideology_lenses import get_lens_metadata, get_lens_link_sources

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

# Party-specific search sites (first link should come from these)
_PARTY_SITES = {
    "pcp":   ["pcp.pt", "avante.pt", "abrilabril.pt"],
    "cae":   ["pcp.pt", "avante.pt", "abrilabril.pt"],
    "be":    ["esquerda.net", "blfranciscomiguel.pt"],
    "livre": ["partidolivre.pt"],
    "pan":   ["pan.com.pt"],
    "ps":    ["ps.pt"],
    "ad":    ["psd.pt"],
    "il":    ["liberal.pt"],
    "chega": ["partidochega.pt"],
}

_NEWS_SOURCES = ["publico.pt", "rtp.pt", "dn.pt", "observador.pt", "expresso.pt", "eco.sapo.pt", "jornaldenegocios.pt"]

def get_card_links(topic: str, context: str = "", lens: str = "cae") -> dict:
    """Search for 3 news links relevant to `topic`.
    Link 1: party-specific source for this lens.
    Links 2-3: general news sources.
    Returns {"links": [{"url":..., "title":...}], "cached": bool}"""
    # ── LLM DISABLED: stub mode while validating charts ──
    return {"links": [], "cached": False, "error": "LLM disabled — chart validation mode"}
    # ── END STUB ──

    if not ANTHROPIC_KEY:
        return {"links": [], "cached": False, "error": "no key"}

    cache_key = hashlib.md5(f"{lens}:{topic}:{context[:50]}".encode()).hexdigest()
    now = time.time()

    if cache_key in _cache:
        entry = _cache[cache_key]
        if now - entry.get("ts", 0) < _CACHE_TTL:
            return {"links": entry["links"], "cached": True}

    # Build lens-aware search prompt
    meta = get_lens_metadata(lens)
    party_name = meta.get("party", "") if meta else ""
    party_sites = _PARTY_SITES.get(lens, [])
    party_site_str = " OR ".join(f"site:{s}" for s in party_sites) if party_sites else ""

    if party_name and party_sites:
        search_1 = (
            f"PESQUISA 1: Pesquisa em {party_sites[0]} — artigo, resolução ou posição "
            f"do {party_name} sobre este tema económico.\n"
        )
        link_1_instruction = (
            f"o primeiro link DEVE ser de {' ou '.join(party_sites[:2])} "
            f"(posição do {party_name} sobre o tema)"
        )
    else:
        search_1 = "PESQUISA 1: Pesquisa artigo de opinião ou análise sobre este tema.\n"
        link_1_instruction = "o primeiro link deve ser análise/opinião sobre o tema"

    prompt = (
        f"Faz DUAS pesquisas web sobre: {topic} em Portugal\n"
        f"Contexto: {context[:200]}\n\n"
        f"{search_1}"
        f"PESQUISA 2: Pesquisa notícia recente (últimos 6 meses) em "
        f"{', '.join(_NEWS_SOURCES[:5])}.\n\n"
        f"Devolve EXACTAMENTE 3 links: {link_1_instruction}, "
        f"os outros dois de fontes jornalísticas ({', '.join(_NEWS_SOURCES[:4])}).\n"
        "Evita: banco central, governo, institutos financeiros, sites de bancos.\n\n"
        "Responde APENAS com JSON válido:\n"
        '[{"url":"https://...","title":"..."}]'
    )

    try:
        from .claude_client import search_web

        raw_result = search_web(prompt, max_uses=5, max_tokens=400, timeout=30)
        raw = raw_result["text"]

        # Parse JSON from response (existing logic)
        import re
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        links = json.loads(m.group(0)) if m else []
        links = [l for l in links if isinstance(l, dict) and l.get("url") and l.get("title")][:3]

        # Validate URLs — drop unreachable/404
        import urllib.request as _ur, concurrent.futures as _cf
        def _check(lnk):
            url = lnk["url"]
            ua = {"User-Agent": "Mozilla/5.0 (compatible; PrumoBot/1.0)"}
            try:
                r = _ur.Request(url, headers=ua, method="HEAD")
                with _ur.urlopen(r, timeout=5) as resp:
                    if resp.status < 400:
                        return lnk, True
            except Exception as e:
                if '405' in str(e):
                    return lnk, True
            # Fallback: GET with range
            try:
                r = _ur.Request(url, headers={**ua, "Range": "bytes=0-512"}, method="GET")
                with _ur.urlopen(r, timeout=5) as resp:
                    return lnk, resp.status < 400 or resp.status == 206
            except Exception as e:
                if '403' in str(e):
                    return lnk, True  # paywalled but exists
                return lnk, False
        if links:
            with _cf.ThreadPoolExecutor(max_workers=4) as ex:
                checked = list(ex.map(_check, links))
            links = [lnk for lnk, ok in checked if ok]

        _cache[cache_key] = {"links": links, "ts": now}
        _save_cache()
        print(f"[card_links] {lens}/{topic!r}: {len(links)} links", flush=True)
        return {"links": links, "cached": False}

    except Exception as exc:
        print(f"[card_links] error for {lens}/{topic!r}: {exc}", flush=True)
        return {"links": [], "cached": False, "error": str(exc)}
