"""
QShield Explainable Migration Prioritization Methodology
=========================================================

Deterministic, weighted risk scoring for quantum migration priority.

This is NOT an official NIST score. It is QShield's internal methodology
for prioritizing cryptographic migration work based on the factors most
relevant to quantum computing threats.

FACTOR WEIGHTS (sum = 1.0):
  Cryptographic quantum vulnerability : 0.30
  Confidentiality / data lifetime      : 0.20
  Business criticality                 : 0.20
  External exposure                    : 0.15
  Migration complexity                 : 0.10
  Compliance / data sensitivity        : 0.05

Output: score 0–100, severity band, factor breakdown, deterministic explanation.

IMPORTANT DESIGN DECISION:
  Quantum migration risk and classical/legacy security risk are scored and
  reported SEPARATELY. An MD5 finding may have high classical risk but near-zero
  quantum migration priority.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

# ── Weight table (must sum to 1.0) ────────────────────────────────────────────

WEIGHTS = {
    "crypto_vulnerability":   0.30,
    "confidentiality":        0.20,
    "business_criticality":   0.20,
    "external_exposure":      0.15,
    "migration_complexity":   0.10,
    "compliance_sensitivity": 0.05,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

# ── Finding input (passed from DB layer — pure data, no SQLAlchemy) ───────────

@dataclass
class FindingInput:
    """Lightweight view of a CryptoFinding for scoring (no DB coupling)."""
    id: str
    algorithm: str
    algorithm_family: str
    category: str              # FindingCategory string value
    quantum_status: str        # QuantumStatus string value
    key_size: int | None       # bits, may be None
    usage_context: str | None  # e.g. "key_exchange", "signing", "hash"
    confidence: float          # 0–1
    file_path: str


@dataclass
class ApplicationContext:
    """Business context inputs from the Application model."""
    business_criticality: str        # critical / high / medium / low
    internet_exposed: bool
    data_sensitivity: str            # top_secret / restricted / internal / public
    confidentiality_requirement: str # long_term / medium_term / short_term
    data_lifetime_years: int
    environment: str                 # production / staging / development / research


# ── Factor human-readable labels ─────────────────────────────────────────────

FACTOR_LABELS: dict[str, str] = {
    "crypto_vulnerability":   "Cryptographic Quantum Vulnerability",
    "confidentiality":        "Confidentiality / Data Lifetime",
    "business_criticality":   "Business Criticality",
    "external_exposure":      "External Exposure",
    "migration_complexity":   "Migration Complexity",
    "compliance_sensitivity": "Compliance / Data Sensitivity",
}


# ── Score sub-components ──────────────────────────────────────────────────────

@dataclass
class FactorScore:
    factor: str
    label: str                # Human-readable factor name
    weight: float
    raw_value: float          # 0.0–1.0 pre-weight
    weighted_contribution: float  # raw_value × weight × 100 (BEFORE gate)
    rationale: str


@dataclass
class FindingRiskResult:
    finding_id: str
    algorithm: str
    algorithm_family: str
    quantum_migration_score: float        # 0–100 (after crypto-vulnerability gate)
    raw_weighted_sum: float               # sum of weighted_contributions before gate
    crypto_vulnerability_gate: float      # gate multiplier applied (0.0–1.0)
    quantum_migration_severity: str       # Low / Moderate / High / Critical
    classical_legacy_risk: str | None     # None if not legacy
    classical_legacy_rationale: str | None
    factors: list[FactorScore]
    explanation: str
    migration_priority: str              # immediate / near_term / long_term / low
    nist_recommendation: str | None


@dataclass
class ScanRiskResult:
    scan_id: str
    overall_quantum_score: float          # Weighted aggregate 0–100
    overall_severity: str                 # Low / Moderate / High / Critical
    finding_scores: list[FindingRiskResult]
    # Aggregate counts
    vulnerable_count: int
    safe_count: int
    borderline_count: int
    legacy_count: int
    # Factor summary (average contribution across all findings)
    factor_summary: dict[str, float]
    # Human-readable summary (deterministic template)
    summary_text: str
    # Top 5 highest-priority findings (by migration score)
    top_priority_finding_ids: list[str]


# ── Lookup tables ─────────────────────────────────────────────────────────────

# Quantum vulnerability raw score by quantum_status
_QV_SCORE: dict[str, float] = {
    "vulnerable":  1.00,   # Broken by Shor's algorithm
    "borderline":  0.50,   # Weakened by Grover by ~half
    "unknown":     0.40,   # Cannot rule out vulnerability
    "hybrid":      0.20,   # Partial protection
    "safe":        0.00,   # Not affected
}

# Category adjustment multipliers (on top of quantum_status base)
_CATEGORY_MULTIPLIER: dict[str, float] = {
    "QUANTUM_VULNERABLE_PUBLIC_KEY": 1.00,  # Full weight
    "LEGACY_DEPRECATED":             0.20,  # Classical issue, not quantum — heavy discount
    "HASH":                          0.60,  # Grover halving: relevant but not critical
    "SYMMETRIC":                     0.50,  # Grover halving
    "POST_QUANTUM":                  0.00,  # Already migrated
    "UNKNOWN_REVIEW":                0.50,  # Treat conservatively
}

# Usage context urgency multiplier
_USAGE_MULTIPLIER: dict[str, float] = {
    "key_exchange": 1.00,  # Most critical — confidentiality of session
    "signing":      0.90,  # Authentication chain
    "encryption":   0.90,
    "key_wrap":     0.85,
    "authentication": 0.80,
    "certificate":  0.85,
    "hash":         0.55,
    "mac":          0.55,
    "kdf":          0.65,
}

# Key size vulnerability multiplier (only for RSA & DH families)
def _key_size_factor(algorithm_family: str, key_size: int | None) -> float:
    """
    Smaller keys are more urgently vulnerable (easier to attack quantum or classical).
    Larger keys still vulnerable but marginally lower priority.
    For non-asymmetric families this factor is neutral (1.0).
    """
    if algorithm_family in ("RSA", "DH", "DSA") and key_size:
        # 1024-bit: maximum urgency. 4096-bit: slightly reduced (still vulnerable)
        if key_size <= 1024:  return 1.00
        if key_size <= 2048:  return 0.95
        if key_size <= 3072:  return 0.85
        return 0.75  # 4096+
    if algorithm_family in ("ECC", "ECDSA", "ECDH") and key_size:
        # P-192/224: nearly broken classically too
        if key_size < 256:    return 1.00
        if key_size < 384:    return 0.90
        return 0.80  # P-521
    return 1.00  # No key size adjustment for other families


# ── Factor sub-scorers ────────────────────────────────────────────────────────

def _score_crypto_vulnerability(finding: FindingInput) -> tuple[float, str]:
    """Returns (raw 0–1, rationale)."""
    base = _QV_SCORE.get(finding.quantum_status, 0.4)
    cat_mult = _CATEGORY_MULTIPLIER.get(finding.category, 0.5)
    usage_mult = _USAGE_MULTIPLIER.get(finding.usage_context or "", 1.0)
    ks_factor = _key_size_factor(finding.algorithm_family, finding.key_size)

    raw = min(1.0, base * cat_mult * usage_mult * ks_factor)

    ks_note = f", {finding.key_size}-bit key" if finding.key_size else ""
    usage_note = f" used for {finding.usage_context}" if finding.usage_context else ""
    return raw, (
        f"{finding.algorithm}{ks_note}{usage_note} — "
        f"quantum_status={finding.quantum_status}, "
        f"category={finding.category}"
    )


def _score_confidentiality(ctx: ApplicationContext) -> tuple[float, str]:
    """Data lifetime / harvest-now risk."""
    req_scores = {
        "long_term":   1.00,  # >10 years: high harvest-now risk
        "medium_term": 0.60,
        "short_term":  0.15,
    }
    base = req_scores.get(ctx.confidentiality_requirement, 0.60)
    # Boost for very long data lifetime years
    if ctx.data_lifetime_years >= 20:
        base = min(1.0, base + 0.15)
    elif ctx.data_lifetime_years >= 10:
        base = min(1.0, base + 0.05)

    return base, (
        f"confidentiality_requirement={ctx.confidentiality_requirement}, "
        f"data_lifetime_years={ctx.data_lifetime_years}"
    )


def _score_business_criticality(ctx: ApplicationContext) -> tuple[float, str]:
    scores = {
        "critical": 1.00,
        "high":     0.75,
        "medium":   0.45,
        "low":      0.20,
    }
    # Staging/dev environments reduce score
    env_mult = {"production": 1.0, "staging": 0.8, "development": 0.6, "research": 0.5}
    base = scores.get(ctx.business_criticality, 0.45)
    mult = env_mult.get(ctx.environment, 1.0)
    raw = base * mult
    return raw, (
        f"business_criticality={ctx.business_criticality}, "
        f"environment={ctx.environment}"
    )


def _score_external_exposure(ctx: ApplicationContext) -> tuple[float, str]:
    """Internet-facing systems are higher priority for harvest-now attacks."""
    if ctx.internet_exposed:
        return 0.95, "internet-exposed: harvest-now attack surface is external"
    return 0.25, "internal system: not directly exposed to internet"


def _score_migration_complexity(finding: FindingInput) -> tuple[float, str]:
    """
    Estimate migration effort by algorithm family.
    Higher score = more complex = harder to migrate = higher priority to start NOW.
    """
    complexity: dict[str, float] = {
        "RSA":    0.85,  # Pervasive; complex key management migration
        "DH":     0.80,
        "DSA":    0.75,
        "ECDSA":  0.70,
        "ECC":    0.70,
        "ECDH":   0.70,
        "AES":    0.20,  # Easy: increase key length
        "SHA":    0.25,
        "MD5":    0.30,  # Legacy: should already be replaced
        "TLS":    0.60,  # Config change + library upgrade
        "PQC":    0.05,  # Already migrated
    }
    family = finding.algorithm_family.upper()
    raw = complexity.get(family, 0.50)
    return raw, f"algorithm_family={finding.algorithm_family} — migration complexity={raw:.0%}"


def _score_compliance_sensitivity(ctx: ApplicationContext) -> tuple[float, str]:
    scores = {
        "top_secret":  1.00,
        "restricted":  0.80,  # PII, financial, health
        "internal":    0.40,
        "public":      0.10,
    }
    raw = scores.get(ctx.data_sensitivity, 0.40)
    return raw, f"data_sensitivity={ctx.data_sensitivity}"


# ── Main scoring function ─────────────────────────────────────────────────────

def _severity_band(score: float) -> str:
    if score >= 75: return "Critical"
    if score >= 55: return "High"
    if score >= 35: return "Moderate"
    return "Low"


def _migration_priority(score: float) -> str:
    if score >= 75: return "immediate"
    if score >= 55: return "near_term"
    if score >= 35: return "long_term"
    return "low"


NIST_RECOMMENDATIONS: dict[str, str] = {
    "RSA":   "Migrate to ML-KEM (FIPS 203) for key encapsulation or ML-DSA (FIPS 204) for digital signatures.",
    "DH":    "Migrate to ML-KEM (FIPS 203) for key agreement.",
    "DSA":   "Migrate to ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) for digital signatures.",
    "ECDSA": "Migrate to ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) for digital signatures.",
    "ECC":   "Migrate to ML-KEM (FIPS 203) for key exchange; ML-DSA (FIPS 204) for signatures.",
    "ECDH":  "Migrate to ML-KEM (FIPS 203) for key encapsulation.",
    "AES":   "AES-256 is quantum-safe. Ensure key length is 256 bits if long-term security required.",
    "SHA":   "SHA-384/SHA-512 or SHA-3 family (FIPS 202) provides adequate post-quantum security.",
    "MD5":   "Replace with SHA-256 or SHA-3 immediately (classical security failure).",
    "SHA1":  "Replace with SHA-256 or SHA-3 (classically broken; SHAttered attack).",
    "TLS":   "Configure TLS 1.3+ with hybrid PQC key exchange (X25519Kyber768 or equivalent).",
    "PQC":   "Already using a post-quantum algorithm. Verify FIPS 203/204/205 compliance.",
    "ChaCha20": "ChaCha20-Poly1305 is quantum-safe for symmetric encryption.",
}


def _classical_legacy_risk(finding: FindingInput) -> tuple[str | None, str | None]:
    """
    Determines if there is a CLASSICAL (non-quantum) security concern.
    Returns (severity_label, rationale) or (None, None).
    """
    family = finding.algorithm_family.upper()
    if family in ("MD5", "MD4"):
        return "Critical", "MD5 is classically broken — collision attacks are trivially computable. Replace immediately (classical concern, not quantum)."
    if family in ("SHA1", "SHA-1"):
        return "High", "SHA-1 is classically broken — practical collision attacks demonstrated (SHAttered, 2017). Classical concern."
    if family in ("DES", "3DES", "RC4", "RC2"):
        return "Critical", f"{finding.algorithm_family} is classically insecure. Deprecated per NIST. Replace with AES-256 (classical concern, not quantum)."
    if finding.key_size and family == "RSA" and finding.key_size < 2048:
        return "High", f"RSA-{finding.key_size} is below NIST minimum of 2048 bits — classically weak. Immediate classical remediation required."
    return None, None


def score_finding(
    finding: FindingInput,
    ctx: ApplicationContext,
) -> FindingRiskResult:
    """
    Score a single finding against the application's business context.

    KEY DESIGN PRINCIPLE:
    The crypto_vulnerability factor acts as a gate on quantum migration priority.
    A quantum-safe algorithm (AES-256, ML-KEM) or a classical/legacy algorithm (MD5)
    should score LOW for quantum migration even in a critical, internet-facing app,
    because there is no quantum threat to migrate away from.

    Implementation: the weighted score is multiplied by a gate derived from the
    crypto_vulnerability raw value. This means context factors (business criticality,
    exposure) can only push the score up when there is actually a quantum vulnerability.

    Classical/legacy risk (MD5, SHA-1, DES) is reported separately and is NOT
    reflected in the quantum_migration_score.
    """
    # ── Per-factor scoring ──────────────────────────────────────────────────
    qv_raw,    qv_rat    = _score_crypto_vulnerability(finding)
    conf_raw,  conf_rat  = _score_confidentiality(ctx)
    biz_raw,   biz_rat   = _score_business_criticality(ctx)
    exp_raw,   exp_rat   = _score_external_exposure(ctx)
    mig_raw,   mig_rat   = _score_migration_complexity(finding)
    comp_raw,  comp_rat  = _score_compliance_sensitivity(ctx)

    factors = [
        FactorScore("crypto_vulnerability",   FACTOR_LABELS["crypto_vulnerability"],   WEIGHTS["crypto_vulnerability"],   qv_raw,   round(qv_raw   * WEIGHTS["crypto_vulnerability"]   * 100, 1), qv_rat),
        FactorScore("confidentiality",         FACTOR_LABELS["confidentiality"],        WEIGHTS["confidentiality"],        conf_raw, round(conf_raw * WEIGHTS["confidentiality"]        * 100, 1), conf_rat),
        FactorScore("business_criticality",    FACTOR_LABELS["business_criticality"],   WEIGHTS["business_criticality"],   biz_raw,  round(biz_raw  * WEIGHTS["business_criticality"]   * 100, 1), biz_rat),
        FactorScore("external_exposure",       FACTOR_LABELS["external_exposure"],      WEIGHTS["external_exposure"],      exp_raw,  round(exp_raw  * WEIGHTS["external_exposure"]      * 100, 1), exp_rat),
        FactorScore("migration_complexity",    FACTOR_LABELS["migration_complexity"],   WEIGHTS["migration_complexity"],   mig_raw,  round(mig_raw  * WEIGHTS["migration_complexity"]   * 100, 1), mig_rat),
        FactorScore("compliance_sensitivity",  FACTOR_LABELS["compliance_sensitivity"], WEIGHTS["compliance_sensitivity"], comp_raw, round(comp_raw * WEIGHTS["compliance_sensitivity"] * 100, 1), comp_rat),
    ]

    # Raw weighted sum before gate
    raw_score = round(sum(f.weighted_contribution for f in factors), 1)

    # ── Crypto-vulnerability gate ───────────────────────────────────────────
    # The quantum migration score is gated by the crypto vulnerability factor.
    # A quantum-safe or legacy algorithm has low qv_raw, so the gate suppresses
    # the contribution of business context factors to the overall score.
    # Gate formula: score = raw_score * gate_mult
    # gate_mult ranges from 0.0 (qv_raw=0, completely safe) to 1.0 (qv_raw=1, fully vulnerable)
    gate_mult = round(min(1.0, qv_raw * 1.2), 3)  # 1.2 so qv_raw=0.833 → gate=1.0
    score = round(raw_score * gate_mult, 1)
    score = max(0.0, min(100.0, score))

    severity  = _severity_band(score)
    priority  = _migration_priority(score)
    cl_risk, cl_rationale = _classical_legacy_risk(finding)
    nist_rec  = NIST_RECOMMENDATIONS.get(finding.algorithm_family, None)
    if not nist_rec:
        # Try uppercase family prefix match
        for k, v in NIST_RECOMMENDATIONS.items():
            if finding.algorithm_family.upper().startswith(k):
                nist_rec = v
                break

    # ── Deterministic explanation ───────────────────────────────────────────
    explanation_parts: list[str] = []
    if qv_raw >= 0.7:
        explanation_parts.append(f"quantum-vulnerable {finding.category.replace('_', ' ').lower()}")
    elif qv_raw >= 0.4:
        explanation_parts.append(f"partially quantum-relevant {finding.algorithm_family} usage")
    else:
        explanation_parts.append(f"low quantum relevance ({finding.algorithm_family})")

    if conf_raw >= 0.8:
        explanation_parts.append("long confidentiality requirement (harvest-now risk)")
    elif conf_raw >= 0.5:
        explanation_parts.append("medium-term confidentiality requirement")

    if biz_raw >= 0.7:
        explanation_parts.append(f"high-criticality {ctx.environment} system")
    elif biz_raw >= 0.4:
        explanation_parts.append(f"medium-criticality {ctx.environment} system")

    if exp_raw >= 0.8:
        explanation_parts.append("internet-facing (external attack surface)")

    if comp_raw >= 0.7:
        explanation_parts.append(f"sensitive data ({ctx.data_sensitivity})")

    explanation = (
        f"Migration priority {severity} ({score:.0f}/100). "
        + " + ".join(explanation_parts)
        + f". Recommended action: {priority.replace('_', ' ')}."
    )
    # Append gate note when it significantly reduces the score (>10 point suppression)
    if raw_score - score > 10:
        explanation += (
            f" [Note: raw weighted sum was {raw_score:.0f}/100; reduced to {score:.0f} by "
            f"crypto-vulnerability gate ({gate_mult:.0%}) because this algorithm has low quantum relevance.]"
        )

    return FindingRiskResult(
        finding_id=finding.id,
        algorithm=finding.algorithm,
        algorithm_family=finding.algorithm_family,
        quantum_migration_score=score,
        raw_weighted_sum=raw_score,
        crypto_vulnerability_gate=gate_mult,
        quantum_migration_severity=severity,
        classical_legacy_risk=cl_risk,
        classical_legacy_rationale=cl_rationale,
        factors=factors,
        explanation=explanation,
        migration_priority=priority,
        nist_recommendation=nist_rec,
    )


def score_scan(
    scan_id: str,
    findings: Sequence[FindingInput],
    ctx: ApplicationContext,
) -> ScanRiskResult:
    """
    Score all findings for a scan and produce aggregate result.

    The overall quantum score is the severity-weighted P90 of finding scores
    (not a simple average — penalises scans with critical outliers more).
    """
    if not findings:
        return ScanRiskResult(
            scan_id=scan_id,
            overall_quantum_score=0.0,
            overall_severity="Low",
            finding_scores=[],
            vulnerable_count=0,
            safe_count=0,
            borderline_count=0,
            legacy_count=0,
            factor_summary={k: 0.0 for k in WEIGHTS},
            summary_text="No cryptographic findings detected in this scan. No migration action required.",
            top_priority_finding_ids=[],
        )

    scored = [score_finding(f, ctx) for f in findings]

    # Counts
    qs_map = {f.id: f.quantum_status for f in findings}
    cat_map = {f.id: f.category for f in findings}
    vulnerable_count = sum(1 for f in findings if f.quantum_status == "vulnerable")
    safe_count       = sum(1 for f in findings if f.quantum_status == "safe")
    borderline_count = sum(1 for f in findings if f.quantum_status == "borderline")
    legacy_count     = sum(1 for f in findings if f.category == "LEGACY_DEPRECATED")

    # Aggregate score: 75th-percentile of quantum-relevant finding scores
    # (treats scans with more vulnerable findings more seriously than average)
    all_scores = sorted([s.quantum_migration_score for s in scored], reverse=True)
    if len(all_scores) >= 4:
        p75_idx = max(0, math.floor(0.25 * len(all_scores)))
        overall = round(all_scores[p75_idx], 1)
    else:
        overall = round(max(all_scores), 1)

    overall = max(0.0, min(100.0, overall))
    overall_severity = _severity_band(overall)

    # Factor summary: mean weighted contribution per factor across all findings
    factor_totals: dict[str, float] = {k: 0.0 for k in WEIGHTS}
    for s in scored:
        for f in s.factors:
            factor_totals[f.factor] += f.weighted_contribution
    factor_summary = {k: round(v / len(scored), 1) for k, v in factor_totals.items()}

    # Top 5 priority findings
    top5 = sorted(scored, key=lambda s: s.quantum_migration_score, reverse=True)[:5]
    top_ids = [s.finding_id for s in top5]

    # Summary text
    vul_note = (
        f"{vulnerable_count} quantum-vulnerable finding(s) requiring migration"
        if vulnerable_count
        else "no quantum-vulnerable algorithms detected"
    )
    legacy_note = (
        f"; {legacy_count} classical/legacy finding(s) requiring immediate remediation"
        if legacy_count
        else ""
    )
    summary_text = (
        f"Scan {scan_id}: {overall_severity} quantum-migration priority (score {overall:.0f}/100). "
        f"{vul_note}{legacy_note}. "
        f"Business context: {ctx.business_criticality} criticality, "
        f"{'internet-exposed' if ctx.internet_exposed else 'internal'}, "
        f"{ctx.confidentiality_requirement} confidentiality requirement."
    )

    return ScanRiskResult(
        scan_id=scan_id,
        overall_quantum_score=overall,
        overall_severity=overall_severity,
        finding_scores=scored,
        vulnerable_count=vulnerable_count,
        safe_count=safe_count,
        borderline_count=borderline_count,
        legacy_count=legacy_count,
        factor_summary=factor_summary,
        summary_text=summary_text,
        top_priority_finding_ids=top_ids,
    )
