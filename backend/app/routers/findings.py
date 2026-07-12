"""
Findings router — returns CBOM findings for a completed scan.
Scanner populates these in Phase 3. Router is wired now so frontend can call it.

Implemented:
  GET /api/findings                     — list findings (filter by scan_id)
  GET /api/findings/{id}               — single finding detail
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finding import CryptoFinding
from app.schemas.scan import FindingResponse, FindingListResponse

router = APIRouter(prefix="/findings", tags=["findings"])


def _get_finding_or_404(db: Session, finding_id: str) -> CryptoFinding:
    finding = db.get(CryptoFinding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
    return finding


@router.get(
    "",
    response_model=FindingListResponse,
    summary="List crypto findings (CBOM)",
)
def list_findings(
    scan_id: str | None = Query(default=None),
    quantum_status: str | None = Query(default=None),
    algorithm_family: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(CryptoFinding)
    if scan_id:
        q = q.filter(CryptoFinding.scan_id == scan_id)
    if quantum_status:
        q = q.filter(CryptoFinding.quantum_status == quantum_status)
    if algorithm_family:
        q = q.filter(CryptoFinding.algorithm_family == algorithm_family)
    total = q.count()
    items = (
        q.order_by(CryptoFinding.risk_score.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return FindingListResponse(total=total, items=items)


@router.get(
    "/{finding_id}",
    response_model=FindingResponse,
    summary="Get single crypto finding detail",
)
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    return _get_finding_or_404(db, finding_id)
