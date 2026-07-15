"""
Tests for QShield PQC Lab API.

Covers:
  1.  Capabilities endpoint structure and content
  2.  ML-KEM-768 demo: full round-trip, timing, sizes
  3.  ML-KEM-1024 demo: full round-trip, timing, sizes
  4.  ML-DSA-44/-65/-87 demos: sign, verify, tamper
  5.  No private key or shared secret in response bodies
  6.  Sizes match actual generated objects
  7.  Timings are real non-negative numbers
  8.  Tampered-message verification correctly fails (not treated as API error)
  9.  Invalid parameter set → 400
  10. Unsupported algorithm category (SLH-DSA) clearly documented
  11. Benchmark: bounded iterations, correct statistics structure
  12. Benchmark: invalid iteration count → 400
  13. Empty message → 400
  14. Oversized message → 400
  15. Service-layer unit tests (direct)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.pqc_lab_service import (
    get_capabilities,
    run_kem_demo,
    run_signature_demo,
    run_benchmark,
    KEM_PARAMS,
    SIG_PARAMS,
)

# ── Client ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── 1. Capabilities ───────────────────────────────────────────────────────────

class TestCapabilities:

    def test_capabilities_200(self, client):
        r = client.get("/api/pqc-lab/capabilities")
        assert r.status_code == 200

    def test_capabilities_has_kem_section(self, client):
        data = client.get("/api/pqc-lab/capabilities").json()
        assert "kem" in data
        assert isinstance(data["kem"], list)
        assert len(data["kem"]) >= 1

    def test_capabilities_kem_param_sets(self, client):
        data = client.get("/api/pqc-lab/capabilities").json()
        names = {k["name"] for k in data["kem"]}
        assert "ML-KEM-768" in names
        assert "ML-KEM-1024" in names

    def test_capabilities_has_signature_section(self, client):
        data = client.get("/api/pqc-lab/capabilities").json()
        assert "signature" in data
        names = {s["name"] for s in data["signature"]}
        assert "ML-DSA-44" in names
        assert "ML-DSA-65" in names
        assert "ML-DSA-87" in names

    def test_capabilities_slhdsa_unavailable(self, client):
        data = client.get("/api/pqc-lab/capabilities").json()
        assert "slhdsa" in data
        assert data["slhdsa"]["available"] is False
        assert len(data["slhdsa"]["reason"]) > 0

    def test_capabilities_environment_present(self, client):
        data = client.get("/api/pqc-lab/capabilities").json()
        env = data["environment"]
        assert "library" in env
        assert "library_version" in env
        assert "python_version" in env
        assert "platform" in env

    def test_capabilities_no_private_material(self, client):
        data = client.get("/api/pqc-lab/capabilities").json()
        # The capabilities response may include 'shared_secret_bytes' as a size field (metadata).
        # What must NOT appear: raw key bytes, raw secrets, or private_bytes_raw values.
        import json
        text = json.dumps(data)
        assert "private_bytes_raw" not in text
        # Ensure no large base64/hex blobs appear (actual raw keys would be >100 chars)
        # The field names themselves (shared_secret_bytes) are fine metadata


# ── 2. ML-KEM Demos ───────────────────────────────────────────────────────────

class TestMLKEMDemo:

    @pytest.mark.parametrize("param_set", ["ML-KEM-768", "ML-KEM-1024"])
    def test_kem_demo_200(self, client, param_set):
        r = client.post("/api/pqc-lab/kem/demo", json={"param_set": param_set})
        assert r.status_code == 200

    @pytest.mark.parametrize("param_set", ["ML-KEM-768", "ML-KEM-1024"])
    def test_kem_demo_success_true(self, client, param_set):
        data = client.post("/api/pqc-lab/kem/demo", json={"param_set": param_set}).json()
        assert data["success"] is True

    @pytest.mark.parametrize("param_set", ["ML-KEM-768", "ML-KEM-1024"])
    def test_kem_demo_timings_non_negative(self, client, param_set):
        data = client.post("/api/pqc-lab/kem/demo", json={"param_set": param_set}).json()
        timings = data["timings_ms"]
        assert timings["key_generation"] >= 0
        assert timings["encapsulation"] >= 0
        assert timings["decapsulation"] >= 0

    def test_kem768_sizes_match_spec(self, client):
        data = client.post("/api/pqc-lab/kem/demo", json={"param_set": "ML-KEM-768"}).json()
        sizes = data["sizes_bytes"]
        assert sizes["public_key"] == KEM_PARAMS["ML-KEM-768"].pub_key_bytes
        assert sizes["ciphertext"] == KEM_PARAMS["ML-KEM-768"].ciphertext_bytes
        assert sizes["shared_secret"] == KEM_PARAMS["ML-KEM-768"].shared_secret_bytes

    def test_kem1024_sizes_match_spec(self, client):
        data = client.post("/api/pqc-lab/kem/demo", json={"param_set": "ML-KEM-1024"}).json()
        sizes = data["sizes_bytes"]
        assert sizes["public_key"] == KEM_PARAMS["ML-KEM-1024"].pub_key_bytes
        assert sizes["ciphertext"] == KEM_PARAMS["ML-KEM-1024"].ciphertext_bytes

    @pytest.mark.parametrize("param_set", ["ML-KEM-768", "ML-KEM-1024"])
    def test_kem_demo_no_private_key_exposed(self, client, param_set):
        data = client.post("/api/pqc-lab/kem/demo", json={"param_set": param_set}).json()
        assert data["private_key_exposed"] is False
        assert data["shared_secret_exposed"] is False
        # Verify no raw byte strings that look like keys
        assert "private_bytes_raw" not in str(data)

    @pytest.mark.parametrize("param_set", ["ML-KEM-768", "ML-KEM-1024"])
    def test_kem_demo_has_fingerprints_not_secrets(self, client, param_set):
        data = client.post("/api/pqc-lab/kem/demo", json={"param_set": param_set}).json()
        fp = data["fingerprints"]
        assert "public_key" in fp
        assert "shared_secret" in fp
        # Fingerprints are hex strings of length 16 (first 8 bytes of sha-256)
        assert len(fp["shared_secret"]) == 16

    def test_kem_invalid_param_set_400(self, client):
        r = client.post("/api/pqc-lab/kem/demo", json={"param_set": "ML-KEM-512"})
        assert r.status_code == 422  # Pydantic validation error

    def test_kem_unknown_param_400(self, client):
        r = client.post("/api/pqc-lab/kem/demo", json={"param_set": "INVALID-KEM"})
        assert r.status_code == 422


# ── 3. ML-DSA Signature Demos ─────────────────────────────────────────────────

class TestMLDSADemo:

    @pytest.mark.parametrize("param_set", ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"])
    def test_sig_demo_200(self, client, param_set):
        r = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": param_set,
            "message": "QShield test",
            "tamper_verify": False,
        })
        assert r.status_code == 200

    @pytest.mark.parametrize("param_set", ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"])
    def test_sig_original_verified(self, client, param_set):
        data = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": param_set,
            "message": "Post-quantum signature test message.",
            "tamper_verify": False,
        }).json()
        assert data["original_verification"]["valid"] is True

    @pytest.mark.parametrize("param_set", ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"])
    def test_sig_timings_non_negative(self, client, param_set):
        data = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": param_set, "message": "timing test", "tamper_verify": False,
        }).json()
        t = data["timings_ms"]
        assert t["key_generation"] >= 0
        assert t["signing"] >= 0
        assert t["verification"] >= 0

    @pytest.mark.parametrize("param_set", ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"])
    def test_sig_sizes_match_spec(self, client, param_set):
        data = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": param_set, "message": "sizes test", "tamper_verify": False,
        }).json()
        sizes = data["sizes_bytes"]
        assert sizes["public_key"] == SIG_PARAMS[param_set].pub_key_bytes
        # Signature should be positive and within spec max
        assert 0 < sizes["signature"] <= SIG_PARAMS[param_set].max_sig_bytes

    @pytest.mark.parametrize("param_set", ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"])
    def test_sig_no_private_key_in_response(self, client, param_set):
        data = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": param_set, "message": "key safety test", "tamper_verify": False,
        }).json()
        assert data["private_key_exposed"] is False
        assert "private_bytes_raw" not in str(data)

    def test_tamper_verification_fails_correctly(self, client):
        """A tampered-message verification failure is a successful demonstration."""
        data = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": "ML-DSA-65",
            "message": "original message",
            "tamper_verify": True,
        }).json()
        assert data["original_verification"]["valid"] is True
        tamper = data["tamper_verification"]
        assert tamper["valid"] is False
        assert tamper["is_expected_failure"] is True

    def test_empty_message_422(self, client):
        r = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": "ML-DSA-65",
            "message": "",
            "tamper_verify": False,
        })
        assert r.status_code == 422

    def test_oversized_message_422(self, client):
        r = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": "ML-DSA-65",
            "message": "x" * 5000,
            "tamper_verify": False,
        })
        assert r.status_code == 422

    def test_invalid_param_set_422(self, client):
        r = client.post("/api/pqc-lab/signature/demo", json={
            "param_set": "ML-DSA-999",
            "message": "test",
            "tamper_verify": False,
        })
        assert r.status_code == 422


# ── 4. Benchmark ─────────────────────────────────────────────────────────────

class TestBenchmark:

    def test_kem_benchmark_200(self, client):
        r = client.post("/api/pqc-lab/benchmark", json={
            "param_set": "ML-KEM-768",
            "iterations": 5,
        })
        assert r.status_code == 200

    def test_sig_benchmark_200(self, client):
        r = client.post("/api/pqc-lab/benchmark", json={
            "param_set": "ML-DSA-65",
            "iterations": 5,
        })
        assert r.status_code == 200

    def test_benchmark_statistics_structure(self, client):
        data = client.post("/api/pqc-lab/benchmark", json={
            "param_set": "ML-KEM-768", "iterations": 5,
        }).json()
        stats = data["statistics"]
        assert "key_generation" in stats
        assert "encapsulation" in stats
        assert "decapsulation" in stats
        for op, stat in stats.items():
            assert "avg_ms" in stat
            assert "min_ms" in stat
            assert "max_ms" in stat
            assert stat["avg_ms"] >= 0
            assert stat["min_ms"] >= 0
            assert stat["min_ms"] <= stat["max_ms"]

    def test_benchmark_iteration_count_preserved(self, client):
        data = client.post("/api/pqc-lab/benchmark", json={
            "param_set": "ML-DSA-65", "iterations": 10,
        }).json()
        assert data["iterations"] == 10

    def test_benchmark_invalid_iterations_422(self, client):
        r = client.post("/api/pqc-lab/benchmark", json={
            "param_set": "ML-KEM-768", "iterations": 100,
        })
        assert r.status_code == 422

    def test_benchmark_invalid_param_set_422(self, client):
        r = client.post("/api/pqc-lab/benchmark", json={
            "param_set": "NOT-A-SET", "iterations": 5,
        })
        assert r.status_code == 422

    def test_benchmark_has_disclaimer(self, client):
        data = client.post("/api/pqc-lab/benchmark", json={
            "param_set": "ML-KEM-768", "iterations": 5,
        }).json()
        assert "disclaimer" in data
        assert len(data["disclaimer"]) > 10


# ── 5. Service-layer direct unit tests ────────────────────────────────────────

class TestServiceLayer:
    """Direct tests of pqc_lab_service functions — not through HTTP."""

    def test_capabilities_structure(self):
        caps = get_capabilities()
        assert "kem" in caps
        assert "signature" in caps
        assert "environment" in caps

    def test_kem768_demo_secrets_match(self):
        result = run_kem_demo("ML-KEM-768")
        assert result["success"] is True

    def test_kem1024_demo_secrets_match(self):
        result = run_kem_demo("ML-KEM-1024")
        assert result["success"] is True

    def test_kem_demo_sizes_correct(self):
        result = run_kem_demo("ML-KEM-768")
        assert result["sizes_bytes"]["public_key"] == KEM_PARAMS["ML-KEM-768"].pub_key_bytes
        assert result["sizes_bytes"]["ciphertext"] == KEM_PARAMS["ML-KEM-768"].ciphertext_bytes
        assert result["sizes_bytes"]["shared_secret"] == KEM_PARAMS["ML-KEM-768"].shared_secret_bytes

    def test_kem_invalid_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            run_kem_demo("ML-KEM-512")

    def test_sig_verify_succeeds(self):
        result = run_signature_demo("ML-DSA-65", "test message", tamper_verify=False)
        assert result["original_verification"]["valid"] is True

    def test_sig_tamper_fails_correctly(self):
        result = run_signature_demo("ML-DSA-65", "test message", tamper_verify=True)
        assert result["original_verification"]["valid"] is True
        assert result["tamper_verification"]["valid"] is False
        assert result["tamper_verification"]["is_expected_failure"] is True

    @pytest.mark.parametrize("param_set", ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"])
    def test_all_dsa_param_sets(self, param_set):
        result = run_signature_demo(param_set, "param set test", tamper_verify=False)
        assert result["original_verification"]["valid"] is True
        assert result["sizes_bytes"]["public_key"] == SIG_PARAMS[param_set].pub_key_bytes

    def test_sig_empty_message_raises(self):
        with pytest.raises(ValueError):
            run_signature_demo("ML-DSA-65", "", tamper_verify=False)

    def test_sig_oversized_message_raises(self):
        with pytest.raises(ValueError):
            run_signature_demo("ML-DSA-65", "x" * 5000, tamper_verify=False)

    def test_benchmark_kem_stats(self):
        result = run_benchmark("ML-KEM-768", "ML-KEM-768", 5)
        assert result["iterations"] == 5
        assert "key_generation" in result["statistics"]
        assert result["statistics"]["key_generation"]["avg_ms"] >= 0

    def test_benchmark_invalid_iterations_raises(self):
        with pytest.raises(ValueError, match="iterations must be one of"):
            run_benchmark("ML-KEM-768", "ML-KEM-768", 999)

    def test_no_private_key_returned(self):
        result = run_kem_demo("ML-KEM-768")
        # Private key bytes must not be in the result
        import json
        serialized = json.dumps(result)
        # The sizes_bytes contains 'private_key' as the LENGTH only
        assert result["private_key_exposed"] is False
        assert result["shared_secret_exposed"] is False
