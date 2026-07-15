"""
PQC Lab router — /api/pqc-lab

Replaces the stub router with real cryptographic endpoints.

Endpoints:
  GET  /api/pqc-lab/capabilities         — supported algorithms, environment, metadata
  POST /api/pqc-lab/kem/demo             — ML-KEM round-trip demonstration
  POST /api/pqc-lab/signature/demo       — ML-DSA sign/verify demonstration
  POST /api/pqc-lab/benchmark            — bounded multi-iteration benchmark

Design:
  - All operations are ephemeral in-memory
  - No private keys or shared secrets are persisted or returned
  - Only fingerprints (SHA-256 prefixes) are returned for cryptographic objects
  - Input validation via Pydantic v2 schemas
  - Invalid algorithm/parameter → 400 Bad Request
  - Library failure → 503 Service Unavailable
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.services.pqc_lab_service import (
    get_capabilities,
    run_kem_demo,
    run_signature_demo,
    run_benchmark,
    KEM_PARAMS,
    SIG_PARAMS,
    _ALLOWED_ITERATIONS,
)

router = APIRouter(prefix="/pqc-lab", tags=["pqc-lab"])


# ── Request schemas ───────────────────────────────────────────────────────────

class KEMDemoRequest(BaseModel):
    param_set: str = Field(default="ML-KEM-768", description="ML-KEM parameter set name")

    @field_validator("param_set")
    @classmethod
    def validate_param_set(cls, v: str) -> str:
        if v not in KEM_PARAMS:
            raise ValueError(
                f"Unsupported ML-KEM parameter set {v!r}. "
                f"Available: {list(KEM_PARAMS.keys())}"
            )
        return v


class SignatureDemoRequest(BaseModel):
    param_set: str = Field(default="ML-DSA-65", description="ML-DSA parameter set name")
    message: str = Field(
        default="QShield PQC Lab — post-quantum signature demonstration.",
        min_length=1,
        max_length=4096,
        description="Message to sign (UTF-8 string, max 4096 chars)",
    )
    tamper_verify: bool = Field(
        default=True,
        description="Also verify signature against a tampered message (expected to fail)",
    )

    @field_validator("param_set")
    @classmethod
    def validate_param_set(cls, v: str) -> str:
        if v not in SIG_PARAMS:
            raise ValueError(
                f"Unsupported ML-DSA parameter set {v!r}. "
                f"Available: {list(SIG_PARAMS.keys())}"
            )
        return v


class BenchmarkRequest(BaseModel):
    param_set: str = Field(description="Algorithm parameter set name (ML-KEM-* or ML-DSA-*)")
    iterations: int = Field(default=10, description=f"Iteration count — must be one of {sorted(_ALLOWED_ITERATIONS)}")

    @field_validator("param_set")
    @classmethod
    def validate_param_set(cls, v: str) -> str:
        all_sets = {**KEM_PARAMS, **SIG_PARAMS}
        if v not in all_sets:
            raise ValueError(
                f"Unknown parameter set {v!r}. "
                f"Available: {list(all_sets.keys())}"
            )
        return v

    @field_validator("iterations")
    @classmethod
    def validate_iterations(cls, v: int) -> int:
        if v not in _ALLOWED_ITERATIONS:
            raise ValueError(
                f"iterations must be one of {sorted(_ALLOWED_ITERATIONS)} to prevent server overload."
            )
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/capabilities",
    summary="PQC Lab — supported algorithms and runtime environment",
)
def pqc_capabilities():
    """
    Returns the complete list of supported PQC algorithms, parameter sets,
    and real runtime/library environment metadata.

    Does NOT perform any cryptographic operation.
    """
    try:
        return get_capabilities()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"PQC Lab unavailable: {exc}",
        )


@router.post(
    "/kem/demo",
    summary="ML-KEM round-trip demonstration (real keypair, encapsulate, decapsulate)",
)
def kem_demo(request: KEMDemoRequest):
    """
    Executes a complete ML-KEM key establishment round-trip:
      1. Generate keypair
      2. Encapsulate (derive + encrypt shared secret)
      3. Decapsulate (recover shared secret)
      4. Verify both shared secrets match

    Returns timings, sizes, and verification result.
    Private key and shared secret are NEVER returned — only fingerprints.
    """
    try:
        return run_kem_demo(request.param_set)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"KEM operation failed: {exc}",
        )


@router.post(
    "/signature/demo",
    summary="ML-DSA sign and verify demonstration (real keypair, real message)",
)
def signature_demo(request: SignatureDemoRequest):
    """
    Executes a complete ML-DSA signature round-trip:
      1. Generate keypair
      2. Sign the provided message
      3. Verify signature against original message (expected: valid)
      4. Optionally verify against tampered message (expected: invalid — correct behavior)

    A tampered-message verification failure is a SUCCESSFUL cryptographic demonstration.
    Private key is NEVER returned.
    """
    try:
        return run_signature_demo(
            param_set=request.param_set,
            message=request.message,
            tamper_verify=request.tamper_verify,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Signature operation failed: {exc}",
        )


@router.post(
    "/benchmark",
    summary="Bounded multi-iteration benchmark (real measured timings)",
)
def benchmark(request: BenchmarkRequest):
    """
    Runs real cryptographic operations over a bounded number of iterations
    and returns min/avg/max timing statistics.

    Iterations must be one of: 5, 10, 25, 50 — no arbitrary values accepted.
    All timings are measured with Python's performance counter.
    Results depend on hardware, operating system, runtime, and current system load.
    """
    try:
        return run_benchmark(
            algorithm=request.param_set,
            param_set=request.param_set,
            iterations=request.iterations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Benchmark failed: {exc}",
        )
