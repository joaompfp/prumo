"""The public Prumo site: server-rendered, read-only, no JavaScript.

Every page reads through `ingest.db.read_db_readonly`, which opens the database strictly
read-only and refuses a schema that does not match this code (HTTP 503, like `ingest status`).
Only GET and HEAD are routed. Assets are local; the CSP forbids everything else.
"""
import csv
import io
import logging
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from app import reads
from app.charts import line_chart, sparkline, two_series_chart
from app.formatting import format_count, format_date, format_datetime, format_period, format_value
from ingest.db import ReadOnlyOpenError, read_db_readonly
from presentation import MissingText
from presentation.web import mount_prefix as _base

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR.parent / "static"
DEFAULT_DB = "/data/prumo.sqlite3"
PAGE_METHODS = ["GET", "HEAD"]
NAV = (("/", "Início"), ("/temas/economy", "Economia"), ("/temas/demography", "Demografia"),
       ("/temas/energy", "Energia"), ("/comparar", "Comparações"), ("/fontes", "Fontes"),
       ("/metodologia", "Metodologia"))
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self' data:; "
                               "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


log = logging.getLogger("prumo.app")


def _templates() -> Jinja2Templates:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.globals.update(chart=line_chart, chart_two=two_series_chart, spark=sparkline,
                       format_value=format_value, format_period=format_period,
                       format_datetime=format_datetime, format_date=format_date,
                       format_count=format_count)
    return Jinja2Templates(env=env)


def _render(templates: Jinja2Templates, request: Request, name: str, context: dict,
            status: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, name, {"base": _base(request), "nav": NAV,
                                                      "path": request.url.path, **context},
                                      status_code=status)


def _read(request: Request, work):
    """Run a read function on a read-only handle; ReadOnlyOpenError becomes a 503 page."""
    return read_db_readonly(request.app.state.db_path, work)


def _csv_response(export: reads.CsvExport) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(export.header)
    for row in export.rows:
        writer.writerow(row)
    writer.writerow([])
    for line in export.footer:
        writer.writerow([line])
    return Response(content="\ufeff" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{export.filename}"'})


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Prumo", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.db_path = db_path or os.environ.get("PRUMO_DB_PATH") or DEFAULT_DB
    templates = _templates()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        # A cached page must not be reused across mount prefixes.
        vary = response.headers.get("Vary")
        if not vary:
            response.headers["Vary"] = "X-Forwarded-Prefix"
        elif "x-forwarded-prefix" not in vary.lower():
            response.headers["Vary"] = f"{vary}, X-Forwarded-Prefix"
        return response

    def unavailable(request: Request, exc: Exception):
        """503 for an unusable database: the reason belongs in the log, not on a public page
        (the exception string carries the database path and the schema versions)."""
        log.error("database unusable on %s: %s", request.url.path, exc)
        return _render(templates, request, "503.html", {}, status=503)

    def page(name: str, work, status: int = 200):
        """Decorator: read on a read-only handle, render `name`, 503 on an unusable database."""
        def route(request: Request):
            try:
                data = _read(request, work)
            except ReadOnlyOpenError as exc:
                return unavailable(request, exc)
            if data is None:
                return _render(templates, request, "404.html", {}, status=404)
            return _render(templates, request, name, {"page": data}, status=status)
        return route

    @app.api_route("/healthz", methods=PAGE_METHODS)
    def healthz():
        return {"status": "ok"}

    # CSV routes first: `/series/{id}` would otherwise swallow the `.csv` suffix.
    @app.api_route("/series/{series_id}.csv", methods=PAGE_METHODS)
    def series_csv(request: Request, series_id: str):
        try:
            export = _read(request, lambda db: reads.series_csv(db, series_id))
        except ReadOnlyOpenError as exc:
            log.error("database unusable on %s: %s", request.url.path, exc)
            return PlainTextResponse(status_code=503)
        if export is None:
            return PlainTextResponse("Série não publicada.", status_code=404)
        return _csv_response(export)

    @app.api_route("/calculadas/{key:path}.csv", methods=PAGE_METHODS)
    def derived_csv(request: Request, key: str):
        try:
            export = _read(request, lambda db: reads.derived_csv(db, key))
        except ReadOnlyOpenError as exc:
            log.error("database unusable on %s: %s", request.url.path, exc)
            return PlainTextResponse(status_code=503)
        if export is None:
            return PlainTextResponse("Série não publicada.", status_code=404)
        return _csv_response(export)

    app.add_api_route("/", page("home.html", lambda db: reads.home(db)), methods=PAGE_METHODS,
                      response_class=HTMLResponse)

    @app.api_route("/temas/{code}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def theme(request: Request, code: str, grupo: str = "", fonte: str = "",
              frequencia: str = "", pagina: int = Query(1, ge=1)):
        try:
            data = _read(request, lambda db: reads.theme(
                db, code, group=grupo, source=fonte, frequency=frequencia, page=pagina))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "theme.html", {"page": data})

    @app.api_route("/series/{series_id}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def series(request: Request, series_id: str, janela: str = "max", dia: str | None = None):
        try:
            data = _read(request, lambda db: reads.series_page(
                db, series_id, window=janela, day=dia))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "series.html", {"page": data})

    @app.api_route("/calculadas/{key:path}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def derived(request: Request, key: str):
        try:
            data = _read(request, lambda db: reads.derived_page(db, key))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "derived.html", {"page": data})

    @app.api_route("/pesquisa", methods=PAGE_METHODS, response_class=HTMLResponse)
    def search(request: Request, q: str = ""):
        try:
            rows = _read(request, lambda db: reads.search(db, q))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        return _render(templates, request, "search.html", {"query": q, "rows": rows})

    @app.api_route("/fontes", methods=PAGE_METHODS, response_class=HTMLResponse)
    def sources(request: Request):
        try:
            data = _read(request, lambda db: reads.sources_page(db))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        return _render(templates, request, "sources.html", {"page": data})

    @app.api_route("/metodologia", methods=PAGE_METHODS, response_class=HTMLResponse)
    def methodology(request: Request):
        return _render(templates, request, "methodology.html", {})

    @app.api_route("/comparar", methods=PAGE_METHODS, response_class=HTMLResponse)
    def comparisons_index(request: Request):
        try:
            data = _read(request, lambda db: reads.comparisons_index(db))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        return _render(templates, request, "compare_index.html", {"page": data})

    @app.api_route("/comparar/{slug}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def comparison(request: Request, slug: str):
        """A curated pair by slug: the route never accepts two series ids."""
        try:
            data = _read(request, lambda db: reads.comparison_page(db, slug))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "compare.html", {"page": data})

    @app.exception_handler(MissingText)
    def missing_reader_text(request: Request, exc: MissingText):
        """A code with no catalogue text is an operator fault, not a reader's: serve the
        same 503 page as an unusable database, but log the code so the gap can be fixed."""
        log.error("MissingText on %s: %s", request.url.path, exc)
        return _render(templates, request, "503.html", {}, status=503)

    @app.exception_handler(sqlite3.OperationalError)
    def unusable_database(request: Request, exc: sqlite3.OperationalError):
        """Right schema version but a view or table this code expects is missing."""
        log.exception("unusable database on %s", request.url.path)
        return _render(templates, request, "503.html", {}, status=503)

    @app.exception_handler(404)
    def not_found(request: Request, exc):
        return _render(templates, request, "404.html", {}, status=404)

    return app


app = create_app()
