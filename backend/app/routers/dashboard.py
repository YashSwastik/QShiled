"""
Dashboard router — GET /api/dashboard

Provides a single aggregated summary of a scan's security posture for the
executive dashboard.  All values are derived from existing DB state; this
router does NOT re-implement risk, recommendation, or roadmap engines.

Endpoints:
  GET /api/dashboard?scan_id=<id>  — full dashboard summary for one scan
  GET /api/dashboard/scans         — list completed scans (with app name) for selector

Quantum Readiness Score Methodology
------------------------------------
Range: 0–100.  Higher = more quantum-ready.
This is QShield's internal deterministic score.  It is NOT an official NIST
score or compliance certification.

Components (weights):

  S_exposure   (60%) — proportion of findings that are NOT quantum-vulnerable
                        = (total − vulnerable) / total
                        No findings → 1.0 (unknown exposure, not guaranteed safe)

  S_risk_inv   (25%) — 1 − (mean quantum_migration_score / 100)
                        for all findings that have a risk score.
                        No risk-scored findings → 1.0 (no measured risk)

  S_progress   (15%) — fraction of roadmap items that have reached MIGRATED
                        No roadmap items → 1.0 (nothing to migrate yet)

Final score:
  QRS = round(60 × S_exposure + 25 × S_risk_inv + 15 × S_progress)
  Clamped to [0, 100].

Readiness labels:
  90–100 → High Readiness
  70–89  → Moderate-High Readiness
  50–69  → Moderate Readiness
  30–49  → Limited Readiness
  0–29   → Low Readiness
"""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus
from app.models.finding import CryptoFinding, QuantumStatus, FindingCategory
from app.models.application import Application
from app.models.risk_assessment import RiskAssessment
from app.models.roadmap import RoadmapItem as RoadmapItemORM
from app.services.roadmap_engine import MIGRATION_STAGES

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ScanOption(BaseModel):
    """Lightweight scan entry for the application/scan selector."""
    scan_id: str
    scan_name: str
    application_id: str
    application_name: str
    status: str
    completed_at: datetime | None = None
    finding_count: int


class AlgorithmCount(BaseModel):
    family: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class StageCount(BaseModel):
    stage: str
    count: int


class WaveCount(BaseModel):
    wave: int
    label: str
    count: int


class TopAsset(BaseModel):
    application_id: str
    application_name: str
    highest_severity: str
    relevant_findings: int
    wave: int | None = None


class TopFinding(BaseModel):
    finding_id: str
    scan_id: str
    algorithm: str
    algorithm_family: str
    file_path: str | None
    risk_score: float
    severity: str
    migration_priority: str | None


class ReadinessMethodology(BaseModel):
    description: str
    component_exposure_weight: float = 0.60
    component_risk_weight: float = 0.25
    component_progress_weight: float = 0.15
    s_exposure: float
    s_risk_inv: float
    s_progress: float
    disclaimer: str = (
        "This score reflects QShield's internal deterministic migration prioritization methodology. "
        "It is not an official NIST risk score or a compliance certification."
    )


class DashboardSummary(BaseModel):
    # Scan context
    scan_id: str
    scan_name: str
    scan_status: str
    application_id: str | None
    application_name: str
    completed_at: datetime | None = None

    # Quantum Readiness Score
    quantum_readiness_score: int          # 0–100
    readiness_label: str                  # e.g. "Moderate Readiness"
    readiness_methodology: ReadinessMethodology

    # Findings summary
    total_findings: int
    quantum_relevant_findings: int        # vulnerable + borderline
    quantum_safe_findings: int
    critical_findings: int
    high_findings: int
    moderate_findings: int
    low_findings: int

    # Algorithm distribution (top families by count)
    algorithm_distribution: list[AlgorithmCount]

    # Severity distribution (from per_finding_scores in RiskAssessment)
    severity_distribution: list[SeverityCount]

    # Migration status
    total_roadmap_items: int
    migrated_items: int
    migration_progress_pct: float         # 0–100
    stage_distribution: list[StageCount]  # per MIGRATION_STAGES
    wave_distribution: list[WaveCount]    # per wave 1/2/3

    # Priority attention
    top_assets: list[TopAsset]            # up to 5 priority applications
    top_findings: list[TopFinding]        # up to 5 highest-risk findings

    # Scanning state hint
    has_running_scan: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────

_SEVERITY_ORDER = ["Critical", "High", "Moderate", "Low"]
_SEVERITY_SCORE_MAP = {"Critical": 75.0, "High": 50.0, "Moderate": 25.0, "Low": 0.0}

READINESS_LABELS = [
    (90, "High Readiness"),
    (70, "Moderate-High Readiness"),
    (50, "Moderate Readiness"),
    (30, "Limited Readiness"),
    (0,  "Low Readiness"),
]


def _readiness_label(score: int) -> str:
    for threshold, label in READINESS_LABELS:
        if score >= threshold:
            return label
    return "Low Readiness"


def _compute_readiness(
    total_findings: int,
    vulnerable_count: int,
    avg_risk_score: float | None,
    total_roadmap: int,
    migrated_count: int,
) -> tuple[int, ReadinessMethodology]:
    """
    Deterministic Quantum Readiness Score.

    S_exposure  (60%) — proportion of non-vulnerable findings
    S_risk_inv  (25%) — 1 − (avg quantum migration score / 100)
    S_progress  (15%) — migrated roadmap items / total roadmap items

    Returns (score_0_100, methodology_detail)
    """
    # Component 1: exposure (no findings = no measured exposure = 1.0)
    if total_findings > 0:
        s_exposure = (total_findings - vulnerable_count) / total_findings
    else:
        s_exposure = 1.0

    # Component 2: risk inversion (no scored findings = no measured risk = 1.0)
    if avg_risk_score is not None and total_findings > 0:
        s_risk_inv = max(0.0, 1.0 - avg_risk_score / 100.0)
    else:
        s_risk_inv = 1.0

    # Component 3: migration progress (no items = nothing to migrate = 1.0)
    if total_roadmap > 0:
        s_progress = migrated_count / total_roadmap
    else:
        s_progress = 1.0

    raw = 60.0 * s_exposure + 25.0 * s_risk_inv + 15.0 * s_progress
    score = int(round(min(100.0, max(0.0, raw))))

    methodology = ReadinessMethodology(
        description=(
            "QRS = 60% × (non-vulnerable findings ÷ total findings) "
            "+ 25% × (1 − avg_risk_score ÷ 100) "
            "+ 15% × (migrated_roadmap_items ÷ total_roadmap_items). "
            "Each component defaults to 1.0 when there is no data (no scans, "
            "no risk scores, no roadmap items)."
        ),
        s_exposure=round(s_exposure, 4),
        s_risk_inv=round(s_risk_inv, 4),
        s_progress=round(s_progress, 4),
    )
    return score, methodology


def _severity_from_score(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Low"


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/scans",
    response_model=list[ScanOption],
    summary="List completed scans with application context (for dashboard selector)",
)
def list_dashboard_scans(db: Session = Depends(get_db)):
    """
    Returns all completed scans (most recent first) with their application name.
    Also includes running/queued scans so the UI can show scanning state.
    """
    scans = (
        db.query(Scan)
        .order_by(Scan.created_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for s in scans:
        app = db.get(Application, s.application_id)
        result.append(ScanOption(
            scan_id=s.id,
            scan_name=s.name,
            application_id=s.application_id,
            application_name=app.name if app else "Unknown Application",
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
            completed_at=s.completed_at,
            finding_count=s.finding_count,
        ))
    return result


@router.get(
    "",
    response_model=DashboardSummary,
    summary="Aggregated dashboard summary for a scan",
)
def get_dashboard(
    scan_id: str = Query(..., description="UUID of the target scan"),
    db: Session = Depends(get_db),
):
    """
    Returns a single aggregated dashboard summary derived from real DB state:
      - Findings, quantum status breakdown
      - Algorithm family distribution
      - Severity distribution (from persisted RiskAssessment.per_finding_scores)
      - Roadmap stage/wave distribution (from persisted RoadmapItem.stage)
      - Quantum Readiness Score (deterministic formula documented above)
      - Top priority assets and highest-risk findings
      - Scanning state hint

    Does NOT re-run the risk engine, recommendation engine, or roadmap engine.
    Consumes already-persisted results produced by those engines.
    """
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")

    app = db.get(Application, scan.application_id) if scan.application_id else None
    app_name = app.name if app else "Unknown Application"

    # ── Findings ───────────────────────────────────────────────────────────────
    findings: list[CryptoFinding] = (
        db.query(CryptoFinding)
        .filter(CryptoFinding.scan_id == scan_id)
        .all()
    )
    total_findings = len(findings)

    vulnerable_count = sum(
        1 for f in findings
        if (f.quantum_status.value if hasattr(f.quantum_status, "value") else str(f.quantum_status))
        in ("vulnerable",)
    )
    borderline_count = sum(
        1 for f in findings
        if (f.quantum_status.value if hasattr(f.quantum_status, "value") else str(f.quantum_status))
        in ("borderline",)
    )
    safe_count = sum(
        1 for f in findings
        if (f.quantum_status.value if hasattr(f.quantum_status, "value") else str(f.quantum_status))
        in ("safe", "hybrid")
    )
    quantum_relevant = vulnerable_count + borderline_count

    # Algorithm family distribution
    family_counts: dict[str, int] = {}
    for f in findings:
        family_counts[f.algorithm_family] = family_counts.get(f.algorithm_family, 0) + 1
    algo_dist = sorted(
        [AlgorithmCount(family=k, count=v) for k, v in family_counts.items()],
        key=lambda x: x.count, reverse=True,
    )[:10]

    # ── Risk assessment (persisted) ────────────────────────────────────────────
    ra: RiskAssessment | None = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.scan_id == scan_id)
        .first()
    )

    per_finding_severity: dict[str, str] = {}  # finding_id → severity
    per_finding_priority: dict[str, str] = {}  # finding_id → migration_priority
    avg_risk_score: float | None = None

    if ra and ra.per_finding_scores:
        scores = [
            entry.get("quantum_migration_score", 0.0) or 0.0
            for entry in ra.per_finding_scores
        ]
        if scores:
            avg_risk_score = sum(scores) / len(scores)
        for entry in ra.per_finding_scores:
            fid = entry.get("finding_id")
            if fid:
                sev = entry.get("quantum_migration_severity") or _severity_from_score(
                    entry.get("quantum_migration_score") or 0.0
                )
                per_finding_severity[fid] = sev
                per_finding_priority[fid] = entry.get("migration_priority") or "low"

    # Severity distribution from per-finding data (or estimate from FindingCategory)
    sev_counts: dict[str, int] = {s: 0 for s in _SEVERITY_ORDER}
    safe_sev_count = 0
    for f in findings:
        fid = f.id
        if fid in per_finding_severity:
            sev = per_finding_severity[fid]
            if sev in sev_counts:
                sev_counts[sev] += 1
            else:
                safe_sev_count += 1
        else:
            # Fallback: estimate from quantum_status
            qs = f.quantum_status.value if hasattr(f.quantum_status, "value") else str(f.quantum_status)
            if qs == "vulnerable":
                sev_counts["High"] += 1
            elif qs == "borderline":
                sev_counts["Moderate"] += 1
            elif qs in ("safe", "hybrid"):
                safe_sev_count += 1
            else:
                sev_counts["Low"] += 1

    severity_dist = [
        SeverityCount(severity=s, count=sev_counts[s]) for s in _SEVERITY_ORDER
    ]
    severity_dist.append(SeverityCount(severity="Safe", count=safe_sev_count))

    critical_count = sev_counts["Critical"]
    high_count = sev_counts["High"]
    moderate_count = sev_counts["Moderate"]
    low_count = sev_counts["Low"]

    # ── Roadmap items (persisted) ──────────────────────────────────────────────
    roadmap_items: list[RoadmapItemORM] = (
        db.query(RoadmapItemORM)
        .filter(RoadmapItemORM.scan_id == scan_id)
        .all()
    )
    total_roadmap = len(roadmap_items)
    migrated_count = sum(1 for r in roadmap_items if r.stage == "MIGRATED")

    # Stage distribution
    stage_counts: dict[str, int] = {s: 0 for s in MIGRATION_STAGES}
    for r in roadmap_items:
        stage = r.stage if r.stage in stage_counts else "DISCOVERED"
        stage_counts[stage] += 1
    stage_dist = [StageCount(stage=s, count=stage_counts[s]) for s in MIGRATION_STAGES]

    # Wave distribution (from roadmap_items priority field — proxy for wave)
    # RoadmapItem.priority stores wave as 1/2/3 (set by roadmap engine)
    wave_counts: dict[int, int] = {1: 0, 2: 0, 3: 0}
    wave_labels = {1: "NOW", 2: "NEXT", 3: "LATER"}
    for r in roadmap_items:
        # Wave is encoded in priority: 1=wave1, 2=wave2, 3=wave3
        w = r.priority if r.priority in wave_counts else 3
        wave_counts[w] += 1
    wave_dist = [
        WaveCount(wave=w, label=wave_labels[w], count=wave_counts[w])
        for w in sorted(wave_counts)
    ]

    # Migration progress percentage (MIGRATED = 100%, DISCOVERED = 0%)
    if total_roadmap > 0:
        # Weight each stage by its position in the lifecycle
        stage_weights = {s: i / (len(MIGRATION_STAGES) - 1) for i, s in enumerate(MIGRATION_STAGES)}
        weighted_sum = sum(stage_weights.get(r.stage, 0.0) for r in roadmap_items)
        migration_progress_pct = round((weighted_sum / total_roadmap) * 100, 1)
    else:
        migration_progress_pct = 0.0

    # ── Quantum Readiness Score ───────────────────────────────────────────────
    qrs, methodology = _compute_readiness(
        total_findings=total_findings,
        vulnerable_count=vulnerable_count,
        avg_risk_score=avg_risk_score,
        total_roadmap=total_roadmap,
        migrated_count=migrated_count,
    )

    # ── Top priority assets ───────────────────────────────────────────────────
    # Use application-level aggregation: for the current scan's application,
    # show highest severity + finding count. For complete multi-app view
    # the frontend can call this endpoint per scan.
    top_assets: list[TopAsset] = []
    if app and total_findings > 0:
        # Determine highest severity for this application
        highest_sev = "Low"
        for sev in ["Critical", "High", "Moderate", "Low"]:
            if sev_counts.get(sev, 0) > 0:
                highest_sev = sev
                break
        # Best wave across roadmap items
        best_wave: int | None = None
        if roadmap_items:
            best_wave = min(r.priority for r in roadmap_items if r.priority in (1, 2, 3))
        top_assets.append(TopAsset(
            application_id=app.id,
            application_name=app.name,
            highest_severity=highest_sev,
            relevant_findings=quantum_relevant,
            wave=best_wave,
        ))

    # ── Top findings (highest quantum migration risk) ─────────────────────────
    finding_scores: list[tuple[float, CryptoFinding]] = []
    for f in findings:
        score_val = 0.0
        if ra and ra.per_finding_scores:
            for entry in ra.per_finding_scores:
                if entry.get("finding_id") == f.id:
                    score_val = float(entry.get("quantum_migration_score") or 0.0)
                    break
        elif f.risk_score is not None:
            score_val = float(f.risk_score)
        finding_scores.append((score_val, f))

    finding_scores.sort(key=lambda x: x[0], reverse=True)
    top_findings = [
        TopFinding(
            finding_id=f.id,
            scan_id=scan_id,
            algorithm=f.algorithm,
            algorithm_family=f.algorithm_family,
            file_path=f.file_path,
            risk_score=round(score, 1),
            severity=per_finding_severity.get(f.id, _severity_from_score(score)),
            migration_priority=per_finding_priority.get(f.id),
        )
        for score, f in finding_scores[:5]
    ]

    # ── Has running scan? ─────────────────────────────────────────────────────
    running = (
        db.query(Scan)
        .filter(
            Scan.application_id == scan.application_id,
            Scan.status.in_(["queued", "running"]),
        )
        .first()
    )

    return DashboardSummary(
        scan_id=scan.id,
        scan_name=scan.name,
        scan_status=scan.status.value if hasattr(scan.status, "value") else str(scan.status),
        application_id=scan.application_id,
        application_name=app_name,
        completed_at=scan.completed_at,
        quantum_readiness_score=qrs,
        readiness_label=_readiness_label(qrs),
        readiness_methodology=methodology,
        total_findings=total_findings,
        quantum_relevant_findings=quantum_relevant,
        quantum_safe_findings=safe_count,
        critical_findings=critical_count,
        high_findings=high_count,
        moderate_findings=moderate_count,
        low_findings=low_count,
        algorithm_distribution=algo_dist,
        severity_distribution=severity_dist,
        total_roadmap_items=total_roadmap,
        migrated_items=migrated_count,
        migration_progress_pct=migration_progress_pct,
        stage_distribution=stage_dist,
        wave_distribution=wave_dist,
        top_assets=top_assets,
        top_findings=top_findings,
        has_running_scan=running is not None,
    )
