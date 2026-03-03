import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import TEMPLATES_DIR, STATIC_DIR, CUSTOM_LENS_DEFAULT

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/embed.js")
def embed_js():
    """Serve the CAE embed script with CORS and cache headers."""
    path = os.path.join(STATIC_DIR, "js", "embed.js")
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


def _count_indicators() -> int:
    """Count unique indicators in the database (cached after first call)."""
    if not hasattr(_count_indicators, "_n"):
        try:
            from ..services.db import get_db
            conn = get_db()
            _count_indicators._n = conn.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT source, indicator FROM indicators)"
            ).fetchone()[0]
        except Exception:
            from ..constants import CATALOG
            _count_indicators._n = sum(len(s.get("indicators", {})) for s in CATALOG.values())
    return _count_indicators._n


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    # Use X-Forwarded-Prefix from Traefik StripPrefix, fall back to env var
    prefix = request.headers.get("X-Forwarded-Prefix", "")
    if not prefix:
        from ..config import BASE_PATH
        prefix = BASE_PATH
    prefix = prefix.rstrip("/")
    from ..services.interpret import _load_ideology
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "base_path": prefix,
        "ideology": _load_ideology(),
        "n_indicators": _count_indicators(),
        "custom_lens_default": CUSTOM_LENS_DEFAULT,
    })
