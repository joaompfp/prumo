"""The backoffice web app: server-rendered, strictly read-only, GET/HEAD routes only.

Every page reads through ingest.db.read_db_readonly (mode=ro, query_only, never migrates or
creates the file). A missing database or a schema that differs from this code is answered
with HTTP 503 and the refusal message, exactly like `python -m ingest status`.
"""
import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypeVar
from urllib.parse import parse_qs, urlencode

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi import Path as PathParam
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.charts import sparkline
from backoffice import reads, replay
from backoffice.deps import (
    DEFAULT_ALLOWED_HOSTS,
    LANG,
    allowed_hosts_from_env,
    editorial_path_from_env,
    paths_from_env,
)
from backoffice.editorial import Editorial, EditorialBusy, EditorialUnavailable, same_origin
from backoffice.registry_notes import inactive_notes
from backoffice.ttl_cache import TtlCache
from ingest.db import Db, EditorialConflict, EditorialRefused, ReadOnlyOpenError, read_db_readonly
from ingest.editorial_rules import MAX_SLOTS
from ingest.registry import load_registry
from presentation import MissingText

log = logging.getLogger("backoffice")

T = TypeVar("T")
TEMPLATES = Path(__file__).resolve().parent / "templates"
# The publish preview renders the public card partial, so the operator sees the card the home
# will draw, not a paraphrase of it.
APP_TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"
PAGE_METHODS = ["GET", "HEAD"]
STATUS_TTL_S = 30.0  # the full status report is reused this long across pages
SQLITE_MAX_INT = 2**63 - 1  # largest id SQLite can bind; above it -> 422, never a 500
# No JavaScript anywhere: nothing may run, load or frame the pages; inline styles only.
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
                               "img-src 'self' data:; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
}


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
    env = Environment(loader=FileSystemLoader([TEMPLATES, APP_TEMPLATES]), autoescape=True)
    env.filters["link"] = link
    env.filters["as_json"] = as_json
    env.globals.update(spark=sparkline)
    return Jinja2Templates(env=env)


def create_app(db_path: Path, registry_path: Path,
               now: Callable[[], datetime] | None = None, *,
               raw_dir: Path | None = None, status_ttl_s: float = STATUS_TTL_S,
               monotonic: Callable[[], float] = time.monotonic,
               allowed_hosts: list[str] = DEFAULT_ALLOWED_HOSTS,
               editorial_db_path: Path | None = None) -> FastAPI:
    """`raw_dir` is the raw evidence store verification items are replayed from (None: the
    replay page says it cannot replay). The full status report is computed at most once per
    `status_ttl_s` (on the `monotonic` clock), and so is the /derived list; pages show
    their generated_at and age. Requests
    whose Host header is not in `allowed_hosts` get 400 (DNS-rebinding guard)."""
    specs = load_registry(registry_path)  # fail fast at startup on a bad registry
    clock = now or (lambda: datetime.now(timezone.utc))
    templates = _templates()
    app = FastAPI(title="Prumo backoffice", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))

    @app.middleware("http")  # added last, so outermost: the 400 host refusal carries it too
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    def read(fn: Callable[[Db], T]) -> T:
        return read_db_readonly(db_path, fn)

    editorial = Editorial(db_path, editorial_db_path, lang=LANG)

    status_cache = TtlCache(status_ttl_s, monotonic)
    derived_cache = TtlCache(status_ttl_s, monotonic)  # /derived evaluates every derived key

    def status():
        """The full-registry status report (ingest.status.build_status), cached."""
        return status_cache.get(lambda: read(lambda db: reads.status_report(db, specs, clock())))

    def render(request: Request, name: str, status_code: int = 200, **context):
        return templates.TemplateResponse(request, name, context, status_code=status_code)

    def with_status(report) -> dict:
        """The cached report plus how old it is now (pages say when it was generated)."""
        return {"report": report, "report_age_s": reads.report_age_s(report, clock()),
                "status_ttl_s": int(status_ttl_s)}

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
        return render(request, "overview.html", **with_status(status()))

    @app.api_route("/queue", methods=PAGE_METHODS)
    def queue(request: Request):
        at = clock()
        report = status()
        q = read(lambda db: reads.queue(db, specs, report, at))
        return render(request, "queue.html", queue=q, generated_at=at.isoformat(),
                      **with_status(report))

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
                      inactive_notes=notes.get(spec.id, []), **with_status(report))

    @app.api_route("/derived", methods=PAGE_METHODS)
    def derived_list(request: Request):
        generated_at, rows = derived_cache.get(
            lambda: (clock(), read(reads.derived_list)))
        return render(request, "derived_list.html", rows=rows,
                      generated_at=generated_at.isoformat(),
                      age_s=max(0, int((clock() - generated_at).total_seconds())),
                      status_ttl_s=int(status_ttl_s))

    @app.api_route("/derived/{key}", methods=PAGE_METHODS)
    def derived_detail(request: Request, key: str):
        d = read(lambda db: reads.derived_detail(db, key))
        if d is None:
            return render(request, "error.html", 404, title="Unknown derived series",
                          message=f"unknown derived series: {key} (not in the database)")
        return render(request, "derived_detail.html", d=d, s=d.series,
                      base=by_id.get(d.series["base_series_id"]),
                      cap=reads.OBSERVATION_CAP, list_cap=reads.DETAIL_LIST_CAP)

    @app.api_route("/verification/item/{item_id}", methods=PAGE_METHODS)
    def verification_item(request: Request,
                          item_id: int = PathParam(ge=1, le=SQLITE_MAX_INT)):
        try:
            r = read(lambda db: replay.replay(db, raw_dir, item_id, specs))
        except KeyError:
            return render(request, "error.html", 404, title="Unknown verification item",
                          message=f"unknown verification item: {item_id}")
        return render(request, "item.html", r=r, i=r.item, known=r.item["series_id"] in by_id)

    # --- editorial composition: the only write path in this app ------------------------------
    #
    # Every POST is a plain form (no JavaScript), checked against `Origin` because there is no
    # session to ride, and answered with a 303 back to the page so a reload cannot re-submit.
    # Nothing here touches served data: the mutations write `editorial_*` and nothing else.
    # The handlers are async only to read the body; every database call runs in the threadpool,
    # so a lock wait cannot stall /healthz or the rest of the backoffice.

    CANDIDATES_PER_PAGE = 40
    MAX_FORM_BYTES = 16_384

    @app.exception_handler(EditorialUnavailable)
    def editorial_unavailable(request: Request, exc: EditorialUnavailable):
        log.error("editorial write path unavailable: %s", exc)
        return render(request, "error.html", 503, title="Editorial editor unavailable",
                      message="the writable mount is not configured or not usable; reads are "
                              "unaffected. See docs/data/operations.md, editorial section.")

    async def form(request: Request) -> dict[str, str]:
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_FORM_BYTES:
            raise HTTPException(status_code=413, detail="form too large")
        body = (await request.body())[:MAX_FORM_BYTES]
        return {k: v[0] for k, v in
                parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True).items()}

    def editor_page(request: Request, slug: str, *, status_code: int = 200, **extra):
        try:
            page = editorial.page(slug)
        except MissingText:
            return render(request, "error.html", 404, title="Unknown page",
                          message=f"unknown page: {slug}")
        query = request.query_params
        page_no = int(query.get("pagina", "1")) if query.get("pagina", "1").isdigit() else 1
        page_no = max(1, page_no)
        rows = editorial.candidates(
            slug, query=query.get("q", ""), source=query.get("fonte", ""),
            theme=query.get("tema", ""), limit=CANDIDATES_PER_PAGE + 1,
            offset=(page_no - 1) * CANDIDATES_PER_PAGE)
        return render(request, "editorial_page.html", status_code=status_code, page=page,
                      cards=editorial.draft_cards(slug), base="",
                      candidates=rows[:CANDIDATES_PER_PAGE],
                      more=len(rows) > CANDIDATES_PER_PAGE, pagina=page_no,
                      events=read(lambda db: db.editorial_events(slug)),
                      max_slots=MAX_SLOTS, **extra)

    def guard(request: Request) -> None:
        if not same_origin(request):
            raise HTTPException(status_code=403, detail="cross-origin form refused")

    def apply(slug: str, action: str, fields: dict[str, str]) -> tuple[int, str | None]:
        """Run one mutation. Returns (status, message): 303 means it landed."""
        try:
            version = int(fields.get("version", "0"))
            to_position = int(fields.get("to_position", "0"))
        except ValueError:
            return 422, "invalid numeric field"
        note = fields.get("note", "").strip()
        auto_note = note or f"{action} via backoffice"
        try:
            if action == "add":
                editorial.add(slug, fields.get("series_id", ""),
                              fields.get("derived_key") or None, version, auto_note)
            elif action == "move":
                editorial.move(slug, fields.get("series_id", ""), to_position, version,
                               auto_note)
            elif action == "remove":
                editorial.remove(slug, fields.get("series_id", ""), version, auto_note)
            elif action == "discard":
                editorial.discard(slug, version, auto_note)
            elif action == "publish":
                editorial.publish(slug, version, note)
            elif action == "reset":
                editorial.reset(slug, version, note)
            else:  # pragma: no cover - the routes below name every action
                return 404, f"unknown action: {action}"
        except (EditorialBusy, EditorialConflict) as e:
            return 409, str(e)
        except (EditorialRefused, ValueError) as e:
            return 422, str(e)
        except MissingText:
            return 404, f"unknown page: {slug}"
        return 303, None

    @app.api_route("/editorial", methods=PAGE_METHODS)
    def editorial_list(request: Request):
        return render(request, "editorial_list.html", pages=editorial.pages(),
                      available=editorial.available())

    @app.api_route("/editorial/{slug}", methods=PAGE_METHODS)
    def editorial_detail(request: Request, slug: str):
        return editor_page(request, slug)

    async def mutate(request: Request, slug: str, action: str):
        guard(request)
        fields = await form(request)
        status, message = await run_in_threadpool(apply, slug, action, fields)
        if status == 303:
            return RedirectResponse(f"/editorial/{slug}", status_code=303)
        if status == 404:
            return render(request, "error.html", 404, title="Unknown page", message=message)
        return await run_in_threadpool(editor_page, request, slug, status_code=status,
                                       error=message)

    @app.post("/editorial/{slug}/add")
    async def editorial_add(request: Request, slug: str):
        return await mutate(request, slug, "add")

    @app.post("/editorial/{slug}/move")
    async def editorial_move(request: Request, slug: str):
        return await mutate(request, slug, "move")

    @app.post("/editorial/{slug}/remove")
    async def editorial_remove(request: Request, slug: str):
        return await mutate(request, slug, "remove")

    @app.post("/editorial/{slug}/discard")
    async def editorial_discard(request: Request, slug: str):
        return await mutate(request, slug, "discard")

    @app.post("/editorial/{slug}/publish")
    async def editorial_publish(request: Request, slug: str):
        return await mutate(request, slug, "publish")

    @app.post("/editorial/{slug}/reset")
    async def editorial_reset(request: Request, slug: str):
        return await mutate(request, slug, "reset")

    return app


def app_from_env() -> FastAPI:
    """uvicorn entry point (`uvicorn backoffice.app:app_from_env --factory`)."""
    db_path, registry_path, raw_dir = paths_from_env()
    return create_app(db_path, registry_path, raw_dir=raw_dir,
                      allowed_hosts=allowed_hosts_from_env(),
                      editorial_db_path=editorial_path_from_env())
