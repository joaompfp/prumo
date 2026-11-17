"""Public route for the indicator notebook.

Registered by `app.main.create_app` next to the other thin public routes, so the notebook
shares the shell, mount prefix, security headers and 503 policy. Only GET and HEAD are routed;
a malformed or over-limit address is the same generic 404 as an unpublic page.
"""
from fastapi import Request
from fastapi.responses import HTMLResponse

from app import notebook
from ingest.db import ReadOnlyOpenError, read_db_readonly

PAGE_METHODS = ["GET", "HEAD"]


def add_routes(app, *, templates, render, unavailable) -> None:
    """Add `/caderno` to `app`.

    `render` is the public `_render(templates, request, name, context, status=...)` function
    and `unavailable` the 503 handler owned by `app.main`; passing them keeps this module free
    of a second template loader or a second error policy. The response carries the notebook's
    noindex header; the template asks base.html for the matching robots meta block.
    """

    def noindex(response):
        response.headers["X-Robots-Tag"] = "noindex, follow"
        return response

    def load(request: Request, work):
        """(data, None) or (None, a 503 response): one read-only snapshot per request."""
        try:
            return read_db_readonly(request.app.state.db_path, work), None
        except ReadOnlyOpenError as exc:
            return None, unavailable(request, exc)

    @app.api_route("/caderno", methods=PAGE_METHODS, response_class=HTMLResponse)
    def notebook_page(request: Request):
        selection = notebook.parse_selection(request.query_params.getlist("s"))
        query = notebook.parse_query(request.query_params.get("q", ""))
        if selection is None or query is None:
            return noindex(render(templates, request, "404.html", {}, status=404))
        data, failure = load(request, lambda db: notebook.page(db, selection, query))
        if failure is not None:
            return noindex(failure)
        return noindex(render(templates, request, "notebook.html", {"page": data}))
