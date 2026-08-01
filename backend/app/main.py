"""
InfraMind AI - FastAPI Backend Service Main Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import create_all_tables
from app.core.limiter import limiter
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown lifecycle handler.
    IMPORTANT: capture the running asyncio loop here — this coroutine runs
    in the event loop thread, so asyncio.get_running_loop() works correctly.
    Sync route handlers (run in ThreadPoolExecutor) use this stored loop
    to schedule broadcasts via run_coroutine_threadsafe().
    """
    import asyncio as _asyncio
    from app.core.event_loop import set_main_loop
    set_main_loop(_asyncio.get_running_loop())

    create_all_tables()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "InfraMind AI — Intelligent Endpoint Monitoring & AI Incident Analysis Platform. "
        "Real-time telemetry, alerting, and AI-powered diagnostics for Windows endpoints."
    ),
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate limiting middleware ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS middleware ───────────────────────────────────────────────────────────
origins = [str(origin).rstrip("/") for origin in (settings.BACKEND_CORS_ORIGINS or [])]
if "*" in origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── API v1 routes ─────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)


# ── Base routes ───────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def read_root():
    """Root status endpoint."""
    return {
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "status": "online",
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """Health check endpoint for container / load balancer probes."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
