"""
Crypto Detection Rule Registry
==============================

Each Rule describes one cryptographic pattern.  Rules are pure data — no
side-effects.  The scanners consume this registry at import time.

Category taxonomy (keeps quantum migration separate from classical weaknesses):

  QUANTUM_VULNERABLE_PUBLIC_KEY   RSA, DH, ECDSA, ECDH, DSA — broken by Shor's
  SYMMETRIC                       AES, ChaCha20              — Grover halves sec
  HASH                            SHA-2, SHA-3               — Grover halves sec
  LEGACY_DEPRECATED               MD5, SHA-1, DES, RC4, 3DES — broken classically
  POST_QUANTUM                    ML-KEM, ML-DSA, SLH-DSA, FN-DSA — NIST approved
  UNKNOWN_REVIEW                  Unrecognised / needs manual review

Quantum relevance notes:
  - AES-256 is NOT quantum-vulnerable (keyspace still 128-bit post-Grover)
  - SHA-256 is NOT broken; SHA-1/MD5 are CLASSICAL weaknesses only
  - RSA/ECDSA/DH/DSA ARE quantum-vulnerable (Shor's algorithm)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Category(str, Enum):
    QUANTUM_VULNERABLE_PUBLIC_KEY = "QUANTUM_VULNERABLE_PUBLIC_KEY"
    SYMMETRIC                     = "SYMMETRIC"
    HASH                          = "HASH"
    LEGACY_DEPRECATED             = "LEGACY_DEPRECATED"
    POST_QUANTUM                  = "POST_QUANTUM"
    UNKNOWN_REVIEW                = "UNKNOWN_REVIEW"


class QuantumStatus(str, Enum):
    vulnerable  = "vulnerable"   # Shor's breaks it
    safe        = "safe"         # quantum-safe (PQC / large symmetric / SHA-3)
    borderline  = "borderline"   # Grover halves security (AES-128, SHA-256)
    deprecated  = "deprecated"   # Classically broken — separate concern
    unknown     = "unknown"


@dataclass(frozen=True)
class Rule:
    """Immutable rule descriptor."""
    id: str                        # e.g. "RSA-001"
    algorithm: str                 # canonical name, e.g. "RSA"
    algorithm_family: str          # e.g. "RSA"
    category: Category
    quantum_status: QuantumStatus
    base_confidence: float         # 0.0 – 1.0

    # Regex patterns (compiled lazily).  Each is a raw string.
    # Applied to individual source lines.
    patterns: tuple[str, ...] = field(default_factory=tuple)

    # If non-empty, ALL of these must be absent in the line (avoid FP)
    negative_patterns: tuple[str, ...] = field(default_factory=tuple)

    description: str = ""
    legacy_security_note: str = ""   # Set only for LEGACY_DEPRECATED

    # Key-size hints: list of (regex-group-name, multiplier) — optional
    key_size_group: str = ""         # named group in patterns to parse key size

    # File extensions this rule applies to (empty = all text files)
    file_extensions: tuple[str, ...] = field(default_factory=tuple)

    # True if rule also applies to certificate files
    cert_rule: bool = False

    nist_recommendation: str = ""


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

RULES: list[Rule] = [

    # ═══════════════════════════════════════════════════════════════════════
    # RSA
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="RSA-001",
        algorithm="RSA",
        algorithm_family="RSA",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.80,
        patterns=(
            r"(?i)\bRSA\b",
            r"(?i)generateRSAKey|RSAPublicKey|RSAPrivateKey|RSA\.generate|"
            r"rsa\.new_key|load_pem_private_key|load_pem_public_key",
        ),
        negative_patterns=(r"#.*\bRSA\b", r"//.*\bRSA\b", r"\*.*\bRSA\b"),
        description="RSA asymmetric algorithm — broken by Shor's algorithm on quantum computers.",
        nist_recommendation=(
            "Migrate to ML-KEM (FIPS 203) for key encapsulation or "
            "ML-DSA (FIPS 204) for signatures."
        ),
        file_extensions=(".py", ".java", ".js", ".ts", ".cs"),
    ),
    Rule(
        id="RSA-002",
        algorithm="RSA",
        algorithm_family="RSA",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.90,
        patterns=(
            r"(?i)padding\.PKCS1v15|OAEP|PSS\b",
            r"(?i)RSAEncryptionPKCS1|RSASignaturePKCS1",
        ),
        description="RSA padding scheme usage — confirms RSA asymmetric operation.",
        nist_recommendation=(
            "Migrate to ML-KEM (FIPS 203) for key encapsulation or "
            "ML-DSA (FIPS 204) for signatures."
        ),
        file_extensions=(".py", ".java", ".js", ".ts", ".cs"),
    ),
    Rule(
        id="RSA-003",
        algorithm="RSA",
        algorithm_family="RSA",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.95,
        patterns=(r"-----BEGIN RSA (PRIVATE|PUBLIC) KEY-----",),
        description="RSA PEM block detected in source or config.",
        nist_recommendation=(
            "Replace RSA keys with ML-KEM or ML-DSA (NIST FIPS 203/204)."
        ),
        cert_rule=True,
        file_extensions=(".pem", ".crt", ".cer", ".config", ".conf", ".py",
                         ".java", ".js", ".ts", ".cs", ".yaml", ".yml",
                         ".json", ".xml", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # Diffie-Hellman
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="DH-001",
        algorithm="Diffie-Hellman",
        algorithm_family="DH",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.80,
        patterns=(
            r"(?i)\bDiffieHellman\b|\bDHKeyExchange\b|\bDHPublicKey\b|\bDHParameters\b",
            r"(?i)\bdh\.generate_parameters\b|\bDH\.generate\b",
            r"(?i)DiffieHellmanKeyExchange|DiffieHellmanGroup",
        ),
        description="Diffie-Hellman key exchange — vulnerable to Shor's algorithm.",
        nist_recommendation="Replace with ML-KEM (FIPS 203) for key agreement.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
    Rule(
        id="DH-002",
        algorithm="Diffie-Hellman",
        algorithm_family="DH",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.85,
        patterns=(r"(?i)\bDHE\b|\bDHE-RSA\b|\bEDH\b|TLS_DHE_",),
        description="DHE cipher suite — Diffie-Hellman ephemeral key exchange.",
        nist_recommendation="Replace with ML-KEM (FIPS 203) for key agreement.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml",
                         ".properties", ".xml"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # ECC (Elliptic Curve in general — also covers ECDH/ECDSA parents)
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="ECC-001",
        algorithm="ECC",
        algorithm_family="ECC",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.82,
        patterns=(
            r"(?i)\belliptic.{0,10}curve\b",
            r"(?i)\bec\.generate_private_key\b|\bEC_KEY_new_by_curve_name\b",
            r"(?i)\bECPublicKey\b|\bECPrivateKey\b|\bP-256\b|\bP-384\b|\bP-521\b|\bsecp256r1\b|\bsecp384r1\b",
        ),
        description="Elliptic curve cryptography — broken by Shor's algorithm.",
        nist_recommendation=(
            "Migrate to ML-KEM (FIPS 203) for KEX or ML-DSA (FIPS 204) for signatures."
        ),
        file_extensions=(".py", ".java", ".js", ".ts", ".cs"),
    ),
    Rule(
        id="ECC-002",
        algorithm="ECC",
        algorithm_family="ECC",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.95,
        patterns=(r"-----BEGIN EC (PRIVATE|PUBLIC) KEY-----",),
        description="ECC PEM block detected.",
        nist_recommendation="Replace EC keys with ML-KEM or ML-DSA (NIST FIPS 203/204).",
        cert_rule=True,
        file_extensions=(".pem", ".crt", ".cer", ".config", ".conf",
                         ".py", ".java", ".js", ".ts", ".cs",
                         ".yaml", ".yml", ".json", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # ECDSA
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="ECDSA-001",
        algorithm="ECDSA",
        algorithm_family="ECDSA",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.88,
        patterns=(
            r"(?i)\bECDSA\b|\bec\.ECDSA\b|\bECDSA\.sign\b|\bECDSA\.verify\b",
            r"(?i)\bECDSA_sign\b|\bECDSA_verify\b",
        ),
        description="ECDSA digital signature — broken by Shor's algorithm.",
        nist_recommendation="Migrate to ML-DSA (FIPS 204) or SLH-DSA (FIPS 205).",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # ECDH
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="ECDH-001",
        algorithm="ECDH",
        algorithm_family="ECDH",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.88,
        patterns=(
            r"(?i)\bECDH\b|\bECDHE\b|\bephemeral.{0,5}ecdh\b",
            r"(?i)\bECDH\.generate\b|\bECDHKeyAgreement\b",
        ),
        description="ECDH key agreement — broken by Shor's algorithm.",
        nist_recommendation="Migrate to ML-KEM (FIPS 203) for key agreement.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # DSA
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="DSA-001",
        algorithm="DSA",
        algorithm_family="DSA",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.85,
        patterns=(
            r"(?i)\bDSA\b(?![\w-])",          # DSA not followed by more word chars (avoids ECDSA match)
            r"(?i)\bdsa\.generate_private_key\b|\bDSAPublicKey\b|\bDSAPrivateKey\b",
        ),
        negative_patterns=(r"(?i)\bECDSA\b|\bML-DSA\b|\bFN-DSA\b|\bSLH-DSA\b",),
        description="DSA digital signature algorithm — broken by Shor's algorithm.",
        nist_recommendation="Migrate to ML-DSA (FIPS 204).",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # AES
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="AES-001",
        algorithm="AES",
        algorithm_family="AES",
        category=Category.SYMMETRIC,
        quantum_status=QuantumStatus.safe,   # AES-256 is post-quantum safe
        base_confidence=0.80,
        patterns=(
            r"(?i)\bAES\b|\bAES-(?:128|192|256)\b|\bAES_(?:128|192|256)\b",
            r"(?i)\bAES\.new\b|\bAesCipher\b|\bAesCryptoServiceProvider\b",
            r"(?i)\bCipher\.getInstance\s*\(\s*[\"']AES",
        ),
        description="AES symmetric cipher. AES-256 is quantum-safe; AES-128 has borderline post-quantum security.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml",
                         ".json", ".properties", ".xml"),
    ),
    Rule(
        id="AES-002",
        algorithm="AES-GCM",
        algorithm_family="AES",
        category=Category.SYMMETRIC,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.90,
        patterns=(
            r"(?i)\bAES.{0,5}GCM\b|\bGCM\b(?=.*AES)",
            r"(?i)\bAEAD\b|\bGCMBlockCipher\b",
        ),
        description="AES-GCM authenticated encryption — quantum-safe for 256-bit keys.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # ChaCha20
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="CHACHA-001",
        algorithm="ChaCha20-Poly1305",
        algorithm_family="ChaCha20",
        category=Category.SYMMETRIC,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.90,
        patterns=(
            r"(?i)\bChaCha20\b|\bchachacha\b",
            r"(?i)\bPoly1305\b",
            r"(?i)\bChaCha20Poly1305\b|\bXChaCha20\b",
        ),
        description="ChaCha20-Poly1305 stream cipher/AEAD — quantum-safe at 256-bit key.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # SHA-2 / SHA-3 family
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="HASH-001",
        algorithm="SHA-256",
        algorithm_family="SHA-2",
        category=Category.HASH,
        quantum_status=QuantumStatus.borderline,   # Grover: effective 128-bit
        base_confidence=0.82,
        patterns=(
            r"(?i)\bSHA.?256\b|\bSHA2.?256\b",
            r"(?i)hashlib\.sha256\b|MessageDigest\.getInstance\s*\([\"']SHA-256",
            r"(?i)CryptoJS\.SHA256\b",
        ),
        description="SHA-256 hash. Still safe for most uses; Grover's algorithm reduces effective security to ~128 bits.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
    Rule(
        id="HASH-002",
        algorithm="SHA-384",
        algorithm_family="SHA-2",
        category=Category.HASH,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.82,
        patterns=(
            r"(?i)\bSHA.?384\b|\bSHA2.?384\b",
            r"(?i)hashlib\.sha384\b|MessageDigest\.getInstance\s*\([\"']SHA-384",
        ),
        description="SHA-384 hash — quantum-safe.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
    Rule(
        id="HASH-003",
        algorithm="SHA-512",
        algorithm_family="SHA-2",
        category=Category.HASH,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.82,
        patterns=(
            r"(?i)\bSHA.?512\b|\bSHA2.?512\b",
            r"(?i)hashlib\.sha512\b|MessageDigest\.getInstance\s*\([\"']SHA-512",
        ),
        description="SHA-512 hash — quantum-safe.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
    Rule(
        id="HASH-004",
        algorithm="SHA-3",
        algorithm_family="SHA-3",
        category=Category.HASH,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.85,
        patterns=(
            r"(?i)\bSHA.?3.{0,5}(?:256|384|512)\b|\bSHA3\b",
            r"(?i)hashlib\.sha3_\d+\b",
            r"(?i)\bShake128\b|\bShake256\b|\bKeccak\b",
        ),
        description="SHA-3 / Keccak family — quantum-safe.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # LEGACY — SHA-1 (classical weakness, NOT quantum issue)
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="LEGACY-001",
        algorithm="SHA-1",
        algorithm_family="SHA-1",
        category=Category.LEGACY_DEPRECATED,
        quantum_status=QuantumStatus.deprecated,
        base_confidence=0.85,
        patterns=(
            r"(?i)\bSHA1\b|\bSHA-1\b",
            r"(?i)hashlib\.sha1\b|MessageDigest\.getInstance\s*\([\"']SHA-?1[\"']",
            r"(?i)CryptoJS\.SHA1\b|System\.Security\.Cryptography\.SHA1\b",
        ),
        description=(
            "SHA-1 cryptographic hash — classically broken (collision attacks). "
            "NOT a quantum-specific concern; retire immediately regardless."
        ),
        legacy_security_note=(
            "SHA-1 has been demonstrated to be collision-vulnerable (SHAttered 2017). "
            "Replace with SHA-256 or SHA-3 urgently."
        ),
        nist_recommendation="SHA-1 is deprecated per NIST SP 800-131A. Use SHA-256/SHA-3.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml",
                         ".properties", ".xml"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # LEGACY — MD5
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="LEGACY-002",
        algorithm="MD5",
        algorithm_family="MD5",
        category=Category.LEGACY_DEPRECATED,
        quantum_status=QuantumStatus.deprecated,
        base_confidence=0.88,
        patterns=(
            r"(?i)\bmd5\b",
            r"(?i)hashlib\.md5\b|MessageDigest\.getInstance\s*\([\"']MD5",
            r"(?i)CryptoJS\.MD5\b|System\.Security\.Cryptography\.MD5\b",
            r"(?i)MD5Digest\b|MD5Cng\b",
        ),
        description=(
            "MD5 cryptographic hash — classically broken (collision + preimage). "
            "This is a classical security failure, not a quantum-specific concern."
        ),
        legacy_security_note=(
            "MD5 collisions are trivially computable. Replace with SHA-256 or SHA-3. "
            "Never use for signatures, certificates, or passwords."
        ),
        nist_recommendation="MD5 is disallowed per NIST SP 800-131A. Replace immediately.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml",
                         ".properties", ".xml", ".json"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # LEGACY — DES / 3DES
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="LEGACY-003",
        algorithm="DES",
        algorithm_family="DES",
        category=Category.LEGACY_DEPRECATED,
        quantum_status=QuantumStatus.deprecated,
        base_confidence=0.87,
        patterns=(
            r"(?i)\bDES\b(?!K)|\b3DES\b|\bTripleDES\b|\bDESede\b",
            r"(?i)Cipher\.getInstance\s*\([\"']DES",
            r"(?i)TripleDESCryptoServiceProvider\b|DESCryptoServiceProvider\b",
        ),
        negative_patterns=(r"(?i)\bDEScription\b|\bDESkriptor\b",),
        description=(
            "DES/3DES — broken by classical attacks (56-bit key). "
            "Classical weakness, not a quantum concern."
        ),
        legacy_security_note="Replace with AES-256 immediately.",
        nist_recommendation="DES/3DES deprecated per NIST SP 800-67r2. Use AES-256.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml",
                         ".properties", ".xml"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # LEGACY — RC4
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="LEGACY-004",
        algorithm="RC4",
        algorithm_family="RC4",
        category=Category.LEGACY_DEPRECATED,
        quantum_status=QuantumStatus.deprecated,
        base_confidence=0.90,
        patterns=(
            r"(?i)\bRC4\b|\bARC4\b|\bARCFOUR\b",
            r"(?i)Cipher\.getInstance\s*\([\"']RC4",
        ),
        description="RC4 stream cipher — broken by classical attacks. Do not use.",
        legacy_security_note="RC4 is prohibited in TLS (RFC 7465). Replace with AES-GCM or ChaCha20-Poly1305.",
        nist_recommendation="RC4 is deprecated. Use AES-256-GCM or ChaCha20-Poly1305.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # POST-QUANTUM (NIST FIPS 203/204/205 approved)
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="PQC-001",
        algorithm="ML-KEM",
        algorithm_family="ML-KEM",
        category=Category.POST_QUANTUM,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.90,
        patterns=(
            r"(?i)\bML.KEM\b|\bKyber\b|\bKyber512\b|\bKyber768\b|\bKyber1024\b",
            r"(?i)\bKEMKeyPairGenerator\b|\bKyberKEM\b",
        ),
        description="ML-KEM (CRYSTALS-Kyber) — NIST FIPS 203 approved KEM. Quantum-safe.",
        nist_recommendation="Already using NIST-approved PQC. Continue.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
    Rule(
        id="PQC-002",
        algorithm="ML-DSA",
        algorithm_family="ML-DSA",
        category=Category.POST_QUANTUM,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.90,
        patterns=(
            r"(?i)\bML.DSA\b|\bDilithium\b|\bDilithium2\b|\bDilithium3\b|\bDilithium5\b",
            r"(?i)\bDSAKeyPairGenerator\b(?=.*Dilithium)",
        ),
        description="ML-DSA (CRYSTALS-Dilithium) — NIST FIPS 204 approved signature. Quantum-safe.",
        nist_recommendation="Already using NIST-approved PQC. Continue.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
    Rule(
        id="PQC-003",
        algorithm="SLH-DSA",
        algorithm_family="SLH-DSA",
        category=Category.POST_QUANTUM,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.90,
        patterns=(
            r"(?i)\bSLH.DSA\b|\bSPHINCS\b|\bSPHINCSPlus\b|\bSPHINCS\+\b",
            r"(?i)SPHINCS_plus|sphincs.plus|sphincsplus",
        ),
        description="SLH-DSA (SPHINCS+) — NIST FIPS 205 approved signature. Quantum-safe.",
        nist_recommendation="Already using NIST-approved PQC. Continue.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
    Rule(
        id="PQC-004",
        algorithm="FN-DSA",
        algorithm_family="FN-DSA",
        category=Category.POST_QUANTUM,
        quantum_status=QuantumStatus.safe,
        base_confidence=0.90,
        patterns=(
            r"(?i)\bFN.DSA\b|\bFalcon\b(?=.{0,30}(?:sign|key|pqc|post.quantum))",
        ),
        description="FN-DSA (FALCON) — NIST FIPS 206 approved signature. Quantum-safe.",
        nist_recommendation="Already using NIST-approved PQC. Continue.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # TLS / Cipher suite patterns (config files + source)
    # ═══════════════════════════════════════════════════════════════════════
    Rule(
        id="TLS-001",
        algorithm="TLS-cipher-suite",
        algorithm_family="TLS",
        category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=QuantumStatus.vulnerable,
        base_confidence=0.75,
        patterns=(
            r"(?i)TLS_(?:ECDHE|DHE|RSA)(?:_[A-Z0-9]+)?_WITH_",
            r"(?i)\bRSA_WITH_AES\b|\bECDHE_RSA\b|\bECDHE_ECDSA\b",
            r"(?i)ECDHE-RSA-|ECDHE-ECDSA-|DHE-RSA-",
        ),
        description="TLS cipher suite using quantum-vulnerable key exchange (RSA/ECDHE/DHE).",
        nist_recommendation=(
            "Transition to TLS 1.3 with ML-KEM hybrid key exchange "
            "(see IETF draft-ietf-tls-hybrid-design)."
        ),
        file_extensions=(".conf", ".config", ".yaml", ".yml",
                         ".properties", ".xml", ".json",
                         ".py", ".java", ".js", ".ts", ".cs"),
    ),
    Rule(
        id="TLS-002",
        algorithm="TLS-weak",
        algorithm_family="TLS",
        category=Category.LEGACY_DEPRECATED,
        quantum_status=QuantumStatus.deprecated,
        base_confidence=0.85,
        patterns=(
            r"(?i)\bTLSv1\.0\b|\bTLSv1\.1\b|\bSSLv2\b|\bSSLv3\b",
            r"(?i)ssl_version\s*=\s*[\"']?(TLSv1|SSLv[23])",
            r"(?i)PROTOCOL_TLSv1(?!_2|_3)\b",
        ),
        description="Weak/deprecated TLS version (TLS 1.0/1.1 or SSL).",
        legacy_security_note="TLS 1.0/1.1 deprecated per RFC 8996. Upgrade to TLS 1.3.",
        nist_recommendation="NIST SP 800-52r2 requires TLS 1.2 minimum; TLS 1.3 recommended.",
        file_extensions=(".py", ".java", ".js", ".ts", ".cs",
                         ".conf", ".config", ".yaml", ".yml", ".properties"),
    ),
]


# ---------------------------------------------------------------------------
# Compiled pattern cache (built once at import time)
# ---------------------------------------------------------------------------

@dataclass
class CompiledRule:
    rule: Rule
    compiled_patterns: list[re.Pattern]
    compiled_negative: list[re.Pattern]


def _compile_rules() -> list[CompiledRule]:
    compiled = []
    for r in RULES:
        pos = [re.compile(p) for p in r.patterns]
        neg = [re.compile(p) for p in r.negative_patterns]
        compiled.append(CompiledRule(rule=r, compiled_patterns=pos, compiled_negative=neg))
    return compiled


COMPILED_RULES: list[CompiledRule] = _compile_rules()


def get_rules_for_extension(ext: str) -> list[CompiledRule]:
    """Return all compiled rules applicable to the given file extension."""
    ext = ext.lower()
    return [
        cr for cr in COMPILED_RULES
        if not cr.rule.file_extensions or ext in cr.rule.file_extensions
    ]
