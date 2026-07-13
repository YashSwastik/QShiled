"""
QShield Migration Knowledge Base
=================================
Version: 1.0

Structured, versionable knowledge base mapping cryptographic algorithm families
and purposes to migration guidance.

Design rules:
  - Pure data only — no scoring logic, no DB coupling, no network calls.
  - Keyed by (algorithm_family, crypto_purpose) strings.
  - Maintained separately from recommendation execution logic.
  - NIST references use current finalized standard names (FIPS 203/204/205/206).

TECHNICAL CORRECTNESS:
  ML-KEM  → key encapsulation (key establishment)
  ML-DSA  → lattice-based digital signatures
  SLH-DSA → stateless hash-based digital signatures
  FN-DSA  → FALCON; fast lattice signatures (FIPS 206)

  NEVER recommend ML-KEM for signing purposes.
  NEVER recommend ML-DSA/SLH-DSA for key establishment.
"""
from __future__ import annotations

from dataclasses import dataclass, field

KB_VERSION = "1.0"

# ── Purpose identifiers ───────────────────────────────────────────────────────

PURPOSE_KEY_ESTABLISHMENT = "key_establishment"
PURPOSE_ENCRYPTION        = "encryption"
PURPOSE_DIGITAL_SIGNATURE = "digital_signature"
PURPOSE_SYMMETRIC_ENCRYPTION = "symmetric_encryption"
PURPOSE_HASHING           = "hashing"
PURPOSE_MAC               = "mac"
PURPOSE_KEY_DERIVATION    = "key_derivation"
PURPOSE_CERTIFICATE       = "certificate"
PURPOSE_UNKNOWN           = "unknown"


@dataclass(frozen=True)
class MigrationGuidance:
    """
    Structured migration guidance for one (algorithm_family, purpose) pair.

    All fields contain curated technical knowledge sourced from:
      - NIST SP 800-208
      - NIST SP 800-131A Rev. 2
      - NIST FIPS 203, 204, 205, 206
      - NIST FIPS 140-3 transition guidelines
      - CISA/NSA Post-Quantum Cryptography FAQs
    """
    # Identity
    algorithm_family: str
    purpose: str

    # Why migration is needed (quantum threat model)
    quantum_threat: str

    # Recommended PQC target category (not a specific product)
    recommended_target_category: str

    # Specific NIST-standardized algorithm names to evaluate
    recommended_algorithms: tuple[str, ...]

    # NIST standard references
    nist_standards: tuple[str, ...]

    # Typical migration effort
    effort_estimate: str  # low / medium / high / very_high

    # Ordered prerequisites before migration begins
    prerequisites: tuple[str, ...]

    # High-level ordered migration steps
    migration_steps: tuple[str, ...]

    # Testing requirements
    testing_requirements: tuple[str, ...]

    # Interoperability / compatibility considerations
    interoperability_notes: tuple[str, ...]

    # Validation checklist items
    validation_checklist: tuple[str, ...]

    # Approximate timeline guidance
    timeline_guidance: str = ""

    # Additional technical notes
    technical_notes: str = ""


# ── Knowledge base entries ────────────────────────────────────────────────────

_ENTRIES: list[MigrationGuidance] = [

    # =========================================================================
    # RSA — Key Establishment / Encryption
    # =========================================================================
    MigrationGuidance(
        algorithm_family="RSA",
        purpose=PURPOSE_KEY_ESTABLISHMENT,
        quantum_threat=(
            "RSA key encapsulation and encryption are broken by Shor's algorithm on a "
            "cryptographically relevant quantum computer (CRQC). "
            "RSA-2048 offers no quantum security; RSA-4096 is also fully broken by Shor's. "
            "Harvest-now-decrypt-later (HNDL) attacks are active: encrypted data captured "
            "today can be decrypted when CRQCs become available."
        ),
        recommended_target_category="Key Encapsulation Mechanism (KEM) — NIST PQC standardized",
        recommended_algorithms=(
            "ML-KEM-768 (FIPS 203, NIST Level 3) — general purpose",
            "ML-KEM-1024 (FIPS 203, NIST Level 5) — high-security contexts",
            "ML-KEM-512 (FIPS 203, NIST Level 1) — constrained environments with lower security requirements",
        ),
        nist_standards=("FIPS 203 (ML-KEM / CRYSTALS-Kyber)", "NIST SP 800-227 (Recommendations for Key-Encapsulation Mechanisms)"),
        effort_estimate="high",
        prerequisites=(
            "Inventory all RSA key sizes and key establishment endpoints currently in use.",
            "Identify all protocols relying on RSA key transport or RSA-OAEP.",
            "Assess hybrid mode feasibility (classical + PQC in parallel) for migration period.",
            "Review library/framework support for ML-KEM in your language ecosystem.",
            "Identify certificate authority (CA) and PKI dependencies for key transport chains.",
        ),
        migration_steps=(
            "1. Evaluate ML-KEM parameter set appropriate for the security level (768 recommended for general use).",
            "2. Implement hybrid key establishment: ML-KEM alongside existing RSA during transition period.",
            "3. Update key exchange protocols (TLS, SSH, custom) to negotiate ML-KEM.",
            "4. Replace RSA-encrypted session/symmetric key delivery with ML-KEM encapsulation.",
            "5. Update key storage, HSM, and KMS to support ML-KEM key material.",
            "6. Retire RSA key establishment after dual-stack transition is validated.",
            "7. Update documentation, runbooks, and key management procedures.",
        ),
        testing_requirements=(
            "Unit tests: ML-KEM encapsulation/decapsulation round-trip correctness.",
            "Integration tests: end-to-end session establishment with ML-KEM.",
            "Interoperability tests: validate with at least two independent ML-KEM implementations.",
            "Regression tests: confirm legacy RSA paths still function during hybrid period.",
            "Performance benchmarks: measure latency and throughput impact of ML-KEM.",
            "Key size validation: confirm ciphertext and public key sizes are handled correctly.",
        ),
        interoperability_notes=(
            "ML-KEM is not drop-in compatible with RSA key transport APIs; protocol-level changes required.",
            "TLS 1.3 hybrid key exchange extensions (X25519MLKEM768) are available in some libraries.",
            "SSH PQC extensions for ML-KEM key exchange are available in newer OpenSSH versions.",
            "Hybrid mode (classical + PQC) recommended during transition to maintain backward compatibility.",
            "HSMs and hardware security tokens may not yet support ML-KEM — verify vendor roadmaps.",
        ),
        validation_checklist=(
            "[ ] ML-KEM parameter set selected and documented.",
            "[ ] Public key and ciphertext sizes accommodated in all storage/transport systems.",
            "[ ] Hybrid key establishment validated with test vectors from NIST ACVP.",
            "[ ] All RSA key establishment endpoints replaced or dual-stacked.",
            "[ ] Key derivation from ML-KEM shared secret is correct (no raw KEM output used as key).",
            "[ ] Rollback plan in place if interoperability issues arise.",
            "[ ] Security review completed for new key management procedures.",
        ),
        timeline_guidance=(
            "Start hybrid mode within 6–12 months. Full migration recommended within 2–3 years "
            "for long-lived sensitive systems."
        ),
        technical_notes=(
            "ML-KEM (CRYSTALS-Kyber) produces a shared secret via encapsulation/decapsulation. "
            "It is NOT an encryption scheme — do not use the KEM output directly as data. "
            "Always derive a symmetric key (AES-256) from the KEM shared secret using a KDF."
        ),
    ),

    # =========================================================================
    # RSA — Digital Signatures
    # =========================================================================
    MigrationGuidance(
        algorithm_family="RSA",
        purpose=PURPOSE_DIGITAL_SIGNATURE,
        quantum_threat=(
            "RSA signatures (PKCS#1 v1.5, PSS) are broken by Shor's algorithm on a CRQC. "
            "Forging RSA signatures becomes computationally feasible post-CRQC. "
            "Code signing, certificate validation, and authentication chains relying on "
            "RSA signatures will require migration to quantum-resistant alternatives."
        ),
        recommended_target_category="Lattice-based or hash-based digital signature — NIST PQC standardized",
        recommended_algorithms=(
            "ML-DSA-65 (FIPS 204, NIST Level 3) — general purpose digital signatures",
            "ML-DSA-87 (FIPS 204, NIST Level 5) — high-security signature contexts",
            "SLH-DSA-SHA2-128s (FIPS 205) — stateless hash-based, conservative option",
            "SLH-DSA-SHA2-256s (FIPS 205) — hash-based, maximum conservatism",
            "FN-DSA (FIPS 206 / FALCON) — compact signatures for constrained environments",
        ),
        nist_standards=(
            "FIPS 204 (ML-DSA / CRYSTALS-Dilithium)",
            "FIPS 205 (SLH-DSA / SPHINCS+)",
            "FIPS 206 (FN-DSA / FALCON)",
        ),
        effort_estimate="high",
        prerequisites=(
            "Inventory all RSA signing keys, certificates, and signing endpoints.",
            "Identify all signature verification paths (code signing, JWT, TLS certs, S/MIME, etc.).",
            "Assess signature size tolerance — PQC signatures are significantly larger than RSA.",
            "Review PKI hierarchy: intermediate and root CA certificates may need migration.",
            "Assess whether stateless (SLH-DSA) or performance-optimized (ML-DSA, FN-DSA) is preferable.",
        ),
        migration_steps=(
            "1. Select PQC signature algorithm: ML-DSA-65 for general use; SLH-DSA for maximum conservatism.",
            "2. Generate new PQC signing key pairs and certificates (potentially dual-signed during transition).",
            "3. Update signing infrastructure: HSMs, code signing pipelines, certificate issuance.",
            "4. Update verification paths to accept PQC signatures (protocol and library support).",
            "5. Implement hybrid signing (dual RSA + PQC signature) during transition period.",
            "6. Rotate certificates and update trust stores.",
            "7. Retire RSA signing keys after validation of PQC signing infrastructure.",
        ),
        testing_requirements=(
            "Unit tests: sign/verify round-trip with PQC algorithm and NIST test vectors.",
            "Integration tests: full signature validation chain (signer → verifier via protocol).",
            "Certificate chain tests: root → intermediate → leaf with PQC keys.",
            "Signature size tests: confirm all storage and transport systems handle larger PQC signatures.",
            "Interoperability tests: validate with independent implementations.",
            "Regression tests: confirm existing RSA paths work during hybrid period.",
        ),
        interoperability_notes=(
            "PQC signatures are significantly larger than RSA (ML-DSA-65: ~3.3 KB; SLH-DSA: 8–50 KB). "
            "All signature storage, transport, and processing paths must accommodate larger sizes.",
            "X.509 certificate support for PQC is evolving — verify CA vendor support.",
            "TLS 1.3 extensions for PQC certificates are in active standardization.",
            "Code signing formats (Authenticode, GPG, JAR signing) may require toolchain updates.",
            "JWT/JWS specifications for PQC keys are being standardized.",
        ),
        validation_checklist=(
            "[ ] PQC signature algorithm selected and rationale documented.",
            "[ ] Signature and public key sizes accommodated across all systems.",
            "[ ] Test vectors validated against NIST ACVP.",
            "[ ] Certificate chain migrated or dual-stacked.",
            "[ ] All RSA signing endpoints converted or hybrid-mode enabled.",
            "[ ] Signature verification tested end-to-end in production-like environment.",
            "[ ] Key rotation procedures updated to reflect new key generation process.",
        ),
        timeline_guidance=(
            "Begin parallel infrastructure within 6 months. "
            "Full migration for long-lived certificates recommended within 2 years."
        ),
        technical_notes=(
            "Do NOT use ML-KEM for digital signatures. ML-KEM is a Key Encapsulation Mechanism only. "
            "For signatures, choose from: ML-DSA (lattice, performance-optimized), "
            "SLH-DSA (hash-based, most conservative), or FN-DSA (FALCON, compact). "
            "Choice depends on signature size tolerance, signing/verification performance, and conservatism preference."
        ),
    ),

    # =========================================================================
    # ECDSA — Digital Signatures (default purpose; ECDSA is always signing)
    # =========================================================================
    MigrationGuidance(
        algorithm_family="ECDSA",
        purpose=PURPOSE_DIGITAL_SIGNATURE,
        quantum_threat=(
            "ECDSA is broken by Shor's algorithm on a CRQC. "
            "The elliptic-curve discrete logarithm problem (ECDLP), which ECDSA security depends on, "
            "is efficiently solved by quantum computers. "
            "This affects all NIST curves: P-256, P-384, P-521, secp256k1."
        ),
        recommended_target_category="Lattice-based or hash-based digital signature — NIST PQC standardized",
        recommended_algorithms=(
            "ML-DSA-65 (FIPS 204, NIST Level 3) — general purpose, performance-optimized",
            "ML-DSA-87 (FIPS 204, NIST Level 5) — high-security contexts",
            "SLH-DSA-SHA2-128f (FIPS 205) — hash-based, fast variant",
            "FN-DSA (FIPS 206 / FALCON) — compact signatures",
        ),
        nist_standards=(
            "FIPS 204 (ML-DSA / CRYSTALS-Dilithium)",
            "FIPS 205 (SLH-DSA / SPHINCS+)",
            "FIPS 206 (FN-DSA / FALCON)",
        ),
        effort_estimate="high",
        prerequisites=(
            "Inventory all ECDSA keys, certificates, and signing use cases.",
            "Identify curve variants in use (P-256, P-384, P-521).",
            "Assess signature size constraints — PQC signatures are larger than ECDSA.",
            "Review all JWT, TLS, code signing, and SSH usage of ECDSA.",
            "Evaluate whether FN-DSA's smaller size is required for constrained environments.",
        ),
        migration_steps=(
            "1. Select target PQC signature algorithm (ML-DSA-65 recommended for general use).",
            "2. Generate PQC signing keys and issue PQC certificates from updated CA.",
            "3. Update signing and verification code to use selected PQC library.",
            "4. Deploy hybrid ECDSA + PQC signing during transition period.",
            "5. Update certificate trust stores and verification chains.",
            "6. Migrate TLS, SSH, JWT, and other protocol-level signature uses.",
            "7. Retire ECDSA keys after full PQC migration verified.",
        ),
        testing_requirements=(
            "Unit tests: sign/verify round-trip with NIST ACVP test vectors.",
            "Signature size accommodation tests across all affected systems.",
            "Certificate chain validation tests with PQC certificates.",
            "Protocol integration tests (TLS handshake, SSH auth, JWT validation).",
            "Interoperability tests against independent PQC implementations.",
        ),
        interoperability_notes=(
            "ML-DSA signatures (~2.4–3.3 KB) are significantly larger than ECDSA P-256 (~64 bytes).",
            "IANA and IETF are standardizing PQC algorithm identifiers for TLS/SSH/X.509.",
            "Hybrid signature schemes (classical + PQC) are recommended for transition period.",
            "Some certificate formats have size constraints that may need updating.",
        ),
        validation_checklist=(
            "[ ] PQC signature algorithm selected for each ECDSA use case.",
            "[ ] Signature size impacts assessed and all systems updated.",
            "[ ] NIST ACVP test vector validation completed.",
            "[ ] Certificate hierarchy updated or dual-stacked.",
            "[ ] All ECDSA signing endpoints migrated or hybrid-mode enabled.",
            "[ ] End-to-end signature verification tested.",
        ),
        timeline_guidance=(
            "Similar timeline to RSA signatures. Start hybrid mode within 6–12 months."
        ),
        technical_notes=(
            "ECDSA is exclusively a digital signature scheme. "
            "Do not conflate ECDSA with ECDH (key agreement). "
            "ECDH requires a separate, KEM-oriented migration path."
        ),
    ),

    # =========================================================================
    # ECDH — Key Agreement / Key Establishment
    # =========================================================================
    MigrationGuidance(
        algorithm_family="ECDH",
        purpose=PURPOSE_KEY_ESTABLISHMENT,
        quantum_threat=(
            "ECDH key agreement is broken by Shor's algorithm. "
            "The shared secret computed via ECDH can be recovered quantum-computationally. "
            "Forward secrecy achieved by ECDHE is not quantum-forward-secret — sessions can be "
            "retrospectively decrypted once CRQCs are available."
        ),
        recommended_target_category="Key Encapsulation Mechanism (KEM) — NIST PQC standardized",
        recommended_algorithms=(
            "ML-KEM-768 (FIPS 203, NIST Level 3) — primary recommendation",
            "ML-KEM-1024 (FIPS 203, NIST Level 5) — high-security contexts",
        ),
        nist_standards=("FIPS 203 (ML-KEM / CRYSTALS-Kyber)",),
        effort_estimate="high",
        prerequisites=(
            "Identify all ECDH/ECDHE key agreement locations (TLS, SSH, custom protocols).",
            "Assess hybrid key exchange feasibility for transition period.",
            "Review library support for ML-KEM in the protocol/framework stack.",
            "Identify all curves in use (X25519, P-256, P-384).",
        ),
        migration_steps=(
            "1. Replace ECDH with ML-KEM for key encapsulation in custom protocols.",
            "2. For TLS: enable X25519MLKEM768 hybrid group (broadly supported).",
            "3. For SSH: enable ML-KEM key exchange extensions.",
            "4. Implement hybrid ECDH + ML-KEM during transition period.",
            "5. Retire ECDH after dual-stack period validated.",
        ),
        testing_requirements=(
            "ML-KEM encapsulation/decapsulation round-trip tests.",
            "Protocol-level integration tests (TLS handshake with ML-KEM group).",
            "Interoperability tests with independent ML-KEM implementations.",
            "Hybrid mode regression tests.",
        ),
        interoperability_notes=(
            "TLS 1.3 hybrid groups (X25519MLKEM768) are available in OpenSSL 3.x, BoringSSL, and others.",
            "ML-KEM ciphertext is larger than ECDH public key — buffer sizes may need updating.",
            "ECDH and ML-KEM have fundamentally different APIs: no direct drop-in substitution.",
        ),
        validation_checklist=(
            "[ ] All ECDH/ECDHE usages identified and migration path selected.",
            "[ ] ML-KEM parameter set selected per security requirement.",
            "[ ] Hybrid key exchange deployed and tested.",
            "[ ] All session establishment paths migrated.",
            "[ ] Performance impact measured and acceptable.",
        ),
        timeline_guidance="Start hybrid TLS within 6 months for internet-facing services.",
        technical_notes=(
            "ML-KEM is key encapsulation, not key agreement. "
            "The API differs from ECDH — one party encapsulates, the other decapsulates. "
            "Use a KDF to derive the final symmetric key from the ML-KEM shared secret."
        ),
    ),

    # =========================================================================
    # ECC (general ECC, purpose not deterministically known)
    # =========================================================================
    MigrationGuidance(
        algorithm_family="ECC",
        purpose=PURPOSE_KEY_ESTABLISHMENT,
        quantum_threat=(
            "Elliptic curve cryptography is broken by Shor's algorithm. "
            "ECC used for key agreement requires migration to ML-KEM. "
        ),
        recommended_target_category="Key Encapsulation Mechanism (KEM) — NIST PQC standardized",
        recommended_algorithms=(
            "ML-KEM-768 (FIPS 203) — for key establishment",
        ),
        nist_standards=("FIPS 203 (ML-KEM)",),
        effort_estimate="high",
        prerequisites=(
            "Determine whether this ECC usage is key establishment or signing.",
            "If key establishment: follow ECDH migration path.",
            "If signing: follow ECDSA migration path.",
        ),
        migration_steps=(
            "1. Clarify cryptographic purpose (key establishment vs. signing) from source context.",
            "2. Apply the ECDH (key establishment) or ECDSA (signing) migration path accordingly.",
        ),
        testing_requirements=("Purpose-specific tests per ECDH or ECDSA guidance.",),
        interoperability_notes=("Purpose must be determined before specific migration steps apply.",),
        validation_checklist=("[ ] ECC purpose clarified as key establishment or signing.",),
        technical_notes=(
            "Generic ECC detection without clear purpose context. "
            "Inspect source code to determine if this is ECDH (key agreement) or ECDSA (signing). "
            "Migration target differs: ML-KEM for key establishment, ML-DSA/SLH-DSA for signing."
        ),
    ),
    MigrationGuidance(
        algorithm_family="ECC",
        purpose=PURPOSE_DIGITAL_SIGNATURE,
        quantum_threat="Elliptic curve discrete logarithm problem solved by Shor's algorithm.",
        recommended_target_category="Lattice-based or hash-based digital signature — NIST PQC standardized",
        recommended_algorithms=("ML-DSA-65 (FIPS 204)", "SLH-DSA-SHA2-128f (FIPS 205)"),
        nist_standards=("FIPS 204 (ML-DSA)", "FIPS 205 (SLH-DSA)"),
        effort_estimate="high",
        prerequisites=("Confirm ECC usage is for signing; inspect source context.",),
        migration_steps=("Follow ECDSA migration guidance for digital signatures.",),
        testing_requirements=("PQC signature round-trip tests.",),
        interoperability_notes=("PQC signatures are larger than ECC signatures.",),
        validation_checklist=("[ ] PQC signing algorithm selected and validated.",),
        technical_notes="ECC used for digital signatures. Follows same path as ECDSA.",
    ),

    # =========================================================================
    # DH / Diffie-Hellman — Key Agreement
    # =========================================================================
    MigrationGuidance(
        algorithm_family="DH",
        purpose=PURPOSE_KEY_ESTABLISHMENT,
        quantum_threat=(
            "Discrete-logarithm-based Diffie-Hellman key agreement is broken by Shor's algorithm. "
            "Both finite-field DH and DH ephemeral (DHE) variants are broken. "
            "Session keys established via DH today can be recovered retrospectively by a CRQC."
        ),
        recommended_target_category="Key Encapsulation Mechanism (KEM) — NIST PQC standardized",
        recommended_algorithms=(
            "ML-KEM-768 (FIPS 203, NIST Level 3)",
            "ML-KEM-1024 (FIPS 203, NIST Level 5)",
        ),
        nist_standards=("FIPS 203 (ML-KEM / CRYSTALS-Kyber)",),
        effort_estimate="high",
        prerequisites=(
            "Inventory all DH/DHE parameters and group sizes in use.",
            "Identify all protocols using DH (TLS, IKE/IPsec, SSH, custom).",
            "Assess hybrid mode feasibility for transition.",
        ),
        migration_steps=(
            "1. Replace DH with ML-KEM for key encapsulation in custom protocols.",
            "2. For TLS: upgrade from DHE to ML-KEM or X25519MLKEM768.",
            "3. For IPsec/IKEv2: enable quantum-resistant key exchange extensions.",
            "4. Deploy hybrid DH + ML-KEM during transition.",
            "5. Retire DH after migration validated.",
        ),
        testing_requirements=(
            "ML-KEM encapsulation/decapsulation correctness tests.",
            "Protocol integration tests (TLS/SSH/IKE with ML-KEM).",
            "Interoperability tests.",
        ),
        interoperability_notes=(
            "DHE and ML-KEM have fundamentally different APIs.",
            "IKEv2 PQC extensions (RFC 9370) are available for IPsec.",
        ),
        validation_checklist=(
            "[ ] All DH key agreement replaced with ML-KEM.",
            "[ ] Hybrid mode validated during transition.",
            "[ ] Protocol negotiation updated to prefer ML-KEM.",
        ),
        technical_notes="DH is exclusively for key agreement. Migration target is ML-KEM, not ML-DSA.",
    ),

    # =========================================================================
    # DSA — Digital Signatures
    # =========================================================================
    MigrationGuidance(
        algorithm_family="DSA",
        purpose=PURPOSE_DIGITAL_SIGNATURE,
        quantum_threat=(
            "DSA (Digital Signature Algorithm) is broken by Shor's algorithm. "
            "Additionally, DSA is being deprecated classically (NIST SP 800-131A for context). "
            "Both quantum and classical vulnerabilities apply."
        ),
        recommended_target_category="Lattice-based or hash-based digital signature — NIST PQC standardized",
        recommended_algorithms=(
            "ML-DSA-65 (FIPS 204) — general purpose",
            "SLH-DSA-SHA2-128s (FIPS 205) — conservative option",
        ),
        nist_standards=("FIPS 204 (ML-DSA)", "FIPS 205 (SLH-DSA)"),
        effort_estimate="medium",
        prerequisites=(
            "Inventory all DSA keys and signing use cases.",
            "Note: DSA migration is doubly urgent — both quantum and classical weaknesses.",
        ),
        migration_steps=(
            "1. Treat as high priority due to dual (classical + quantum) vulnerability.",
            "2. Select ML-DSA or SLH-DSA as replacement.",
            "3. Migrate signing infrastructure, keys, and certificates.",
            "4. Update all verification paths.",
        ),
        testing_requirements=("PQC signing round-trip tests.", "Verification chain tests."),
        interoperability_notes=("DSA is already widely deprecated — parallel migration to PQC preferred over Ed25519 intermediate step.",),
        validation_checklist=("[ ] All DSA signing replaced.", "[ ] Classical DSA keys revoked."),
        technical_notes="DSA is signing-only. Never recommend ML-KEM as a DSA replacement.",
    ),

    # =========================================================================
    # AES — Symmetric Encryption
    # =========================================================================
    MigrationGuidance(
        algorithm_family="AES",
        purpose=PURPOSE_SYMMETRIC_ENCRYPTION,
        quantum_threat=(
            "Symmetric algorithms are NOT broken by Shor's algorithm. "
            "Grover's algorithm provides a quadratic speedup for brute-force search, "
            "effectively halving the security level: AES-128 → 64-bit post-quantum, "
            "AES-256 → 128-bit post-quantum (still considered secure). "
            "AES-128 in quantum-sensitive contexts should be upgraded to AES-256. "
            "This is NOT equivalent to the quantum vulnerability of RSA/ECDSA/DH."
        ),
        recommended_target_category="Symmetric — AES-256, no PQC replacement needed",
        recommended_algorithms=(
            "AES-256-GCM (preferred — authenticated encryption)",
            "AES-256-CBC with HMAC-SHA-256 (if GCM not available)",
            "ChaCha20-Poly1305 (alternative authenticated stream cipher)",
        ),
        nist_standards=("NIST SP 800-38D (AES-GCM)", "FIPS 197 (AES)"),
        effort_estimate="low",
        prerequisites=(
            "Identify all AES key sizes in use.",
            "If AES-128: plan upgrade to AES-256.",
            "If AES-256: confirm algorithm mode (prefer GCM).",
        ),
        migration_steps=(
            "1. Upgrade all AES-128 usages to AES-256.",
            "2. Migrate from ECB or CBC mode to GCM (authenticated encryption).",
            "3. Ensure proper IV/nonce generation (unique per encryption operation).",
            "4. No PQC replacement required — this is a key-size and mode upgrade.",
        ),
        testing_requirements=(
            "Key size validation: confirm AES-256 is used.",
            "Mode validation: confirm GCM or other AEAD mode.",
            "Round-trip encryption/decryption tests.",
        ),
        interoperability_notes=(
            "AES-256 is universally supported. Minimal interoperability concerns.",
            "GCM mode is broadly supported in TLS 1.3 and modern frameworks.",
        ),
        validation_checklist=(
            "[ ] All AES-128 upgraded to AES-256.",
            "[ ] All ECB/CBC mode usages migrated to GCM or ChaCha20-Poly1305.",
            "[ ] IV/nonce uniqueness confirmed in all encryption paths.",
        ),
        timeline_guidance="Upgrade AES-128 → AES-256 within 6 months for sensitive systems.",
        technical_notes=(
            "AES is NOT quantum-vulnerable in the same sense as RSA/ECDSA/DH. "
            "Do NOT recommend ML-KEM or ML-DSA as AES replacements. "
            "This is a symmetric algorithm — Grover risk is addressed by using 256-bit keys."
        ),
    ),

    # =========================================================================
    # ChaCha20 — Symmetric Encryption
    # =========================================================================
    MigrationGuidance(
        algorithm_family="ChaCha20",
        purpose=PURPOSE_SYMMETRIC_ENCRYPTION,
        quantum_threat=(
            "ChaCha20-Poly1305 is not broken by Shor's algorithm. "
            "Grover's algorithm provides a quadratic speedup, reducing effective security "
            "from 256 bits to ~128 bits — still considered secure for quantum contexts. "
            "No PQC replacement needed."
        ),
        recommended_target_category="Symmetric — already quantum-resistant at current key size",
        recommended_algorithms=("ChaCha20-Poly1305 (retain)", "AES-256-GCM (alternative)"),
        nist_standards=("RFC 8439 (ChaCha20-Poly1305)",),
        effort_estimate="low",
        prerequisites=("Verify 256-bit key is in use.",),
        migration_steps=("1. Confirm current implementation uses 256-bit key.", "2. No migration required unless downgrading to smaller key."),
        testing_requirements=("Confirm key size is 256 bits.", "Nonce uniqueness validation."),
        interoperability_notes=("ChaCha20-Poly1305 is widely supported in TLS 1.3.",),
        validation_checklist=("[ ] 256-bit key confirmed.", "[ ] Nonce reuse prevention confirmed."),
        technical_notes="ChaCha20-Poly1305 is symmetric and quantum-resistant at 256-bit. No PQC migration needed.",
    ),

    # =========================================================================
    # SHA-2 family — Hashing
    # =========================================================================
    MigrationGuidance(
        algorithm_family="SHA-2",
        purpose=PURPOSE_HASHING,
        quantum_threat=(
            "SHA-2 family is not broken by Shor's algorithm (which targets discrete-log/factoring). "
            "Grover's algorithm reduces collision resistance by roughly half. "
            "SHA-256 provides ~128-bit post-quantum collision security (borderline). "
            "SHA-384 and SHA-512 maintain adequate security post-quantum. "
            "Not equivalent to RSA/ECDSA quantum vulnerability."
        ),
        recommended_target_category="Hashing — SHA-384/SHA-512 or SHA-3 for quantum-sensitive contexts",
        recommended_algorithms=(
            "SHA-512 (adequate post-quantum)",
            "SHA-384 (adequate post-quantum)",
            "SHA3-256 / SHA3-512 (alternative, quantum-resistant)",
        ),
        nist_standards=("FIPS 180-4 (SHA-2)", "FIPS 202 (SHA-3)"),
        effort_estimate="low",
        prerequisites=("Identify all SHA-256 usages where collision resistance is critical.",),
        migration_steps=(
            "1. Upgrade SHA-256 to SHA-512 in security-critical hash contexts.",
            "2. For non-critical uses (checksums), SHA-256 may be acceptable.",
            "3. Consider SHA-3 variants for new designs.",
        ),
        testing_requirements=("Hash output size validation.", "Performance impact assessment."),
        interoperability_notes=("SHA-512 and SHA-3 are widely supported.", "SHA-256 still acceptable for signatures if combined with PQC signature algorithm."),
        validation_checklist=("[ ] Critical SHA-256 usages upgraded to SHA-512.", "[ ] New designs use SHA-3 or SHA-512."),
        technical_notes="SHA-2 is NOT equivalent to RSA/ECDSA vulnerability. Do not recommend ML-KEM/ML-DSA for hash functions.",
    ),

    # =========================================================================
    # SHA-3 family — Hashing
    # =========================================================================
    MigrationGuidance(
        algorithm_family="SHA-3",
        purpose=PURPOSE_HASHING,
        quantum_threat=(
            "SHA-3 is not broken by Shor's algorithm. "
            "Grover's algorithm applies but SHA3-256 provides ~128-bit post-quantum security "
            "and SHA3-512 provides ~256-bit — considered adequate. "
            "No migration generally required."
        ),
        recommended_target_category="Hashing — SHA-3 is already quantum-resistant; no migration needed",
        recommended_algorithms=("SHA3-256 (retain)", "SHA3-512 (high-security contexts)"),
        nist_standards=("FIPS 202 (SHA-3)",),
        effort_estimate="low",
        prerequisites=("No migration prerequisites for SHA-3.",),
        migration_steps=("1. No migration required. SHA-3 is already quantum-resistant.",),
        testing_requirements=("Verify SHA-3 variant (256 vs 512) is appropriate for security level.",),
        interoperability_notes=("SHA-3 is NIST-standardized and broadly supported.",),
        validation_checklist=("[ ] SHA-3 variant confirmed appropriate for security level.",),
        technical_notes="SHA-3 is appropriate for post-quantum contexts. No PQC replacement required.",
    ),

    # =========================================================================
    # MD5 — Legacy/Deprecated (classical, not quantum)
    # =========================================================================
    MigrationGuidance(
        algorithm_family="MD5",
        purpose=PURPOSE_HASHING,
        quantum_threat=(
            "MD5 is NOT primarily a quantum concern — it is classically broken. "
            "MD5 collision attacks are feasible with classical computers (2^18 operations for chosen-prefix). "
            "MD5 preimage attacks are not practical but the algorithm is cryptographically deprecated. "
            "This is a CLASSICAL security issue, not a quantum migration priority."
        ),
        recommended_target_category="Classical security remediation — replace with SHA-256 or SHA-3 (not PQC)",
        recommended_algorithms=(
            "SHA-256 (minimum for security uses)",
            "SHA-384 / SHA-512 (preferred for security-critical contexts)",
            "SHA3-256 / SHA3-512 (new designs)",
        ),
        nist_standards=("FIPS 180-4 (SHA-2)", "FIPS 202 (SHA-3)", "NIST SP 800-131A Rev. 2"),
        effort_estimate="low",
        prerequisites=("Inventory all MD5 usage patterns (hashing, HMACs, checksums).",),
        migration_steps=(
            "1. Replace MD5 with SHA-256 or SHA-3 for all security purposes.",
            "2. Non-security uses (file integrity checksums) may use SHA-256 for consistency.",
            "3. Update all HMAC-MD5 to HMAC-SHA-256 or HMAC-SHA-512.",
        ),
        testing_requirements=("Output compatibility tests (hash size changes from 16 to 32 bytes).", "HMAC output size validation."),
        interoperability_notes=("MD5 is still used in legacy protocols — migration requires protocol coordination.",),
        validation_checklist=("[ ] All MD5 hashing replaced with SHA-256+.", "[ ] All HMAC-MD5 replaced with HMAC-SHA-256+."),
        technical_notes=(
            "MD5 is a CLASSICAL security concern — not equivalent to quantum vulnerability of RSA/ECDSA. "
            "Do NOT recommend ML-KEM or ML-DSA as MD5 replacements. "
            "Remediation is SHA-2/SHA-3, not PQC."
        ),
    ),

    # =========================================================================
    # SHA-1 — Legacy/Deprecated (classical)
    # =========================================================================
    MigrationGuidance(
        algorithm_family="SHA-1",
        purpose=PURPOSE_HASHING,
        quantum_threat=(
            "SHA-1 is a CLASSICAL security concern. "
            "SHA-1 collision attacks are practical (SHAttered attack: 2^63 operations). "
            "SHA-1 is deprecated by NIST (SP 800-131A Rev. 2). "
            "This is NOT the same as quantum vulnerability from Shor's algorithm."
        ),
        recommended_target_category="Classical security remediation — replace with SHA-256 or SHA-3",
        recommended_algorithms=(
            "SHA-256 (minimum replacement)",
            "SHA-384 / SHA-512 (preferred)",
            "SHA3-256 / SHA3-512",
        ),
        nist_standards=("NIST SP 800-131A Rev. 2 (SHA-1 deprecated)", "FIPS 180-4 (SHA-2)"),
        effort_estimate="low",
        prerequisites=("Inventory all SHA-1 usage: TLS, certificates, code signing, HMACs.",),
        migration_steps=(
            "1. Replace all SHA-1 with SHA-256 or SHA-3.",
            "2. Update certificate chains using SHA-1 signatures.",
            "3. Update TLS cipher suites to remove SHA-1 PRF.",
        ),
        testing_requirements=("Certificate chain validation after migration.", "SHA-1 removal scan confirmation."),
        interoperability_notes=("Major browsers and systems already reject SHA-1 certificates.",),
        validation_checklist=("[ ] All SHA-1 replaced.", "[ ] SHA-1 certificates revoked/replaced."),
        technical_notes=(
            "SHA-1 is a classical security issue — not a quantum vulnerability. "
            "Do NOT recommend ML-KEM or ML-DSA. "
            "Remediation is SHA-2 or SHA-3 migration."
        ),
    ),

    # =========================================================================
    # ML-KEM, ML-DSA, SLH-DSA, FN-DSA — Post-Quantum (no migration needed)
    # =========================================================================
    MigrationGuidance(
        algorithm_family="ML-KEM",
        purpose=PURPOSE_KEY_ESTABLISHMENT,
        quantum_threat="ML-KEM is a NIST-standardized post-quantum algorithm (FIPS 203). No quantum migration required.",
        recommended_target_category="Already post-quantum (ML-KEM)",
        recommended_algorithms=("ML-KEM in use — no migration needed",),
        nist_standards=("FIPS 203 (ML-KEM)",),
        effort_estimate="low",
        prerequisites=("Confirm parameter set (ML-KEM-512/768/1024) meets security requirements.",),
        migration_steps=("1. Verify correct ML-KEM parameter set for security level.", "2. No further migration required."),
        testing_requirements=("Confirm NIST ACVP test vector compliance.",),
        interoperability_notes=("ML-KEM is NIST-standardized and broadly supported in major libraries.",),
        validation_checklist=("[ ] ML-KEM parameter set appropriate for security level.",),
        technical_notes="Already using NIST PQC standard — no quantum migration needed.",
    ),
    MigrationGuidance(
        algorithm_family="ML-DSA",
        purpose=PURPOSE_DIGITAL_SIGNATURE,
        quantum_threat="ML-DSA is a NIST-standardized post-quantum signature algorithm (FIPS 204). No quantum migration required.",
        recommended_target_category="Already post-quantum (ML-DSA)",
        recommended_algorithms=("ML-DSA in use — no migration needed",),
        nist_standards=("FIPS 204 (ML-DSA)",),
        effort_estimate="low",
        prerequisites=("Confirm ML-DSA parameter set (44/65/87) meets security requirements.",),
        migration_steps=("1. Verify security level.", "2. No further migration required."),
        testing_requirements=("NIST ACVP test vector compliance.",),
        interoperability_notes=("ML-DSA is NIST-standardized.",),
        validation_checklist=("[ ] ML-DSA parameter set confirmed.",),
        technical_notes="Already using NIST PQC standard — no quantum migration needed.",
    ),
    MigrationGuidance(
        algorithm_family="SLH-DSA",
        purpose=PURPOSE_DIGITAL_SIGNATURE,
        quantum_threat="SLH-DSA is a NIST-standardized post-quantum hash-based signature (FIPS 205). No quantum migration required.",
        recommended_target_category="Already post-quantum (SLH-DSA)",
        recommended_algorithms=("SLH-DSA in use — no migration needed",),
        nist_standards=("FIPS 205 (SLH-DSA)",),
        effort_estimate="low",
        prerequisites=(),
        migration_steps=("1. No migration required.",),
        testing_requirements=("NIST ACVP test vector compliance.",),
        interoperability_notes=(),
        validation_checklist=("[ ] SLH-DSA parameter set confirmed appropriate.",),
        technical_notes="Already using NIST PQC standard — no quantum migration needed.",
    ),
    MigrationGuidance(
        algorithm_family="FN-DSA",
        purpose=PURPOSE_DIGITAL_SIGNATURE,
        quantum_threat="FN-DSA (FALCON, FIPS 206) is a NIST-standardized post-quantum signature. No quantum migration required.",
        recommended_target_category="Already post-quantum (FN-DSA/FALCON)",
        recommended_algorithms=("FN-DSA in use — no migration needed",),
        nist_standards=("FIPS 206 (FN-DSA / FALCON)",),
        effort_estimate="low",
        prerequisites=(),
        migration_steps=("1. No migration required.",),
        testing_requirements=("NIST ACVP test vector compliance.",),
        interoperability_notes=(),
        validation_checklist=("[ ] FN-DSA parameter set confirmed appropriate.",),
        technical_notes="Already using NIST PQC standard — no quantum migration needed.",
    ),
]

# ── Index for fast lookup ─────────────────────────────────────────────────────

_INDEX: dict[tuple[str, str], MigrationGuidance] = {
    (entry.algorithm_family, entry.purpose): entry
    for entry in _ENTRIES
}


def lookup(algorithm_family: str, purpose: str) -> MigrationGuidance | None:
    """
    Look up migration guidance for an (algorithm_family, purpose) pair.
    Returns None if no entry exists (caller should mark as manual_review).
    """
    return _INDEX.get((algorithm_family, purpose))


def list_all() -> list[MigrationGuidance]:
    """Return all KB entries (for admin/inspection)."""
    return list(_ENTRIES)
