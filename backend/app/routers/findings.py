"""
Findings router — CBOM inventory API.

Endpoints:
  GET  /api/findings           — list with filter/search/sort/paginate
  GET  /api/findings/{id}      — single finding detail
  GET  /api/findings/summary   — aggregate counts by category & quantum_status

Filter params:
  scan_id, quantum_status, algorithm_family, category, search, sort_by, sort_dir, page, page_size
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finding import CryptoFinding, QuantumStatus, FindingCategory
from app.schemas.scan import FindingResponse, FindingListResponse

router = APIRouter(prefix="/findings", tags=["findings"])

_SORTABLE = {
    "algorithm":      CryptoFinding.algorithm,
    "algorithm_family": CryptoFinding.algorithm_family,
    "confidence":     CryptoFinding.confidence,
    "risk_score":     CryptoFinding.risk_score,
    "file_path":      CryptoFinding.file_path,
    "line_number":    CryptoFinding.line_number,
    "quantum_status": CryptoFinding.quantum_status,
    "category":       CryptoFinding.category,
    "created_at":     CryptoFinding.created_at,
}


def _get_finding_or_404(db: Session, finding_id: str) -> CryptoFinding:
    f = db.get(CryptoFinding, finding_id)
    if not f:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
    return f


@router.get(
    "/summary",
    summary="Aggregate CBOM counts for a scan",
)
def findings_summary(
    scan_id: str = Query(..., description="Scan ID"),
    db: Session = Depends(get_db),
):
    """
    Returns aggregate counts:
      - total findings
      - by_category (dict)
      - by_quantum_status (dict)
      - by_algorithm_family (top 10 list)
    """
    base = db.query(CryptoFinding).filter(CryptoFinding.scan_id == scan_id)
    total = base.count()

    by_cat = (
        db.query(CryptoFinding.category, func.count(CryptoFinding.id))
        .filter(CryptoFinding.scan_id == scan_id)
        .group_by(CryptoFinding.category)
        .all()
    )
    by_qs = (
        db.query(CryptoFinding.quantum_status, func.count(CryptoFinding.id))
        .filter(CryptoFinding.scan_id == scan_id)
        .group_by(CryptoFinding.quantum_status)
        .all()
    )
    by_family = (
        db.query(CryptoFinding.algorithm_family, func.count(CryptoFinding.id))
        .filter(CryptoFinding.scan_id == scan_id)
        .group_by(CryptoFinding.algorithm_family)
        .order_by(func.count(CryptoFinding.id).desc())
        .limit(10)
        .all()
    )

    return {
        "scan_id": scan_id,
        "total": total,
        "by_category": {k: v for k, v in by_cat},
        "by_quantum_status": {k: v for k, v in by_qs},
        "by_algorithm_family": [
            {"family": fam, "count": cnt} for fam, cnt in by_family
        ],
    }


@router.get(
    "",
    response_model=FindingListResponse,
    summary="List crypto findings (CBOM)",
)
def list_findings(
    scan_id: str | None = Query(default=None),
    quantum_status: str | None = Query(default=None),
    algorithm_family: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Search algorithm, file_path, or usage_context"),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
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
    if category:
        q = q.filter(CryptoFinding.category == category)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                CryptoFinding.algorithm.ilike(term),
                CryptoFinding.algorithm_family.ilike(term),
                CryptoFinding.file_path.ilike(term),
                CryptoFinding.usage_context.ilike(term),
            )
        )

    sort_col = _SORTABLE.get(sort_by, CryptoFinding.created_at)
    if sort_dir == "desc":
        q = q.order_by(sort_col.desc().nullslast())
    else:
        q = q.order_by(sort_col.asc().nullsfirst())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return FindingListResponse(total=total, items=items)


@router.get(
    "/{finding_id}",
    response_model=FindingResponse,
    summary="Get single crypto finding detail",
)
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    return _get_finding_or_404(db, finding_id)
