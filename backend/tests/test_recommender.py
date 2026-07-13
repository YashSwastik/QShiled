"""
Tests for Part 8: Migration Recommendation Engine

Covers at minimum:
  1. RSA key establishment → KEM path
  2. RSA signature → PQC signature path (NOT ML-KEM)
  3. ECDSA → PQC signature path
  4. Symmetric (AES) → NOT treated as quantum-vulnerable public-key
  5. Unknown purpose → manual review, no invented target

Also asserts:
  - Determinism: same input → same output
  - RSA signature does NOT recommend ML-KEM for signing
  - RSA key establishment does NOT get a signature recommendation
  - Unknown purpose never invents a PQC target
  - AES is NOT labelled quantum-vulnerable public-key
  - RSA → ML-KEM only for encryption/KEM, never for signing
"""
from __future__ import annotations

import pytest

from app.services.analyzer import FindingInput
from app.services.kb.knowledge_base import (
    PURPOSE_KEY_ESTABLISHMENT,
    PURPOSE_DIGITAL_SIGNATURE,
    PURPOSE_SYMMETRIC_ENCRYPTION,
    PURPOSE_HASHING,
    PURPOSE_UNKNOWN,
)
from app.services.kb.purpose_classifier import classify_purpose
from app.services.recommender import (
    recommend_for_finding,
    recommend_for_scan,
)


# ── Helper factories ──────────────────────────────────────────────────────────

def _finding(
    id: str,
    algorithm: str,
    algorithm_family: str,
    category: str,
    quantum_status: str,
    usage_context: str | None = None,
    key_size: int | None = None,
    file_path: str = "src/crypto.py",
) -> FindingInput:
    return FindingInput(
        id=id,
        algorithm=algorithm,
        algorithm_family=algorithm_family,
        category=category,
        quantum_status=quantum_status,
        key_size=key_size,
        usage_context=usage_context,
        confidence=0.90,
        file_path=file_path,
    )


# ── Purpose classifier tests ──────────────────────────────────────────────────

class TestPurposeClassifier:

    def test_ecdsa_always_signature(self):
        """ECDSA is unambiguously a digital signature algorithm."""
        result = classify_purpose("ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", None, None)
        assert result.purpose == PURPOSE_DIGITAL_SIGNATURE
        assert result.confidence >= 0.90
        assert not result.requires_manual_review

    def test_ecdh_always_key_establishment(self):
        """ECDH is unambiguously key agreement."""
        result = classify_purpose("ECDH", "QUANTUM_VULNERABLE_PUBLIC_KEY", None, None)
        assert result.purpose == PURPOSE_KEY_ESTABLISHMENT
        assert result.confidence >= 0.90
        assert not result.requires_manual_review

    def test_aes_always_symmetric(self):
        """AES is unambiguously symmetric encryption."""
        result = classify_purpose("AES", "SYMMETRIC", None, None)
        assert result.purpose == PURPOSE_SYMMETRIC_ENCRYPTION
        assert not result.requires_manual_review

    def test_sha2_always_hashing(self):
        result = classify_purpose("SHA-2", "HASH", None, None)
        assert result.purpose == PURPOSE_HASHING

    def test_md5_classified_as_hashing_not_quantum(self):
        result = classify_purpose("MD5", "LEGACY_DEPRECATED", None, None)
        assert result.purpose == PURPOSE_HASHING

    def test_sha1_classified_as_hashing(self):
        result = classify_purpose("SHA-1", "LEGACY_DEPRECATED", None, None)
        assert result.purpose == PURPOSE_HASHING

    def test_dh_always_key_establishment(self):
        result = classify_purpose("DH", "QUANTUM_VULNERABLE_PUBLIC_KEY", None, None)
        assert result.purpose == PURPOSE_KEY_ESTABLISHMENT

    def test_dsa_always_signature(self):
        result = classify_purpose("DSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", None, None)
        assert result.purpose == PURPOSE_DIGITAL_SIGNATURE

    def test_rsa_signing_context(self):
        """RSA with signing usage_context → digital_signature."""
        result = classify_purpose("RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "signing", None)
        assert result.purpose == PURPOSE_DIGITAL_SIGNATURE

    def test_rsa_key_exchange_context(self):
        """RSA with key_exchange usage_context → key_establishment."""
        result = classify_purpose("RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "key_exchange", None)
        assert result.purpose == PURPOSE_KEY_ESTABLISHMENT

    def test_rsa_encryption_context(self):
        """RSA with encryption usage_context → key_establishment."""
        result = classify_purpose("RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "encryption", None)
        assert result.purpose == PURPOSE_KEY_ESTABLISHMENT

    def test_rsa_no_context_unknown(self):
        """RSA without any context → unknown, requires manual review."""
        result = classify_purpose("RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", None, None)
        assert result.purpose == PURPOSE_UNKNOWN
        assert result.requires_manual_review is True

    def test_ecc_no_context_unknown(self):
        """Generic ECC without context → unknown, requires manual review."""
        result = classify_purpose("ECC", "QUANTUM_VULNERABLE_PUBLIC_KEY", None, None)
        assert result.purpose == PURPOSE_UNKNOWN
        assert result.requires_manual_review is True

    def test_pqc_ml_kem_key_establishment(self):
        result = classify_purpose("ML-KEM", "POST_QUANTUM", None, None)
        assert result.purpose == PURPOSE_KEY_ESTABLISHMENT
        assert result.confidence >= 0.95

    def test_pqc_ml_dsa_signature(self):
        result = classify_purpose("ML-DSA", "POST_QUANTUM", None, None)
        assert result.purpose == PURPOSE_DIGITAL_SIGNATURE


# ── Recommender correctness tests ─────────────────────────────────────────────

class TestRecommender:

    # ── (1) RSA key establishment → KEM path ─────────────────────────────────
    def test_rsa_key_establishment_gets_kem_recommendation(self):
        f = _finding("f-rsa-enc", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="key_exchange")
        rec = recommend_for_finding(f)
        assert rec.crypto_purpose == PURPOSE_KEY_ESTABLISHMENT
        assert "ML-KEM" in rec.recommended_target_category or any(
            "ML-KEM" in a for a in rec.recommended_algorithms
        ), f"Expected ML-KEM in recommendations, got: {rec.recommended_algorithms}"
        # Must NOT mention ML-DSA as the primary/target for key establishment
        assert rec.kb_entry_key == "RSA:key_establishment"
        assert rec.is_quantum_concern is True

    # ── (2) RSA signature → PQC sig path, NOT ML-KEM ─────────────────────────
    def test_rsa_signature_gets_signature_recommendation(self):
        f = _finding("f-rsa-sig", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="signing")
        rec = recommend_for_finding(f)
        assert rec.crypto_purpose == PURPOSE_DIGITAL_SIGNATURE
        # Must NOT recommend ML-KEM for signing
        mlkem_in_algos = any("ML-KEM" in a for a in rec.recommended_algorithms)
        assert not mlkem_in_algos, (
            f"ML-KEM must NOT appear in RSA-signature recommendations. "
            f"Got: {rec.recommended_algorithms}"
        )
        # Must recommend ML-DSA or SLH-DSA
        assert any("ML-DSA" in a or "SLH-DSA" in a for a in rec.recommended_algorithms), (
            f"Expected ML-DSA or SLH-DSA in signature recommendations. "
            f"Got: {rec.recommended_algorithms}"
        )
        assert rec.kb_entry_key == "RSA:digital_signature"

    def test_rsa_signature_target_is_not_kem(self):
        """The recommended_target_category must NOT contain 'KEM' for RSA used for signing."""
        f = _finding("f-rsa-sig2", "RSA-4096", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="signing")
        rec = recommend_for_finding(f)
        assert "KEM" not in rec.recommended_target_category, (
            f"RSA signature should recommend a signature category, not KEM. "
            f"Got: {rec.recommended_target_category}"
        )

    def test_rsa_key_establishment_target_is_not_signature(self):
        """The recommended_target_category must NOT be a signature category for RSA key establishment."""
        f = _finding("f-rsa-enc2", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="encryption")
        rec = recommend_for_finding(f)
        assert "signature" not in rec.recommended_target_category.lower() or \
               "KEM" in rec.recommended_target_category, \
               f"Got unexpected target: {rec.recommended_target_category}"

    # ── (3) ECDSA → signature-oriented recommendation ─────────────────────────
    def test_ecdsa_gets_signature_recommendation(self):
        f = _finding("f-ecdsa", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context=None)
        rec = recommend_for_finding(f)
        assert rec.crypto_purpose == PURPOSE_DIGITAL_SIGNATURE
        # Must NOT recommend ML-KEM
        assert not any("ML-KEM" in a for a in rec.recommended_algorithms), (
            f"ECDSA must not recommend ML-KEM. Got: {rec.recommended_algorithms}"
        )
        # Must recommend ML-DSA or SLH-DSA
        assert any("ML-DSA" in a or "SLH-DSA" in a for a in rec.recommended_algorithms)
        assert rec.kb_entry_key == "ECDSA:digital_signature"
        assert rec.requires_manual_review is False
        assert rec.is_quantum_concern is True

    def test_ecdsa_nist_standards_present(self):
        f = _finding("f-ecdsa-n", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        rec = recommend_for_finding(f)
        standards = " ".join(rec.nist_standards)
        assert "FIPS 204" in standards or "FIPS 205" in standards

    # ── (4) Symmetric crypto — NOT treated as quantum-vulnerable public-key ───
    def test_aes_is_not_quantum_vulnerable(self):
        f = _finding("f-aes", "AES-256", "AES", "SYMMETRIC", "safe")
        rec = recommend_for_finding(f)
        assert rec.is_quantum_concern is False
        assert rec.crypto_purpose == PURPOSE_SYMMETRIC_ENCRYPTION

    def test_aes_does_not_recommend_pqc_algorithms(self):
        """AES must NOT recommend ML-KEM, ML-DSA, or SLH-DSA."""
        f = _finding("f-aes-2", "AES-256-GCM", "AES", "SYMMETRIC", "safe")
        rec = recommend_for_finding(f)
        for algo in rec.recommended_algorithms:
            assert "ML-KEM" not in algo, f"AES must not recommend ML-KEM: {algo}"
            assert "ML-DSA" not in algo, f"AES must not recommend ML-DSA: {algo}"
            assert "SLH-DSA" not in algo, f"AES must not recommend SLH-DSA: {algo}"

    def test_aes_recommended_category_is_symmetric(self):
        f = _finding("f-aes-3", "AES-128", "AES", "SYMMETRIC", "borderline")
        rec = recommend_for_finding(f)
        assert "Symmetric" in rec.recommended_target_category or "AES" in rec.recommended_target_category

    def test_chacha20_not_quantum_vulnerable(self):
        f = _finding("f-chacha", "ChaCha20-Poly1305", "ChaCha20", "SYMMETRIC", "safe")
        rec = recommend_for_finding(f)
        assert rec.is_quantum_concern is False
        assert not any("ML-KEM" in a or "ML-DSA" in a for a in rec.recommended_algorithms)

    # ── (5) Unknown purpose — manual review, no invented target ───────────────
    def test_rsa_no_context_requires_manual_review(self):
        """RSA with no usage_context → unknown purpose → manual review."""
        f = _finding("f-rsa-unk", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context=None)
        rec = recommend_for_finding(f)
        assert rec.requires_manual_review is True
        assert rec.crypto_purpose == PURPOSE_UNKNOWN

    def test_unknown_purpose_no_invented_target(self):
        """When purpose is unknown, recommended_algorithms must be empty."""
        f = _finding("f-rsa-unk2", "RSA-4096", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context=None)
        rec = recommend_for_finding(f)
        assert rec.recommended_algorithms == [], (
            f"Unknown purpose must produce empty recommended_algorithms. "
            f"Got: {rec.recommended_algorithms}"
        )

    def test_unknown_purpose_target_category_signals_review(self):
        f = _finding("f-rsa-unk3", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable")
        rec = recommend_for_finding(f)
        assert "manual" in rec.recommended_target_category.lower() or \
               "review" in rec.recommended_target_category.lower()

    def test_unknown_family_manual_review(self):
        """Completely unknown algorithm family → manual review."""
        f = _finding("f-unk", "WIDGET-256", "WIDGET", "UNKNOWN_REVIEW", "unknown")
        rec = recommend_for_finding(f)
        assert rec.requires_manual_review is True

    # ── Determinism tests ──────────────────────────────────────────────────────

    def test_rsa_signing_deterministic(self):
        """Same RSA signing input always produces the same recommendation."""
        f = _finding("f-det", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="signing")
        rec1 = recommend_for_finding(f)
        rec2 = recommend_for_finding(f)
        assert rec1.crypto_purpose == rec2.crypto_purpose
        assert rec1.recommended_algorithms == rec2.recommended_algorithms
        assert rec1.kb_entry_key == rec2.kb_entry_key
        assert rec1.migration_steps == rec2.migration_steps

    def test_aes_deterministic(self):
        f = _finding("f-det-aes", "AES-256", "AES", "SYMMETRIC", "safe")
        rec1 = recommend_for_finding(f)
        rec2 = recommend_for_finding(f)
        assert rec1.crypto_purpose == rec2.crypto_purpose
        assert rec1.recommended_algorithms == rec2.recommended_algorithms

    # ── Strict separation tests ────────────────────────────────────────────────

    def test_rsa_sig_never_recommends_ml_kem_as_replacement(self):
        """ML-KEM must NEVER appear in the recommended_algorithms for an RSA signing use."""
        f = _finding("f-rsa-sig-strict", "RSA-2048", "RSA",
                     "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable", usage_context="signing")
        rec = recommend_for_finding(f)
        for algo in rec.recommended_algorithms:
            assert "ML-KEM" not in algo, (
                f"ML-KEM is a KEM, NOT a signature algorithm. "
                f"It must never appear in an RSA-signing recommendation. Found: {algo}"
            )

    def test_rsa_kem_never_recommends_signature_as_replacement(self):
        """ML-DSA and SLH-DSA must NOT appear as primary recommended algorithms for RSA key establishment."""
        f = _finding("f-rsa-kem-strict", "RSA-2048", "RSA",
                     "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable", usage_context="key_exchange")
        rec = recommend_for_finding(f)
        # The KB entry should be RSA:key_establishment
        assert rec.kb_entry_key == "RSA:key_establishment"
        # Primary recommended category must contain "KEM"
        assert "KEM" in rec.recommended_target_category

    def test_ecdsa_never_recommends_ml_kem(self):
        f = _finding("f-ecdsa-strict", "ECDSA", "ECDSA",
                     "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        rec = recommend_for_finding(f)
        for algo in rec.recommended_algorithms:
            assert "ML-KEM" not in algo, (
                f"ECDSA is a signature algorithm. ML-KEM must never be recommended. Found: {algo}"
            )

    def test_symmetric_not_labelled_quantum_vulnerable_public_key(self):
        """Symmetric algorithms must never be treated as Shor-vulnerable public-key crypto."""
        f = _finding("f-sym-strict", "AES-128", "AES", "SYMMETRIC", "borderline")
        rec = recommend_for_finding(f)
        assert rec.is_quantum_concern is False, (
            "AES (symmetric) is not broken by Shor's algorithm and must not be "
            "labelled as a quantum (public-key) concern."
        )

    # ── Additional algorithm coverage ─────────────────────────────────────────

    def test_ecdh_gets_kem_recommendation(self):
        f = _finding("f-ecdh", "ECDH", "ECDH", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable")
        rec = recommend_for_finding(f)
        assert rec.crypto_purpose == PURPOSE_KEY_ESTABLISHMENT
        assert any("ML-KEM" in a for a in rec.recommended_algorithms)

    def test_dh_gets_kem_recommendation(self):
        f = _finding("f-dh", "Diffie-Hellman", "DH", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable")
        rec = recommend_for_finding(f)
        assert rec.crypto_purpose == PURPOSE_KEY_ESTABLISHMENT
        assert any("ML-KEM" in a for a in rec.recommended_algorithms)

    def test_dsa_gets_signature_recommendation(self):
        f = _finding("f-dsa", "DSA", "DSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        rec = recommend_for_finding(f)
        assert rec.crypto_purpose == PURPOSE_DIGITAL_SIGNATURE
        assert not any("ML-KEM" in a for a in rec.recommended_algorithms)

    def test_md5_not_quantum_concern(self):
        f = _finding("f-md5", "MD5", "MD5", "LEGACY_DEPRECATED", "deprecated")
        rec = recommend_for_finding(f)
        assert rec.is_quantum_concern is False
        assert not any("ML-KEM" in a for a in rec.recommended_algorithms)
        assert not any("ML-DSA" in a for a in rec.recommended_algorithms)

    def test_sha1_not_quantum_concern(self):
        f = _finding("f-sha1", "SHA-1", "SHA-1", "LEGACY_DEPRECATED", "deprecated")
        rec = recommend_for_finding(f)
        assert rec.is_quantum_concern is False

    def test_pqc_ml_kem_already_safe(self):
        """ML-KEM in use → already post-quantum, effort is low."""
        f = _finding("f-mlkem", "ML-KEM-768", "ML-KEM", "POST_QUANTUM", "safe")
        rec = recommend_for_finding(f)
        assert rec.effort_estimate == "low"
        assert "Already post-quantum" in rec.recommended_target_category

    def test_pqc_ml_dsa_already_safe(self):
        f = _finding("f-mldsa", "ML-DSA-65", "ML-DSA", "POST_QUANTUM", "safe")
        rec = recommend_for_finding(f)
        assert rec.effort_estimate == "low"

    # ── Migration priority passthrough from Part 7 ────────────────────────────

    def test_part7_priority_consumed_not_recalculated(self):
        """Migration priority from Part 7 must appear unchanged in recommendation."""
        f = _finding("f-pri", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="signing")
        rec = recommend_for_finding(f, migration_priority="immediate", quantum_migration_score=87.3)
        assert rec.migration_priority == "immediate"
        assert rec.quantum_migration_score == 87.3

    def test_part7_score_none_when_not_provided(self):
        f = _finding("f-nopri", "AES-256", "AES", "SYMMETRIC", "safe")
        rec = recommend_for_finding(f)
        assert rec.migration_priority is None
        assert rec.quantum_migration_score is None


# ── Scan-level recommendation tests ──────────────────────────────────────────

class TestScanRecommendations:

    def test_scan_with_mixed_findings(self):
        findings = [
            _finding("f1", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="signing"),
            _finding("f2", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable"),
            _finding("f3", "AES-256", "AES", "SYMMETRIC", "safe"),
            _finding("f4", "MD5", "MD5", "LEGACY_DEPRECATED", "deprecated"),
        ]
        priority_map = {
            "f1": ("immediate", 82.0),
            "f2": ("near_term", 65.0),
            "f3": ("low", 5.0),
            "f4": ("low", 8.0),
        }
        result = recommend_for_scan("scan-mix", findings, priority_map=priority_map)
        assert result.total_findings == 4
        assert result.quantum_concern_count == 2   # RSA + ECDSA
        # First recommendation should be the highest-priority (f1 = immediate)
        assert result.recommendations[0].finding_id == "f1"

    def test_scan_no_findings(self):
        result = recommend_for_scan("scan-empty", [])
        assert result.total_findings == 0
        assert result.recommendations == []
        assert result.quantum_concern_count == 0

    def test_scan_sorting_by_priority(self):
        """immediate > near_term > long_term > low."""
        findings = [
            _finding("slow",  "AES-256",   "AES",   "SYMMETRIC",                     "safe"),
            _finding("fast",  "RSA-2048",  "RSA",   "QUANTUM_VULNERABLE_PUBLIC_KEY",  "vulnerable",
                     usage_context="signing"),
        ]
        pm = {"slow": ("low", 5.0), "fast": ("immediate", 90.0)}
        result = recommend_for_scan("scan-sort", findings, pm)
        assert result.recommendations[0].finding_id == "fast"
        assert result.recommendations[1].finding_id == "slow"

    def test_scan_deterministic(self):
        """Same scan input → same output order and values."""
        findings = [
            _finding("d1", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context="key_exchange"),
            _finding("d2", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable"),
        ]
        r1 = recommend_for_scan("scan-det", findings)
        r2 = recommend_for_scan("scan-det", findings)
        assert [r.finding_id for r in r1.recommendations] == \
               [r.finding_id for r in r2.recommendations]
        assert [r.recommended_algorithms for r in r1.recommendations] == \
               [r.recommended_algorithms for r in r2.recommendations]

    def test_scan_summary_has_kb_version(self):
        findings = [_finding("x1", "AES-256", "AES", "SYMMETRIC", "safe")]
        result = recommend_for_scan("scan-kbv", findings)
        assert "1.0" in result.kb_version
