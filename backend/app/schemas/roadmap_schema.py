"""
Pydantic v2 schemas for the Migration Roadmap API.

All values are derived deterministically from actual scan data.
"""
from __future__ import annotations
from pydantic import BaseModel


class WaveSummarySchema(BaseModel):
    wave: int
    label: str
    item_count: int
    description: str


class RoadmapItemSchema(BaseModel):
    # Identity
    finding_id: str
    scan_id: str

    # Application
    application_name: str
    application_id: str | None = None

    # Algorithm context
    algorithm: str
    algorithm_family: str
    file_path: str | None = None

    # Wave
    wave: int
    wave_label: str

    # Risk scores (from Part 7 — consumed)
    migration_priority: str | None = None
    quantum_migration_score: float | None = None
    quantum_migration_severity: str | None = None

    # Purpose (from Part 8 — consumed)
    crypto_purpose: str
    requires_manual_review: bool

    # Recommended migration target (from Part 8 KB)
    recommended_target_category: str
    recommended_algorithms: list[str]
    effort_estimate: str
    nist_standards: list[str]

    # Roadmap-specific
    reason: str
    recommended_action: str
    dependencies: list[str]
    status: str            # Current lifecycle stage (mutable)
    migration_stage: str   # alias

    # Provenance
    kb_version: str


class ScanRoadmapResponse(BaseModel):
    scan_id: str
    application_name: str
    application_id: str | None = None
    total_items: int
    wave_summaries: list[WaveSummarySchema]
    items: list[RoadmapItemSchema]
    summary: str


class RoadmapItemStatusUpdate(BaseModel):
    """Request body for PATCH /api/roadmap/items/{finding_id}"""
    scan_id: str
    status: str

    model_config = {"str_strip_whitespace": True}
