"""
Scans router — Phase 1 stub (model-level endpoints without scanner execution).

Implemented now:
  POST  /api/scans          — create scan record (queued state)
  GET   /api/scans          — list scans (filter by application_id)
  GET   /api/scans/{id}     — scan detail
  GET   /api/scans/{id}/status — lightweight status poll

Scanner invocation (Phase 3) wires into POST /api/scans as BackgroundTask.
Findings endpoints (Phase 3) live in findings.py.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan
from app.models.application import Application
from app.models.base import new_uuid
from app.schemas.scan import (
    ScanCreate,
    ScanResponse,
    ScanStatusResponse,
    ScanListResponse,
)

router = APIRouter(prefix="/scans", tags=["scans"])


def _get_scan_or_404(db: Session, scan_id: str) -> Scan:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    return scan


@router.post(
    "",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create scan (queued — scanner not yet running)",
)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)):
    # Validate application exists
    app = db.get(Application, payload.application_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{payload.application_id}' not found")

    scan = Scan(
        id=new_uuid(),
        application_id=payload.application_id,
        name=payload.name,
        scan_type=payload.scan_type,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


@router.get(
    "",
    response_model=ScanListResponse,
    summary="List scans",
)
def list_scans(
    application_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Scan)
    if application_id:
        q = q.filter(Scan.application_id == application_id)
    total = q.count()
    items = q.order_by(Scan.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ScanListResponse(total=total, items=items)


@router.get(
    "/{scan_id}",
    response_model=ScanResponse,
    summary="Get scan detail",
)
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    return _get_scan_or_404(db, scan_id)


@router.get(
    "/{scan_id}/status",
    response_model=ScanStatusResponse,
    summary="Lightweight scan status poll",
)
def get_scan_status(scan_id: str, db: Session = Depends(get_db)):
    return _get_scan_or_404(db, scan_id)


@router.delete(
    "/{scan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scan and all findings",
)
def delete_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = _get_scan_or_404(db, scan_id)
    db.delete(scan)
    db.commit()
