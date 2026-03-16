"""Haiku interpretation service for Explorador/Analise charts."""
import os
import re
import ssl as _ssl
import urllib.request as _ur
import hashlib
import json
import time
from urllib.request import Request
from ..config import CAE_DB_PATH, INTERPRET_CACHE_PATH, OUTPUT_LANGUAGES, DEFAULT_OUTPUT_LANGUAGE

ANTHROPIC_KEY = os.environ.get("CAE_ANTHROPIC_TOKEN", "")
_DATA_DIR = os.path.dirname(CAE_DB_PATH)
_IDEOLOGY_PATH = os.path.join(_DATA_DIR, "ideology.txt")
_CACHE_PATH = INTERPRET_CACHE_PATH
CACHE_TTL = 2592000  # 30 dias

# Load disk cache into memory at import time
_cache: dict = {}
try:
    if os.path.exists(_CACHE_PATH):
        _disk = json.loads(open(_CACHE_PATH, encoding="utf-8").read())
        now0 = time.time()
        _cache = {k: (v["ts"], v["result"]) for k, v in _disk.items()
                  if now0 - v["ts"] < CACHE_TTL}
        print(f"[interpret] loaded {len(_cache)} cached entries from disk", flush=True)
except Exception as _e:
    print(f"[interpret] cache load error: {_e}", flush=True)


def _save_cache() -> None:
    try:
        payload = {k: {"ts": v[0], "result": v[1]} for k, v in _cache.items()}
        open(_CACHE_PATH, "w", encoding="utf-8").write(
            json.dumps(payload, ensure_ascii=False, indent=2)
        )
    except Exception as e:
        print(f"[interpret] cache write error: {e}", flush=True)

_IDEOLOGY_DEFAULT = (
    "És um analista económico que trabalha para a Comissão de Assuntos Económicos "
    "do Partido Comunista Português (PCP). "
    "A tua análise parte do impacto real sobre os trabalhadores, as famílias e a "
    "indústria nacional — não da perspectiva dos mercados financeiros. "
    "Interessa-te: poder de compra, emprego, custo de vida, soberania energética, "
    "precariedade laboral, investimento público e convergência com a UE."
)


def _load_ideology() -> str:
    """Load ideological context from /data/ideology.txt, fallback to default."""
    try:
        if os.path.exists(_IDEOLOGY_PATH):
            return open(_IDEOLOGY_PATH, encoding="utf-8").read().strip()
    except Exception:
        pass
    return _IDEOLOGY_DEFAULT

# Build SSL context once at import time — explicitly loads proxy CA cert if set
_ssl_ctx = _ssl.create_default_context()
_cert_file = os.environ.get("SSL_CERT_FILE")
if _cert_file and os.path.exists(_cert_file):
    _ssl_ctx.load_verify_locations(_cert_file)
    print(f"[interpret] SSL context loaded: {_cert_file}", flush=True)
_opener = _ur.build_opener(_ur.HTTPSHandler(context=_ssl_ctx))


def _parse_links(text: str) -> tuple:
    """Extract LINKS:[...] from text. Uses raw_decode for correct nested-JSON handling."""
    marker = '\nLINKS:'
    idx = text.rfind(marker)
    if idx == -1:
        return text.strip(), []
    try:
        json_start = text.index('[', idx + len(marker))
        links, _ = json.JSONDecoder().raw_decode(text, json_start)
        return text[:idx].strip(), links
    except Exception:
        return text[:idx].strip(), []


def interpret_chart(series: list, from_p: str, to_p: str, lens: str = None, custom_ideology: str = None, output_language: str = None):
    """Call Claude Haiku (with web search) to interpret chart data.
    Returns dict {"text": str, "links": list} or None if unconfigured.
    Optional lens parameter selects a political perspective (see ideology_lenses.py).
    When lens='custom', custom_ideology contains the user-provided ideology text.
    output_language selects the response language (key from site.json output_languages)."""
    # ── LLM DISABLED: stub mode while validating charts ──
    indicator_names = ", ".join(f"{s.get('source','?')}/{s.get('indicator','?')}" for s in series)
    return {"text": f"[Análise IA desactivada — modo de validação de gráficos]\n\nIndicadores: {indicator_names}\nPeríodo: {from_p} → {to_p}\nLente: {lens or 'default'}", "links": []}
    # ── END STUB ──

    if not ANTHROPIC_KEY:
        return None

    # Custom ideology gets its own cache key (hash of text), never 'default'
    lens_key = lens or "default"
    if lens == "custom" and custom_ideology:
        lens_key = "custom:" + hashlib.md5(custom_ideology.encode()).hexdigest()[:8]
    lang_key = output_language or DEFAULT_OUTPUT_LANGUAGE
    # Quantize periods to quarter start for cache hits — ±1 month won't miss
    def _quantize(p):
        if not p or len(p) < 7:
            return p
        try:
            m = int(p[5:7])
            q = ((m - 1) // 3) * 3 + 1
            return f"{p[:5]}{q:02d}"
        except Exception:
            return p
    key = hashlib.md5(json.dumps(
        [{"s": s["source"], "i": s["indicator"]} for s in series] + [_quantize(from_p), _quantize(to_p), lens_key, lang_key]
    ).encode()).hexdigest()

    now = time.time()
    if key in _cache and now - _cache[key][0] < CACHE_TTL:
        return _cache[key][1]

    prompt = _build_prompt(series, from_p, to_p, lens=lens, custom_ideology=custom_ideology, output_language=output_language)
    if not prompt:
        return None

    try:
        body = json.dumps({
            "model": "claude-sonnet-4-5-20251001" if lens_key == "kriolu" else "claude-haiku-4-5-20251001",
            "max_tokens": 1400,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            "messages": [{"role": "user", "content": prompt}]
        }).encode()

        req = Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        )

        with _opener.open(req, timeout=35) as resp:
            data = json.loads(resp.read())
            # Collect text blocks (response may include server_tool_use/web_search_tool_result blocks)
            text_parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            full_text = "\n".join(text_parts).strip()
            text, links = _parse_links(full_text)
            result = {"text": text, "links": links}
            _cache[key] = (now, result)
            _save_cache()
            return result

    except Exception as exc:
        print(f"[interpret] error: {exc}", flush=True)
        return None


def _months_between(from_p: str, to_p: str) -> int:
    """Approximate months between two YYYY-MM strings. Returns 0 if unparseable."""
    try:
        fy, fm = int(from_p[:4]), int(from_p[5:7])
        ty, tm = int(to_p[:4]), int(to_p[5:7])
        return max(1, (ty - fy) * 12 + (tm - fm))
    except Exception:
        return 0


def _sample_evenly(data: list, max_pts: int) -> list:
    """Return at most max_pts evenly-spaced elements, preserving order."""
    if not data or len(data) <= max_pts:
        return data
    # Spread indices across the full range
    indices = {round(i * (len(data) - 1) / (max_pts - 1)) for i in range(max_pts)}
    return [data[i] for i in sorted(indices)]


def _build_prompt(series, from_p, to_p, lens=None, custom_ideology=None, output_language=None):
    if not series:
        return None

    # ── Adaptive horizon ───────────────────────────────────────────
    n_months = _months_between(from_p, to_p) if (from_p and to_p) else 0

    if n_months == 0:           # "Tudo" ou sem datas — escala desconhecida, usa estrutural
        max_pts, focus = 24, "tendência estrutural de longo prazo"
    elif n_months <= 15:        # 1A — foco conjuntural
        max_pts, focus = n_months, "evolução conjuntural recente"
    elif n_months <= 30:        # 2A
        max_pts, focus = 24, "tendência de curto prazo (últimos 2 anos)"
    elif n_months <= 72:        # 5A
        max_pts, focus = 30, "ciclo económico de médio prazo"
    else:                       # 10A / Tudo
        max_pts, focus = 24, "tendência estrutural de longo prazo"

    period_str = (
        f"{from_p} a {to_p}" if (from_p and to_p)
        else (to_p or "período mais recente")
    )

    parts = []
    for s in series:
        raw = list(s.get("data") or s.get("values") or [])
        # Filter to the requested window
        if from_p:
            raw = [d for d in raw if str(d.get("period", "")) >= from_p]
        if to_p:
            raw = [d for d in raw if str(d.get("period", "")) <= to_p]
        data = _sample_evenly(raw, max_pts)
        if not data:
            continue
        vals = ", ".join(
            f"{d.get('period', '?')}: {d.get('value', '?')}" for d in data
        )
        parts.append(
            f"* {s.get('label', s.get('indicator', '?'))} "
            f"[código: {s.get('indicator', '?')} · fonte: {s.get('source', '?')} · unidade: {s.get('unit', '') or 'n/d'}]: {vals}"
        )

    if not parts:
        return None

    indicator_labels = ", ".join(
        f'"{s.get("label", s.get("indicator", "?"))}"' for s in series
    )

    if lens:
        from .ideology_lenses import get_lens_prompt
        context = get_lens_prompt(lens, custom_ideology=custom_ideology)
    else:
        context = _load_ideology()

    # Resolve output language description from site.json map
    lang_code = output_language or DEFAULT_OUTPUT_LANGUAGE
    lang_desc = OUTPUT_LANGUAGES.get(lang_code, OUTPUT_LANGUAGES.get(DEFAULT_OUTPUT_LANGUAGE, "português europeu (sem brasileirismos)"))

    # Hard language constraint at the very top of the prompt
    lang_prefix = (
        f"IDIOMA OBRIGATÓRIO: toda a tua resposta DEVE ser escrita em {lang_desc}.\n\n"
    )

    from .prompt_loader import load_prompt
    instruction = load_prompt("interpret",
        indicator_labels=indicator_labels,
        lang_desc=lang_desc,
        focus=focus,
        period_str=period_str,
    )
    return f"{lang_prefix}{context}\n\n{instruction}\n\n" + "\n".join(parts)
