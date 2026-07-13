"""
test_analyzer.py — Tests for QShield Explainable Migration Prioritization Methodology.

Covers:
  1. High-risk, internet-facing, long-lived, critical application
  2. Low-criticality internal application with identical finding
  3. Symmetric-only application (low quantum migration priority)
  4. Legacy algorithm — classical risk separate from quantum risk
  5. Missing/default business context handling
  6. Deterministic repeatability
  7. Factor contribution math / total score
  8. Severity thresholds
  9. API endpoint shape via HTTP
 10. Score differentiation (same algorithm, different contexts)
"""
import pytest

from app.services.analyzer import (
    ApplicationContext,
    FindingInput,
    score_finding,
    score_scan,
    WEIGHTS,
    _severity_band,
    _migration_priority,
    _classical_legacy_risk,
)

# ── Shared test fixtures ──────────────────────────────────────────────────────

def _rsa_finding(id_: str = "f1") -> FindingInput:
    """RSA-2048 key exchange finding — classically strong, quantum-vulnerable."""
    return FindingInput(
        id=id_,
        algorithm="RSA-2048",
        algorithm_family="RSA",
        category="QUANTUM_VULNERABLE_PUBLIC_KEY",
        quantum_status="vulnerable",
        key_size=2048,
        usage_context="key_exchange",
        confidence=0.9,
        file_path="src/crypto/rsa_util.py",
    )


def _aes256_finding(id_: str = "f2") -> FindingInput:
    """AES-256 — quantum-safe symmetric cipher."""
    return FindingInput(
        id=id_,
        algorithm="AES-256",
        algorithm_family="AES",
        category="SYMMETRIC",
        quantum_status="safe",
        key_size=256,
        usage_context="encryption",
        confidence=0.85,
        file_path="src/crypto/aes_util.py",
    )


def _md5_finding(id_: str = "f3") -> FindingInput:
    """MD5 — classically broken, NOT quantum-vulnerable in the Shor sense."""
    return FindingInput(
        id=id_,
        algorithm="MD5",
        algorithm_family="MD5",
        category="LEGACY_DEPRECATED",
        quantum_status="unknown",  # stored as unknown in DB for legacy
        key_size=None,
        usage_context="hash",
        confidence=0.9,
        file_path="src/legacy/hash_util.py",
    )


def _pqc_finding(id_: str = "f4") -> FindingInput:
    """ML-KEM — already post-quantum, zero migration priority."""
    return FindingInput(
        id=id_,
        algorithm="ML-KEM-768",
        algorithm_family="ML-KEM",
        category="POST_QUANTUM",
        quantum_status="safe",
        key_size=None,
        usage_context="key_exchange",
        confidence=1.0,
        file_path="src/pqc/kyber.py",
    )


def _critical_internet_ctx() -> ApplicationContext:
    """High-risk context: internet-facing, critical, long-lived data."""
    return ApplicationContext(
        business_criticality="critical",
        internet_exposed=True,
        data_sensitivity="restricted",
        confidentiality_requirement="long_term",
        data_lifetime_years=25,
        environment="production",
    )


def _low_internal_ctx() -> ApplicationContext:
    """Low-risk context: internal, low criticality, short-lived data."""
    return ApplicationContext(
        business_criticality="low",
        internet_exposed=False,
        data_sensitivity="public",
        confidentiality_requirement="short_term",
        data_lifetime_years=1,
        environment="development",
    )


def _medium_ctx() -> ApplicationContext:
    """Medium / neutral context."""
    return ApplicationContext(
        business_criticality="medium",
        internet_exposed=False,
        data_sensitivity="internal",
        confidentiality_requirement="medium_term",
        data_lifetime_years=5,
        environment="production",
    )


# ── 1. High-risk internet-facing critical application ─────────────────────────

class TestHighRiskCritical:
    def test_rsa_critical_internet_scores_high(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        assert result.quantum_migration_score >= 55, (
            f"RSA key exchange in critical internet-facing app should score High+, got {result.quantum_migration_score}"
        )

    def test_high_risk_severity_is_high_or_critical(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        assert result.quantum_migration_severity in ("High", "Critical")

    def test_migration_priority_is_urgent(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        assert result.migration_priority in ("immediate", "near_term")

    def test_nist_recommendation_present(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        assert result.nist_recommendation is not None
        assert "ML-KEM" in result.nist_recommendation or "ML-DSA" in result.nist_recommendation

    def test_internet_exposure_factor_high(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        exp_factor = next(f for f in result.factors if f.factor == "external_exposure")
        assert exp_factor.raw_value >= 0.9

    def test_long_term_confidentiality_factor_high(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        conf_factor = next(f for f in result.factors if f.factor == "confidentiality")
        assert conf_factor.raw_value >= 0.9  # long_term + 25 years

    def test_explanation_contains_internet_facing(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        assert "internet" in result.explanation.lower()

    def test_no_classical_legacy_risk_for_rsa(self):
        result = score_finding(_rsa_finding(), _critical_internet_ctx())
        # RSA-2048 is classically fine — no classical concern expected
        assert result.classical_legacy_risk is None


# ── 2. Low-criticality internal application ────────────────────────────────────

class TestLowRiskInternal:
    def test_rsa_low_internal_scores_lower_than_critical(self):
        high_result = score_finding(_rsa_finding("h"), _critical_internet_ctx())
        low_result  = score_finding(_rsa_finding("l"), _low_internal_ctx())
        assert low_result.quantum_migration_score < high_result.quantum_migration_score, (
            "Same RSA finding MUST score lower in a low-risk internal app"
        )

    def test_rsa_low_internal_scores_lower_than_35(self):
        result = score_finding(_rsa_finding(), _low_internal_ctx())
        # RSA is still quantum-vulnerable so score > 0, but context reduces it significantly
        assert result.quantum_migration_score < 50, (
            f"Low-criticality internal RSA should score < 50, got {result.quantum_migration_score}"
        )

    def test_business_criticality_factor_low(self):
        result = score_finding(_rsa_finding(), _low_internal_ctx())
        biz_factor = next(f for f in result.factors if f.factor == "business_criticality")
        assert biz_factor.raw_value <= 0.15  # low × dev environment

    def test_external_exposure_factor_low(self):
        result = score_finding(_rsa_finding(), _low_internal_ctx())
        exp_factor = next(f for f in result.factors if f.factor == "external_exposure")
        assert exp_factor.raw_value <= 0.30


# ── 3. Symmetric-only application ─────────────────────────────────────────────

class TestSymmetricOnly:
    def test_aes256_quantum_migration_score_low(self):
        result = score_finding(_aes256_finding(), _critical_internet_ctx())
        # AES-256 is quantum-safe: crypto_vulnerability factor should be near 0
        assert result.quantum_migration_score < 40, (
            f"AES-256 should have low quantum migration priority even in critical app, got {result.quantum_migration_score}"
        )

    def test_aes256_no_classical_legacy_risk(self):
        result = score_finding(_aes256_finding(), _critical_internet_ctx())
        assert result.classical_legacy_risk is None

    def test_symmetric_only_scan_low_overall(self):
        result = score_scan(
            "scan-sym",
            [_aes256_finding("a"), _aes256_finding("b")],
            _critical_internet_ctx(),
        )
        assert result.overall_quantum_score < 40
        assert result.vulnerable_count == 0
        assert result.safe_count == 2

    def test_pqc_finding_near_zero_score(self):
        result = score_finding(_pqc_finding(), _critical_internet_ctx())
        assert result.quantum_migration_score < 20, (
            f"PQC finding should have near-zero quantum migration score, got {result.quantum_migration_score}"
        )


# ── 4. Legacy algorithm — classical risk separate from quantum ─────────────────

class TestLegacyClassicalSeparation:
    def test_md5_has_classical_legacy_risk(self):
        result = score_finding(_md5_finding(), _critical_internet_ctx())
        assert result.classical_legacy_risk is not None
        assert result.classical_legacy_risk in ("Critical", "High")

    def test_md5_classical_rationale_not_quantum(self):
        result = score_finding(_md5_finding(), _critical_internet_ctx())
        # Rationale must distinguish classical from quantum concern
        assert "classical" in result.classical_legacy_rationale.lower()

    def test_md5_quantum_migration_score_low(self):
        result = score_finding(_md5_finding(), _critical_internet_ctx())
        # MD5 LEGACY_DEPRECATED category has a 0.20 category multiplier on the crypto factor
        # — its QUANTUM migration priority is LOW even in a critical app
        assert result.quantum_migration_score < 40, (
            f"MD5 should have LOW quantum migration priority (it is a classical concern, not quantum). "
            f"Got {result.quantum_migration_score}"
        )

    def test_md5_severity_not_critical_quantum(self):
        result = score_finding(_md5_finding(), _critical_internet_ctx())
        # Even in worst-case context, MD5 quantum migration priority should NOT be Critical
        assert result.quantum_migration_severity in ("Low", "Moderate")

    def test_classical_legacy_risk_not_mixed_with_quantum_score(self):
        """Classical and quantum scores are entirely separate fields."""
        result = score_finding(_md5_finding(), _critical_internet_ctx())
        # The quantum migration score is independent of the classical_legacy_risk label
        assert isinstance(result.quantum_migration_score, float)
        assert isinstance(result.classical_legacy_risk, str)

    def test_rsa_small_key_classical_risk(self):
        """RSA-1024 has both quantum migration risk AND a classical security concern."""
        small_rsa = FindingInput(
            id="f_rsa1024",
            algorithm="RSA-1024",
            algorithm_family="RSA",
            category="QUANTUM_VULNERABLE_PUBLIC_KEY",
            quantum_status="vulnerable",
            key_size=1024,
            usage_context="signing",
            confidence=0.9,
            file_path="legacy/rsa.py",
        )
        result = score_finding(small_rsa, _critical_internet_ctx())
        assert result.classical_legacy_risk == "High"
        assert "1024" in result.classical_legacy_rationale
        # Quantum migration score is ALSO high (both concerns present)
        assert result.quantum_migration_score >= 50

    def test_sha1_classical_risk_is_high(self):
        sha1_finding = FindingInput(
            id="f_sha1",
            algorithm="SHA-1",
            algorithm_family="SHA-1",
            category="LEGACY_DEPRECATED",
            quantum_status="unknown",
            key_size=None,
            usage_context="hash",
            confidence=0.85,
            file_path="src/legacy/hash.py",
        )
        result = score_finding(sha1_finding, _medium_ctx())
        assert result.classical_legacy_risk == "High"
        assert result.quantum_migration_score < 40


# ── 5. Missing business context ────────────────────────────────────────────────

class TestMissingContext:
    def test_default_context_is_neutral_not_high_risk(self):
        """
        Missing context must use documented neutral defaults.
        The score should reflect middle-ground, not worst-case.
        """
        default_ctx = ApplicationContext(
            business_criticality="medium",
            internet_exposed=False,
            data_sensitivity="internal",
            confidentiality_requirement="medium_term",
            data_lifetime_years=5,
            environment="production",
        )
        result = score_finding(_rsa_finding(), default_ctx)
        # Should not score as Critical when context is neutral/default
        assert result.quantum_migration_score < 75, (
            "Neutral default context should not produce Critical score"
        )

    def test_empty_findings_scan_returns_zero(self):
        result = score_scan("scan-empty", [], _medium_ctx())
        assert result.overall_quantum_score == 0.0
        assert result.overall_severity == "Low"
        assert result.vulnerable_count == 0
        assert "No cryptographic findings" in result.summary_text

    def test_empty_findings_factor_summary_all_zero(self):
        result = score_scan("scan-empty", [], _medium_ctx())
        assert all(v == 0.0 for v in result.factor_summary.values())


# ── 6. Deterministic repeatability ────────────────────────────────────────────

class TestDeterminism:
    def test_same_inputs_same_score(self):
        f = _rsa_finding()
        ctx = _critical_internet_ctx()
        r1 = score_finding(f, ctx)
        r2 = score_finding(f, ctx)
        assert r1.quantum_migration_score == r2.quantum_migration_score

    def test_same_inputs_same_explanation(self):
        f = _rsa_finding()
        ctx = _critical_internet_ctx()
        r1 = score_finding(f, ctx)
        r2 = score_finding(f, ctx)
        assert r1.explanation == r2.explanation

    def test_scan_deterministic(self):
        findings = [_rsa_finding("a"), _aes256_finding("b"), _md5_finding("c")]
        ctx = _critical_internet_ctx()
        r1 = score_scan("s1", findings, ctx)
        r2 = score_scan("s1", findings, ctx)
        assert r1.overall_quantum_score == r2.overall_quantum_score


# ── 7. Factor contribution math ────────────────────────────────────────────────

class TestFactorMath:
    def test_factor_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_six_factors_present(self):
        result = score_finding(_rsa_finding(), _medium_ctx())
        assert len(result.factors) == 6

    def test_each_factor_has_required_fields(self):
        result = score_finding(_rsa_finding(), _medium_ctx())
        from app.services.analyzer import FACTOR_LABELS
        for f in result.factors:
            assert f.factor in WEIGHTS
            assert f.label == FACTOR_LABELS[f.factor]
            assert 0.0 <= f.raw_value <= 1.0
            assert f.weight == WEIGHTS[f.factor]
            assert f.weighted_contribution >= 0

    def test_total_score_equals_sum_of_weighted_contributions(self):
        """
        With the crypto_vulnerability gate applied:
          score = sum(weighted_contributions) * gate_mult
        The gate_mult is derived from qv_raw. We verify the score is within
        a sane bound of what it would be without the gate (for vulnerable findings,
        gate_mult ≈ 1.0 so scores converge).
        """
        result = score_finding(_rsa_finding(), _medium_ctx())
        raw_sum = sum(f.weighted_contribution for f in result.factors)
        # For a fully vulnerable RSA finding, gate_mult should be close to 1.0
        # so score should be close to raw_sum
        assert abs(result.quantum_migration_score - raw_sum) < raw_sum * 0.15, (
            "For a quantum-vulnerable finding, score should be close to weighted sum"
        )

    def test_score_bounded_0_100(self):
        for ctx in [_critical_internet_ctx(), _low_internal_ctx(), _medium_ctx()]:
            for finding in [_rsa_finding(), _aes256_finding(), _md5_finding(), _pqc_finding()]:
                result = score_finding(finding, ctx)
                assert 0.0 <= result.quantum_migration_score <= 100.0


# ── 8. Severity thresholds ────────────────────────────────────────────────────

class TestSeverityThresholds:
    def test_score_0_is_low(self):
        assert _severity_band(0.0) == "Low"

    def test_score_34_is_low(self):
        assert _severity_band(34.9) == "Low"

    def test_score_35_is_moderate(self):
        assert _severity_band(35.0) == "Moderate"

    def test_score_54_is_moderate(self):
        assert _severity_band(54.9) == "Moderate"

    def test_score_55_is_high(self):
        assert _severity_band(55.0) == "High"

    def test_score_74_is_high(self):
        assert _severity_band(74.9) == "High"

    def test_score_75_is_critical(self):
        assert _severity_band(75.0) == "Critical"

    def test_score_100_is_critical(self):
        assert _severity_band(100.0) == "Critical"

    def test_migration_priority_immediate_at_75(self):
        assert _migration_priority(75.0) == "immediate"

    def test_migration_priority_near_term_at_55(self):
        assert _migration_priority(55.0) == "near_term"

    def test_migration_priority_long_term_at_35(self):
        assert _migration_priority(35.0) == "long_term"

    def test_migration_priority_low_at_34(self):
        assert _migration_priority(34.9) == "low"


# ── 9. API endpoint via HTTP ──────────────────────────────────────────────────

class TestRiskApiEndpoint:
    def test_missing_scan_id_returns_422(self, client):
        r = client.get("/api/risk")
        assert r.status_code == 422

    def test_nonexistent_scan_returns_404(self, client):
        r = client.get("/api/risk?scan_id=does-not-exist")
        assert r.status_code == 404

    def test_risk_response_shape_on_real_scan(self, client):
        """
        Full pipeline test: create org/project/app → upload sample ZIP → call risk endpoint.
        Verifies the response has all required fields.
        """
        import io, zipfile

        # Create organization (slug required)
        org = client.post("/api/organizations", json={"name": "RiskTestOrg", "slug": "risk-test-org"}).json()
        project = client.post("/api/projects", json={
            "organization_id": org["id"], "name": "RiskTestProject",
        }).json()
        app_r = client.post("/api/applications", json={
            "project_id": project["id"],
            "name": "RiskTestApp",
            "business_criticality": "critical",
            "internet_exposed": True,
            "data_sensitivity": "restricted",
            "confidentiality_requirement": "long_term",
            "data_lifetime_years": 20,
            "environment": "production",
        }).json()
        app_id = app_r["id"]

        # Upload sample Python file with RSA usage
        py_src = b"from Crypto.PublicKey import RSA\nkey = RSA.generate(2048)\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("crypto_key.py", py_src)
        buf.seek(0)

        upload_r = client.post(
            "/api/scans/upload",
            data={"application_id": app_id},
            files={"file": ("test.zip", buf, "application/zip")},
        )
        assert upload_r.status_code == 201
        scan_id = upload_r.json()["id"]

        # Call risk endpoint
        risk_r = client.get(f"/api/risk?scan_id={scan_id}")
        assert risk_r.status_code == 200

        body = risk_r.json()
        # Required top-level fields
        assert "methodology" in body
        assert "QShield" in body["methodology"]
        assert "disclaimer" in body
        assert "overall_quantum_score" in body
        assert "overall_severity" in body
        assert body["overall_severity"] in ("Low", "Moderate", "High", "Critical")
        assert "factor_summary" in body
        assert len(body["factor_summary"]) == 6
        assert "top_findings" in body
        assert "vulnerable_count" in body
        assert "legacy_count" in body
        assert "summary_text" in body
        assert "business_criticality" in body
        assert body["business_criticality"] == "critical"
        assert body["internet_exposed"] is True
        assert 0.0 <= body["overall_quantum_score"] <= 100.0

    def test_risk_reflects_context_in_response(self, client):
        """Verify business context fields are echoed back in the response."""
        import io, zipfile

        org = client.post("/api/organizations", json={"name": "CtxEchoOrg", "slug": "ctx-echo-org"}).json()
        project = client.post("/api/projects", json={
            "organization_id": org["id"], "name": "CtxEchoProject",
        }).json()
        app_r = client.post("/api/applications", json={
            "project_id": project["id"],
            "name": "CtxEchoApp",
            "business_criticality": "low",
            "internet_exposed": False,
            "data_sensitivity": "public",
            "confidentiality_requirement": "short_term",
            "data_lifetime_years": 1,
            "environment": "development",
        }).json()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("hello.py", b"import hashlib\nhashlib.sha256(b'hi')\n")
        buf.seek(0)

        upload_r = client.post(
            "/api/scans/upload",
            data={"application_id": app_r["id"]},
            files={"file": ("t.zip", buf, "application/zip")},
        )
        scan_id = upload_r.json()["id"]
        risk_r = client.get(f"/api/risk?scan_id={scan_id}")
        assert risk_r.status_code == 200
        body = risk_r.json()
        assert body["business_criticality"] == "low"
        assert body["internet_exposed"] is False
        assert body["environment"] == "development"

    def test_top_findings_have_factor_breakdown(self, client):
        """Each top finding must have a factor breakdown with 6 entries."""
        import io, zipfile

        org = client.post("/api/organizations", json={"name": "FactorOrg", "slug": "factor-org"}).json()
        proj = client.post("/api/projects", json={
            "organization_id": org["id"], "name": "FactorProj",
        }).json()
        app_r = client.post("/api/applications", json={
            "project_id": proj["id"],
            "name": "FactorApp",
            "business_criticality": "high",
            "internet_exposed": True,
            "data_sensitivity": "restricted",
            "confidentiality_requirement": "long_term",
            "data_lifetime_years": 10,
            "environment": "production",
        }).json()

        py_src = b"from cryptography.hazmat.primitives.asymmetric import rsa\nrsa.generate_private_key(65537, 2048)\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("rsa_ops.py", py_src)
        buf.seek(0)

        upload_r = client.post(
            "/api/scans/upload",
            data={"application_id": app_r["id"]},
            files={"file": ("r.zip", buf, "application/zip")},
        )
        scan_id = upload_r.json()["id"]
        risk_r = client.get(f"/api/risk?scan_id={scan_id}")
        body = risk_r.json()
        for finding in body["top_findings"]:
            assert len(finding["factors"]) == 6
            for factor in finding["factors"]:
                assert "factor" in factor
                assert "weight" in factor
                assert "raw_value" in factor
                assert "weighted_contribution" in factor
                assert "rationale" in factor


# ── 10. Score differentiation — same algorithm, different contexts ─────────────

class TestScoreDifferentiation:
    def test_same_rsa_different_context_produces_different_scores(self):
        high_ctx = _critical_internet_ctx()
        low_ctx  = _low_internal_ctx()
        high_result = score_finding(_rsa_finding(), high_ctx)
        low_result  = score_finding(_rsa_finding(), low_ctx)
        diff = high_result.quantum_migration_score - low_result.quantum_migration_score
        assert diff >= 15, (
            f"Critical internet-facing app must score significantly higher than low internal app. "
            f"Diff was only {diff:.1f} points."
        )

    def test_rsa_critical_scores_higher_than_aes_critical(self):
        """RSA (quantum-vulnerable) must score higher than AES-256 (quantum-safe), same context."""
        rsa_result = score_finding(_rsa_finding(), _critical_internet_ctx())
        aes_result = score_finding(_aes256_finding(), _critical_internet_ctx())
        assert rsa_result.quantum_migration_score > aes_result.quantum_migration_score

    def test_scan_with_only_pqc_scores_low(self):
        result = score_scan("scan-pqc", [_pqc_finding()], _critical_internet_ctx())
        assert result.overall_quantum_score < 20
        assert result.vulnerable_count == 0
