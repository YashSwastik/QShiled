"""
Deterministic Cryptographic Purpose Classifier
================================================

Classifies the cryptographic purpose of a detected algorithm/finding
using only evidence already available from the scanner output:
  - algorithm_family
  - category (from scanner rules taxonomy)
  - usage_context (set by AST scanner and cert scanner)
  - raw_snippet / evidence text
  - detection_method

Design rules:
  - Pure function — no DB, no network, no LLM.
  - Returns (purpose, confidence, reasoning) tuple.
  - If evidence is insufficient, marks as PURPOSE_UNKNOWN with reasoning.
  - Does NOT invent a purpose when evidence is absent.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.kb.knowledge_base import (
    PURPOSE_KEY_ESTABLISHMENT,
    PURPOSE_DIGITAL_SIGNATURE,
    PURPOSE_SYMMETRIC_ENCRYPTION,
    PURPOSE_HASHING,
    PURPOSE_MAC,
    PURPOSE_KEY_DERIVATION,
    PURPOSE_CERTIFICATE,
    PURPOSE_UNKNOWN,
)


@dataclass(frozen=True)
class PurposeClassification:
    purpose: str           # one of the PURPOSE_* constants
    confidence: float      # 0.0 – 1.0
    reasoning: str         # deterministic, human-readable explanation
    requires_manual_review: bool


# ── Algorithm-family defaults ─────────────────────────────────────────────────
# Some families have unambiguous purposes from their definition alone.

_FAMILY_DEFAULTS: dict[str, tuple[str, float, str]] = {
    # (purpose, confidence, reasoning)
    "ECDSA":   (PURPOSE_DIGITAL_SIGNATURE, 0.97,
                "ECDSA (Elliptic Curve Digital Signature Algorithm) exclusively performs digital signatures."),
    "DSA":     (PURPOSE_DIGITAL_SIGNATURE, 0.97,
                "DSA (Digital Signature Algorithm) exclusively performs digital signatures."),
    "ECDH":    (PURPOSE_KEY_ESTABLISHMENT, 0.95,
                "ECDH (Elliptic Curve Diffie-Hellman) exclusively performs key agreement/establishment."),
    "DH":      (PURPOSE_KEY_ESTABLISHMENT, 0.95,
                "Diffie-Hellman exclusively performs key agreement/establishment."),
    "AES":     (PURPOSE_SYMMETRIC_ENCRYPTION, 0.95,
                "AES is a symmetric block cipher used for symmetric encryption."),
    "ChaCha20":(PURPOSE_SYMMETRIC_ENCRYPTION, 0.95,
                "ChaCha20-Poly1305 is a symmetric stream cipher used for authenticated encryption."),
    "SHA-2":   (PURPOSE_HASHING, 0.95,
                "SHA-2 family algorithms are cryptographic hash functions."),
    "SHA-3":   (PURPOSE_HASHING, 0.95,
                "SHA-3 family algorithms are cryptographic hash functions."),
    "MD5":     (PURPOSE_HASHING, 0.97,
                "MD5 is a hash function (classically broken — not a quantum concern)."),
    "SHA-1":   (PURPOSE_HASHING, 0.97,
                "SHA-1 is a hash function (classically deprecated — not a Shor's concern)."),
    # PQC families — purpose clear from algorithm definition
    "ML-KEM":  (PURPOSE_KEY_ESTABLISHMENT, 0.99,
                "ML-KEM is a Key Encapsulation Mechanism (NIST FIPS 203) — key establishment only."),
    "ML-DSA":  (PURPOSE_DIGITAL_SIGNATURE, 0.99,
                "ML-DSA is a digital signature algorithm (NIST FIPS 204)."),
    "SLH-DSA": (PURPOSE_DIGITAL_SIGNATURE, 0.99,
                "SLH-DSA is a stateless hash-based digital signature algorithm (NIST FIPS 205)."),
    "FN-DSA":  (PURPOSE_DIGITAL_SIGNATURE, 0.99,
                "FN-DSA (FALCON) is a digital signature algorithm (NIST FIPS 206)."),
}

# ── Usage-context keyword → purpose map ──────────────────────────────────────
# These come directly from the scanner (AST: "key_generation", "hash", "cipher_init")
# and cert scanner ("certificate", "private_key").

_CONTEXT_TO_PURPOSE: dict[str, tuple[str, float]] = {
    # key establishment / transport
    "key_exchange":    (PURPOSE_KEY_ESTABLISHMENT, 0.90),
    "key_agreement":   (PURPOSE_KEY_ESTABLISHMENT, 0.90),
    "key_transport":   (PURPOSE_KEY_ESTABLISHMENT, 0.90),
    "key_wrap":        (PURPOSE_KEY_ESTABLISHMENT, 0.88),
    "key_generation":  (PURPOSE_KEY_ESTABLISHMENT, 0.70),  # lower: could be for signing too
    # signing
    "signing":         (PURPOSE_DIGITAL_SIGNATURE, 0.90),
    "signature":       (PURPOSE_DIGITAL_SIGNATURE, 0.90),
    "verification":    (PURPOSE_DIGITAL_SIGNATURE, 0.85),
    "sign":            (PURPOSE_DIGITAL_SIGNATURE, 0.85),
    "verify":          (PURPOSE_DIGITAL_SIGNATURE, 0.80),
    "authentication":  (PURPOSE_DIGITAL_SIGNATURE, 0.75),  # could be MAC, lower
    # encryption/decryption — symmetric for symmetric families; key_establishment for asymmetric
    # NOTE: purpose_classify() for RSA/DH/ECC handles the ambiguity in _classify_rsa/_classify_ecc
    # These entries are used primarily for symmetric family lookups (AES, ChaCha20)
    "encryption":      (PURPOSE_SYMMETRIC_ENCRYPTION, 0.85),
    "decryption":      (PURPOSE_SYMMETRIC_ENCRYPTION, 0.85),
    "cipher_init":     (PURPOSE_SYMMETRIC_ENCRYPTION, 0.80),
    "cipher":          (PURPOSE_SYMMETRIC_ENCRYPTION, 0.80),
    # asymmetric encryption → treated as key establishment (RSA-OAEP, etc.)
    "encrypt":         (PURPOSE_KEY_ESTABLISHMENT, 0.80),  # unlikely scanner value but safe
    "decrypt":         (PURPOSE_KEY_ESTABLISHMENT, 0.80),
    # hashing
    "hash":            (PURPOSE_HASHING, 0.92),
    "hashing":         (PURPOSE_HASHING, 0.92),
    "digest":          (PURPOSE_HASHING, 0.90),
    "checksum":        (PURPOSE_HASHING, 0.85),
    # mac
    "mac":             (PURPOSE_MAC, 0.90),
    "hmac":            (PURPOSE_MAC, 0.90),
    # kdf
    "kdf":             (PURPOSE_KEY_DERIVATION, 0.90),
    "key_derivation":  (PURPOSE_KEY_DERIVATION, 0.90),
    "pbkdf":           (PURPOSE_KEY_DERIVATION, 0.90),
    # cert/pki
    "certificate":     (PURPOSE_CERTIFICATE, 0.90),
    "private_key":     (PURPOSE_KEY_ESTABLISHMENT, 0.70),  # could be signing too
}

# ── Evidence snippet keyword hints (lower confidence, only for RSA/ECC ambiguity) ──

_SNIPPET_SIGNING_HINTS = frozenset({
    "sign", "signature", "verify", "pss", "pkcs1v15",
    "signing_key", "verif", "signer",
})
_SNIPPET_ENCRYPTION_HINTS = frozenset({
    "encrypt", "decrypt", "oaep", "wrap", "unwrap",
    "cipher", "encapsulat", "key_transport",
})


def _evidence_hints(evidence: str | None) -> tuple[str | None, float]:
    """
    Check raw snippet for signing vs encryption hints.
    Returns (hinted_purpose|None, confidence_boost).
    Only used for ambiguous families (RSA, ECC).
    """
    if not evidence:
        return None, 0.0
    ev = evidence.lower()
    sig_hits = sum(1 for h in _SNIPPET_SIGNING_HINTS if h in ev)
    enc_hits = sum(1 for h in _SNIPPET_ENCRYPTION_HINTS if h in ev)
    if sig_hits > enc_hits and sig_hits >= 1:
        return PURPOSE_DIGITAL_SIGNATURE, 0.10
    if enc_hits > sig_hits and enc_hits >= 1:
        return PURPOSE_KEY_ESTABLISHMENT, 0.10
    return None, 0.0


def classify_purpose(
    algorithm_family: str,
    category: str,
    usage_context: str | None,
    evidence: str | None,
    detection_method: str = "regex",
) -> PurposeClassification:
    """
    Deterministically classify the cryptographic purpose of a finding.

    Args:
        algorithm_family: e.g. "RSA", "AES", "ECDSA"
        category: scanner Category enum value string
        usage_context: from scanner (may be None for regex hits)
        evidence: masked source snippet (may be None)
        detection_method: "regex" | "ast" | "cert_parse"

    Returns:
        PurposeClassification with purpose, confidence, reasoning, manual_review flag.
    """

    # ── 1. Unambiguous family defaults ───────────────────────────────────────
    if algorithm_family in _FAMILY_DEFAULTS:
        default_purpose, default_conf, default_reason = _FAMILY_DEFAULTS[algorithm_family]

        # Even for unambiguous families, usage_context can refine confidence
        if usage_context:
            ctx_lower = usage_context.lower()
            ctx_result = _CONTEXT_TO_PURPOSE.get(ctx_lower)
            if ctx_result:
                ctx_purpose, ctx_conf = ctx_result
                # Only accept if it aligns with the definitive default
                if ctx_purpose == default_purpose:
                    # Consistent — boost confidence slightly
                    final_conf = min(0.99, default_conf + 0.02)
                    return PurposeClassification(
                        purpose=default_purpose,
                        confidence=round(final_conf, 3),
                        reasoning=(
                            f"{default_reason} "
                            f"Usage context '{usage_context}' confirms {ctx_purpose}."
                        ),
                        requires_manual_review=False,
                    )
                # Conflicting usage_context for an unambiguous family: trust the family
                return PurposeClassification(
                    purpose=default_purpose,
                    confidence=round(default_conf * 0.95, 3),
                    reasoning=(
                        f"{default_reason} "
                        f"Usage context '{usage_context}' is inconsistent — "
                        f"algorithm family definition takes precedence."
                    ),
                    requires_manual_review=False,
                )

        return PurposeClassification(
            purpose=default_purpose,
            confidence=round(default_conf, 3),
            reasoning=default_reason,
            requires_manual_review=False,
        )

    # ── 2. RSA — ambiguous (can be key establishment OR signatures) ───────────
    if algorithm_family == "RSA":
        return _classify_rsa(usage_context, evidence, detection_method)

    # ── 3. ECC — ambiguous (ECDH or ECDSA-like, without family distinction) ──
    if algorithm_family == "ECC":
        return _classify_ecc(usage_context, evidence, detection_method)

    # ── 4. Category-level fallbacks ───────────────────────────────────────────
    cat_upper = category.upper() if category else ""

    if cat_upper == "SYMMETRIC":
        return PurposeClassification(
            purpose=PURPOSE_SYMMETRIC_ENCRYPTION,
            confidence=0.80,
            reasoning=(
                f"Algorithm family '{algorithm_family}' is in the SYMMETRIC category — "
                "classified as symmetric encryption. Not quantum-vulnerable via Shor's algorithm."
            ),
            requires_manual_review=False,
        )

    if cat_upper == "HASH":
        return PurposeClassification(
            purpose=PURPOSE_HASHING,
            confidence=0.80,
            reasoning=(
                f"Algorithm family '{algorithm_family}' is in the HASH category — "
                "classified as hashing."
            ),
            requires_manual_review=False,
        )

    if cat_upper == "LEGACY_DEPRECATED":
        return PurposeClassification(
            purpose=PURPOSE_HASHING,
            confidence=0.75,
            reasoning=(
                f"Algorithm family '{algorithm_family}' is classically deprecated. "
                "Classified as hashing/MAC (classical concern, not quantum migration priority)."
            ),
            requires_manual_review=False,
        )

    if cat_upper == "POST_QUANTUM":
        return PurposeClassification(
            purpose=PURPOSE_KEY_ESTABLISHMENT,
            confidence=0.70,
            reasoning=(
                f"Algorithm family '{algorithm_family}' is in the POST_QUANTUM category — "
                "likely key establishment or signing. Manual verification recommended."
            ),
            requires_manual_review=True,
        )

    # ── 5. Unknown / fallback ─────────────────────────────────────────────────
    return PurposeClassification(
        purpose=PURPOSE_UNKNOWN,
        confidence=0.0,
        reasoning=(
            f"Cryptographic purpose of '{algorithm_family}' (category: {category}) "
            "could not be determined from available evidence. "
            "Manual review of source context is required before migration planning."
        ),
        requires_manual_review=True,
    )


# Contexts that unambiguously indicate RSA key transport / asymmetric encryption
# (RSA-OAEP, key wrap/unwrap) — these map to key_establishment, not symmetric encryption.
_RSA_ENCRYPTION_AS_KEM_CONTEXTS = frozenset({
    "encryption", "decryption", "encrypt", "decrypt",
    "key_transport", "key_wrap", "key_unwrap",
    "oaep", "pkcs1_enc",
})


def _classify_rsa(
    usage_context: str | None,
    evidence: str | None,
    detection_method: str,
) -> PurposeClassification:
    """RSA is ambiguous — used for both key establishment and digital signatures.

    Disambiguation priority:
      1. usage_context that unambiguously signals signing → digital_signature
      2. usage_context that signals RSA encryption/key-transport → key_establishment
         (RSA encryption is _asymmetric_ key transport, not symmetric cipher)
      3. Generic _CONTEXT_TO_PURPOSE lookup for other values
      4. Evidence snippet keyword hints (low confidence)
      5. cert_parse detection → key_establishment (low confidence, manual review)
      6. Fallback → unknown, manual review
    """
    if usage_context:
        ctx_lower = usage_context.lower()

        # Signing signals take highest priority
        _SIGNING_CONTEXTS = frozenset({
            "signing", "sign", "signature", "verification", "verify",
        })
        if ctx_lower in _SIGNING_CONTEXTS:
            return PurposeClassification(
                purpose=PURPOSE_DIGITAL_SIGNATURE,
                confidence=0.90,
                reasoning=(
                    f"RSA purpose classified as 'digital_signature' "
                    f"from scanner usage_context: '{usage_context}'."
                ),
                requires_manual_review=False,
            )

        # RSA encryption = asymmetric key transport (OAEP) → key_establishment
        if ctx_lower in _RSA_ENCRYPTION_AS_KEM_CONTEXTS:
            return PurposeClassification(
                purpose=PURPOSE_KEY_ESTABLISHMENT,
                confidence=0.85,
                reasoning=(
                    f"RSA usage_context '{usage_context}' indicates asymmetric encryption "
                    "(key transport / RSA-OAEP). RSA encryption is used for key establishment "
                    "workflows, not symmetric data encryption. "
                    "Migration path: ML-KEM (FIPS 203) for key encapsulation."
                ),
                requires_manual_review=False,
            )

        # Remaining generic lookup (key_exchange, key_generation, authentication, etc.)
        ctx_result = _CONTEXT_TO_PURPOSE.get(ctx_lower)
        if ctx_result:
            ctx_purpose, ctx_conf = ctx_result
            if ctx_purpose in (PURPOSE_DIGITAL_SIGNATURE, PURPOSE_KEY_ESTABLISHMENT):
                return PurposeClassification(
                    purpose=ctx_purpose,
                    confidence=round(ctx_conf, 3),
                    reasoning=(
                        f"RSA purpose classified as '{ctx_purpose}' "
                        f"from scanner usage_context: '{usage_context}'."
                    ),
                    requires_manual_review=ctx_conf < 0.80,
                )

    # Evidence snippet hints (lower confidence)
    hint_purpose, hint_boost = _evidence_hints(evidence)
    if hint_purpose in (PURPOSE_DIGITAL_SIGNATURE, PURPOSE_KEY_ESTABLISHMENT):
        conf = 0.55 + hint_boost
        return PurposeClassification(
            purpose=hint_purpose,
            confidence=round(conf, 3),
            reasoning=(
                f"RSA purpose inferred as '{hint_purpose}' from source code keywords "
                f"in evidence snippet. Confidence is limited — manual review recommended."
            ),
            requires_manual_review=True,
        )

    # cert_parse detection strongly suggests key establishment (private key / cert)
    if detection_method == "cert_parse":
        return PurposeClassification(
            purpose=PURPOSE_KEY_ESTABLISHMENT,
            confidence=0.75,
            reasoning=(
                "RSA key detected via certificate/PEM parsing. "
                "Certificate keys are typically used for key establishment or authentication. "
                "Manual review recommended to confirm specific use case."
            ),
            requires_manual_review=True,
        )

    # Insufficient evidence — mark unknown
    return PurposeClassification(
        purpose=PURPOSE_UNKNOWN,
        confidence=0.0,
        reasoning=(
            "RSA detected but cryptographic purpose (key establishment/encryption vs. "
            "digital signatures) cannot be determined from available evidence. "
            "Inspect source code context: OAEP/key-wrapping usage → key establishment; "
            "PSS/PKCS1v15-sign usage → digital signatures. Manual review required."
        ),
        requires_manual_review=True,
    )


def _classify_ecc(
    usage_context: str | None,
    evidence: str | None,
    detection_method: str,
) -> PurposeClassification:
    """Generic ECC detection — ambiguous between ECDH (key agreement) and ECDSA (signing)."""

    if usage_context:
        ctx_lower = usage_context.lower()
        ctx_result = _CONTEXT_TO_PURPOSE.get(ctx_lower)
        if ctx_result:
            ctx_purpose, ctx_conf = ctx_result
            if ctx_purpose in (PURPOSE_DIGITAL_SIGNATURE, PURPOSE_KEY_ESTABLISHMENT):
                return PurposeClassification(
                    purpose=ctx_purpose,
                    confidence=round(ctx_conf, 3),
                    reasoning=(
                        f"Generic ECC purpose classified as '{ctx_purpose}' "
                        f"from usage_context: '{usage_context}'."
                    ),
                    requires_manual_review=ctx_conf < 0.80,
                )

    hint_purpose, hint_boost = _evidence_hints(evidence)
    if hint_purpose in (PURPOSE_DIGITAL_SIGNATURE, PURPOSE_KEY_ESTABLISHMENT):
        conf = 0.50 + hint_boost
        return PurposeClassification(
            purpose=hint_purpose,
            confidence=round(conf, 3),
            reasoning=(
                f"Generic ECC purpose inferred as '{hint_purpose}' from evidence keywords. "
                "Low confidence — manual review required."
            ),
            requires_manual_review=True,
        )

    # Default ECC to key-establishment (most common generic ECC usage)
    # but low confidence and flag manual review
    return PurposeClassification(
        purpose=PURPOSE_UNKNOWN,
        confidence=0.0,
        reasoning=(
            "Generic ECC detected but purpose (ECDH key agreement vs. ECDSA signing) "
            "cannot be definitively determined. Inspect whether this is ECDH (key agreement — "
            "migrate to ML-KEM) or ECDSA (digital signatures — migrate to ML-DSA/SLH-DSA). "
            "Manual review required."
        ),
        requires_manual_review=True,
    )
