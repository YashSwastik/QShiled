from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.routers import health
from app.routers import projects, scans, findings
from app.routers import upload as upload_router
from app.routers import risk as risk_router_module
from app.routers.stubs import roadmap_router, pqc_lab_router, reports_router

settings = get_settings()

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: DB init on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "QShield — Quantum-Safe Cryptography Migration Toolkit. "
        "Discovers cryptographic usage, builds a CBOM, scores quantum-migration risk, "
        "and generates NIST PQC-aligned migration recommendations."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler — structured error responses ─────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )

# ── Routers ───────────────────────────────────────────────────────────────────
# Health (legacy path kept for backward compat)
app.include_router(health.router, prefix="/api/v1")

# Core API  — all under /api
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(scans.router, prefix=API_PREFIX)
app.include_router(upload_router.router, prefix=API_PREFIX)
app.include_router(findings.router, prefix=API_PREFIX)

# Phase stubs (wired, return 200 with "not yet implemented" message)
app.include_router(risk_router_module.router, prefix=API_PREFIX)
app.include_router(roadmap_router, prefix=API_PREFIX)
app.include_router(pqc_lab_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "QShield API",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
