import os
import time
import threading

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import PORT, STATIC_DIR, CAE_DB_PATH, ANALYTICS_DB_PATH, TEMPLATES_DIR, BASE_PATH
from .routes.api import router as api_router
from .routes.share import router as share_router
from .routes.pages import router as pages_router
from .routes.london import router as london_router

app = FastAPI(
    title="CAE Dashboard",
    description="Indicadores Económicos Portugal — Plataforma de Dados",
    version="7.0",
    docs_url="/docs",
    redoc_url=None,
)

_error_templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Branded 404 page for HTML requests, JSON for API calls."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    prefix = request.headers.get("X-Forwarded-Prefix", "") or BASE_PATH
    return _error_templates.TemplateResponse(
        "404.html",
        {"request": request, "base_path": prefix.rstrip("/"), "path": request.url.path},
        status_code=404,
    )


# CORS — allow POST for /api/track
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def analytics_middleware(request: Request, call_next):
    """Log API requests to analytics DB (non-blocking, fire-and-forget)."""
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    response.headers["X-Response-Time"] = f"{duration}ms"
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/stats"):
        try:
            from .analytics import log_event
            log_event(
                event="api_call",
                host=request.headers.get("host", ""),
                path=path,
                extra=f"status={response.status_code},ms={duration}",
            )
        except Exception:
            pass  # analytics must never break the app
    return response


# Static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Routes — share router MUST precede pages (pages has catch-all /{full_path:path})
app.include_router(api_router)
app.include_router(london_router)
app.include_router(share_router)
app.include_router(pages_router)


@app.get("/healthz")
def healthz():
    """Health check with DB validation — returns 503 if DB is unreachable."""
    from .database import get_db
    try:
        conn = get_db()
        row = conn.execute("SELECT COUNT(DISTINCT indicator) AS n FROM indicators").fetchone()
        indicator_count = row[0] if row else 0
        # Check freshness: most recent period in DB
        fresh = conn.execute("SELECT MAX(period) FROM indicators").fetchone()
        latest_period = fresh[0] if fresh else None
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "error", "detail": f"DB unreachable: {e}"})
    return {"status": "ok", "indicators": indicator_count, "latest_period": latest_period}




@app.on_event("startup")
def startup():
    energy_db = os.path.join(os.path.dirname(CAE_DB_PATH), "energy-data.db")
    print(f"CAE Dashboard v7.0 — FastAPI", flush=True)
    print(f"DB: {CAE_DB_PATH}", flush=True)
    print(f"Analytics DB: {ANALYTICS_DB_PATH}", flush=True)
    if os.path.exists(energy_db):
        print(f"Energy DB: {energy_db}", flush=True)
    else:
        print(f"Energy DB not found, using main DB for all sources", flush=True)
    # Analysis is managed via batch scripts — no startup pre-warming


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, workers=1)
