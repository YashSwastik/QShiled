"""
QShield Deterministic Recommendation Engine  (Part 8)
======================================================

Consumes:
  - CryptoFinding data (as FindingInput from analyzer.py)
  - Existing Part 7 migration priority/risk scores (no duplication)
  - Purpose classifier output
  - Migration knowledge base entries

Output:
  - Per-finding MigrationRecommendation
  - Scan-level ScanRecommendationResult

Design rules:
  - Deterministic: same input → same output, always.
  - No LLM, no AI, no network calls.
  - Does NOT create a second risk methodology.
  - Consumes Part 7 migration_priority for ordering.
  - Pure Python, no DB operations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.services.analyzer import FindingInput
from app.services.kb.knowledge_base import (
    KB_VERSION,
    MigrationGuidance,
    PURPOSE_UNKNOWN,
    lookup,
)
from app.services.kb.purpose_classifier import PurposeClassification, classify_purpose

# Re-export for convenience
__all__ = [
    "MigrationRecommendation",
    "ScanRecommendationResult",
    "recommend_for_scan",
    "recommend_for_finding",
]

# ── Output types ──────────────────────────────────────────────────────────────

@dataclass
class MigrationRecommendation:
    """
    Complete migration recommendation for a single finding.
    All values are deterministically derived — none are hardcoded.
    """
    finding_id: str
    algorithm: str
    algorithm_family: str
    file_path: str | None

    # Purpose classification
    crypto_purpose: str
    purpose_confidence: float
    purpose_reasoning: str
    requires_manual_review: bool

    # Current state
    current_state_description: str     # human-readable description of what was found
    quantum_threat: str                 # from KB — why action is needed (or not)
    is_quantum_concern: bool            # False for symmetric/hash/legacy classical issues

    # Migration priority (from Part 7 risk engine — NOT recalculated here)
    migration_priority: str | None      # immediate / near_term / long_term / low / None
    quantum_migration_score: float | None  # 0–100 from Part 7

    # Recommendation content (from KB or manual-review message)
    recommended_target_category: str
    recommended_algorithms: list[str]
    nist_standards: list[str]
    effort_estimate: str

    # Structured guidance
    prerequisites: list[str]
    migration_steps: list[str]
    testing_requirements: list[str]
    interoperability_notes: list[str]
    validation_checklist: list[str]

    # Optional extras
    timeline_guidance: str
    technical_notes: str

    # KB provenance
    kb_version: str = KB_VERSION
    kb_entry_key: str | None = None    # "RSA:digital_signature" etc.


# ── Per-finding recommendation ────────────────────────────────────────────────

# Priority ordering weight (for sorting — aligns with Part 7 priority labels)
_PRIORITY_ORDER: dict[str, int] = {
    "immediate": 0,
    "near_term": 1,
    "long_term": 2,
    "low": 3,
    None: 4,  # type: ignore[misc]
}


def recommend_for_finding(
    finding: FindingInput,
    migration_priority: str | None = None,
    quantum_migration_score: float | None = None,
) -> MigrationRecommendation:
    """
    Generate a deterministic migration recommendation for one finding.

    Args:
        finding: FindingInput from the analyzer/DB layer.
        migration_priority: Part 7 output (imported, not recalculated).
        quantum_migration_score: Part 7 score 0–100 (imported, not recalculated).

    Returns:
        MigrationRecommendation — fully populated from KB + classifier.
    """
    # ── 1. Classify purpose ──────────────────────────────────────────────────
    classification: PurposeClassification = classify_purpose(
        algorithm_family=finding.algorithm_family,
        category=finding.category,
        usage_context=finding.usage_context,
        evidence=finding.file_path,   # file_path as weak evidence hint is less reliable
        detection_method="regex",
    )

    # ── 2. Look up KB entry ──────────────────────────────────────────────────
    kb_entry: MigrationGuidance | None = None
    kb_key: str | None = None

    if classification.purpose != PURPOSE_UNKNOWN:
        kb_entry = lookup(finding.algorithm_family, classification.purpose)
        if kb_entry:
            kb_key = f"{finding.algorithm_family}:{classification.purpose}"

    # ── 3. Build "current state" description ─────────────────────────────────
    ks_note = f" ({finding.key_size}-bit key)" if finding.key_size else ""
    ctx_note = f" used for {finding.usage_context}" if finding.usage_context else ""
    file_note = f" in {finding.file_path}" if finding.file_path else ""
    current_state = (
        f"{finding.algorithm}{ks_note}{ctx_note} detected{file_note}. "
        f"Algorithm family: {finding.algorithm_family}. "
        f"Quantum status: {finding.quantum_status}. "
        f"Scanner category: {finding.category}."
    )

    # ── 4. Determine if this is a genuine quantum concern ────────────────────
    is_quantum = finding.quantum_status == "vulnerable" or (
        finding.category == "QUANTUM_VULNERABLE_PUBLIC_KEY"
    )

    # ── 5. Build recommendation from KB entry or manual-review message ───────
    if kb_entry:
        return MigrationRecommendation(
            finding_id=finding.id,
            algorithm=finding.algorithm,
            algorithm_family=finding.algorithm_family,
            file_path=finding.file_path,
            crypto_purpose=classification.purpose,
            purpose_confidence=classification.confidence,
            purpose_reasoning=classification.reasoning,
            requires_manual_review=classification.requires_manual_review,
            current_state_description=current_state,
            quantum_threat=kb_entry.quantum_threat,
            is_quantum_concern=is_quantum,
            migration_priority=migration_priority,
            quantum_migration_score=quantum_migration_score,
            recommended_target_category=kb_entry.recommended_target_category,
            recommended_algorithms=list(kb_entry.recommended_algorithms),
            nist_standards=list(kb_entry.nist_standards),
            effort_estimate=kb_entry.effort_estimate,
            prerequisites=list(kb_entry.prerequisites),
            migration_steps=list(kb_entry.migration_steps),
            testing_requirements=list(kb_entry.testing_requirements),
            interoperability_notes=list(kb_entry.interoperability_notes),
            validation_checklist=list(kb_entry.validation_checklist),
            timeline_guidance=kb_entry.timeline_guidance,
            technical_notes=kb_entry.technical_notes,
            kb_version=KB_VERSION,
            kb_entry_key=kb_key,
        )

    else:
        # No KB entry — manual review required
        if classification.purpose == PURPOSE_UNKNOWN:
            reason = (
                "Cryptographic purpose could not be determined from available scanner evidence. "
                "Manual inspection of source context is required before a migration target can be recommended. "
                f"Classifier reasoning: {classification.reasoning}"
            )
            target_category = "Manual review required — purpose not determinable"
        else:
            reason = (
                f"No specific migration guidance is available in the knowledge base for "
                f"'{finding.algorithm_family}' used for '{classification.purpose}'. "
                "Manual review is recommended."
            )
            target_category = "Manual review required — no KB entry for this combination"

        return MigrationRecommendation(
            finding_id=finding.id,
            algorithm=finding.algorithm,
            algorithm_family=finding.algorithm_family,
            file_path=finding.file_path,
            crypto_purpose=classification.purpose,
            purpose_confidence=classification.confidence,
            purpose_reasoning=classification.reasoning,
            requires_manual_review=True,
            current_state_description=current_state,
            quantum_threat=reason,
            is_quantum_concern=is_quantum,
            migration_priority=migration_priority,
            quantum_migration_score=quantum_migration_score,
            recommended_target_category=target_category,
            recommended_algorithms=[],
            nist_standards=[],
            effort_estimate="unknown",
            prerequisites=[
                "Manually inspect source code to determine cryptographic purpose.",
                "Consult with application owner to understand key usage context.",
            ],
            migration_steps=[
                "1. Determine cryptographic purpose (key establishment, signing, encryption, etc.).",
                "2. Re-evaluate with QShield after purpose is known.",
            ],
            testing_requirements=["Purpose-specific tests after manual review."],
            interoperability_notes=[],
            validation_checklist=["[ ] Cryptographic purpose determined.", "[ ] Migration path selected."],
            timeline_guidance="",
            technical_notes=reason,
            kb_version=KB_VERSION,
            kb_entry_key=None,
        )


# ── Scan-level aggregation ────────────────────────────────────────────────────

@dataclass
class ScanRecommendationResult:
    """Aggregated recommendation result for an entire scan."""
    scan_id: str
    kb_version: str
    total_findings: int
    recommendations: list[MigrationRecommendation]
    manual_review_count: int
    quantum_concern_count: int    # findings where quantum migration is the concern
    classical_only_count: int     # findings with classical-only concerns (MD5, SHA-1)
    safe_count: int               # already-safe findings (AES-256, PQC, SHA-512)
    summary: str


def recommend_for_scan(
    scan_id: str,
    findings: Sequence[FindingInput],
    # Part 7 priority map: {finding_id: (migration_priority, quantum_migration_score)}
    priority_map: dict[str, tuple[str | None, float | None]] | None = None,
) -> ScanRecommendationResult:
    """
    Generate deterministic recommendations for all findings in a scan.

    Args:
        scan_id: The scan identifier.
        findings: All findings for this scan.
        priority_map: Part 7 output to consume (never recalculated here).

    Returns:
        ScanRecommendationResult with ordered recommendations.
    """
    pm = priority_map or {}
    recommendations: list[MigrationRecommendation] = []

    for f in findings:
        pri, score = pm.get(f.id, (None, None))
        rec = recommend_for_finding(f, migration_priority=pri, quantum_migration_score=score)
        recommendations.append(rec)

    # Sort: by Part 7 priority first, then by quantum_migration_score descending
    recommendations.sort(key=lambda r: (
        _PRIORITY_ORDER.get(r.migration_priority, 4),          # type: ignore[arg-type]
        -(r.quantum_migration_score or 0.0),
    ))

    manual_count    = sum(1 for r in recommendations if r.requires_manual_review)
    quantum_count   = sum(1 for r in recommendations if r.is_quantum_concern)
    classical_count = sum(
        1 for r in recommendations
        if not r.is_quantum_concern and r.requires_manual_review is False
        and r.effort_estimate != "unknown"
    )
    safe_count = sum(
        1 for r in recommendations
        if r.recommended_target_category.startswith("Already post-quantum")
        or r.recommended_target_category.startswith("Symmetric — already")
        or r.recommended_target_category.startswith("Hashing — SHA-3")
    )

    q_note = (
        f"{quantum_count} finding(s) require quantum migration"
        if quantum_count else "no quantum-vulnerable findings"
    )
    mr_note = (
        f"; {manual_count} require manual purpose review"
        if manual_count else ""
    )
    summary = (
        f"Scan {scan_id}: {len(findings)} findings analysed. "
        f"{q_note}{mr_note}. "
        f"Knowledge base version {KB_VERSION}."
    )

    return ScanRecommendationResult(
        scan_id=scan_id,
        kb_version=KB_VERSION,
        total_findings=len(findings),
        recommendations=recommendations,
        manual_review_count=manual_count,
        quantum_concern_count=quantum_count,
        classical_only_count=classical_count,
        safe_count=safe_count,
        summary=summary,
    )
