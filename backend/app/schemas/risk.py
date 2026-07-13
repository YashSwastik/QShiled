"""
Pydantic v2 schemas for the Risk Analysis API.

These mirror the analyzer.py data classes but are serializable over HTTP.
"""
from pydantic import BaseModel


METHODOLOGY_NAME = "QShield Explainable Migration Prioritization Methodology"
METHODOLOGY_VERSION = "1.0"

_GATE_EXPLANATION = (
    "The quantum migration score is the weighted sum of all factors, scaled by a "
    "crypto-vulnerability gate derived from the algorithm's quantum relevance. "
    "Quantum-safe algorithms (AES-256, ML-KEM) and classical/legacy-only algorithms (MD5, SHA-1) "
    "receive a low gate value, suppressing context factors from inflating quantum migration priority "
    "when no quantum threat exists. Classical security concerns for those algorithms are reported "
    "separately in classical_legacy_risk."
)


class FactorScoreSchema(BaseModel):
    factor: str
    label: str                 # Human-readable factor name
    weight: float
    raw_value: float           # 0.0–1.0 pre-weight
    weighted_contribution: float   # raw_value × weight × 100 (before gate)
    rationale: str


class FindingRiskSchema(BaseModel):
    finding_id: str
    algorithm: str
    algorithm_family: str
    file_path: str | None = None
    quantum_migration_score: float       # 0–100 (after gate)
    raw_weighted_sum: float              # sum(weighted_contributions) before gate
    crypto_vulnerability_gate: float     # gate multiplier (0.0–1.0)
    quantum_migration_severity: str      # Low / Moderate / High / Critical
    classical_legacy_risk: str | None    # None if no classical concern
    classical_legacy_rationale: str | None
    factors: list[FactorScoreSchema]
    explanation: str
    migration_priority: str              # immediate / near_term / long_term / low
    nist_recommendation: str | None


class ScanRiskResponse(BaseModel):
    """
    Full risk analysis response for a scan.
    All values are calculated by the backend; no frontend hardcoding.
    """
    methodology: str = METHODOLOGY_NAME
    methodology_version: str = METHODOLOGY_VERSION
    methodology_description: str = _GATE_EXPLANATION
    disclaimer: str = (
        "This score reflects QShield's internal migration prioritization methodology. "
        "It is not an official NIST risk score or a compliance certification."
    )

    scan_id: str
    overall_quantum_score: float         # 0–100
    overall_severity: str                # Low / Moderate / High / Critical

    # Counts
    vulnerable_count: int
    safe_count: int
    borderline_count: int
    legacy_count: int                    # Classical/legacy — separate from quantum

    # Factor summary: average weighted contribution per factor (before gate)
    factor_summary: dict[str, float]

    # Top-priority per-finding details (ordered by score descending, up to 10)
    top_findings: list[FindingRiskSchema]

    # Human-readable summary
    summary_text: str

    # Context used for scoring (echoed back for transparency)
    business_criticality: str
    internet_exposed: bool
    confidentiality_requirement: str
    data_sensitivity: str
    data_lifetime_years: int
    environment: str
    context_defaulted: bool = False      # True when app context was unavailable
