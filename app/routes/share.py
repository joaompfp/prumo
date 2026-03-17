"""Share routes: /s/ prefix for social-sharing with dynamic OG tags.

Bot crawlers (Facebook, Twitter, LinkedIn, Telegram, etc.) receive an HTML
page with OpenGraph meta tags and an <meta http-equiv="refresh"> redirect.
Human browsers are immediately redirected to the SPA dashboard.

Image endpoints serve Playwright pre-generated PNGs when available,
falling back to Pillow-rendered cards.
"""

import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from ..config import TEMPLATES_DIR, SHARE_CARDS_DIR
from ..services.share_card import generate_kpi_card_fallback, generate_painel_card

router = APIRouter(prefix="/s")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ── Lightweight painel cache (avoids rebuilding on every share hit) ──────
_painel_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 3600  # 1 hour


def _get_painel() -> dict:
    """Return cached build_painel() result, refreshing after TTL."""
    now = time.time()
    if _painel_cache["data"] is None or now - _painel_cache["ts"] > _CACHE_TTL:
        from ..services.painel import build_painel
        _painel_cache["data"] = build_painel()
        _painel_cache["ts"] = now
    return _painel_cache["data"]


def _find_kpi(kpi_id: str) -> tuple[dict | None, str]:
    """Find a KPI by id across all painel sections. Returns (kpi, section_name)."""
    painel = _get_painel()
    for section in painel.get("sections", []):
        for kpi in section.get("kpis", []):
            if kpi.get("id") == kpi_id:
                return kpi, section.get("name", "")
    return None, ""


def _base_url(request: Request) -> str:
    """Derive the public base URL, respecting reverse-proxy headers."""
    # Prefer X-Forwarded-* headers set by Traefik
    proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host", "")
    prefix = request.headers.get("X-Forwarded-Prefix", "").rstrip("/")
    if host:
        return f"{proto}://{host}{prefix}"
    return str(request.base_url).rstrip("/")


# ═══════════════════════════════════════════════════════════════════════════
#  KPI share page + image
# ═══════════════════════════════════════════════════════════════════════════

@router.api_route("/kpi/{kpi_id}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def share_kpi(request: Request, kpi_id: str):
    """OG-tagged HTML page for a single KPI share link."""
    base = _base_url(request)
    kpi, section_name = _find_kpi(kpi_id)

    if not kpi:
        # KPI not found — generic fallback
        return templates.TemplateResponse("share.html", {
            "request": request,
            "title": "Prumo PT",
            "og_title": "Prumo PT \u2014 Economia a R\u00e9gua e Esquadro",
            "og_description": "Dashboard de indicadores econ\u00f3micos portugueses.",
            "og_image_url": f"{base}/static/images/prumo/logo-og.png",
            "canonical_url": base,
            "redirect_url": base,
        })

    # Build dynamic OG tags
    label = kpi.get("label", kpi_id)
    value = kpi.get("value")
    unit = kpi.get("unit", "")
    yoy = kpi.get("yoy")
    period = kpi.get("period", "")
    source = kpi.get("source", "")
    description = kpi.get("description", "")

    value_str = str(value) if value is not None else "\u2014"
    yoy_str = ""
    if yoy is not None:
        arrow = "\u2191" if yoy > 0 else "\u2193" if yoy < 0 else "\u2192"
        yoy_unit = kpi.get("yoy_unit") or "%"
        yoy_str = f" ({arrow}{abs(yoy):.1f}{yoy_unit})"

    og_title = f"{label}: {value_str} {unit}{yoy_str} \u2014 Prumo PT"
    # Build description with context (trend commentary)
    context = kpi.get("context", "")
    annotation = kpi.get("annotation", "")
    parts = []
    if context:
        parts.append(context)
    if annotation:
        parts.append(annotation)
    if description:
        parts.append(description)
    parts.append(f"Dados: {period}, Fonte: {source}.")
    og_description = " ".join(parts)

    return templates.TemplateResponse("share.html", {
        "request": request,
        "title": og_title,
        "og_title": og_title,
        "og_description": og_description,
        "og_image_url": f"{base}/s/kpi/{kpi_id}/image.png",
        "canonical_url": f"{base}/s/kpi/{kpi_id}",
        "redirect_url": f"{base}/#painel",
    })


@router.api_route("/kpi/{kpi_id}/image.png", methods=["GET", "HEAD"])
def share_kpi_image(kpi_id: str):
    """Serve a 1200x630 PNG card for a KPI (Playwright cache or Pillow fallback)."""
    kpi, section_name = _find_kpi(kpi_id)
    if not kpi:
        return Response(status_code=404)

    period = kpi.get("period", "unknown")
    # Check for Playwright pre-generated image first
    cache_file = os.path.join(SHARE_CARDS_DIR, f"kpi_{kpi_id}_{period}.png")
    if os.path.exists(cache_file):
        return FileResponse(
            cache_file, media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # Pillow fallback generation
    os.makedirs(SHARE_CARDS_DIR, exist_ok=True)
    img_bytes = generate_kpi_card_fallback(kpi, section_name)

    # Cache to disk (best-effort)
    fallback_file = os.path.join(SHARE_CARDS_DIR, f"kpi_{kpi_id}_{period}_fallback.png")
    try:
        with open(fallback_file, "wb") as f:
            f.write(img_bytes)
    except OSError:
        pass

    return Response(
        content=img_bytes, media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Painel share page + image
# ═══════════════════════════════════════════════════════════════════════════

@router.api_route("/painel", methods=["GET", "HEAD"], response_class=HTMLResponse)
def share_painel(request: Request):
    """OG-tagged HTML page for the full Painel snapshot."""
    painel = _get_painel()
    updated = painel.get("updated", "")
    base = _base_url(request)

    og_title = f"Portugal em 60 segundos ({updated}) \u2014 Prumo PT"
    og_description = (
        "Dashboard de indicadores econ\u00f3micos portugueses com an\u00e1lise IA. "
        "9 fontes oficiais."
    )

    return templates.TemplateResponse("share.html", {
        "request": request,
        "title": og_title,
        "og_title": og_title,
        "og_description": og_description,
        "og_image_url": f"{base}/s/painel/image.png",
        "canonical_url": f"{base}/s/painel",
        "redirect_url": f"{base}/#painel",
    })


@router.api_route("/painel/image.png", methods=["GET", "HEAD"])
def share_painel_image():
    """Serve a 1200x630 PNG summary card for the Painel."""
    painel = _get_painel()
    updated = painel.get("updated", "")

    # Check for Playwright pre-generated image
    cache_file = os.path.join(SHARE_CARDS_DIR, f"painel_{updated}.png")
    if os.path.exists(cache_file):
        return FileResponse(
            cache_file, media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # Build highlights from painel sections (first few KPIs with yoy data)
    highlights = []
    for section in painel.get("sections", []):
        for kpi in section.get("kpis", []):
            if kpi.get("yoy") is not None and kpi.get("label"):
                yoy = kpi["yoy"]
                yoy_unit = kpi.get("yoy_unit") or "%"
                arrow = "\u2191" if yoy > 0 else "\u2193" if yoy < 0 else "\u2192"
                sentence = f"{kpi['label']}: {arrow}{abs(yoy):.1f}{yoy_unit}"
                highlights.append({
                    "sentence": sentence,
                    "sentiment": kpi.get("sentiment", "neutral"),
                })
            if len(highlights) >= 5:
                break
        if len(highlights) >= 5:
            break

    # Try to get headline from painel analysis cache
    headline = ""
    try:
        from ..services.painel_headline import get_painel_headline
        hl_result = get_painel_headline(painel.get("sections", []), updated)
        headline = hl_result.get("headline", "")
    except Exception:
        pass
    if not headline:
        headline = f"Economia portuguesa \u2014 {updated}"

    os.makedirs(SHARE_CARDS_DIR, exist_ok=True)
    img_bytes = generate_painel_card(headline, highlights, updated)

    # Cache to disk
    fallback_file = os.path.join(SHARE_CARDS_DIR, f"painel_{updated}_fallback.png")
    try:
        with open(fallback_file, "wb") as f:
            f.write(img_bytes)
    except OSError:
        pass

    return Response(
        content=img_bytes, media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
