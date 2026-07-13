"""
Pydantic v2 schemas for the Migration Recommendations API.

These mirror the recommender.py data classes for HTTP serialization.
All values come from the backend deterministic engine — no hardcoding.
"""
from __future__ import annotations

from pydantic import BaseModel


class MigrationRecommendationSchema(BaseModel):
    finding_id: str
    algorithm: str
    algorithm_family: str
    file_path: str | None = None

    # Purpose
    crypto_purpose: str
    purpose_confidence: float
    purpose_reasoning: str
    requires_manual_review: bool

    # Current state
    current_state_description: str
    quantum_threat: str
    is_quantum_concern: bool

    # Part 7 priority (consumed, not recalculated)
    migration_priority: str | None = None
    quantum_migration_score: float | None = None

    # Target
    recommended_target_category: str
    recommended_algorithms: list[str]
    nist_standards: list[str]
    effort_estimate: str

    # Guidance
    prerequisites: list[str]
    migration_steps: list[str]
    testing_requirements: list[str]
    interoperability_notes: list[str]
    validation_checklist: list[str]

    timeline_guidance: str
    technical_notes: str

    # Provenance
    kb_version: str
    kb_entry_key: str | None = None


class ScanRecommendationResponse(BaseModel):
    scan_id: str
    kb_version: str
    total_findings: int
    recommendations: list[MigrationRecommendationSchema]
    manual_review_count: int
    quantum_concern_count: int
    classical_only_count: int
    safe_count: int
    summary: str
