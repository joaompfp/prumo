"""Haiku interpretation service for Explorador/Analise charts."""
import os
import hashlib
import json
import time
from urllib.request import Request, urlopen

ANTHROPIC_KEY = os.environ.get("CAE_ANTHROPIC_TOKEN", "")
_cache: dict = {}
CACHE_TTL = 300  # 5 min


def interpret_chart(series: list, from_p: str, to_p: str):
    """Call Claude Haiku to interpret chart data. Returns None if unconfigured."""
    if not ANTHROPIC_KEY:
        return None

    key = hashlib.md5(json.dumps(
        [{"s": s["source"], "i": s["indicator"]} for s in series] + [from_p, to_p]
    ).encode()).hexdigest()

    now = time.time()
    if key in _cache and now - _cache[key][0] < CACHE_TTL:
        return _cache[key][1]

    prompt = _build_prompt(series, from_p, to_p)
    if not prompt:
        return None

    try:
        body = json.dumps({
            "model": "claude-haiku-4-5-20250414",
            "max_tokens": 220,
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

        with urlopen(req, timeout=20) as resp:
            text = json.loads(resp.read())["content"][0]["text"].strip()
            _cache[key] = (now, text)
            return text

    except Exception:
        return None


def _build_prompt(series, from_p, to_p):
    if not series:
        return None

    parts = []
    for s in series:
        data = (s.get("data") or s.get("values") or [])[-12:]
        if not data:
            continue
        vals = ", ".join(
            f"{d.get('period', '?')}: {d.get('value', '?')}" for d in data
        )
        parts.append(
            f"* {s.get('label', s.get('indicator', '?'))} "
            f"({s.get('source', '?')}) [{s.get('unit', '')}]: {vals}"
        )

    if not parts:
        return None

    return (
        "Analisa estes indicadores economicos de Portugal em 2-3 frases directas e concisas, "
        "em portugues europeu (sem brasileirismos). "
        "Foca-te no significado economico e na tendencia recente. "
        "Nao descreves os numeros em bruto - interpretas o que significam.\n\n"
        + "\n".join(parts)
    )
