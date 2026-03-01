import os
import time
import threading

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


def _prewarm_painel():
    """Pre-generate Painel IA analysis in the background after startup."""
    time.sleep(8)  # let uvicorn finish binding
    try:
        from .services.painel import build_painel
        from .services.painel_analysis import get_painel_analysis
        data = build_painel()
        sections = data.get("sections", [])
        updated = data.get("updated", "")
        if not sections or not updated:
            print("[startup] painel pre-warm: no data available", flush=True)
            return
        print(f"[startup] pre-warming Painel IA for period {updated}…", flush=True)
        result = get_painel_analysis(sections, updated)
        if result.get("cached"):
            print(f"[startup] Painel IA already cached for {updated}", flush=True)
        elif result.get("text"):
            ms = result.get("generation_ms", "?")
            print(f"[startup] Painel IA generated in {ms}ms for {updated}", flush=True)
        else:
            print(f"[startup] Painel IA failed: {result.get('error')}", flush=True)
    except Exception as e:
        print(f"[startup] painel pre-warm error: {e}", flush=True)


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
    threading.Thread(target=_prewarm_painel, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, workers=1)
