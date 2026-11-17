"""Public routes for authored CMS pages and charts.

Registered by `app.main.create_app` on the public loader, so a CMS page shares the shell,
prefix, security headers and 503 handling of every other public page. Only GET and HEAD are
routed; an unknown, draft-only or unpublished slug is a 404, exactly like an absent page.
"""
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import cms_reads
from ingest.db import ReadOnlyOpenError, read_db_readonly
from presentation.web import mount_prefix, prefixed

PAGE_METHODS = ["GET", "HEAD"]


def add_routes(app, *, templates, render, unavailable) -> None:
    """Add /paginas, /paginas/{slug} and /graficos/{slug} to `app`.

    `render` is the public `_render(templates, request, name, context, status=..., script=...)`
    function and `unavailable` the 503 handler, both owned by `app.main`; passing them keeps
    this module free of a second template loader or a second error policy.
    """

    def load(request: Request, work):
        """(data, None) or (None, a 503 response): one read-only snapshot per request."""
        try:
            return read_db_readonly(request.app.state.db_path, work), None
        except ReadOnlyOpenError as exc:
            return None, unavailable(request, exc)

    @app.api_route("/paginas", methods=PAGE_METHODS, response_class=HTMLResponse)
    def cms_index(request: Request):
        data, failure = load(request, lambda db: cms_reads.index(db))
        if failure is not None:
            return failure
        return render(templates, request, "cms_index.html", {"page": data})

    @app.api_route("/paginas/{slug}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def cms_page(request: Request, slug: str):
        if slug == cms_reads.HOME_SLUG:
            # The homepage is canonical at `/`. A draft or an unpublished document is not a
            # page and must not leak its body (or even its existence) through this old address.
            published, failure = load(request, cms_reads.home_is_published)
            if failure is not None:
                return failure
            if published:
                return RedirectResponse(prefixed(mount_prefix(request), "/"), status_code=301)
            return render(templates, request, "404.html", {}, status=404)
        data, failure = load(request, lambda db: cms_reads.public_page(db, slug))
        if failure is not None:
            return failure
        if data is None:
            return render(templates, request, "404.html", {}, status=404)
        return render(templates, request, "cms_page.html", {"page": data},
                      script=data.has_charts)

    @app.api_route("/graficos/{slug}", methods=PAGE_METHODS, response_class=HTMLResponse)
    def cms_chart(request: Request, slug: str):
        data, failure = load(request, lambda db: cms_reads.public_chart(db, slug))
        if failure is not None:
            return failure
        if data is None:
            return render(templates, request, "404.html", {}, status=404)
        return render(templates, request, "cms_chart.html", {"page": data},
                      script=data.chart_payload is not None)
