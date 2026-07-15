"""
QShield PQC Lab Service
========================

Executes REAL post-quantum cryptographic operations using the cryptography
package (PyCA) backed by OpenSSL 3.x.

Supported algorithms (verified against cryptography 49.0.0):

  ML-KEM-768  (FIPS 203, key establishment, KEM)
  ML-KEM-1024 (FIPS 203, key establishment, KEM)
  ML-DSA-44   (FIPS 204, digital signatures)
  ML-DSA-65   (FIPS 204, digital signatures)
  ML-DSA-87   (FIPS 204, digital signatures)

SLH-DSA (FIPS 205) is NOT available in the current cryptography build on this platform.

CRITICAL API NOTE — ML-KEM encapsulate() return order:
  pub.encapsulate() returns (shared_secret: bytes, ciphertext: bytes)
  The shared_secret is the first element (32 bytes).
  The ciphertext is the second element (varies by parameter set).

SECURITY NOTE:
  - Private keys and shared secrets are NEVER returned to the caller.
  - Only fingerprints (first 8 hex chars of SHA-256) are returned.
  - No sensitive material is logged.
  - All operations are ephemeral in-memory only.
"""
from __future__ import annotations

import hashlib
import platform
import sys
import time
from dataclasses import dataclass, field
from typing import Sequence

import cryptography

# ── ML-KEM (FIPS 203) ────────────────────────────────────────────────────────
from cryptography.hazmat.primitives.asymmetric.mlkem import (
    MLKEM768PrivateKey,
    MLKEM1024PrivateKey,
)

# ── ML-DSA (FIPS 204) ────────────────────────────────────────────────────────
from cryptography.hazmat.primitives.asymmetric.mldsa import (
    MLDSA44PrivateKey,
    MLDSA65PrivateKey,
    MLDSA87PrivateKey,
)

# ── SLH-DSA not available in this build ──────────────────────────────────────
SLHDSA_AVAILABLE = False

# ── Parameter set registry ────────────────────────────────────────────────────

@dataclass(frozen=True)
class KEMParamSet:
    name: str           # e.g. "ML-KEM-768"
    std_category: str   # "ML-KEM"
    standard: str       # "FIPS 203"
    security_level: str  # NIST security level label
    pub_key_bytes: int
    priv_key_bytes: int
    ciphertext_bytes: int
    shared_secret_bytes: int


@dataclass(frozen=True)
class SigParamSet:
    name: str
    std_category: str
    standard: str
    security_level: str
    pub_key_bytes: int
    priv_key_bytes: int
    max_sig_bytes: int


KEM_PARAMS: dict[str, KEMParamSet] = {
    "ML-KEM-768": KEMParamSet(
        name="ML-KEM-768",
        std_category="ML-KEM",
        standard="FIPS 203",
        security_level="Level 3 (AES-192 equivalent)",
        pub_key_bytes=1184,
        priv_key_bytes=2400,
        ciphertext_bytes=1088,
        shared_secret_bytes=32,
    ),
    "ML-KEM-1024": KEMParamSet(
        name="ML-KEM-1024",
        std_category="ML-KEM",
        standard="FIPS 203",
        security_level="Level 5 (AES-256 equivalent)",
        pub_key_bytes=1568,
        priv_key_bytes=3168,
        ciphertext_bytes=1568,
        shared_secret_bytes=32,
    ),
}

SIG_PARAMS: dict[str, SigParamSet] = {
    "ML-DSA-44": SigParamSet(
        name="ML-DSA-44",
        std_category="ML-DSA",
        standard="FIPS 204",
        security_level="Level 2 (AES-128 equivalent)",
        pub_key_bytes=1312,
        priv_key_bytes=2528,
        max_sig_bytes=2420,
    ),
    "ML-DSA-65": SigParamSet(
        name="ML-DSA-65",
        std_category="ML-DSA",
        standard="FIPS 204",
        security_level="Level 3 (AES-192 equivalent)",
        pub_key_bytes=1952,
        priv_key_bytes=4032,
        max_sig_bytes=3309,
    ),
    "ML-DSA-87": SigParamSet(
        name="ML-DSA-87",
        std_category="ML-DSA",
        standard="FIPS 204",
        security_level="Level 5 (AES-256 equivalent)",
        pub_key_bytes=2592,
        priv_key_bytes=4896,
        max_sig_bytes=4627,
    ),
}


def _fingerprint(data: bytes) -> str:
    """Return first 8 hex chars of SHA-256 — never the raw secret."""
    return hashlib.sha256(data).hexdigest()[:16]


def _ms(t: float) -> float:
    """Round perf_counter seconds to milliseconds, 3dp."""
    return round(t * 1000, 3)


# ── Environment metadata ──────────────────────────────────────────────────────

def get_environment() -> dict:
    return {
        "library": "cryptography (PyCA / pyOpenSSL)",
        "library_version": cryptography.__version__,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "platform_system": platform.system(),
        "openssl_backend": True,  # cryptography uses OpenSSL backend
        "slhdsa_available": SLHDSA_AVAILABLE,
    }


# ── Capabilities ──────────────────────────────────────────────────────────────

def get_capabilities() -> dict:
    kem_caps = [
        {
            "name": p.name,
            "std_category": p.std_category,
            "standard": p.standard,
            "security_level": p.security_level,
            "purpose": "Key Establishment / Key Encapsulation Mechanism",
            "operations": ["key_generation", "encapsulation", "decapsulation"],
            "pub_key_bytes": p.pub_key_bytes,
            "ciphertext_bytes": p.ciphertext_bytes,
            "shared_secret_bytes": p.shared_secret_bytes,
        }
        for p in KEM_PARAMS.values()
    ]
    sig_caps = [
        {
            "name": p.name,
            "std_category": p.std_category,
            "standard": p.standard,
            "security_level": p.security_level,
            "purpose": "Digital Signatures",
            "operations": ["key_generation", "signing", "verification"],
            "pub_key_bytes": p.pub_key_bytes,
            "max_sig_bytes": p.max_sig_bytes,
        }
        for p in SIG_PARAMS.values()
    ]
    return {
        "environment": get_environment(),
        "kem": kem_caps,
        "signature": sig_caps,
        "slhdsa": {
            "available": False,
            "reason": "SLH-DSA (FIPS 205) is not exposed by the current cryptography build on this platform.",
        },
        "disclaimer": (
            "This implementation uses the PyCA cryptography library backed by OpenSSL. "
            "The PQC Lab is a demonstration and evaluation environment. "
            "Running a demonstration does not automatically migrate a production application."
        ),
    }


# ── Private key factory ───────────────────────────────────────────────────────

_KEM_KEY_FACTORIES = {
    "ML-KEM-768":  MLKEM768PrivateKey.generate,
    "ML-KEM-1024": MLKEM1024PrivateKey.generate,
}

_SIG_KEY_FACTORIES = {
    "ML-DSA-44": MLDSA44PrivateKey.generate,
    "ML-DSA-65": MLDSA65PrivateKey.generate,
    "ML-DSA-87": MLDSA87PrivateKey.generate,
}


# ── KEM demonstration ─────────────────────────────────────────────────────────

def run_kem_demo(param_set: str) -> dict:
    """
    Execute a complete ML-KEM round-trip:
      1. Generate keypair
      2. Encapsulate (sender side)
      3. Decapsulate (recipient side)
      4. Verify shared-secret equality

    Returns timings, sizes, and verification result.
    NEVER returns private key or shared secret.

    NOTE: cryptography.encapsulate() returns (shared_secret, ciphertext).
    """
    if param_set not in _KEM_KEY_FACTORIES:
        raise ValueError(f"Unsupported ML-KEM parameter set: {param_set!r}")

    factory = _KEM_KEY_FACTORIES[param_set]
    params = KEM_PARAMS[param_set]

    # --- Step 1: Key generation ---
    t0 = time.perf_counter()
    priv_key = factory()
    t_keygen = _ms(time.perf_counter() - t0)
    pub_key = priv_key.public_key()

    pub_bytes = pub_key.public_bytes_raw()
    priv_bytes = priv_key.private_bytes_raw()

    # --- Step 2: Encapsulate (sender) ---
    # Returns (shared_secret, ciphertext) per cryptography 49 API
    t0 = time.perf_counter()
    ss_enc, ciphertext = pub_key.encapsulate()
    t_encap = _ms(time.perf_counter() - t0)

    # --- Step 3: Decapsulate (recipient) ---
    t0 = time.perf_counter()
    ss_dec = priv_key.decapsulate(ciphertext)
    t_decap = _ms(time.perf_counter() - t0)

    # --- Step 4: Verify ---
    secrets_match = ss_enc == ss_dec

    return {
        "param_set": param_set,
        "std_category": "ML-KEM",
        "standard": "FIPS 203",
        "security_level": params.security_level,
        "success": secrets_match,
        "verification_message": (
            "Encapsulated and decapsulated shared secrets matched — key establishment successful."
            if secrets_match else
            "UNEXPECTED: shared secrets did not match."
        ),
        "timings_ms": {
            "key_generation": t_keygen,
            "encapsulation": t_encap,
            "decapsulation": t_decap,
        },
        "sizes_bytes": {
            "public_key": len(pub_bytes),
            "private_key": len(priv_bytes),   # length only — bytes NOT returned
            "ciphertext": len(ciphertext),
            "shared_secret": len(ss_enc),
        },
        "fingerprints": {
            "public_key": _fingerprint(pub_bytes),
            "shared_secret": _fingerprint(ss_enc),  # fingerprint, NOT the secret
        },
        "private_key_exposed": False,
        "shared_secret_exposed": False,
        "note": "Private key and shared secret are ephemeral and not returned. Fingerprints are SHA-256 prefixes only.",
        "environment": get_environment(),
    }


# ── Signature demonstration ───────────────────────────────────────────────────

def run_signature_demo(param_set: str, message: str, tamper_verify: bool = False) -> dict:
    """
    Execute a complete ML-DSA signature round-trip:
      1. Generate keypair
      2. Sign message
      3. Verify signature against original message
      4. Optionally verify against tampered message (expected to fail)

    A tampered-message verification failure is a SUCCESSFUL cryptographic result.
    """
    if param_set not in _SIG_KEY_FACTORIES:
        raise ValueError(f"Unsupported ML-DSA parameter set: {param_set!r}")
    if not message or not message.strip():
        raise ValueError("Message must not be empty.")
    if len(message) > 4096:
        raise ValueError("Message too long (max 4096 chars).")

    factory = _SIG_KEY_FACTORIES[param_set]
    params = SIG_PARAMS[param_set]
    msg_bytes = message.encode("utf-8")

    # --- Step 1: Key generation ---
    t0 = time.perf_counter()
    signing_key = factory()
    t_keygen = _ms(time.perf_counter() - t0)
    verify_key = signing_key.public_key()

    pub_bytes = verify_key.public_bytes_raw()
    priv_bytes = signing_key.private_bytes_raw()

    # --- Step 2: Sign ---
    t0 = time.perf_counter()
    signature = signing_key.sign(msg_bytes)
    t_sign = _ms(time.perf_counter() - t0)

    # --- Step 3: Verify original ---
    t0 = time.perf_counter()
    try:
        verify_key.verify(signature, msg_bytes)
        original_valid = True
        original_error = None
    except Exception as e:
        original_valid = False
        original_error = str(e)
    t_verify = _ms(time.perf_counter() - t0)

    result = {
        "param_set": param_set,
        "std_category": "ML-DSA",
        "standard": "FIPS 204",
        "security_level": params.security_level,
        "message_length_bytes": len(msg_bytes),
        "original_verification": {
            "valid": original_valid,
            "message": (
                "Signature verified — original message authenticated."
                if original_valid else f"Unexpected verification failure: {original_error}"
            ),
        },
        "timings_ms": {
            "key_generation": t_keygen,
            "signing": t_sign,
            "verification": t_verify,
        },
        "sizes_bytes": {
            "public_key": len(pub_bytes),
            "private_key": len(priv_bytes),   # length only
            "signature": len(signature),
        },
        "fingerprints": {
            "public_key": _fingerprint(pub_bytes),
            "signature": _fingerprint(signature),
        },
        "private_key_exposed": False,
        "environment": get_environment(),
    }

    # --- Step 4: Optional tamper test ---
    if tamper_verify:
        tampered_msg = (message + " [tampered]").encode("utf-8")
        t0 = time.perf_counter()
        try:
            verify_key.verify(signature, tampered_msg)
            tamper_valid = True
            tamper_msg_str = "UNEXPECTED: tampered message verified — this should not happen."
        except Exception:
            tamper_valid = False
            tamper_msg_str = (
                "Signature rejected for modified message — "
                "signature integrity demonstrated correctly."
            )
        t_tamper = _ms(time.perf_counter() - t0)

        result["tamper_verification"] = {
            "valid": tamper_valid,
            "message": tamper_msg_str,
            "timing_ms": t_tamper,
            "is_expected_failure": not tamper_valid,
        }

    return result


# ── Benchmark ─────────────────────────────────────────────────────────────────

_ALLOWED_ITERATIONS = {5, 10, 25, 50}
_DEFAULT_SIG_MSG = b"QShield PQC benchmark message"


def run_benchmark(algorithm: str, param_set: str, iterations: int) -> dict:
    """
    Run multiple iterations of PQC operations and return min/avg/max timings.
    All iteration counts must be in the allowed set to prevent abuse.
    """
    if iterations not in _ALLOWED_ITERATIONS:
        raise ValueError(f"iterations must be one of {sorted(_ALLOWED_ITERATIONS)}")

    category = None
    if param_set in KEM_PARAMS:
        category = "kem"
    elif param_set in SIG_PARAMS:
        category = "signature"
    else:
        raise ValueError(f"Unknown parameter set: {param_set!r}")

    results: dict[str, list[float]] = {
        "key_generation": [],
    }

    if category == "kem":
        results["encapsulation"] = []
        results["decapsulation"] = []
        factory = _KEM_KEY_FACTORIES[param_set]
        for _ in range(iterations):
            t0 = time.perf_counter()
            pk = factory()
            results["key_generation"].append(time.perf_counter() - t0)
            pub = pk.public_key()
            t0 = time.perf_counter()
            ss, ct = pub.encapsulate()
            results["encapsulation"].append(time.perf_counter() - t0)
            t0 = time.perf_counter()
            pk.decapsulate(ct)
            results["decapsulation"].append(time.perf_counter() - t0)
        sizes = {
            "public_key_bytes": KEM_PARAMS[param_set].pub_key_bytes,
            "ciphertext_bytes": KEM_PARAMS[param_set].ciphertext_bytes,
            "shared_secret_bytes": KEM_PARAMS[param_set].shared_secret_bytes,
        }
    else:
        results["signing"] = []
        results["verification"] = []
        factory = _SIG_KEY_FACTORIES[param_set]
        for _ in range(iterations):
            t0 = time.perf_counter()
            sk = factory()
            results["key_generation"].append(time.perf_counter() - t0)
            vk = sk.public_key()
            t0 = time.perf_counter()
            sig = sk.sign(_DEFAULT_SIG_MSG)
            results["signing"].append(time.perf_counter() - t0)
            t0 = time.perf_counter()
            vk.verify(sig, _DEFAULT_SIG_MSG)
            results["verification"].append(time.perf_counter() - t0)
        sizes = {
            "public_key_bytes": SIG_PARAMS[param_set].pub_key_bytes,
            "max_sig_bytes": SIG_PARAMS[param_set].max_sig_bytes,
        }

    def _stats(vals: list[float]) -> dict:
        return {
            "avg_ms": round(sum(vals) / len(vals) * 1000, 3),
            "min_ms": round(min(vals) * 1000, 3),
            "max_ms": round(max(vals) * 1000, 3),
        }

    return {
        "param_set": param_set,
        "std_category": ("ML-KEM" if category == "kem" else "ML-DSA"),
        "category": category,
        "iterations": iterations,
        "statistics": {op: _stats(vals) for op, vals in results.items()},
        "sizes_bytes": sizes,
        "environment": get_environment(),
        "disclaimer": (
            "Performance measurements depend on hardware, operating system, runtime, "
            "implementation, system load, and benchmark methodology. "
            "These results reflect a single local run and should not be treated as "
            "universal algorithm performance data."
        ),
    }
