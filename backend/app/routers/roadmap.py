"""
Migration Roadmap router — GET /api/roadmap  + PATCH /api/roadmap/items/{finding_id}

GET  /api/roadmap?scan_id=<id>
  Generates & returns the deterministic migration roadmap for a completed scan.
  Wave assignment is recalculated from live risk + recommendation data on every call.
  Persisted user-status (ASSESSED, PLANNED, etc.) is overlaid on top of the recalculation.

PATCH /api/roadmap/items/{finding_id}?scan_id=<id>
  Updates the migration stage/status of one roadmap item.
  Only valid forward/explicit stage values are accepted.
  Persists to the roadmap_items DB table via the existing RoadmapItem model.

Design:
  - Consumes Part 7 risk results from RiskAssessment.per_finding_scores (no recalculation).
  - Consumes Part 8 recommendation engine deterministically.
  - Wave assignment is always derived from current upstream data.
  - User-controlled stage is overlaid: roadmap recalcs wave/priority but preserves stage.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus
from app.models.finding import CryptoFinding
from app.models.application import Application
from app.models.risk_assessment import RiskAssessment
from app.models.roadmap import RoadmapItem as RoadmapItemORM
from app.models.base import new_uuid
from app.schemas.roadmap_schema import (
    ScanRoadmapResponse,
    RoadmapItemSchema,
    WaveSummarySchema,
    RoadmapItemStatusUpdate,
)
from app.services.analyzer import FindingInput
from app.services.roadmap_engine import (
    build_roadmap,
    VALID_STAGES,
    MIGRATION_STAGES,
)

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


# ── Helpers shared with risk router ──────────────────────────────────────────

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


def _load_priority_map(
    db: Session,
    scan_id: str,
) -> dict[str, tuple[str | None, float | None, str | None]]:
    """Load Part 7 per-finding scores from persisted RiskAssessment."""
    ra = db.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
    if not ra or not ra.per_finding_scores:
        return {}
    result: dict[str, tuple[str | None, float | None, str | None]] = {}
    for entry in ra.per_finding_scores:
        fid = entry.get("finding_id")
        if fid:
            result[fid] = (
                entry.get("migration_priority"),
                entry.get("quantum_migration_score"),
                entry.get("quantum_migration_severity"),
            )
    return result


def _load_stage_overrides(
    db: Session,
    scan_id: str,
) -> dict[str, str]:
    """
    Load user-controlled stage overrides from persisted RoadmapItem rows.
    Returns {finding_id: stage_string} where stage_string is a MIGRATION_STAGES value.
    Uses the authoritative `stage` VARCHAR column (NOT the 4-value status enum).
    """
    rows = db.query(RoadmapItemORM).filter(RoadmapItemORM.scan_id == scan_id).all()
    return {row.finding_id: row.stage for row in rows}


def _persist_roadmap_items(
    db: Session,
    scan_id: str,
    items,
    stage_overrides: dict[str, str],
) -> None:
    """
    Upsert RoadmapItem rows for the scan.
    - For EXISTING rows: update wave/priority fields, but NEVER touch `stage`.
    - For NEW rows: insert with stage="DISCOVERED".
    - Does NOT delete existing rows (preserves user progress).
    """
    existing_ids = {
        row.finding_id
        for row in db.query(RoadmapItemORM.finding_id)
        .filter(RoadmapItemORM.scan_id == scan_id)
        .all()
    }
    for item in items:
        if item.finding_id in existing_ids:
            # Only update derived/engine fields — DO NOT overwrite stage
            row = (
                db.query(RoadmapItemORM)
                .filter(
                    RoadmapItemORM.scan_id == scan_id,
                    RoadmapItemORM.finding_id == item.finding_id,
                )
                .first()
            )
            if row:
                row.priority = item.wave
                # stage is intentionally left untouched here
        else:
            # New finding — insert with DISCOVERED stage
            row = RoadmapItemORM(
                id=new_uuid(),
                scan_id=scan_id,
                finding_id=item.finding_id,
                priority=item.wave,
                effort_estimate=_map_effort(item.effort_estimate),
                replacement_algorithm=",".join(item.recommended_algorithms[:2]) or item.recommended_target_category,
                nist_standard=",".join(item.nist_standards[:2]) if item.nist_standards else None,
                migration_notes=item.recommended_action,
                status=_map_status(MIGRATION_STAGES[0]),
                stage="DISCOVERED",  # authoritative canonical stage field
            )
            db.add(row)
    db.commit()


def _map_effort(effort: str):
    """Map KB effort string to ORM EffortEstimate enum-compatible value."""
    from app.models.roadmap import EffortEstimate
    mapping = {
        "low": EffortEstimate.low,
        "medium": EffortEstimate.medium,
        "high": EffortEstimate.high,
        "very_high": EffortEstimate.high,
        "unknown": EffortEstimate.medium,
    }
    return mapping.get(effort, EffortEstimate.medium)


def _map_status(stage: str):
    """Map MIGRATION_STAGES string to ORM RoadmapItemStatus enum value."""
    from app.models.roadmap import RoadmapItemStatus
    stage_to_status = {
        "DISCOVERED":  RoadmapItemStatus.pending,
        "ASSESSED":    RoadmapItemStatus.pending,
        "PLANNED":     RoadmapItemStatus.in_progress,
        "PILOT":       RoadmapItemStatus.in_progress,
        "TRANSITION":  RoadmapItemStatus.in_progress,
        "VALIDATION":  RoadmapItemStatus.in_progress,
        "MIGRATED":    RoadmapItemStatus.completed,
    }
    return stage_to_status.get(stage, RoadmapItemStatus.pending)


# ── GET /api/roadmap ──────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ScanRoadmapResponse,
    summary="Deterministic migration roadmap for a completed scan",
)
def get_roadmap(
    scan_id: str = Query(..., description="Scan ID to generate roadmap for"),
    db: Session = Depends(get_db),
):
    """
    Generate and return the full migration roadmap for a scan.

    Wave assignments come from:
      - Part 7 quantum migration priority/score (consumed from RiskAssessment)
      - Part 8 deterministic recommendation engine (purpose + effort)
      - Application business context (criticality, exposure, confidentiality)

    User-controlled stage/status is overlaid: the wave recalculates from current
    upstream data, but user progress (ASSESSED, PLANNED, etc.) is preserved.

    This is always recalculated live from actual data — it never serves stale
    hardcoded wave assignments.
    """
    # ── Validate scan ─────────────────────────────────────────────────────────
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    if scan.status != ScanStatus.completed:
        raise HTTPException(
            status_code=409,
            detail=f"Scan status is '{scan.status.value}' — roadmap requires a completed scan",
        )

    # ── Load application context ──────────────────────────────────────────────
    app_obj = db.get(Application, scan.application_id) if scan.application_id else None
    application_name = app_obj.name if app_obj else "Unknown Application"
    application_id = str(app_obj.id) if app_obj else None

    internet_exposed = bool(app_obj.internet_exposed) if app_obj else False
    confidentiality_requirement = (
        app_obj.confidentiality_requirement.value
        if app_obj and hasattr(app_obj.confidentiality_requirement, "value")
        else str(app_obj.confidentiality_requirement) if app_obj else "medium_term"
    )
    business_criticality = (
        app_obj.business_criticality.value
        if app_obj and hasattr(app_obj.business_criticality, "value")
        else str(app_obj.business_criticality) if app_obj else "medium"
    )

    # ── Load findings ─────────────────────────────────────────────────────────
    findings_orm = (
        db.query(CryptoFinding)
        .filter(CryptoFinding.scan_id == scan_id)
        .all()
    )
    finding_inputs = [_finding_to_input(f) for f in findings_orm]

    # ── Load Part 7 priority map (consume, do not recalculate) ───────────────
    priority_map = _load_priority_map(db, scan_id)

    # ── Load user stage overrides (preserve user progress) ───────────────────
    stage_overrides = _load_stage_overrides(db, scan_id)

    # ── Build roadmap (deterministic) ────────────────────────────────────────
    result = build_roadmap(
        scan_id=scan_id,
        application_name=application_name,
        application_id=application_id,
        findings=finding_inputs,
        priority_map=priority_map,
        internet_exposed=internet_exposed,
        confidentiality_requirement=confidentiality_requirement,
        business_criticality=business_criticality,
    )

    # ── Persist new items / update existing ──────────────────────────────────
    _persist_roadmap_items(db, scan_id, result.items, stage_overrides)

    # ── Overlay user-controlled stages ───────────────────────────────────────
    for item in result.items:
        persisted_stage = stage_overrides.get(item.finding_id)
        if persisted_stage and persisted_stage in VALID_STAGES:
            item.status = persisted_stage
            item.migration_stage = persisted_stage

    # ── Serialise ─────────────────────────────────────────────────────────────
    item_schemas = [
        RoadmapItemSchema(
            finding_id=item.finding_id,
            scan_id=item.scan_id,
            application_name=item.application_name,
            application_id=item.application_id,
            algorithm=item.algorithm,
            algorithm_family=item.algorithm_family,
            file_path=item.file_path,
            wave=item.wave,
            wave_label=item.wave_label,
            migration_priority=item.migration_priority,
            quantum_migration_score=item.quantum_migration_score,
            quantum_migration_severity=item.quantum_migration_severity,
            crypto_purpose=item.crypto_purpose,
            requires_manual_review=item.requires_manual_review,
            recommended_target_category=item.recommended_target_category,
            recommended_algorithms=item.recommended_algorithms,
            effort_estimate=item.effort_estimate,
            nist_standards=item.nist_standards,
            reason=item.reason,
            recommended_action=item.recommended_action,
            dependencies=item.dependencies,
            status=item.status,
            migration_stage=item.migration_stage,
            kb_version=item.kb_version,
        )
        for item in result.items
    ]

    wave_schemas = [
        WaveSummarySchema(
            wave=ws.wave,
            label=ws.label,
            item_count=ws.item_count,
            description=ws.description,
        )
        for ws in result.wave_summaries
    ]

    return ScanRoadmapResponse(
        scan_id=result.scan_id,
        application_name=result.application_name,
        application_id=result.application_id,
        total_items=result.total_items,
        wave_summaries=wave_schemas,
        items=item_schemas,
        summary=result.summary,
    )


# ── PATCH /api/roadmap/items/{finding_id} ─────────────────────────────────────

@router.patch(
    "/items/{finding_id}",
    response_model=RoadmapItemSchema,
    summary="Update migration stage/status for a roadmap item",
)
def update_roadmap_item_status(
    finding_id: str,
    body: RoadmapItemStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update the migration stage/status of one roadmap item.

    Valid stages (ordered lifecycle):
      DISCOVERED → ASSESSED → PLANNED → PILOT → TRANSITION → VALIDATION → MIGRATED

    Rules:
      - Only valid stage strings are accepted (case-sensitive).
      - Forward-only: you may not set a stage earlier than the current one.
        (MIGRATED → PILOT is rejected.)
      - The update is persisted and survives roadmap recalculation.
    """
    # ── Validate stage ────────────────────────────────────────────────────────
    new_stage = body.status.upper()
    if new_stage not in VALID_STAGES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"'{body.status}' is not a valid migration stage. "
                f"Valid stages: {', '.join(MIGRATION_STAGES)}"
            ),
        )

    # ── Load the roadmap item row ─────────────────────────────────────────────
    row = (
        db.query(RoadmapItemORM)
        .filter(
            RoadmapItemORM.scan_id == body.scan_id,
            RoadmapItemORM.finding_id == finding_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No roadmap item found for finding '{finding_id}' in scan '{body.scan_id}'. "
                   "Generate the roadmap first via GET /api/roadmap.",
        )

    # ── Enforce forward-only transition ──────────────────────────────────────
    # Read the authoritative stage string directly from the `stage` column.
    current_stage = row.stage if row.stage in VALID_STAGES else "DISCOVERED"
    current_idx = MIGRATION_STAGES.index(current_stage)
    new_idx = MIGRATION_STAGES.index(new_stage)

    if new_idx < current_idx:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cannot transition from '{current_stage}' to '{new_stage}': "
                "migration stages are forward-only. "
                f"Current stage: {current_stage} (index {current_idx}). "
                f"Requested stage: {new_stage} (index {new_idx})."
            ),
        )

    # ── Persist update ────────────────────────────────────────────────────────
    # Write directly to the authoritative `stage` VARCHAR column.
    # Also keep the status enum in sync for backward-compat queries.
    row.stage = new_stage
    row.status = _map_status(new_stage)
    db.commit()

    # ── Re-load finding for response ──────────────────────────────────────────
    finding = db.get(CryptoFinding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")

    # ── Build a lightweight response item ────────────────────────────────────
    scan = db.get(Scan, body.scan_id)
    app_obj = db.get(Application, scan.application_id) if scan and scan.application_id else None
    finding_input = _finding_to_input(finding)
    priority_map = _load_priority_map(db, body.scan_id)
    pri, score, severity = priority_map.get(finding_id, (None, None, None))

    from app.services.roadmap_engine import build_roadmap as _build, RoadmapItem as RI
    mini = build_roadmap(
        scan_id=body.scan_id,
        application_name=app_obj.name if app_obj else "Unknown",
        application_id=str(app_obj.id) if app_obj else None,
        findings=[finding_input],
        priority_map={finding_id: (pri, score, severity)},
        internet_exposed=bool(app_obj.internet_exposed) if app_obj else False,
        confidentiality_requirement=(
            app_obj.confidentiality_requirement.value
            if app_obj and hasattr(app_obj.confidentiality_requirement, "value")
            else "medium_term"
        ),
        business_criticality=(
            app_obj.business_criticality.value
            if app_obj and hasattr(app_obj.business_criticality, "value")
            else "medium"
        ),
    )
    item = mini.items[0]
    item.status = new_stage
    item.migration_stage = new_stage

    return RoadmapItemSchema(
        finding_id=item.finding_id,
        scan_id=item.scan_id,
        application_name=item.application_name,
        application_id=item.application_id,
        algorithm=item.algorithm,
        algorithm_family=item.algorithm_family,
        file_path=item.file_path,
        wave=item.wave,
        wave_label=item.wave_label,
        migration_priority=item.migration_priority,
        quantum_migration_score=item.quantum_migration_score,
        quantum_migration_severity=item.quantum_migration_severity,
        crypto_purpose=item.crypto_purpose,
        requires_manual_review=item.requires_manual_review,
        recommended_target_category=item.recommended_target_category,
        recommended_algorithms=item.recommended_algorithms,
        effort_estimate=item.effort_estimate,
        nist_standards=item.nist_standards,
        reason=item.reason,
        recommended_action=item.recommended_action,
        dependencies=item.dependencies,
        status=new_stage,
        migration_stage=new_stage,
        kb_version=item.kb_version,
    )


def _orm_status_to_stage(orm_status, migration_notes: str | None) -> str:
    """
    Recover the canonical stage string from a persisted RoadmapItem row.
    Prefers the embedded [STAGE:XXX] marker in migration_notes if present.
    Falls back to mapping the ORM status enum.
    """
    import re
    if migration_notes:
        m = re.search(r"\[STAGE:([A-Z_]+)\]", migration_notes)
        if m and m.group(1) in VALID_STAGES:
            return m.group(1)

    from app.models.roadmap import RoadmapItemStatus
    status_val = orm_status.value if hasattr(orm_status, "value") else str(orm_status)
    fallback = {
        "pending":     "DISCOVERED",
        "in_progress": "PLANNED",
        "completed":   "MIGRATED",
        "deferred":    "ASSESSED",
    }
    return fallback.get(status_val, "DISCOVERED")
