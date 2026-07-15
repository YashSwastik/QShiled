"""
Tests for Part 9 — Migration Roadmap Engine (Phase G)

Covers:
  1. Wave 1: Critical + internet-facing + long-lived + quantum-vulnerable
  2. Wave 2: High business impact, internal, near-term priority
  3. Wave 3: Lower-priority, safe/legacy
  4. Symmetric/classical finding NOT Wave 1
  5. Application context changes → wave changes
  6. Risk score changes → wave changes
  7. Recommendation data consumed (not hardcoded)
  8. Valid stage update (unit)
  9. Invalid stage rejected
 10. Determinism
 11. Empty scan
 12. HTTP integration: GET roadmap, PATCH stage, re-GET persists
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.analyzer import FindingInput
from app.services.roadmap_engine import (
    build_roadmap,
    MIGRATION_STAGES,
    VALID_STAGES,
    WAVE_1, WAVE_2, WAVE_3,
    advance_stage,
)
from app.main import app

client = TestClient(app)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _finding(
    id: str,
    algorithm: str,
    family: str,
    category: str,
    quantum_status: str,
    usage_context: str | None = None,
    key_size: int | None = None,
    file_path: str = "src/crypto.py",
) -> FindingInput:
    return FindingInput(
        id=id,
        algorithm=algorithm,
        algorithm_family=family,
        category=category,
        quantum_status=quantum_status,
        key_size=key_size,
        usage_context=usage_context,
        confidence=0.9,
        file_path=file_path,
    )


def _pm(finding_id: str, priority: str, score: float, severity: str = "High"):
    return {finding_id: (priority, score, severity)}


# ── 1. Wave 1: Critical + internet-facing + long-lived + quantum-vulnerable ───

class TestWave1Assignment:
    def test_immediate_priority_goes_wave_1(self):
        f = _finding("f1", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "signing")
        result = build_roadmap(
            "s1", "AppA", "app-1", [f],
            priority_map=_pm("f1", "immediate", 88.0),
            internet_exposed=True,
            confidentiality_requirement="long_term",
            business_criticality="critical",
        )
        assert result.items[0].wave == WAVE_1

    def test_internet_facing_long_term_quantum_elevates_to_wave_1(self):
        """near_term normally → Wave 2, but internet + long_term + quantum → elevated to Wave 1."""
        f = _finding("f2", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s2", "AppB", "app-2", [f],
            priority_map=_pm("f2", "near_term", 58.0),
            internet_exposed=True,
            confidentiality_requirement="long_term",
            business_criticality="medium",
        )
        assert result.items[0].wave == WAVE_1

    def test_high_score_no_priority_goes_wave_1(self):
        """Score ≥ 65 with no Part 7 priority → Wave 1."""
        f = _finding("f3", "RSA-4096", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "key_exchange")
        result = build_roadmap(
            "s3", "AppC", "app-3", [f],
            priority_map={"f3": (None, 70.0, "High")},
            internet_exposed=False,
            confidentiality_requirement="medium_term",
            business_criticality="medium",
        )
        assert result.items[0].wave == WAVE_1

    def test_wave_1_item_has_immediate_action(self):
        f = _finding("f4", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "signing")
        result = build_roadmap(
            "s4", "AppD", "app-4", [f],
            priority_map=_pm("f4", "immediate", 90.0),
        )
        assert "Immediate" in result.items[0].recommended_action

    def test_wave_1_reason_mentions_priority(self):
        f = _finding("f5", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "signing")
        result = build_roadmap(
            "s5", "AppE", "app-5", [f],
            priority_map=_pm("f5", "immediate", 90.0),
        )
        assert "immediate" in result.items[0].reason.lower()


# ── 2. Wave 2: High impact, near-term ────────────────────────────────────────

class TestWave2Assignment:
    def test_near_term_priority_goes_wave_2(self):
        f = _finding("f6", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s6", "AppF", "app-6", [f],
            priority_map=_pm("f6", "near_term", 55.0),
            internet_exposed=False,
            confidentiality_requirement="medium_term",
            business_criticality="medium",
        )
        assert result.items[0].wave == WAVE_2

    def test_score_40_to_64_goes_wave_2(self):
        f = _finding("f7", "DH", "DH", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s7", "AppG", "app-7", [f],
            priority_map={"f7": (None, 50.0, "Moderate")},
            internet_exposed=False,
            confidentiality_requirement="medium_term",
            business_criticality="medium",
        )
        assert result.items[0].wave == WAVE_2

    def test_high_criticality_elevates_wave3_quantum_to_wave2(self):
        """long_term priority → Wave 3, but critical business + quantum → elevated to Wave 2."""
        f = _finding("f8", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s8", "AppH", "app-8", [f],
            priority_map=_pm("f8", "long_term", 30.0),
            internet_exposed=False,
            confidentiality_requirement="medium_term",
            business_criticality="critical",
        )
        assert result.items[0].wave == WAVE_2

    def test_wave_2_action_near_term_prefix(self):
        f = _finding("f9", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s9", "AppI", "app-9", [f],
            priority_map=_pm("f9", "near_term", 55.0),
        )
        assert "Near-term" in result.items[0].recommended_action


# ── 3. Wave 3: Lower-priority, planned modernisation ─────────────────────────

class TestWave3Assignment:
    def test_low_priority_goes_wave_3(self):
        f = _finding("f10", "SHA-1", "SHA-1", "LEGACY_DEPRECATED", "deprecated")
        result = build_roadmap(
            "s10", "AppJ", "app-10", [f],
            priority_map=_pm("f10", "low", 8.0),
        )
        assert result.items[0].wave == WAVE_3

    def test_long_term_priority_goes_wave_3(self):
        f = _finding("f11", "AES-128", "AES", "SYMMETRIC", "borderline")
        result = build_roadmap(
            "s11", "AppK", "app-11", [f],
            priority_map=_pm("f11", "long_term", 20.0),
        )
        assert result.items[0].wave == WAVE_3

    def test_wave_3_action_planned_prefix(self):
        f = _finding("f12", "SHA-256", "SHA-2", "HASH", "safe")
        result = build_roadmap(
            "s12", "AppL", "app-12", [f],
            priority_map=_pm("f12", "low", 5.0),
        )
        assert "Planned" in result.items[0].recommended_action or \
               "Manual" in result.items[0].recommended_action


# ── 4. Symmetric/legacy NOT treated as quantum-critical ───────────────────────

class TestSymmetricAndLegacy:
    def test_aes256_not_wave_1(self):
        f = _finding("f13", "AES-256", "AES", "SYMMETRIC", "safe")
        result = build_roadmap(
            "s13", "AppM", "app-13", [f],
            priority_map=_pm("f13", "low", 5.0),
            internet_exposed=True,
            confidentiality_requirement="long_term",
            business_criticality="critical",
        )
        # AES-256 is not a quantum concern — internet+long_term elevation doesn't apply
        assert result.items[0].wave != WAVE_1

    def test_aes_not_quantum_concern(self):
        f = _finding("f14", "AES-256", "AES", "SYMMETRIC", "safe")
        result = build_roadmap("s14", "AppN", "app-14", [f])
        assert result.items[0].wave == WAVE_3

    def test_md5_legacy_goes_wave_3_not_wave_1(self):
        f = _finding("f15", "MD5", "MD5", "LEGACY_DEPRECATED", "deprecated")
        result = build_roadmap(
            "s15", "AppO", "app-15", [f],
            priority_map=_pm("f15", "low", 8.0),
            internet_exposed=True,   # internet exposure only elevates quantum concerns
            confidentiality_requirement="long_term",
            business_criticality="critical",
        )
        assert result.items[0].wave == WAVE_3

    def test_sha1_not_wave_1_even_critical_context(self):
        f = _finding("f16", "SHA-1", "SHA-1", "LEGACY_DEPRECATED", "deprecated")
        result = build_roadmap(
            "s16", "AppP", "app-16", [f],
            priority_map=_pm("f16", "low", 8.0),
            internet_exposed=True,
            confidentiality_requirement="long_term",
            business_criticality="critical",
        )
        # SHA-1 is classical/legacy, not Shor-vulnerable — elevation rule doesn't fire
        assert result.items[0].wave != WAVE_1


# ── 5. Application context changes → wave changes ─────────────────────────────

class TestContextSensitivity:
    def test_low_exposure_keeps_wave_2(self):
        f = _finding("f17", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s17", "AppQ", "app-17", [f],
            priority_map=_pm("f17", "near_term", 55.0),
            internet_exposed=False,          # no elevation
            confidentiality_requirement="medium_term",
            business_criticality="medium",
        )
        assert result.items[0].wave == WAVE_2

    def test_internet_long_term_elevates_same_finding(self):
        """Same finding + near_term + internet + long_term → Wave 1 (elevated from Wave 2)."""
        f = _finding("f18", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s18", "AppR", "app-18", [f],
            priority_map=_pm("f18", "near_term", 55.0),
            internet_exposed=True,
            confidentiality_requirement="long_term",
            business_criticality="medium",
        )
        assert result.items[0].wave == WAVE_1

    def test_critical_criticality_elevates_wave3_to_wave2(self):
        f = _finding("f19", "DH", "DH", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result_low = build_roadmap(
            "s19a", "AppS", "app-19", [f],
            priority_map=_pm("f19", "long_term", 25.0),
            business_criticality="low",
        )
        result_crit = build_roadmap(
            "s19b", "AppS", "app-19", [f],
            priority_map=_pm("f19", "long_term", 25.0),
            business_criticality="critical",
        )
        assert result_low.items[0].wave == WAVE_3
        assert result_crit.items[0].wave == WAVE_2


# ── 6. Risk score changes → wave changes ─────────────────────────────────────

class TestRiskScoreSensitivity:
    def test_score_below_40_goes_wave_3(self):
        f = _finding("f20", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "signing")
        result = build_roadmap(
            "s20", "AppT", "app-20", [f],
            priority_map={"f20": (None, 30.0, "Low")},
        )
        assert result.items[0].wave == WAVE_3

    def test_score_above_65_goes_wave_1(self):
        f = _finding("f21", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "signing")
        result = build_roadmap(
            "s21", "AppU", "app-21", [f],
            priority_map={"f21": (None, 80.0, "Critical")},
        )
        assert result.items[0].wave == WAVE_1


# ── 7. Recommendation data consumed (action from Part 8) ──────────────────────

class TestRecommendationConsumption:
    def test_recommended_action_comes_from_engine_not_hardcoded(self):
        f = _finding("f22", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap(
            "s22", "AppV", "app-22", [f],
            priority_map=_pm("f22", "immediate", 85.0),
        )
        item = result.items[0]
        # Action must reference the algorithm from the finding
        assert "ECDSA" in item.recommended_action or "ML-DSA" in item.recommended_action or \
               "SLH-DSA" in item.recommended_action or "digital" in item.recommended_action.lower()

    def test_recommended_algorithms_come_from_kb(self):
        f = _finding("f23", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable")
        result = build_roadmap("s23", "AppW", "app-23", [f])
        item = result.items[0]
        # ECDSA must get signature-oriented PQC algorithms from KB
        assert any("ML-DSA" in a or "SLH-DSA" in a for a in item.recommended_algorithms), \
            f"Expected ML-DSA/SLH-DSA in recommended_algorithms, got: {item.recommended_algorithms}"

    def test_manual_review_finding_has_manual_action(self):
        """RSA with no usage_context → unknown purpose → manual review action."""
        f = _finding("f24", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", usage_context=None)
        result = build_roadmap("s24", "AppX", "app-24", [f])
        item = result.items[0]
        assert item.requires_manual_review
        assert "manual" in item.recommended_action.lower()


# ── 8. Valid stage transitions ─────────────────────────────────────────────────

class TestStageTransitions:
    def test_advance_stage_discovered_to_assessed(self):
        assert advance_stage("DISCOVERED") == "ASSESSED"

    def test_advance_stage_assessed_to_planned(self):
        assert advance_stage("ASSESSED") == "PLANNED"

    def test_advance_stage_migrated_returns_none(self):
        assert advance_stage("MIGRATED") is None

    def test_advance_stage_invalid_returns_none(self):
        assert advance_stage("FOOBAR") is None

    def test_all_stages_valid(self):
        for s in MIGRATION_STAGES:
            assert s in VALID_STAGES

    def test_stage_order_is_forward_only(self):
        """Verify MIGRATION_STAGES list maintains the correct 7-step order."""
        expected = ["DISCOVERED", "ASSESSED", "PLANNED", "PILOT", "TRANSITION", "VALIDATION", "MIGRATED"]
        assert MIGRATION_STAGES == expected


# ── 9. Invalid stage rejected ─────────────────────────────────────────────────

class TestInvalidStage:
    def test_invalid_stage_not_in_valid_set(self):
        assert "PENDING" not in VALID_STAGES
        assert "IN_PROGRESS" not in VALID_STAGES
        assert "DONE" not in VALID_STAGES
        assert "" not in VALID_STAGES
        assert "FOOBAR" not in VALID_STAGES


# ── 10. Determinism ───────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_same_wave(self):
        f = _finding("f25", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "signing")
        pm = _pm("f25", "immediate", 90.0)
        r1 = build_roadmap("s25", "AppY", "app-25", [f], priority_map=pm)
        r2 = build_roadmap("s25", "AppY", "app-25", [f], priority_map=pm)
        assert r1.items[0].wave == r2.items[0].wave
        assert r1.items[0].recommended_algorithms == r2.items[0].recommended_algorithms
        assert r1.items[0].recommended_action == r2.items[0].recommended_action

    def test_mixed_scan_order_stable(self):
        findings = [
            _finding("fa", "RSA-2048", "RSA", "QUANTUM_VULNERABLE_PUBLIC_KEY",
                     "vulnerable", "signing"),
            _finding("fb", "AES-256", "AES", "SYMMETRIC", "safe"),
            _finding("fc", "ECDSA", "ECDSA", "QUANTUM_VULNERABLE_PUBLIC_KEY", "vulnerable"),
        ]
        pm = {
            "fa": ("immediate", 90.0, "Critical"),
            "fb": ("low", 5.0, "Low"),
            "fc": ("near_term", 55.0, "High"),
        }
        r1 = build_roadmap("smix", "AppZ", "app-z", findings, priority_map=pm)
        r2 = build_roadmap("smix", "AppZ", "app-z", findings, priority_map=pm)
        for item1, item2 in zip(r1.items, r2.items):
            assert item1.wave == item2.wave
            assert item1.finding_id == item2.finding_id


# ── 11. Empty scan ────────────────────────────────────────────────────────────

class TestEmptyScan:
    def test_empty_scan_returns_zero_items(self):
        result = build_roadmap("s-empty", "EmptyApp", "app-empty", [])
        assert result.total_items == 0
        assert result.items == []
        assert len(result.wave_summaries) == 3
        for ws in result.wave_summaries:
            assert ws.item_count == 0

    def test_empty_scan_summary_text(self):
        result = build_roadmap("s-empty2", "EmptyApp", "app-empty2", [])
        assert "0" in result.summary


# ── 12. Integration: GET /api/roadmap with real DB ─────────────────────────────

class TestRoadmapAPI:
    """HTTP-level integration tests for the roadmap router (uses TestClient + in-memory DB)."""

    def _create_scan(self):
        """Create minimal org/project/app/scan chain for API tests."""
        org_resp = client.post("/api/organizations", json={"name": "TestOrg9", "slug": "testorg9"})
        if org_resp.status_code not in (200, 201):
            org_resp = client.get("/api/organizations")
            org_id = org_resp.json()["items"][0]["id"] if org_resp.json().get("items") else None
            if not org_id:
                pytest.skip("Could not create/retrieve org")
        else:
            org_id = org_resp.json()["id"]

        proj_resp = client.post("/api/projects",
                                json={"name": "TestProj9", "organization_id": org_id})
        proj_id = proj_resp.json()["id"]

        app_resp = client.post("/api/applications", json={
            "name": "TestApp9",
            "project_id": proj_id,
            "business_criticality": "critical",
            "internet_exposed": True,
            "data_sensitivity": "restricted",
            "confidentiality_requirement": "long_term",
            "data_lifetime_years": 15,
            "environment": "production",
        })
        app_id = app_resp.json()["id"]

        return app_id, proj_id, org_id

    def test_roadmap_requires_completed_scan(self):
        """GET /api/roadmap with non-existent scan_id → 404."""
        resp = client.get("/api/roadmap?scan_id=nonexistent-scan")
        assert resp.status_code == 404

    def test_patch_nonexistent_item_404(self):
        """PATCH on finding that has no roadmap item → 404."""
        resp = client.patch("/api/roadmap/items/no-such-finding", json={
            "scan_id": "no-such-scan",
            "status": "ASSESSED",
        })
        assert resp.status_code == 404

    def test_patch_invalid_stage_422(self):
        """PATCH with invalid stage value → 422."""
        resp = client.patch("/api/roadmap/items/some-finding", json={
            "scan_id": "some-scan",
            "status": "IN_PROGRESS",  # not a valid MIGRATION_STAGE
        })
        assert resp.status_code == 422


# ── 13. Stage persistence regression tests ──────────────────────────────────────
#
# These tests exercise the full HTTP roundtrip:
#   GET (generate) → PATCH (update stage) → GET again (recalculate) → stage survives
#
# A shared scan is created once for the whole class so the tests are fast.

def _create_completed_scan_with_findings(c: TestClient) -> tuple[str, str]:
    """
    Create org → project → app → scan → findings → mark scan completed.
    Returns (scan_id, finding_id).
    Uses TEST_SESSION (same DB as TestClient) so all writes are visible to the client.
    """
    import uuid
    from tests.conftest import TEST_SESSION
    from app.models.finding import CryptoFinding, QuantumStatus, FindingCategory
    from app.models.scan import Scan, ScanStatus
    from app.models.base import new_uuid

    suffix = uuid.uuid4().hex[:8]

    org_r = c.post("/api/organizations", json={"name": f"PersistOrg{suffix}", "slug": f"persistorg{suffix}"})
    assert org_r.status_code in (200, 201), f"org create failed: {org_r.text}"
    org_id = org_r.json()["id"]

    proj_r = c.post("/api/projects", json={"name": f"PersistProj{suffix}", "organization_id": org_id})
    assert proj_r.status_code in (200, 201), f"proj create failed: {proj_r.text}"
    proj_id = proj_r.json()["id"]

    app_r = c.post("/api/applications", json={
        "name": f"PersistApp{suffix}",
        "project_id": proj_id,
        "business_criticality": "critical",
        "internet_exposed": True,
        "confidentiality_requirement": "long_term",
        "data_sensitivity": "restricted",
        "environment": "production",
    })
    assert app_r.status_code in (200, 201), f"app create failed: {app_r.text}"
    app_id = app_r.json()["id"]

    scan_r = c.post("/api/scans", json={
        "application_id": app_id,
        "name": f"PersistScan{suffix}",
        "scan_type": "source_code",
    })
    assert scan_r.status_code in (200, 201), f"scan create failed: {scan_r.text}"
    scan_id = scan_r.json()["id"]

    # Insert a finding & mark scan completed using the SAME test DB session
    finding_id = new_uuid()
    db = TEST_SESSION()
    try:
        f = CryptoFinding(
            id=finding_id,
            scan_id=scan_id,
            algorithm="RSA-2048",
            algorithm_family="RSA",
            category=FindingCategory.QUANTUM_VULNERABLE_PUBLIC_KEY,
            quantum_status=QuantumStatus.vulnerable,
            key_size=2048,
            usage_context="signing",
            confidence=0.95,
            file_path="src/auth.py",
            line_number=42,
        )
        db.add(f)
        scan_obj = db.get(Scan, scan_id)
        assert scan_obj is not None, f"Scan {scan_id} not found in test DB"
        scan_obj.status = ScanStatus.completed
        db.commit()
    finally:
        db.close()

    return scan_id, finding_id


class TestStagePersistenceRegression:
    """
    Regression tests for the stage persistence bug (Phase G fix).

    Bug: _load_stage_overrides returned row.status (4-value ORM enum),
         not row.stage (canonical 7-step string). Overlay check failed silently.
         Stage was reset to DISCOVERED on every GET.

    Fix: RoadmapItem.stage (VARCHAR 32) is the authoritative field.
         PATCH writes row.stage. _load_stage_overrides reads row.stage.
         _persist_roadmap_items never overwrites stage for existing rows.
    """

    def test_a_new_item_starts_discovered(self):
        """Test A — new roadmap item defaults to DISCOVERED."""
        scan_id, _ = _create_completed_scan_with_findings(client)
        resp = client.get(f"/api/roadmap?scan_id={scan_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_items"] >= 1
        assert data["items"][0]["status"] == "DISCOVERED"

    def test_b_patched_stage_survives_get(self):
        """
        Test B — PATCH ASSESSED then GET → stage remains ASSESSED.
        This is the exact regression: before the fix, GET returned DISCOVERED.
        """
        scan_id, finding_id = _create_completed_scan_with_findings(client)

        # Generate roadmap first (creates the persisted row)
        r1 = client.get(f"/api/roadmap?scan_id={scan_id}")
        assert r1.status_code == 200
        assert r1.json()["items"][0]["status"] == "DISCOVERED"

        # PATCH to ASSESSED
        patch_r = client.patch(
            f"/api/roadmap/items/{finding_id}",
            json={"scan_id": scan_id, "status": "ASSESSED"},
        )
        assert patch_r.status_code == 200, patch_r.text
        assert patch_r.json()["status"] == "ASSESSED"

        # GET again (deterministic recalculation) — must still be ASSESSED
        r2 = client.get(f"/api/roadmap?scan_id={scan_id}")
        assert r2.status_code == 200
        items = r2.json()["items"]
        target = next(i for i in items if i["finding_id"] == finding_id)
        assert target["status"] == "ASSESSED", (
            f"Stage reverted to '{target['status']}' after GET — persistence bug not fixed"
        )

    def test_c_recalculation_preserves_planned(self):
        """
        Test C — PATCH PLANNED, recalculate roadmap twice → remains PLANNED.
        Covers: wave/priority recalculation must not reset stage.
        """
        scan_id, finding_id = _create_completed_scan_with_findings(client)

        # Seed the roadmap row
        client.get(f"/api/roadmap?scan_id={scan_id}")

        # Advance to PLANNED
        patch_r = client.patch(
            f"/api/roadmap/items/{finding_id}",
            json={"scan_id": scan_id, "status": "PLANNED"},
        )
        assert patch_r.status_code == 200, patch_r.text

        # First recalculation
        r1 = client.get(f"/api/roadmap?scan_id={scan_id}")
        assert r1.status_code == 200
        items_r1 = {i["finding_id"]: i for i in r1.json()["items"]}
        assert items_r1[finding_id]["status"] == "PLANNED", \
            f"After 1st recalc: stage is '{items_r1[finding_id]['status']}'"

        # Second recalculation
        r2 = client.get(f"/api/roadmap?scan_id={scan_id}")
        assert r2.status_code == 200
        items_r2 = {i["finding_id"]: i for i in r2.json()["items"]}
        assert items_r2[finding_id]["status"] == "PLANNED", \
            f"After 2nd recalc: stage is '{items_r2[finding_id]['status']}'"

    def test_d_backward_stage_rejected(self):
        """Test D — backward stage transition is rejected with 422."""
        scan_id, finding_id = _create_completed_scan_with_findings(client)

        # Seed and advance to PILOT
        client.get(f"/api/roadmap?scan_id={scan_id}")
        for stage in ("ASSESSED", "PLANNED", "PILOT"):
            r = client.patch(
                f"/api/roadmap/items/{finding_id}",
                json={"scan_id": scan_id, "status": stage},
            )
            assert r.status_code == 200, f"Stage {stage} failed: {r.text}"

        # Try to go backward to ASSESSED — must fail
        bad_r = client.patch(
            f"/api/roadmap/items/{finding_id}",
            json={"scan_id": scan_id, "status": "ASSESSED"},
        )
        assert bad_r.status_code == 422, (
            f"Backward transition should be 422 but got {bad_r.status_code}: {bad_r.text}"
        )

    def test_e_invalid_stage_value_422(self):
        """Test D (extra) — completely invalid stage value is rejected."""
        scan_id, finding_id = _create_completed_scan_with_findings(client)
        client.get(f"/api/roadmap?scan_id={scan_id}")

        bad_r = client.patch(
            f"/api/roadmap/items/{finding_id}",
            json={"scan_id": scan_id, "status": "PENDING"},
        )
        assert bad_r.status_code == 422
