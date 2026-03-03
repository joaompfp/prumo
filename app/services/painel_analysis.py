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


def _parse_meta_json(text: str) -> tuple:
    """Extract META_JSON:{section_links:{...}, chart_pick:{...}} from end of text."""
    marker = '\nMETA_JSON:'
    idx = text.rfind(marker)
    if idx == -1:
        # Fallback: try old SECTION_LINKS format
        marker_old = '\nSECTION_LINKS:'
        idx_old = text.rfind(marker_old)
        if idx_old == -1:
            return text.strip(), {}, None, {}
        try:
            json_start = text.index('{', idx_old + len(marker_old))
            links, _ = json.JSONDecoder().raw_decode(text, json_start)
            return text[:idx_old].strip(), links, None, {}
        except Exception:
            return text[:idx_old].strip(), {}, None, {}
    try:
        json_start = text.index('{', idx + len(marker))
        meta, _ = json.JSONDecoder().raw_decode(text, json_start)
        section_links = meta.get('section_links', {})
        chart_pick = meta.get('chart_pick')
        section_charts = meta.get('section_charts', {})
        return text[:idx].strip(), section_links, chart_pick, section_charts
    except Exception:
        return text[:idx].strip(), {}, None, {}


def _build_painel_prompt(sections: list, updated: str, lens: str = None, custom_ideology: str = None) -> str:
    if lens:
        from .ideology_lenses import get_lens_prompt, get_lens_link_sources, get_lens_metadata
        ideology = get_lens_prompt(lens, custom_ideology=custom_ideology)
        link_sources = get_lens_link_sources(lens)
        lens_meta = get_lens_metadata(lens)
        lens_meta = None
    else:
        ideology = _load_ideology()
        link_sources = "publico.pt, dn.pt, rtp.pt, observador.pt, expresso.pt, eco.sapo.pt, jornaldenegocios.pt"
        lens_meta = None

    # Build search hint: include party short name + full name in web searches
    search_party_hint = ""
    if lens_meta and lens_meta.get("party"):
        short = lens_meta.get("short", "")
        party = lens_meta["party"]
        search_party_hint = f"Inclui '{short} {party}' nos termos de pesquisa. "
    search_hint = f"{search_party_hint}Usa o tema da secção como termo (ex: 'energia Portugal 2026', 'emprego Portugal recente'). Prioriza artigos o mais recentes possível."

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
    token_budget = n_sections * 200 + 600

    # Build indicator ID list for section_charts guidance
    indicator_ids = []
    for sec in sections:
        for k in sec.get("kpis", []):
            ind_id = k.get("indicator") or k.get("id") or ""
            if ind_id and ind_id not in indicator_ids:
                indicator_ids.append(ind_id)
    ids_str = ", ".join(indicator_ids[:45])

    instruction = (
        f"Tens um orçamento ESTRITO de {token_budget} tokens para análise + links.\n"
        "NÃO escrevas notas, planos, separadores (---) nem texto em inglês. Começa directamente com a análise.\n\n"
        f"PASSO 1 — Pesquisa (silenciosa): pesquisa 2 artigos recentes (últimos 2 meses) por secção. Máx. 6 pesquisas. {search_hint}\n\n"
        "PASSO 2 — Análise em **português europeu** (sem brasileirismos), período: " + updated + ".\n"
        "Para cada secção, escreve EXACTAMENTE 3 frases curtas com **negrito** nos conceitos-chave.\n"
        "Interpreta impacto real para trabalhadores e famílias — não repitas números.\n"
        "Formato OBRIGATÓRIO: cada secção começa com título inline em negrito seguido de dois pontos (ex: **Custo de Vida:**). "
        "NÃO uses cabeçalhos markdown (###). Linha em branco entre parágrafos.\n"
        "Termina com **Síntese:** (máx. 2 frases transversais). Sem listas, sem cabeçalhos markdown.\n\n"
        "PASSO 3 — OBRIGATÓRIO: imediatamente após a última frase, escreve:\n"
        f"META_JSON:{{\"section_links\":{{{{}}}},\"section_charts\":{{{{}}}},\"chart_pick\":{{}}}}\n"
        "Regras para META_JSON:\n"
        f"  section_links: OBRIGATÓRIO 2-3 links REAIS (URLs de artigos específicos, NÃO páginas de categoria) por secção ({sections_list}). "
        f"Fontes EXCLUSIVAS: {link_sources}. "
        "PROIBIDO: fpf.pt, abola.pt, record.pt, zerozero.pt, maisfutebol.iol.pt, ojogo.pt — ZERO links de futebol ou desporto. "
        "Quando pesquisares na web, ADICIONA '-futebol -desporto -liga -seleção' aos termos de pesquisa. "
        "URLs devem conter slug de artigo com pelo menos 3 segmentos (ex: https://observador.pt/2026/03/custo-vida-portuguesa). "
        "Formato: lista de strings. EVITA: bancos, governo, institutos financeiros, páginas de categoria (/noticias, /tema), colunistas pessoais, home pages. "
        "NUNCA uses o mesmo URL em duas secções diferentes. "
        "✓ URL válido: https://publico.pt/2026/03/artigo-custo-vida-salarios (tem ano/mes/slug)\n"
        "✗ URL inválido: https://rtp.pt/noticias/desporto/liga-nacoes (desporto!) ou https://publico.pt/autores/joao (colunista)\n"
        f"  section_charts: para cada secção usa UM ÚNICO id (string, NÃO array) da lista [{ids_str}]"
        " — o indicador que MAIS MENCIONASTE no texto dessa secção. Para 'Síntese': O indicador mais importante de toda a análise.\n"
        "  chart_pick: {{\"indicator\":\"id_exacto\",\"source\":\"FONTE\",\"label\":\"nome\",\"title\":\"insight criativo ≤12 palavras\"}} — mesmo que section_charts[Síntese].\n"
        "META_JSON deve ser a ÚLTIMA linha."
    )

    return f"{ideology}\n\n{instruction}\n\n" + "\n\n".join(section_blocks)


def _build_pt_europa_section() -> dict:
    """Build a Portugal vs. Europa section for the Sonnet prompt."""
    COMPARISONS = [
        ("Inflação HICP",          "EUROSTAT",  "hicp",                    "EU27_2020", "%"),
        ("Desemprego",             "EUROSTAT",  "unemployment",            "EU27_2020", "%"),
        ("Crescimento PIB",        "WORLDBANK", "gdp_growth",              "EU",        "%"),
        ("PIB per Capita PPP",     "WORLDBANK", "gdp_per_capita_ppp",      "EU",        "USD PPP"),
        ("Electricidade Dom.",     "EUROSTAT",  "electricity_price_household", "EU27_2020", "€/kWh"),
        ("Rendimento Hora",        "EUROSTAT",  "earn_ses_pub2s",          "EU27_2020", "€/h"),
        ("Esperança de Vida",      "WORLDBANK", "life_expectancy",         "EU",        "anos"),
        ("Taxa de Emprego",        "WORLDBANK", "employment_rate",         "EU",        "%"),
    ]
    try:
        from .db import get_db
        conn = get_db()
        kpis = []
        for label, source, indicator, ref, unit in COMPARISONS:
            try:
                rows = conn.execute("""
                    SELECT region, value FROM indicators
                    WHERE source=? AND indicator=? AND region IN ('PT','EU27_2020','EU','EU27')
                    ORDER BY period DESC LIMIT 10
                """, [source, indicator]).fetchall()
                vals = {r[0]: r[1] for r in rows}
                pt_val  = vals.get("PT")
                ref_val = vals.get(ref) or vals.get("EU27_2020") or vals.get("EU27") or vals.get("EU")
                if pt_val is None: continue
                diff = None
                if ref_val and ref_val != 0:
                    diff = round(((pt_val - ref_val) / abs(ref_val)) * 100, 1)
                kpis.append({
                    "id": indicator,
                    "label": label,
                    "source": source,
                    "value": round(pt_val, 2),
                    "unit": unit,
                    "yoy": diff,
                    "yoy_unit": f"% vs {ref}",
                    "ref_value": round(ref_val, 2) if ref_val else None,
                    "ref_label": ref,
                })
            except Exception:
                continue
        conn.close()
        return {"id": "pt_europa", "title": "Portugal vs. Europa", "kpis": kpis}
    except Exception as e:
        return {"id": "pt_europa", "title": "Portugal vs. Europa", "kpis": []}


def get_painel_analysis(sections: list, updated: str, force: bool = False, lens: str = None, custom_ideology: str = None) -> dict:
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

    # Custom ideology gets its own cache key (hash of text)
    import hashlib as _hl
    lens_key = lens or "default"
    if lens == "custom" and custom_ideology:
        lens_key = "custom:" + _hl.md5(custom_ideology.encode()).hexdigest()[:8]
    cache_key = f"painel:v21:{updated}:{lens_key}"
    if not force and cache_key in cache:
        entry = cache[cache_key]
        return {
            "text": entry["text"],
            "section_links": entry.get("section_links", {}),
            "chart_pick": entry.get("chart_pick"),
            "section_charts": entry.get("section_charts", {}),
            "generated_at": entry["generated_at"],
            "generation_ms": entry.get("generation_ms"),
            "data_period": updated,
            "cached": True,
        }

    prompt = _build_painel_prompt(sections, updated, lens=lens, custom_ideology=custom_ideology)
    if not prompt:
        return {"text": None, "cached": False, "error": "No KPI data available"}

    try:
        body = json.dumps({
            "model": "claude-opus-4-6",
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

        text, section_links, chart_pick, section_charts = _parse_meta_json(full_text)

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
