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

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from app import (
    cms_comparisons,
    cms_reads,
    cms_routes,
    interactive,
    navigation,
    notebook,
    notebook_routes,
    reads,
)
from app import home as home_page
from app.charts import chart_legend, chart_plot, chart_svg, line_chart, sparkline, two_series_chart
from app.formatting import format_count, format_date, format_datetime, format_period, format_value
from ingest.db import ReadOnlyOpenError, read_db_readonly
from presentation import MissingText
from presentation.notebook import text as notebook_text
from presentation.web import mount_prefix as _base

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR.parent / "static"
DEFAULT_DB = "/data/prumo.sqlite3"
PAGE_METHODS = ["GET", "HEAD"]
# Retained for the backoffice preview context; the public header renders nav_model.
NAV = navigation.legacy_links()
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self' data:; "
                               "font-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
# Only successful detail responses that actually carry a chart payload get this; summaries,
# errors, exports and the backoffice keep the no-script policy above.
CHART_CSP = (SECURITY_HEADERS["Content-Security-Policy"]
             + "; script-src 'self'; script-src-attr 'none'")


log = logging.getLogger("prumo.app")


def _templates() -> Jinja2Templates:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.globals.update(chart=line_chart, chart_two=two_series_chart, chart_svg=chart_svg,
                       chart_plot=chart_plot, chart_legend=chart_legend,
                       chart_js=interactive.asset_path(), spark=sparkline,
                       format_value=format_value, format_period=format_period,
                       format_datetime=format_datetime, format_date=format_date,
                       format_count=format_count, notebook_path=notebook.selection_path,
                       site_navigation=navigation.build_navigation,
                       notebook_copy=notebook_text("pt"))
    return Jinja2Templates(env=env)


def _render(templates: Jinja2Templates, request: Request, name: str, context: dict,
            status: int = 200, script: bool = False) -> HTMLResponse:
    base = _base(request) or navigation.root_path_base(request)
    path = navigation.request_path(request)
    nav_model = navigation.build_navigation(
        path, base, getattr(request.app.state, "notebook_label", "Caderno"))
    response = templates.TemplateResponse(request, name, {"base": base, "nav": NAV,
                                                          "nav_model": nav_model,
                                                          "path": path, **context},
                                          status_code=status)
    if script:
        # One effective policy: the middleware setdefault leaves this explicit header alone.
        response.headers["Content-Security-Policy"] = CHART_CSP
    return response


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
    app.state.notebook_label = notebook_text("pt").nav_label
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path == "/caderno":
            response.headers["X-Robots-Tag"] = "noindex, follow"
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

    @app.api_route("/", methods=PAGE_METHODS, response_class=HTMLResponse)
    def home(request: Request):
        """Legacy home until the first CMS publication; the CMS page thereafter."""
        try:
            plan = _read(request, lambda db: home_page.page(db))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        return _render(templates, request, plan.template, plan.context, status=plan.status,
                       script=plan.script)

    @app.api_route("/temas/{code}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def theme(request: Request, code: str, grupo: str = "", fonte: str = "",
              frequencia: str = "", pagina: str = "1"):
        page = reads.parse_page_number(pagina)
        try:
            data, cms_pages = _read(request, lambda db: (
                reads.theme(db, code, group=grupo, source=fonte, frequency=frequencia,
                            page=page),
                cms_reads.section_pages(db, code)))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "theme.html", {"page": data, "cms_pages": cms_pages})

    @app.api_route("/series/{series_id}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def series(request: Request, series_id: str, janela: str = "max", dia: str | None = None):
        try:
            data = _read(request, lambda db: reads.series_page(
                db, series_id, window=janela, day=dia))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "series.html", {"page": data},
                       script=data.chart_payload is not None)

    @app.api_route("/calculadas/{key:path}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def derived(request: Request, key: str):
        try:
            data = _read(request, lambda db: reads.derived_page(db, key))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "derived.html", {"page": data},
                       script=data.chart_payload is not None)

    @app.api_route("/pesquisa", methods=PAGE_METHODS, response_class=HTMLResponse)
    def search(request: Request, q: str = "", tema: str = "", grupo: str = "",
               fonte: str = "", frequencia: str = "", pagina: str = "1"):
        page = reads.parse_page_number(pagina)
        try:
            data = _read(request, lambda db: reads.search_page(
                db, q, theme=tema, group=grupo, source=fonte, frequency=frequencia,
                page=page))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        return _render(templates, request, "search.html", {"page": data})

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
            data = _read(request, cms_comparisons.index)
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        return _render(templates, request, "compare_index.html", {"page": data})

    @app.api_route("/comparar/paises/{slug}", methods=PAGE_METHODS,
                   response_class=HTMLResponse)
    def country_comparison(request: Request, slug: str):
        """Keep old country bookmarks while the CMS owns the canonical comparison."""
        from fastapi.responses import RedirectResponse
        try:
            data = _read(request, lambda db: cms_comparisons.public_chart(db, slug))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None or data.comparison_group != "countries":
            return _render(templates, request, "404.html", {}, status=404)
        return RedirectResponse(f"{_base(request)}/comparar/{slug}", status_code=301)

    @app.api_route("/comparar/{slug}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def comparison(request: Request, slug: str):
        """Display the operator's published revision; URL settings cannot override it."""
        try:
            data = _read(request, lambda db: cms_comparisons.public_chart(db, slug))
        except ReadOnlyOpenError as exc:
            return unavailable(request, exc)
        if data is None:
            return _render(templates, request, "404.html", {}, status=404)
        return _render(templates, request, "cms_chart.html", {"page": data},
                       script=data.chart_payload is not None)

    cms_routes.add_routes(app, templates=templates, render=_render, unavailable=unavailable)
    notebook_routes.add_routes(app, templates=templates, render=_render, unavailable=unavailable)

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
