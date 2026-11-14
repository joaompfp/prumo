"""The backoffice web app: server-rendered, strictly read-only, GET/HEAD routes only.

Every page reads through ingest.db.read_db_readonly (mode=ro, query_only, never migrates or
creates the file). A missing database or a schema that differs from this code is answered
with HTTP 503 and the refusal message, exactly like `python -m ingest status`.
"""
import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypeVar
from urllib.parse import urlencode

from fastapi import FastAPI, Query, Request
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

from backoffice import reads, replay
from backoffice.deps import paths_from_env
from backoffice.registry_notes import inactive_notes
from backoffice.ttl_cache import TtlCache
from ingest.db import Db, ReadOnlyOpenError, read_db_readonly
from ingest.registry import load_registry

T = TypeVar("T")
TEMPLATES = Path(__file__).resolve().parent / "templates"
PAGE_METHODS = ["GET", "HEAD"]
STATUS_TTL_S = 30.0  # the full status report is reused this long across pages


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
               now: Callable[[], datetime] | None = None, *,
               raw_dir: Path | None = None, status_ttl_s: float = STATUS_TTL_S,
               monotonic: Callable[[], float] = time.monotonic) -> FastAPI:
    """`raw_dir` is the raw evidence store verification items are replayed from (None: the
    replay page says it cannot replay). The full status report is computed at most once per
    `status_ttl_s` (on the `monotonic` clock); pages show its generated_at."""
    specs = load_registry(registry_path)  # fail fast at startup on a bad registry
    clock = now or (lambda: datetime.now(timezone.utc))
    templates = _templates()
    app = FastAPI(title="Prumo backoffice", docs_url=None, redoc_url=None, openapi_url=None)

    def read(fn: Callable[[Db], T]) -> T:
        return read_db_readonly(db_path, fn)

    status_cache = TtlCache(status_ttl_s, monotonic)

    def status():
        """The full-registry status report (ingest.status.build_status), cached."""
        return status_cache.get(lambda: read(lambda db: reads.status_report(db, specs, clock())))

    def render(request: Request, name: str, status_code: int = 200, **context):
        return templates.TemplateResponse(request, name, context, status_code=status_code)

    @app.exception_handler(ReadOnlyOpenError)
    def refused(request: Request, exc: ReadOnlyOpenError):
        return render(request, "error.html", 503, title="Database unavailable",
                    message=f"read-only open refused: {exc}")

    @app.api_route("/healthz", methods=PAGE_METHODS)
    def healthz():
        """Liveness (always 200 while the app runs) plus a DB-readiness flag: a cheap
        read-only open + schema check. A DB hiccup must not make the container flap."""
        try:
            read(lambda db: None)
        except Exception as e:  # any refusal or sqlite error only lowers the flag
            return {"status": "ok", "db": "unavailable", "db_detail": str(e)}
        return {"status": "ok", "db": "ready"}

    @app.api_route("/", methods=PAGE_METHODS)
    def overview(request: Request):
        return render(request, "overview.html", report=status())

    @app.api_route("/queue", methods=PAGE_METHODS)
    def queue(request: Request):
        at = clock()
        report = status()
        q = read(lambda db: reads.queue(db, specs, report, at))
        return render(request, "queue.html", queue=q, generated_at=at.isoformat(),
                      event_limit=reads.QUEUE_EVENT_LIMIT)

    by_id = {s.id: s for s in specs}
    notes = inactive_notes(registry_path.parent, {s.id for s in specs if not s.active})
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
        statuses = reads.series_statuses(status())
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
        report = status()
        d = read(lambda db: reads.series_detail(db, spec, report, period or None))
        return render(request, "series_detail.html", spec=spec, d=d, period=period,
                      label=reads.status_label(d.status), cap=reads.OBSERVATION_CAP,
                      inactive_notes=notes.get(spec.id, []), status_at=report.generated_at)

    @app.api_route("/verification/item/{item_id}", methods=PAGE_METHODS)
    def verification_item(request: Request, item_id: int):
        try:
            r = read(lambda db: replay.replay(db, raw_dir, item_id, specs))
        except KeyError:
            return render(request, "error.html", 404, title="Unknown verification item",
                          message=f"unknown verification item: {item_id}")
        return render(request, "item.html", r=r, i=r.item, known=r.item["series_id"] in by_id)

    return app


def app_from_env() -> FastAPI:
    """uvicorn entry point (`uvicorn backoffice.app:app_from_env --factory`)."""
    db_path, registry_path, raw_dir = paths_from_env()
    return create_app(db_path, registry_path, raw_dir=raw_dir)
