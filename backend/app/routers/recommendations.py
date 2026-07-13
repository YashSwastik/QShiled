"""
Migration Recommendations router — GET /api/recommendations

Returns deterministic, purpose-aware migration recommendations for all findings
in a completed scan.

Recommendations come from:
  - Deterministic purpose classifier (purpose_classifier.py)
  - Curated migration knowledge base (knowledge_base.py)
  - Part 7 risk scores (consumed, never recalculated)

No LLM. No second risk methodology.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus
from app.models.finding import CryptoFinding
from app.models.risk_assessment import RiskAssessment
from app.schemas.recommendation import ScanRecommendationResponse, MigrationRecommendationSchema
from app.services.analyzer import FindingInput
from app.services.recommender import recommend_for_scan

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _finding_to_input(f: CryptoFinding) -> FindingInput:
    """Convert ORM CryptoFinding → pure-data FindingInput (same pattern as risk router)."""
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


def _build_priority_map(
    db: Session,
    scan_id: str,
) -> dict[str, tuple[str | None, float | None]]:
    """
    Load Part 7 per-finding priority/score from persisted RiskAssessment.
    Returns {finding_id: (migration_priority, quantum_migration_score)}.
    Falls back to empty dict if risk has not yet been run.
    """
    ra = db.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
    if not ra or not ra.per_finding_scores:
        return {}
    result: dict[str, tuple[str | None, float | None]] = {}
    for entry in ra.per_finding_scores:
        fid = entry.get("finding_id")
        if fid:
            result[fid] = (
                entry.get("migration_priority"),
                entry.get("quantum_migration_score"),
            )
    return result


@router.get(
    "",
    response_model=ScanRecommendationResponse,
    summary="Deterministic migration recommendations for a completed scan",
)
def get_recommendations(
    scan_id: str = Query(..., description="Scan ID to generate recommendations for"),
    db: Session = Depends(get_db),
):
    """
    Generate deterministic, purpose-aware migration recommendations for all findings.

    Recommendations are derived from:
      - QShield Migration Knowledge Base (version 1.0)
      - Deterministic purpose classification using scanner-provided evidence
      - Part 7 quantum migration priority (consumed, not recalculated)

    Key technical properties:
      - RSA for key establishment → ML-KEM path
      - RSA for signing → ML-DSA/SLH-DSA path (ML-KEM never recommended for signing)
      - ECDSA → ML-DSA/SLH-DSA signature path
      - Symmetric (AES/ChaCha20) → key-size upgrade only, NOT PQC replacement
      - Unknown purpose → manual review, no target invented

    This is NOT a second risk score. Risk scoring is performed by GET /api/risk.
    """
    # ── Load and validate scan ────────────────────────────────────────────────
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    if scan.status != ScanStatus.completed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Scan status is '{scan.status.value}' — "
                "recommendations require a completed scan"
            ),
        )

    # ── Load findings ─────────────────────────────────────────────────────────
    findings_orm = (
        db.query(CryptoFinding)
        .filter(CryptoFinding.scan_id == scan_id)
        .all()
    )
    finding_inputs = [_finding_to_input(f) for f in findings_orm]

    # ── Load Part 7 priority map (consume — do not recalculate) ──────────────
    priority_map = _build_priority_map(db, scan_id)

    # ── Run recommendation engine ─────────────────────────────────────────────
    result = recommend_for_scan(
        scan_id=scan_id,
        findings=finding_inputs,
        priority_map=priority_map,
    )

    # ── Serialise to schema ───────────────────────────────────────────────────
    rec_schemas = [
        MigrationRecommendationSchema(
            finding_id=r.finding_id,
            algorithm=r.algorithm,
            algorithm_family=r.algorithm_family,
            file_path=r.file_path,
            crypto_purpose=r.crypto_purpose,
            purpose_confidence=r.purpose_confidence,
            purpose_reasoning=r.purpose_reasoning,
            requires_manual_review=r.requires_manual_review,
            current_state_description=r.current_state_description,
            quantum_threat=r.quantum_threat,
            is_quantum_concern=r.is_quantum_concern,
            migration_priority=r.migration_priority,
            quantum_migration_score=r.quantum_migration_score,
            recommended_target_category=r.recommended_target_category,
            recommended_algorithms=r.recommended_algorithms,
            nist_standards=r.nist_standards,
            effort_estimate=r.effort_estimate,
            prerequisites=r.prerequisites,
            migration_steps=r.migration_steps,
            testing_requirements=r.testing_requirements,
            interoperability_notes=r.interoperability_notes,
            validation_checklist=r.validation_checklist,
            timeline_guidance=r.timeline_guidance,
            technical_notes=r.technical_notes,
            kb_version=r.kb_version,
            kb_entry_key=r.kb_entry_key,
        )
        for r in result.recommendations
    ]

    return ScanRecommendationResponse(
        scan_id=result.scan_id,
        kb_version=result.kb_version,
        total_findings=result.total_findings,
        recommendations=rec_schemas,
        manual_review_count=result.manual_review_count,
        quantum_concern_count=result.quantum_concern_count,
        classical_only_count=result.classical_only_count,
        safe_count=result.safe_count,
        summary=result.summary,
    )
