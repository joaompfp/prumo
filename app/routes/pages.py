import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import TEMPLATES_DIR, STATIC_DIR

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
    })
