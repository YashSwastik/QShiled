"""
Risk Analysis router — GET /api/risk

Implements QShield Explainable Migration Prioritization Methodology.

Endpoints:
  GET /api/risk?scan_id=<id>   — Full risk analysis for a completed scan

The engine is deterministic and pure (no LLM). All scores are calculated
from real scanner findings + real application business context.

Quantum migration risk and classical/legacy security risk are kept separate.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus
from app.models.finding import CryptoFinding
from app.models.application import Application
from app.models.risk_assessment import RiskAssessment
from app.models.base import new_uuid
from app.schemas.risk import ScanRiskResponse, FindingRiskSchema, FactorScoreSchema, METHODOLOGY_NAME, METHODOLOGY_VERSION
from app.services.analyzer import (
    score_scan,
    FindingInput,
    ApplicationContext,
)

router = APIRouter(prefix="/risk", tags=["risk"])


def _build_app_context(app_obj: Application) -> ApplicationContext:
    """Convert ORM Application to pure-data ApplicationContext for the analyzer."""
    return ApplicationContext(
        business_criticality=app_obj.business_criticality.value
            if hasattr(app_obj.business_criticality, "value")
            else str(app_obj.business_criticality),
        internet_exposed=bool(app_obj.internet_exposed),
        data_sensitivity=app_obj.data_sensitivity.value
            if hasattr(app_obj.data_sensitivity, "value")
            else str(app_obj.data_sensitivity),
        confidentiality_requirement=app_obj.confidentiality_requirement.value
            if hasattr(app_obj.confidentiality_requirement, "value")
            else str(app_obj.confidentiality_requirement),
        data_lifetime_years=int(app_obj.data_lifetime_years or 5),
        environment=app_obj.environment.value
            if hasattr(app_obj.environment, "value")
            else str(app_obj.environment),
    )


def _default_app_context() -> ApplicationContext:
    """
    Fallback when business context is missing.
    Uses documented neutral defaults — does NOT invent high-risk context.
    All factor rationales will state 'defaulted'.
    """
    return ApplicationContext(
        business_criticality="medium",
        internet_exposed=False,
        data_sensitivity="internal",
        confidentiality_requirement="medium_term",
        data_lifetime_years=5,
        environment="production",
    )


def _finding_to_input(f: CryptoFinding) -> FindingInput:
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


def _persist_assessment(
    db: Session,
    scan: Scan,
    result,
    ctx: ApplicationContext,
) -> None:
    """
    Upsert the RiskAssessment record for this scan.
    Also writes per-finding risk_score back to CryptoFinding rows.
    Updates scan.overall_risk_score.
    """
    # Serialise per-finding scores to plain dicts
    per_finding_dicts = [
        {
            "finding_id": fs.finding_id,
            "algorithm": fs.algorithm,
            "algorithm_family": fs.algorithm_family,
            "quantum_migration_score": fs.quantum_migration_score,
            "quantum_migration_severity": fs.quantum_migration_severity,
            "classical_legacy_risk": fs.classical_legacy_risk,
            "migration_priority": fs.migration_priority,
            "factors": [
                {
                    "factor": f.factor,
                    "weight": f.weight,
                    "raw_value": f.raw_value,
                    "weighted_contribution": f.weighted_contribution,
                    "rationale": f.rationale,
                }
                for f in fs.factors
            ],
            "explanation": fs.explanation,
            "nist_recommendation": fs.nist_recommendation,
        }
        for fs in result.finding_scores
    ]

    # Build algorithm family distribution
    family_dist: dict[str, int] = {}
    for fs in result.finding_scores:
        family_dist[fs.algorithm_family] = family_dist.get(fs.algorithm_family, 0) + 1

    # Write risk_score back to each CryptoFinding row
    score_lookup = {fs.finding_id: fs.quantum_migration_score for fs in result.finding_scores}
    factor_lookup = {fs.finding_id: {f.factor: f.weighted_contribution for f in fs.factors} for fs in result.finding_scores}
    findings = db.query(CryptoFinding).filter(CryptoFinding.scan_id == scan.id).all()
    for f in findings:
        if f.id in score_lookup:
            f.risk_score = score_lookup[f.id]
            f.risk_factors = factor_lookup[f.id]

    # Upsert RiskAssessment (delete-and-recreate avoids update complexity)
    existing = db.query(RiskAssessment).filter(RiskAssessment.scan_id == scan.id).first()
    if existing:
        db.delete(existing)
        db.flush()

    ra = RiskAssessment(
        id=new_uuid(),
        scan_id=scan.id,
        overall_risk_score=result.overall_quantum_score,
        overall_severity=result.overall_severity,
        cryptographic_risk_score=result.overall_quantum_score,
        vulnerable_count=result.vulnerable_count,
        safe_count=result.safe_count,
        borderline_count=result.borderline_count,
        unknown_count=0,
        legacy_count=result.legacy_count,
        algorithm_family_distribution=family_dist,
        risk_factor_summary=result.factor_summary,
        per_finding_scores=per_finding_dicts,
        top_priority_finding_ids=result.top_priority_finding_ids,
        methodology_version=METHODOLOGY_VERSION,
        summary_text=result.summary_text,
    )
    db.add(ra)

    # Update scan aggregate
    scan.overall_risk_score = result.overall_quantum_score
    db.commit()


@router.get(
    "",
    response_model=ScanRiskResponse,
    summary="Quantum migration risk analysis for a scan (QShield Methodology)",
)
def get_risk_analysis(
    scan_id: str = Query(..., description="Scan ID to analyse"),
    db: Session = Depends(get_db),
):
    """
    Calculate and return the full quantum migration risk analysis for a scan.

    Uses the QShield Explainable Migration Prioritization Methodology:
      - Cryptographic quantum vulnerability: 30%
      - Confidentiality/data lifetime: 20%
      - Business criticality: 20%
      - External exposure: 15%
      - Migration complexity: 10%
      - Compliance/data sensitivity: 5%

    Quantum migration risk and classical/legacy security risk are reported separately.
    This is NOT an official NIST score.
    """
    # ── Load scan ────────────────────────────────────────────────────────────
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    if scan.status != ScanStatus.completed:
        raise HTTPException(
            status_code=409,
            detail=f"Scan status is '{scan.status.value}' — risk analysis requires a completed scan",
        )

    # ── Load application context ─────────────────────────────────────────────
    context_defaulted = False
    app_obj = db.get(Application, scan.application_id)
    if app_obj:
        ctx = _build_app_context(app_obj)
    else:
        ctx = _default_app_context()
        context_defaulted = True

    # ── Load findings ────────────────────────────────────────────────────────
    findings_orm = db.query(CryptoFinding).filter(CryptoFinding.scan_id == scan_id).all()
    finding_inputs = [_finding_to_input(f) for f in findings_orm]

    # ── Run analyzer ────────────────────────────────────────────────────────
    result = score_scan(scan_id, finding_inputs, ctx)

    # ── Persist results ──────────────────────────────────────────────────────
    _persist_assessment(db, scan, result, ctx)

    # ── Build response ───────────────────────────────────────────────────────
    # file_path lookup for top findings
    fp_map = {f.id: f.file_path for f in findings_orm}

    top_finding_ids_set = set(result.top_priority_finding_ids)
    top_finding_scores = [
        fs for fs in result.finding_scores
        if fs.finding_id in top_finding_ids_set
    ]
    top_finding_scores.sort(key=lambda x: x.quantum_migration_score, reverse=True)

    top_findings_resp = [
        FindingRiskSchema(
            finding_id=fs.finding_id,
            algorithm=fs.algorithm,
            algorithm_family=fs.algorithm_family,
            file_path=fp_map.get(fs.finding_id),
            quantum_migration_score=fs.quantum_migration_score,
            raw_weighted_sum=fs.raw_weighted_sum,
            crypto_vulnerability_gate=fs.crypto_vulnerability_gate,
            quantum_migration_severity=fs.quantum_migration_severity,
            classical_legacy_risk=fs.classical_legacy_risk,
            classical_legacy_rationale=fs.classical_legacy_rationale,
            factors=[
                FactorScoreSchema(
                    factor=f.factor,
                    label=f.label,
                    weight=f.weight,
                    raw_value=f.raw_value,
                    weighted_contribution=f.weighted_contribution,
                    rationale=f.rationale,
                )
                for f in fs.factors
            ],
            explanation=fs.explanation,
            migration_priority=fs.migration_priority,
            nist_recommendation=fs.nist_recommendation,
        )
        for fs in top_finding_scores
    ]

    summary = result.summary_text
    if context_defaulted:
        summary = "[Business context unavailable — neutral defaults used] " + summary

    return ScanRiskResponse(
        scan_id=scan_id,
        overall_quantum_score=result.overall_quantum_score,
        overall_severity=result.overall_severity,
        vulnerable_count=result.vulnerable_count,
        safe_count=result.safe_count,
        borderline_count=result.borderline_count,
        legacy_count=result.legacy_count,
        factor_summary=result.factor_summary,
        top_findings=top_findings_resp,
        summary_text=summary,
        business_criticality=ctx.business_criticality,
        internet_exposed=ctx.internet_exposed,
        confidentiality_requirement=ctx.confidentiality_requirement,
        data_sensitivity=ctx.data_sensitivity,
        data_lifetime_years=ctx.data_lifetime_years,
        environment=ctx.environment,
        context_defaulted=context_defaulted,
    )
