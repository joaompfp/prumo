import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import PORT, STATIC_DIR, CAE_DB_PATH, ANALYTICS_DB_PATH
from .routes.api import router as api_router
from .routes.pages import router as pages_router

app = FastAPI(
    title="CAE Dashboard",
    description="Indicadores Económicos Portugal — Plataforma de Dados",
    version="7.0",
    docs_url="/docs",
    redoc_url=None,
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
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/stats"):
        try:
            from .analytics import log_event
            duration = round((time.time() - start) * 1000)
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

# Routes
app.include_router(api_router)
app.include_router(pages_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, workers=1)
