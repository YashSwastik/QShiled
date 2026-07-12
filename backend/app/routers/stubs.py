"""
Stub routers for Phase 1 — routes are wired but return 501 Not Implemented.
These stubs allow the frontend API client to reference correct URLs without
creating fake behavior. Full implementation in Phases 4, 6, 7.
"""
from fastapi import APIRouter

risk_router = APIRouter(prefix="/risk", tags=["risk"])
roadmap_router = APIRouter(prefix="/roadmap", tags=["roadmap"])
pqc_lab_router = APIRouter(prefix="/pqc-lab", tags=["pqc-lab"])
reports_router = APIRouter(prefix="/reports", tags=["reports"])


@risk_router.get("", summary="Risk assessment — Phase 4")
def risk_stub():
    return {"detail": "Risk analysis endpoint not yet implemented (Phase 4)", "phase": 4}


@roadmap_router.get("", summary="Migration roadmap — Phase 4")
def roadmap_stub():
    return {"detail": "Migration roadmap endpoint not yet implemented (Phase 4)", "phase": 4}


@pqc_lab_router.get("", summary="PQC operations demo — Phase 7")
def pqc_lab_stub():
    return {"detail": "PQC Lab endpoint not yet implemented (Phase 7)", "phase": 7}


@reports_router.get("", summary="Reports — Phase 6")
def reports_stub():
    return {"detail": "Reports endpoint not yet implemented (Phase 6)", "phase": 6}
