"""
QShield Migration Roadmap Engine  (Phase G)
============================================

Generates prioritised migration roadmap waves from:
  - CryptoFinding data (algorithm, quantum_status, category)
  - Part 7 risk scores (consumed, never recalculated)
  - Part 8 recommendation engine (purpose, target, effort)
  - Application business context (criticality, exposure, confidentiality)

Wave assignment is DETERMINISTIC from the actual scan data.
No hardcoded lists of items.

Wave model:
  WAVE 1 — Critical: internet-facing + long-lived data + quantum-vulnerable (score ≥ 65 OR immediate priority)
  WAVE 2 — High:     high business impact or important internal systems (score 40-64 OR near_term priority)
  WAVE 3 — Planned:  lower-priority, modernisation-driven, safe/legacy items (score < 40 OR low/long_term priority)

Migration stages (ordered lifecycle):
  DISCOVERED → ASSESSED → PLANNED → PILOT → TRANSITION → VALIDATION → MIGRATED

Status values (user-settable):
  DISCOVERED, ASSESSED, PLANNED, PILOT, TRANSITION, VALIDATION, MIGRATED

Re-runs: when risk/findings change, old roadmap_items for scan are replaced.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.services.analyzer import FindingInput
from app.services.recommender import recommend_for_finding, MigrationRecommendation

# ── Wave constants ────────────────────────────────────────────────────────────

WAVE_1 = 1  # Critical — immediate action required
WAVE_2 = 2  # High     — near-term action
WAVE_3 = 3  # Planned  — scheduled modernisation

# ── Stage lifecycle ───────────────────────────────────────────────────────────

MIGRATION_STAGES = [
    "DISCOVERED",
    "ASSESSED",
    "PLANNED",
    "PILOT",
    "TRANSITION",
    "VALIDATION",
    "MIGRATED",
]

VALID_STAGES = frozenset(MIGRATION_STAGES)

# ── Output types ──────────────────────────────────────────────────────────────

@dataclass
class RoadmapItem:
    """One prioritised migration task derived from a single finding."""
    # Identity (for DB persistence / update matching)
    finding_id: str
    scan_id: str

    # Asset / Application context
    application_name: str
    application_id: str | None

    # Algorithm context (from finding)
    algorithm: str
    algorithm_family: str
    file_path: str | None

    # Wave assignment (1/2/3) — derived deterministically
    wave: int
    wave_label: str              # "Wave 1 — Critical", etc.

    # Migration priority from Part 7 (consumed)
    migration_priority: str | None
    quantum_migration_score: float | None
    quantum_migration_severity: str | None

    # Purpose from Part 8 recommender (consumed)
    crypto_purpose: str
    requires_manual_review: bool

    # Recommended action (from Part 8 KB)
    recommended_target_category: str
    recommended_algorithms: list[str]
    effort_estimate: str

    # Roadmap-specific fields
    reason: str                 # Human-readable rationale for wave assignment
    recommended_action: str     # Concise next action
    dependencies: list[str]     # finding_ids this item depends on (structural)
    status: str                 # Current migration lifecycle stage
    migration_stage: str        # Alias for status (same value, clearer name)

    # KB provenance
    kb_version: str
    nist_standards: list[str]


@dataclass
class WaveSummary:
    wave: int
    label: str
    item_count: int
    description: str


@dataclass
class ScanRoadmapResult:
    scan_id: str
    application_name: str
    application_id: str | None
    total_items: int
    wave_summaries: list[WaveSummary]
    items: list[RoadmapItem]          # ordered: wave 1 → 2 → 3, then by score desc
    summary: str


# ── Wave assignment logic ─────────────────────────────────────────────────────

# Priority label → wave mapping
_PRIORITY_TO_WAVE: dict[str, int] = {
    "immediate": WAVE_1,
    "near_term":  WAVE_2,
    "long_term":  WAVE_3,
    "low":         WAVE_3,
}

_WAVE_LABELS = {
    WAVE_1: "Wave 1 — Critical",
    WAVE_2: "Wave 2 — High",
    WAVE_3: "Wave 3 — Planned",
}

_WAVE_DESCRIPTIONS = {
    WAVE_1: (
        "Critical quantum-vulnerable algorithms on internet-facing or long-lived-data systems. "
        "Immediate action required — harvest-now-decrypt-later risk is active."
    ),
    WAVE_2: (
        "High-impact internal systems and near-term migration targets. "
        "Plan and resource within 6-12 months."
    ),
    WAVE_3: (
        "Lower-priority, safe, or legacy systems. "
        "Address as part of planned modernisation cycles."
    ),
}


def _assign_wave(
    migration_priority: str | None,
    quantum_migration_score: float | None,
    is_quantum_concern: bool,
    internet_exposed: bool,
    confidentiality_requirement: str,
    business_criticality: str,
) -> tuple[int, str]:
    """
    Deterministically assign a wave (1/2/3) and generate the rationale.

    Priority order of signals:
      1. Part 7 migration_priority (most authoritative — already integrates all factors)
      2. quantum_migration_score as fallback if priority is None
      3. Context modifiers: internet-facing + long-lived data → elevate to Wave 1
    """
    score = quantum_migration_score or 0.0

    # ── Primary: Part 7 priority label ───────────────────────────────────────
    if migration_priority in _PRIORITY_TO_WAVE:
        wave = _PRIORITY_TO_WAVE[migration_priority]
    elif score >= 65:
        wave = WAVE_1
    elif score >= 40:
        wave = WAVE_2
    else:
        wave = WAVE_3

    # ── Context elevation: internet-facing + long-lived data → always Wave 1 ─
    if (
        wave > WAVE_1
        and is_quantum_concern
        and internet_exposed
        and confidentiality_requirement == "long_term"
    ):
        wave = WAVE_1

    # ── Elevation by criticality for Wave 3 → Wave 2 ─────────────────────────
    if (
        wave == WAVE_3
        and is_quantum_concern
        and business_criticality in ("critical", "high")
    ):
        wave = WAVE_2

    # ── Build rationale ───────────────────────────────────────────────────────
    parts: list[str] = []
    if migration_priority:
        parts.append(f"Part 7 migration priority: {migration_priority.replace('_', ' ')}")
    if score:
        parts.append(f"quantum migration score {score:.0f}/100")
    if internet_exposed and is_quantum_concern:
        parts.append("internet-facing system")
    if confidentiality_requirement == "long_term" and is_quantum_concern:
        parts.append("long-term confidentiality requirement (HNDL risk)")
    if business_criticality in ("critical", "high"):
        parts.append(f"{business_criticality} business criticality")
    if not is_quantum_concern:
        parts.append("classical/legacy concern — not Shor-vulnerable")

    reason = "; ".join(parts) if parts else "No specific risk factors identified"
    return wave, reason


def _build_recommended_action(
    rec: MigrationRecommendation,
    wave: int,
) -> str:
    """Generate a concise recommended action for the roadmap item."""
    if rec.requires_manual_review:
        return (
            "Manual review required: determine cryptographic purpose before selecting migration target. "
            "Inspect source code context (signing vs. key establishment)."
        )
    if wave == WAVE_1:
        action_prefix = "Immediate: "
    elif wave == WAVE_2:
        action_prefix = "Near-term: "
    else:
        action_prefix = "Planned: "

    if rec.recommended_algorithms:
        primary = rec.recommended_algorithms[0].split(" (")[0]  # e.g. "ML-KEM-768"
        return (
            f"{action_prefix}migrate {rec.algorithm} "
            f"({rec.crypto_purpose.replace('_', ' ')}) to {primary}. "
            f"Target: {rec.recommended_target_category}."
        )
    return f"{action_prefix}review and remediate {rec.algorithm} usage."


def _build_dependencies(
    finding: FindingInput,
    all_findings: Sequence[FindingInput],
) -> list[str]:
    """
    Identify structural dependencies:
    - Certificate findings depend on key-establishment findings in the same scan
    - Hashing findings with signing context depend on signature findings
    Only returns IDs, not descriptions (caller resolves).
    """
    deps: list[str] = []
    if finding.usage_context == "certificate":
        # Certs depend on PKI key findings
        for f in all_findings:
            if f.id != finding.id and f.usage_context in ("key_generation", "key_exchange", "signing"):
                deps.append(f.id)
                if len(deps) >= 2:
                    break
    return deps


# ── Public API ────────────────────────────────────────────────────────────────

def build_roadmap(
    scan_id: str,
    application_name: str,
    application_id: str | None,
    findings: Sequence[FindingInput],
    # Part 7 priority map: {finding_id: (migration_priority, quantum_migration_score, severity)}
    priority_map: dict[str, tuple[str | None, float | None, str | None]] | None = None,
    # Application context for wave elevation
    internet_exposed: bool = False,
    confidentiality_requirement: str = "medium_term",
    business_criticality: str = "medium",
) -> ScanRoadmapResult:
    """
    Build a fully deterministic, wave-ordered migration roadmap for a scan.

    Args:
        scan_id: scan identifier
        application_name: display name for the application
        application_id: application FK
        findings: all findings for the scan
        priority_map: Part 7 per-finding risk output (consumed, not recalculated)
        internet_exposed: from application context
        confidentiality_requirement: from application context
        business_criticality: from application context

    Returns:
        ScanRoadmapResult with ordered RoadmapItems.
    """
    pm = priority_map or {}
    items: list[RoadmapItem] = []

    for finding in findings:
        pri, score, severity = pm.get(finding.id, (None, None, None))

        # ── Part 8 recommendation (purpose classification + KB lookup) ────────
        rec: MigrationRecommendation = recommend_for_finding(
            finding,
            migration_priority=pri,
            quantum_migration_score=score,
        )

        # ── Wave assignment ───────────────────────────────────────────────────
        wave, reason = _assign_wave(
            migration_priority=pri,
            quantum_migration_score=score,
            is_quantum_concern=rec.is_quantum_concern,
            internet_exposed=internet_exposed,
            confidentiality_requirement=confidentiality_requirement,
            business_criticality=business_criticality,
        )

        # ── Dependencies ──────────────────────────────────────────────────────
        deps = _build_dependencies(finding, findings)

        # ── Recommended action (concise) ──────────────────────────────────────
        action = _build_recommended_action(rec, wave)

        items.append(RoadmapItem(
            finding_id=finding.id,
            scan_id=scan_id,
            application_name=application_name,
            application_id=application_id,
            algorithm=finding.algorithm,
            algorithm_family=finding.algorithm_family,
            file_path=finding.file_path,
            wave=wave,
            wave_label=_WAVE_LABELS[wave],
            migration_priority=pri,
            quantum_migration_score=score,
            quantum_migration_severity=severity,
            crypto_purpose=rec.crypto_purpose,
            requires_manual_review=rec.requires_manual_review,
            recommended_target_category=rec.recommended_target_category,
            recommended_algorithms=rec.recommended_algorithms,
            effort_estimate=rec.effort_estimate,
            reason=reason,
            recommended_action=action,
            dependencies=deps,
            status=MIGRATION_STAGES[0],   # DISCOVERED — default for new items
            migration_stage=MIGRATION_STAGES[0],
            kb_version=rec.kb_version,
            nist_standards=rec.nist_standards,
        ))

    # ── Sort: wave asc, then score desc ──────────────────────────────────────
    items.sort(key=lambda i: (i.wave, -(i.quantum_migration_score or 0.0)))

    # ── Wave summaries ────────────────────────────────────────────────────────
    wave_counts: dict[int, int] = {WAVE_1: 0, WAVE_2: 0, WAVE_3: 0}
    for item in items:
        wave_counts[item.wave] = wave_counts.get(item.wave, 0) + 1

    wave_summaries = [
        WaveSummary(
            wave=w,
            label=_WAVE_LABELS[w],
            item_count=wave_counts.get(w, 0),
            description=_WAVE_DESCRIPTIONS[w],
        )
        for w in (WAVE_1, WAVE_2, WAVE_3)
    ]

    # ── Summary text ─────────────────────────────────────────────────────────
    w1 = wave_counts.get(WAVE_1, 0)
    w2 = wave_counts.get(WAVE_2, 0)
    w3 = wave_counts.get(WAVE_3, 0)
    summary = (
        f"Migration roadmap for '{application_name}': "
        f"{len(findings)} finding(s) → "
        f"Wave 1: {w1} critical, Wave 2: {w2} high, Wave 3: {w3} planned. "
        f"Roadmap is deterministic from scan findings, risk scores, and application context."
    )

    return ScanRoadmapResult(
        scan_id=scan_id,
        application_name=application_name,
        application_id=application_id,
        total_items=len(items),
        wave_summaries=wave_summaries,
        items=items,
        summary=summary,
    )


def advance_stage(current_stage: str) -> str | None:
    """Return the next valid stage after `current_stage`, or None if at MIGRATED."""
    try:
        idx = MIGRATION_STAGES.index(current_stage)
    except ValueError:
        return None
    if idx + 1 < len(MIGRATION_STAGES):
        return MIGRATION_STAGES[idx + 1]
    return None
