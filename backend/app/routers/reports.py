"""
Reports router — Part 12
========================

Endpoints:
  GET  /api/reports                         → list available reports for a scan
  GET  /api/reports/executive?scan_id=      → Executive report JSON preview
  GET  /api/reports/inventory?scan_id=      → Inventory report JSON preview
  GET  /api/reports/roadmap?scan_id=        → Roadmap report JSON preview

  GET  /api/reports/executive/pdf?scan_id=  → Executive PDF download
  GET  /api/reports/inventory/pdf?scan_id=  → Inventory PDF download
  GET  /api/reports/roadmap/pdf?scan_id=    → Roadmap PDF download

  GET  /api/reports/all?scan_id=           → ZIP of all three PDFs

Design:
  - All report data is assembled by calling the *same logic* as existing routers
    (dashboard aggregation, recommendations engine, roadmap engine, findings).
  - No score recalculation — consumes persisted RiskAssessment data and roadmap items.
  - PDF generation is delegated to app.services.report_builder (pure functions).
  - ZIP is assembled in memory — no temp files.
"""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus
from app.models.finding import CryptoFinding
from app.models.application import Application
from app.models.project import Project
from app.models.risk_assessment import RiskAssessment
from app.models.roadmap import RoadmapItem as RoadmapItemORM

# Reuse existing service layer (no duplication)
from app.services.recommender import recommend_for_scan
from app.services.analyzer import FindingInput
from app.services.roadmap_engine import build_roadmap, VALID_STAGES, MIGRATION_STAGES

# Dashboard aggregation helper (internal import — same logic as dashboard router)
from app.routers.dashboard import (
    get_dashboard as _get_dashboard_summary,
    _severity_from_score,
)
from app.routers.roadmap import (
    _finding_to_input,
    _load_priority_map,
    _load_stage_overrides,
    _persist_roadmap_items,
    _map_effort,
    _map_status,
)

from app.services.report_builder import (
    build_executive_pdf,
    build_inventory_pdf,
    build_roadmap_pdf,
)

router = APIRouter(prefix="/reports", tags=["reports"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_filename(text: str, maxlen: int = 40) -> str:
    """Strip non-alphanumeric chars and truncate for use in filenames."""
    safe = re.sub(r"[^\w\-]", "_", text or "project")
    return safe[:maxlen].strip("_") or "project"


def _load_scan_or_404(db: Session, scan_id: str) -> Scan:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    if scan.status != ScanStatus.completed:
        raise HTTPException(
            status_code=409,
            detail=f"Scan status is '{scan.status.value}' — reports require a completed scan",
        )
    return scan


def _load_app_project(db: Session, scan: Scan) -> tuple[Application | None, Project | None]:
    app = db.get(Application, scan.application_id) if scan.application_id else None
    proj = db.get(Project, app.project_id) if (app and app.project_id) else None
    return app, proj


def _findings_for_scan(db: Session, scan_id: str) -> list[CryptoFinding]:
    return db.query(CryptoFinding).filter(CryptoFinding.scan_id == scan_id).all()


def _finding_to_input_local(f: CryptoFinding) -> FindingInput:
    return FindingInput(
        id=f.id,
        algorithm=f.algorithm,
        algorithm_family=f.algorithm_family,
        category=f.category.value if hasattr(f.category, "value") else str(f.category),
        quantum_status=f.quantum_status.value if hasattr(f.quantum_status, "value") else str(f.quantum_status),
        key_size=f.key_size,
        usage_context=f.usage_context,
        confidence=float(f.confidence),
        file_path=f.file_path,
    )


def _build_severity_map(db: Session, scan_id: str) -> dict[str, str]:
    """Return {finding_id: severity_str} from persisted RiskAssessment."""
    ra = db.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
    if not ra or not ra.per_finding_scores:
        return {}
    result = {}
    for entry in ra.per_finding_scores:
        fid = entry.get("finding_id")
        if fid:
            sev = entry.get("quantum_migration_severity") or _severity_from_score(
                entry.get("quantum_migration_score") or 0.0
            )
            result[fid] = sev
    return result


def _assemble_executive_data(db: Session, scan_id: str) -> dict:
    """Assemble all data needed for the Executive report."""
    scan = _load_scan_or_404(db, scan_id)
    app, proj = _load_app_project(db, scan)

    # Reuse dashboard aggregation (same function used by dashboard router)
    dash = _get_dashboard_summary(scan_id=scan_id, db=db)
    dash_dict = dash.model_dump()

    # Reuse recommendation engine
    findings_orm = _findings_for_scan(db, scan_id)
    priority_map = {}
    ra = db.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
    if ra and ra.per_finding_scores:
        for entry in ra.per_finding_scores:
            fid = entry.get("finding_id")
            if fid:
                priority_map[fid] = (
                    entry.get("migration_priority"),
                    entry.get("quantum_migration_score"),
                )
    inputs = [_finding_to_input_local(f) for f in findings_orm]
    rec_result = recommend_for_scan(scan_id=scan_id, findings=inputs, priority_map=priority_map)
    recs = [r.__dict__ if hasattr(r, "__dict__") else r for r in rec_result.recommendations]

    return {
        "scan":  {"id": scan.id, "name": scan.name, "completed_at": str(scan.completed_at)},
        "project": {"name": proj.name if proj else (app.name if app else "—")},
        "dashboard": dash_dict,
        "recommendations": recs,
    }


def _assemble_inventory_data(db: Session, scan_id: str) -> dict:
    """Assemble all data for the Inventory report."""
    scan = _load_scan_or_404(db, scan_id)
    app, proj = _load_app_project(db, scan)
    dash = _get_dashboard_summary(scan_id=scan_id, db=db)
    findings_orm = _findings_for_scan(db, scan_id)
    sev_map = _build_severity_map(db, scan_id)

    def _f2d(f: CryptoFinding) -> dict:
        return {
            "id":               f.id,
            "algorithm":        f.algorithm,
            "algorithm_family": f.algorithm_family,
            "category":         f.category.value if hasattr(f.category, "value") else str(f.category),
            "quantum_status":   f.quantum_status.value if hasattr(f.quantum_status, "value") else str(f.quantum_status),
            "key_size":         f.key_size,
            "usage_context":    f.usage_context,
            "file_path":        f.file_path,
            "line_number":      f.line_number,
            "confidence":       float(f.confidence or 0),
        }

    return {
        "scan":       {"id": scan.id, "name": scan.name},
        "project":    {"name": proj.name if proj else (app.name if app else "—")},
        "dashboard":  dash.model_dump(),
        "findings":   [_f2d(f) for f in findings_orm],
        "severity_map": sev_map,
    }


def _assemble_roadmap_data(db: Session, scan_id: str) -> dict:
    """Assemble all data for the Roadmap report."""
    scan = _load_scan_or_404(db, scan_id)
    app, proj = _load_app_project(db, scan)
    dash = _get_dashboard_summary(scan_id=scan_id, db=db)
    findings_orm = _findings_for_scan(db, scan_id)
    inputs = [_finding_to_input_local(f) for f in findings_orm]

    priority_map = _load_priority_map(db, scan_id)
    stage_overrides = _load_stage_overrides(db, scan_id)

    # Load application context for wave calculations (same as roadmap router)
    app_obj = db.get(Application, scan.application_id) if scan.application_id else None
    application_name = app_obj.name if app_obj else "Unknown Application"
    application_id_str = str(app_obj.id) if app_obj else None
    internet_exposed = bool(app_obj.internet_exposed) if app_obj else False
    confidentiality_req = (
        app_obj.confidentiality_requirement.value
        if app_obj and hasattr(app_obj.confidentiality_requirement, "value")
        else str(app_obj.confidentiality_requirement) if app_obj else "medium_term"
    )
    business_crit = (
        app_obj.business_criticality.value
        if app_obj and hasattr(app_obj.business_criticality, "value")
        else str(app_obj.business_criticality) if app_obj else "medium"
    )

    # Run roadmap engine (idempotent — same as roadmap router)
    roadmap_result = build_roadmap(
        scan_id=scan_id,
        application_name=application_name,
        application_id=application_id_str,
        findings=inputs,
        priority_map=priority_map,
        internet_exposed=internet_exposed,
        confidentiality_requirement=confidentiality_req,
        business_criticality=business_crit,
    )

    # Persist (idempotent upsert)
    _persist_roadmap_items(db, scan_id, roadmap_result.items, stage_overrides)

    # Overlay user-controlled stages
    for item in roadmap_result.items:
        persisted_stage = stage_overrides.get(item.finding_id)
        if persisted_stage and persisted_stage in VALID_STAGES:
            item.stage = persisted_stage

    # Recommendations (for priority actions section)
    priority_map_rec: dict[str, tuple] = {}
    ra = db.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
    if ra and ra.per_finding_scores:
        for entry in ra.per_finding_scores:
            fid = entry.get("finding_id")
            if fid:
                priority_map_rec[fid] = (
                    entry.get("migration_priority"),
                    entry.get("quantum_migration_score"),
                )
    rec_result = recommend_for_scan(scan_id=scan_id, findings=inputs, priority_map=priority_map_rec)
    recs = [r.__dict__ if hasattr(r, "__dict__") else r for r in rec_result.recommendations]

    def _item2d(it) -> dict:
        return {
            "finding_id":                it.finding_id,
            "algorithm":                 it.algorithm,
            "algorithm_family":          it.algorithm_family,
            "file_path":                 it.file_path,
            "wave":                      it.wave,
            "stage":                     getattr(it, "stage", getattr(it, "migration_stage", "DISCOVERED")),
            "effort_estimate":           it.effort_estimate,
            "recommended_target_category": it.recommended_target_category,
            "recommended_algorithms":    list(it.recommended_algorithms or []),
            "nist_standards":            list(it.nist_standards or []),
            "recommended_action":        it.recommended_action,
        }

    def _ws2d(ws) -> dict:
        return {
            "wave":        ws.wave,
            "label":       ws.label,
            "item_count":  ws.item_count,
            "description": ws.description,
        }

    return {
        "scan":     {"id": scan.id, "name": scan.name},
        "project":  {"name": proj.name if proj else (app.name if app else "—")},
        "dashboard": dash.model_dump(),
        "roadmap":  {
            "items":         [_item2d(it) for it in roadmap_result.items],
            "wave_summaries": [_ws2d(ws) for ws in roadmap_result.wave_summaries],
        },
        "recommendations": recs,
    }



# ── JSON preview endpoints ─────────────────────────────────────────────────────

@router.get(
    "",
    summary="List available reports and scan state for the report page",
)
def list_reports(
    scan_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Returns metadata about which reports are available for the scan.
    Used by the frontend to display the reports page with the correct state.
    """
    from app.routers.dashboard import list_dashboard_scans
    scans = list_dashboard_scans(db=db)
    completed = [s for s in scans if s.status == "completed"]

    if scan_id:
        scan = db.get(Scan, scan_id)
        has_risk = bool(
            db.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
        ) if scan else False
        has_roadmap = bool(
            db.query(RoadmapItemORM).filter(RoadmapItemORM.scan_id == scan_id).first()
        ) if scan else False
        return {
            "scan_id": scan_id,
            "completed_scans": [s.model_dump() for s in completed],
            "scan_ready": scan is not None and (scan.status == ScanStatus.completed if hasattr(scan.status, "value") else str(scan.status) == "completed"),
            "has_risk_data": has_risk,
            "has_roadmap_data": has_roadmap,
            "available_reports": [
                {"key": "executive",  "title": "Executive Quantum Readiness",   "available": True},
                {"key": "inventory",  "title": "Technical Cryptographic Inventory", "available": True},
                {"key": "roadmap",    "title": "Migration Roadmap",             "available": True},
            ],
        }

    return {
        "scan_id": None,
        "completed_scans": [s.model_dump() for s in completed],
        "scan_ready": False,
        "available_reports": [],
        "message": "Select a completed scan to generate reports.",
    }


@router.get("/executive", summary="Executive report — JSON preview data")
def get_executive_preview(
    scan_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return _assemble_executive_data(db, scan_id)


@router.get("/inventory", summary="Inventory report — JSON preview data")
def get_inventory_preview(
    scan_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return _assemble_inventory_data(db, scan_id)


@router.get("/roadmap", summary="Roadmap report — JSON preview data")
def get_roadmap_preview(
    scan_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return _assemble_roadmap_data(db, scan_id)


# ── PDF download endpoints ─────────────────────────────────────────────────────

@router.get("/executive/pdf", summary="Executive Quantum Readiness Report — PDF")
def download_executive_pdf(
    scan_id: str = Query(...),
    db: Session = Depends(get_db),
):
    data = _assemble_executive_data(db, scan_id)
    pdf_bytes = build_executive_pdf(data)
    proj_name = _safe_filename(data.get("project", {}).get("name", "project"))
    filename = f"Executive_Report_{proj_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventory/pdf", summary="Technical Cryptographic Inventory Report — PDF")
def download_inventory_pdf(
    scan_id: str = Query(...),
    db: Session = Depends(get_db),
):
    data = _assemble_inventory_data(db, scan_id)
    pdf_bytes = build_inventory_pdf(data)
    proj_name = _safe_filename(data.get("project", {}).get("name", "project"))
    filename = f"Technical_Inventory_Report_{proj_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/roadmap/pdf", summary="Migration Roadmap Report — PDF")
def download_roadmap_pdf(
    scan_id: str = Query(...),
    db: Session = Depends(get_db),
):
    data = _assemble_roadmap_data(db, scan_id)
    pdf_bytes = build_roadmap_pdf(data)
    proj_name = _safe_filename(data.get("project", {}).get("name", "project"))
    filename = f"Migration_Roadmap_Report_{proj_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/all", summary="All reports bundled as ZIP")
def download_all_reports(
    scan_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Generates all three PDFs and bundles them into a ZIP.
    PDFs are built once each — no duplication of report generation logic.
    """
    exec_data = _assemble_executive_data(db, scan_id)
    inv_data  = _assemble_inventory_data(db, scan_id)
    rdmp_data = _assemble_roadmap_data(db, scan_id)

    proj_name = _safe_filename(exec_data.get("project", {}).get("name", "project"))

    exec_pdf  = build_executive_pdf(exec_data)
    inv_pdf   = build_inventory_pdf(inv_data)
    rdmp_pdf  = build_roadmap_pdf(rdmp_data)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Executive_Report_{proj_name}.pdf",            exec_pdf)
        zf.writestr(f"Technical_Inventory_Report_{proj_name}.pdf",  inv_pdf)
        zf.writestr(f"Migration_Roadmap_Report_{proj_name}.pdf",    rdmp_pdf)

    zip_buf.seek(0)
    zip_filename = f"QShield_Reports_{proj_name}.zip"

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
