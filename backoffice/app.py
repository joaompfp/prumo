"""The backoffice web app: server-rendered, strictly read-only, GET/HEAD routes only.

Every page reads through ingest.db.read_db_readonly (mode=ro, query_only, never migrates or
creates the file). A missing database or a schema that differs from this code is answered
with HTTP 503 and the refusal message, exactly like `python -m ingest status`.
"""
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

from backoffice import reads
from backoffice.deps import paths_from_env
from ingest.db import Db, ReadOnlyOpenError, read_db_readonly
from ingest.registry import load_registry

T = TypeVar("T")
TEMPLATES = Path(__file__).resolve().parent / "templates"
PAGE_METHODS = ["GET", "HEAD"]


def link(url: str | None) -> Markup | str:
    """An https:// URL becomes a link; anything else (http, javascript:, data:...) stays text.
    Both are escaped: URLs come from publishers and event details and are untrusted."""
    if url is None:
        return ""
    if url.startswith("https://"):
        return Markup('<a href="{0}" rel="noopener noreferrer">{0}</a>').format(url)
    return escape(url)


def as_json(value) -> str:
    """Compact JSON as plain text (autoescaped by the template like any other string)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _templates() -> Jinja2Templates:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    env.filters["link"] = link
    env.filters["as_json"] = as_json
    return Jinja2Templates(env=env)


def create_app(db_path: Path, registry_path: Path,
               now: Callable[[], datetime] | None = None) -> FastAPI:
    specs = load_registry(registry_path)  # fail fast at startup on a bad registry
    clock = now or (lambda: datetime.now(timezone.utc))
    templates = _templates()
    app = FastAPI(title="Prumo backoffice", docs_url=None, redoc_url=None, openapi_url=None)

    def read(fn: Callable[[Db], T]) -> T:
        return read_db_readonly(db_path, fn)

    def page(request: Request, name: str, status_code: int = 200, **context):
        return templates.TemplateResponse(request, name, context, status_code=status_code)

    @app.exception_handler(ReadOnlyOpenError)
    def refused(request: Request, exc: ReadOnlyOpenError):
        return page(request, "error.html", 503, title="Database unavailable",
                    message=f"read-only open refused: {exc}")

    @app.api_route("/healthz", methods=PAGE_METHODS)
    def healthz():
        return {"status": "ok"}

    @app.api_route("/", methods=PAGE_METHODS)
    def overview(request: Request):
        at = clock()
        return page(request, "overview.html", report=read(lambda db: reads.overview(db, specs, at)))

    @app.api_route("/queue", methods=PAGE_METHODS)
    def queue(request: Request):
        at = clock()
        q = read(lambda db: reads.queue(db, specs, at))
        return page(request, "queue.html", queue=q, generated_at=at.isoformat(),
                    event_limit=reads.QUEUE_EVENT_LIMIT)

    return app


def app_from_env() -> FastAPI:
    """uvicorn entry point (`uvicorn backoffice.app:app_from_env --factory`)."""
    return create_app(*paths_from_env())
