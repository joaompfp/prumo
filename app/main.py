from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .maintenance import PAGE

app = FastAPI(title="Prumo", docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/{full_path:path}", response_class=HTMLResponse)
def maintenance(full_path: str):
    return PAGE
