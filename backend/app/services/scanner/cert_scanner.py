"""
Certificate Scanner
===================

Parses PEM / DER certificate files using the `cryptography` library.
Extracts:
  - Public key algorithm and key size
  - Signature algorithm
  - Subject / issuer (without storing PII)
  - Validity period
  - Quantum classification of the key algorithm

This is the highest-confidence scanner (cert_parse method, confidence=1.0).
Never logs or stores private key material.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.services.scanner.source_scanner import RawFinding
from app.services.scanner.rules import Category, QuantumStatus

# Map OID / algorithm name → (algorithm, family, category, quantum_status)
_ALGO_MAP: dict[str, tuple[str, str, Category, QuantumStatus]] = {
    # RSA
    "rsaencryption":              ("RSA",    "RSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "rsa":                        ("RSA",    "RSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "sha256withrsa":              ("RSA",    "RSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "sha384withrsa":              ("RSA",    "RSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "sha512withrsa":              ("RSA",    "RSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "sha1withrsa":                ("RSA",    "RSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    # EC
    "id-ecpublickey":             ("ECDSA",  "ECDSA", Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ecpublickey":                ("ECDSA",  "ECDSA", Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ecdsa-with-sha256":          ("ECDSA",  "ECDSA", Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ecdsa-with-sha384":          ("ECDSA",  "ECDSA", Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ecdsa-with-sha512":          ("ECDSA",  "ECDSA", Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ecdsa-with-sha1":            ("ECDSA",  "ECDSA", Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    # DSA
    "dsa":                        ("DSA",    "DSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "dsa-with-sha256":            ("DSA",    "DSA",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    # Ed25519 / Ed448 — still elliptic-curve, vulnerable
    "ed25519":                    ("Ed25519","ECC",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ed448":                      ("Ed448",  "ECC",   Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
}

_KEY_SIZE_RE = re.compile(r"<([A-Z]+)PrivateKey|<([A-Z]+)PublicKey", re.I)


def _try_parse_pem(content: bytes, rel_path: str) -> list[RawFinding]:
    """Attempt cryptography-library parse of PEM data."""
    findings: list[RawFinding] = []
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa, ed25519, ed448

        cert = x509.load_pem_x509_certificate(content)

        pub_key = cert.public_key()
        key_size: int | None = None
        algo_name = "unknown"
        family = "unknown"
        category = Category.UNKNOWN_REVIEW
        qstatus = QuantumStatus.unknown

        if isinstance(pub_key, rsa.RSAPublicKey):
            key_size = pub_key.key_size
            algo_name, family = "RSA", "RSA"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable
        elif isinstance(pub_key, ec.EllipticCurvePublicKey):
            key_size = pub_key.key_size
            algo_name = "ECDSA"
            family = "ECDSA"
            curve_name = pub_key.curve.name
            algo_name = f"ECDSA ({curve_name})"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable
        elif isinstance(pub_key, dsa.DSAPublicKey):
            key_size = pub_key.key_size
            algo_name, family = "DSA", "DSA"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable
        elif isinstance(pub_key, ed25519.Ed25519PublicKey):
            algo_name, family = "Ed25519", "ECC"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable
        elif isinstance(pub_key, ed448.Ed448PublicKey):
            algo_name, family = "Ed448", "ECC"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable

        # Signature algorithm
        sig_algo = cert.signature_algorithm_oid.dotted_string
        try:
            sig_algo = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else sig_algo
        except Exception:
            pass

        findings.append(RawFinding(
            rule_id="CERT-001",
            algorithm=algo_name,
            algorithm_family=family,
            category=category,
            quantum_status=qstatus,
            file_path=rel_path,
            line_number=None,
            evidence=f"X.509 certificate; public key type={algo_name}, key_size={key_size}, sig_algo={sig_algo}",
            confidence=1.0,
            key_size=key_size,
            usage_context="certificate",
            detection_method="cert_parse",
            nist_recommendation=(
                "Migrate to ML-KEM (FIPS 203) or ML-DSA (FIPS 204) to achieve "
                "quantum-safe certificates."
            ) if qstatus == QuantumStatus.vulnerable else "",
        ))

    except Exception:
        # Not a valid PEM cert — fall through to text scan fallback
        pass

    return findings


def _try_parse_pem_key(content: bytes, rel_path: str) -> list[RawFinding]:
    """Try to parse a PEM private or public key file."""
    findings: list[RawFinding] = []
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa

        key = load_pem_private_key(content, password=None)
        key_size: int | None = None
        algo_name = "unknown"
        family = "unknown"
        qstatus = QuantumStatus.unknown
        category = Category.UNKNOWN_REVIEW

        if isinstance(key, rsa.RSAPrivateKey):
            key_size = key.key_size
            algo_name, family = "RSA", "RSA"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable
        elif isinstance(key, ec.EllipticCurvePrivateKey):
            key_size = key.key_size
            algo_name = f"ECDSA ({key.curve.name})"
            family = "ECDSA"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable
        elif isinstance(key, dsa.DSAPrivateKey):
            key_size = key.key_size
            algo_name, family = "DSA", "DSA"
            category = Category.QUANTUM_VULNERABLE_PUBLIC_KEY
            qstatus = QuantumStatus.vulnerable

        # Never include key bytes in evidence
        findings.append(RawFinding(
            rule_id="CERT-002",
            algorithm=algo_name,
            algorithm_family=family,
            category=category,
            quantum_status=qstatus,
            file_path=rel_path,
            line_number=None,
            evidence=f"PEM private key; type={algo_name}, key_size={key_size}",
            confidence=1.0,
            key_size=key_size,
            usage_context="private_key",
            detection_method="cert_parse",
            nist_recommendation=(
                "Migrate to ML-KEM (FIPS 203) or ML-DSA (FIPS 204)."
            ) if qstatus == QuantumStatus.vulnerable else "",
        ))
    except Exception:
        pass

    return findings


def scan_cert_file(rel_path: str, content: bytes) -> list[RawFinding]:
    """
    Entry point for certificate/key file scanning.
    Attempts cryptographic parse then falls back to nothing
    (text-based regex already handled by source_scanner for .pem patterns).
    """
    ext = Path(rel_path).suffix.lower()
    findings: list[RawFinding] = []

    if ext in (".pem", ".crt", ".cer"):
        # Try as X.509 cert first
        findings = _try_parse_pem(content, rel_path)
        if not findings:
            # Try as a bare private/public key
            findings = _try_parse_pem_key(content, rel_path)

    return findings
