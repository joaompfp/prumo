from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .maintenance import PAGE

# Only the maintenance page's favicon is kept; the legacy UI is recoverable at the
# `legacy-ui-final` tag.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Prumo", docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.api_route("/healthz", methods=["GET", "HEAD"])
def healthz():
    return {"status": "ok"}


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def maintenance(full_path: str):
    return PAGE
