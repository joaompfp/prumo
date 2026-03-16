"""Sonnet analysis for the Painel section — one-shot, disk-cached."""
import os
import re
import json
import time
from ..interpret import _opener, ANTHROPIC_KEY
from urllib.request import Request
from ...config import CAE_DB_PATH, PAINEL_CACHE_PATH, DEFAULT_OUTPUT_LANGUAGE
from .parser import _parse_meta_json
from .prompt import _build_painel_prompt

_DATA_DIR = os.path.dirname(CAE_DB_PATH)
_CACHE_PATH = PAINEL_CACHE_PATH


def get_painel_analysis(sections: list, updated: str, force: bool = False, lens: str = None, custom_ideology: str = None, output_language: str = None) -> dict:
    """
    Return Sonnet analysis of Painel sections.
    Results are cached to disk keyed by `updated`. Cache survives restarts.
    Pass force=True to regenerate even if cached.
    Cache key versioned (v3) to invalidate old entries without section_links.
    """
    # ── LLM DISABLED: stub mode while validating charts ──
    return {"text": "[Análise Painel IA desactivada — modo de validação de gráficos]", "cached": False, "error": None}
    # ── END STUB ──

    if not ANTHROPIC_KEY:
        return {"text": None, "cached": False, "error": "API key not configured"}

    # Load existing cache
    cache = {}
    try:
        if os.path.exists(_CACHE_PATH):
            cache = json.loads(open(_CACHE_PATH, encoding="utf-8").read())
    except Exception:
        cache = {}

    # Custom ideology gets its own cache key (hash of text)
    import hashlib as _hl
    lens_key = lens or "default"
    if lens == "custom" and custom_ideology:
        lens_key = "custom:" + _hl.md5(custom_ideology.encode()).hexdigest()[:8]
    lang_key = output_language or DEFAULT_OUTPUT_LANGUAGE
    cache_key = f"painel:v23:{updated}:{lens_key}:{lang_key}"
    if not force and cache_key in cache:
        entry = cache[cache_key]
        return {
            "text": entry["text"],
            "headline": entry.get("headline", ""),
            "subheadline": entry.get("subheadline", ""),
            "section_links": entry.get("section_links", {}),
            "chart_pick": entry.get("chart_pick"),
            "section_charts": entry.get("section_charts", {}),
            "generated_at": entry["generated_at"],
            "generation_ms": entry.get("generation_ms"),
            "data_period": updated,
            "cached": True,
        }

    prompt = _build_painel_prompt(sections, updated, lens=lens, custom_ideology=custom_ideology, output_language=output_language)
    if not prompt:
        return {"text": None, "cached": False, "error": "No KPI data available"}

    try:
        body = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 4096,
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

        text, section_links, chart_pick, section_charts, headline, subheadline = _parse_meta_json(full_text)

        # ── Filter out sports/football/irrelevant URLs before validation ──
        _BLOCKED_DOMAINS = {'fpf.pt', 'abola.pt', 'record.pt', 'zerozero.pt',
                            'maisfutebol.iol.pt', 'ojogo.pt', 'tribunaexpresso.pt'}
        _SPORTS_SLUGS = re.compile(
            r'(?:futebol|desporto|liga-nacoes|champions|selecao|benfica|sporting|porto|'
            r'premier-league|euro-2|mundial|jogos-olimpicos|bruno-fernandes|ronaldo|'
            r'campeonato|eliminatorias|transferencias|treinador|equipa-nacional)',
            re.IGNORECASE,
        )
        def _is_sports_url(url: str) -> bool:
            try:
                from urllib.parse import urlparse
                host = urlparse(url).hostname or ''
                # Check blocked domains
                for bd in _BLOCKED_DOMAINS:
                    if host == bd or host.endswith('.' + bd):
                        return True
                # Check URL path for sports slugs
                if _SPORTS_SLUGS.search(url):
                    return True
            except Exception:
                pass
            return False

        for sec in list(section_links.keys()):
            before = len(section_links[sec])
            section_links[sec] = [u for u in section_links[sec] if not _is_sports_url(u)]
            dropped = before - len(section_links[sec])
            if dropped:
                print(f"[painel_analysis] dropped {dropped} sports URL(s) from '{sec}'", flush=True)

        # Validate ALL links — drop 404s/unreachable (model hallucinates URLs)
        import urllib.request as _ur, concurrent.futures as _cf
        def _check_url(url):
            ua = {"User-Agent": "Mozilla/5.0 (compatible; PrumoBot/1.0)"}
            try:
                # Try HEAD first
                req = _ur.Request(str(url), headers=ua, method="HEAD")
                with _ur.urlopen(req, timeout=5) as r:
                    ok = r.status < 400
                    if ok:
                        return url, True
            except Exception as e:
                err = str(e)
                # 405 Method Not Allowed = URL exists, just doesn't accept HEAD
                if '405' in err:
                    return url, True
            # Fallback: GET with range header (minimal download)
            try:
                req = _ur.Request(str(url), headers={**ua, "Range": "bytes=0-512"}, method="GET")
                with _ur.urlopen(req, timeout=5) as r:
                    return url, r.status < 400 or r.status == 206
            except Exception as e:
                err = str(e)
                # 403 from some paywalled sites — still a real article
                if '403' in err:
                    return url, True
                print(f"[painel_analysis] URL check failed: {url} → {err}", flush=True)
                return url, False
        # Collect all unique URLs to check
        all_urls = list({url for links in section_links.values() for url in links if url})
        if all_urls:
            with _cf.ThreadPoolExecutor(max_workers=8) as ex:
                results = dict(ex.map(_check_url, all_urls))
            valid = sum(1 for v in results.values() if v)
            print(f"[painel_analysis] URL validation: {valid}/{len(all_urls)} passed", flush=True)
        else:
            results = {}
        # Filter each section
        for sec in list(section_links.keys()):
            before = len(section_links[sec])
            section_links[sec] = [u for u in section_links[sec] if results.get(u, False)]
            if before and not section_links[sec]:
                print(f"[painel_analysis] WARNING: all {before} URL(s) dropped for '{sec}'", flush=True)

        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cache[cache_key] = {
            "text": text,
            "headline": headline,
            "subheadline": subheadline,
            "section_links": section_links,
            "chart_pick": chart_pick,
            "section_charts": section_charts,
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
            "headline": headline,
            "subheadline": subheadline,
            "section_links": section_links,
            "chart_pick": chart_pick,
            "section_charts": section_charts,
            "generated_at": generated_at,
            "generation_ms": generation_ms,
            "data_period": updated,
            "cached": False,
        }

    except Exception as exc:
        print(f"[painel_analysis] error: {exc}", flush=True)
        return {"text": None, "cached": False, "error": str(exc)}
