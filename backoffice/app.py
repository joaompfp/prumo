"""The backoffice web app: server-rendered, strictly read-only, GET/HEAD routes only.

Every page reads through ingest.db.read_db_readonly (mode=ro, query_only, never migrates or
creates the file). A missing database or a schema that differs from this code is answered
with HTTP 503 and the refusal message, exactly like `python -m ingest status`.
"""
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypeVar
from urllib.parse import urlencode

from fastapi import FastAPI, Query, Request
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

    def render(request: Request, name: str, status_code: int = 200, **context):
        return templates.TemplateResponse(request, name, context, status_code=status_code)

    @app.exception_handler(ReadOnlyOpenError)
    def refused(request: Request, exc: ReadOnlyOpenError):
        return render(request, "error.html", 503, title="Database unavailable",
                    message=f"read-only open refused: {exc}")

    @app.api_route("/healthz", methods=PAGE_METHODS)
    def healthz():
        return {"status": "ok"}

    @app.api_route("/", methods=PAGE_METHODS)
    def overview(request: Request):
        at = clock()
        return render(request, "overview.html",
                      report=read(lambda db: reads.overview(db, specs, at)))

    @app.api_route("/queue", methods=PAGE_METHODS)
    def queue(request: Request):
        at = clock()
        q = read(lambda db: reads.queue(db, specs, at))
        return render(request, "queue.html", queue=q, generated_at=at.isoformat(),
                      event_limit=reads.QUEUE_EVENT_LIMIT)

    by_id = {s.id: s for s in specs}
    options = {"source": sorted({s.source.name for s in specs}),
               "theme": sorted({s.theme for s in specs}),
               "geography": sorted({s.geography for s in specs}),
               "frequency": sorted({s.frequency for s in specs})}

    @app.api_route("/series", methods=PAGE_METHODS)
    def series_list(request: Request, source: str = "", theme: str = "", geography: str = "",
                    frequency: str = "", active: Literal["", "yes", "no"] = "", q: str = "",
                    page: int = Query(1, ge=1)):
        filters = {"source": source, "theme": theme, "geography": geography,
                   "frequency": frequency, "active": active, "q": q}
        chosen = reads.filter_specs(specs, **filters)
        shown = chosen[(page - 1) * reads.PAGE_SIZE:page * reads.PAGE_SIZE]
        at = clock()
        statuses = read(lambda db: reads.series_statuses(db, specs, at))
        rows = [(s, statuses[s.id], reads.status_label(statuses[s.id])) for s in shown]
        query = {k: v for k, v in filters.items() if v}

        def page_url(n: int) -> str:
            return "/series?" + urlencode({**query, "page": n})

        pages = max(1, -(-len(chosen) // reads.PAGE_SIZE))
        return render(request, "series_list.html", rows=rows, total=len(chosen),
                      filters=filters, options=options, page=page, pages=pages,
                      prev_url=page_url(page - 1) if page > 1 else None,
                      next_url=page_url(page + 1) if page < pages else None)

    @app.api_route("/series/{series_id}", methods=PAGE_METHODS)
    def series_detail(request: Request, series_id: str, period: str = ""):
        spec = by_id.get(series_id)
        if spec is None:
            return render(request, "error.html", 404, title="Unknown series",
                          message=f"unknown series: {series_id} (not in the registry)")
        at = clock()
        d = read(lambda db: reads.series_detail(db, spec, specs, at, period or None))
        return render(request, "series_detail.html", spec=spec, d=d, period=period,
                      label=reads.status_label(d.status), cap=reads.OBSERVATION_CAP)

    return app


def app_from_env() -> FastAPI:
    """uvicorn entry point (`uvicorn backoffice.app:app_from_env --factory`)."""
    return create_app(*paths_from_env())
