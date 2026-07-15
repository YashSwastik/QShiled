"""
Tests for the QShield Dashboard API  (GET /api/dashboard and /api/dashboard/scans).

Covers:
  1.  Empty project (no scans) — /scans returns []
  2.  Scan with no findings — readiness defaults correctly
  3.  Scan with quantum-vulnerable findings — readiness drops
  4.  Scan with mixed risk levels — severity distribution correct
  5.  Deterministic Quantum Readiness Score — formula verification
  6.  Readiness score changes when risk state changes (finding added)
  7.  Migration progress / readiness changes when roadmap stages change
  8.  Dashboard aggregation uses real persisted data (not cached/hardcoded)
  9.  No regression to roadmap stage persistence
  10. Completed scan with safe-only findings — readiness high
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.finding import CryptoFinding, QuantumStatus, FindingCategory, DetectionMethod
from app.models.scan import Scan, ScanStatus
from app.models.risk_assessment import RiskAssessment
from app.models.roadmap import RoadmapItem as RoadmapItemORM, EffortEstimate
from app.models.base import new_uuid
from app.routers.dashboard import _compute_readiness

# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from tests.conftest import TEST_SESSION
    with TestClient(app) as c:
        yield c


# Reusable DB session from conftest
@pytest.fixture(scope="module")
def db():
    from tests.conftest import TEST_SESSION
    session = TEST_SESSION()
    try:
        yield session
    finally:
        session.close()


def _make_ids() -> tuple[str, str, str, str]:
    """Return (org_id, proj_id, app_id, scan_id) via API calls."""
    # Can't call API inside this helper — use db directly instead
    return (new_uuid(), new_uuid(), new_uuid(), new_uuid())


def _create_completed_scan(client: TestClient, suffix: str | None = None) -> dict:
    """Create org → project → app → completed scan via HTTP. Returns scan dict."""
    s = suffix or uuid.uuid4().hex[:8]

    org = client.post("/api/organizations", json={"name": f"DashOrg{s}", "slug": f"dasho{s}"})
    assert org.status_code in (200, 201), org.text
    org_id = org.json()["id"]

    proj = client.post("/api/projects", json={"name": f"DashProj{s}", "organization_id": org_id})
    assert proj.status_code in (200, 201)
    proj_id = proj.json()["id"]

    application = client.post("/api/applications", json={
        "name": f"DashApp{s}",
        "project_id": proj_id,
        "business_criticality": "critical",
        "internet_exposed": True,
        "confidentiality_requirement": "long_term",
        "data_sensitivity": "restricted",
        "environment": "production",
    })
    assert application.status_code in (200, 201)
    app_id = application.json()["id"]

    scan = client.post("/api/scans", json={
        "application_id": app_id,
        "name": f"DashScan{s}",
        "scan_type": "source_code",
    })
    assert scan.status_code in (200, 201)
    return scan.json()


def _mark_scan_completed(db_session, scan_id: str) -> None:
    """Mark scan as completed in the test DB."""
    scan = db_session.get(Scan, scan_id)
    assert scan is not None
    scan.status = ScanStatus.completed
    scan.finding_count = 0
    db_session.commit()


def _add_finding(db_session, scan_id: str, qs: QuantumStatus, risk_score: float | None = None) -> str:
    """Insert a CryptoFinding. Returns finding_id."""
    fid = new_uuid()
    f = CryptoFinding(
        id=fid,
        scan_id=scan_id,
        algorithm="RSA-2048",
        algorithm_family="RSA",
        category=FindingCategory.QUANTUM_VULNERABLE_PUBLIC_KEY,
        quantum_status=qs,
        key_size=2048,
        usage_context="signing",
        confidence=0.95,
        file_path="src/auth.py",
        line_number=42,
        risk_score=risk_score,
    )
    db_session.add(f)
    db_session.commit()
    return fid


def _add_risk_assessment(db_session, scan_id: str, per_finding: list[dict]) -> None:
    """Upsert a RiskAssessment with per_finding_scores."""
    existing = db_session.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
    if existing:
        existing.per_finding_scores = per_finding
        existing.overall_risk_score = sum(e.get("quantum_migration_score", 0) for e in per_finding) / max(len(per_finding), 1)
        db_session.commit()
        return
    ra = RiskAssessment(
        id=new_uuid(),
        scan_id=scan_id,
        overall_risk_score=sum(e.get("quantum_migration_score", 0) for e in per_finding) / max(len(per_finding), 1),
        per_finding_scores=per_finding,
    )
    db_session.add(ra)
    db_session.commit()


def _add_roadmap_item(db_session, scan_id: str, finding_id: str, wave: int, stage: str = "DISCOVERED") -> str:
    rid = new_uuid()
    item = RoadmapItemORM(
        id=rid,
        scan_id=scan_id,
        finding_id=finding_id,
        priority=wave,
        effort_estimate=EffortEstimate.medium,
        replacement_algorithm="ML-KEM-768",
        status="pending",
        stage=stage,
    )
    db_session.add(item)
    db_session.commit()
    return rid


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDashboardScans:
    """Test GET /api/dashboard/scans."""

    def test_empty_project_returns_empty_or_list(self, client):
        """List endpoint returns [] or at least a list when no scans exist."""
        r = client.get("/api/dashboard/scans")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_completed_scan_appears_in_list(self, client, db):
        scan = _create_completed_scan(client, "ls1")
        _mark_scan_completed(db, scan["id"])
        r = client.get("/api/dashboard/scans")
        assert r.status_code == 200
        ids = [s["scan_id"] for s in r.json()]
        assert scan["id"] in ids

    def test_scan_option_has_application_name(self, client, db):
        scan = _create_completed_scan(client, "ls2")
        r = client.get("/api/dashboard/scans")
        assert r.status_code == 200
        entry = next((s for s in r.json() if s["scan_id"] == scan["id"]), None)
        assert entry is not None
        assert "application_name" in entry
        assert entry["application_name"] != ""


class TestDashboardNoFindings:
    """Completed scan with no crypto findings."""

    def test_dashboard_returns_200_no_findings(self, client, db):
        scan = _create_completed_scan(client, "nf1")
        _mark_scan_completed(db, scan["id"])
        r = client.get(f"/api/dashboard?scan_id={scan['id']}")
        assert r.status_code == 200

    def test_no_findings_total_is_zero(self, client, db):
        scan = _create_completed_scan(client, "nf2")
        _mark_scan_completed(db, scan["id"])
        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert data["total_findings"] == 0
        assert data["quantum_relevant_findings"] == 0

    def test_no_findings_readiness_is_100(self, client, db):
        """With no findings and no roadmap items, all components = 1.0 → score = 100."""
        scan = _create_completed_scan(client, "nf3")
        _mark_scan_completed(db, scan["id"])
        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert data["quantum_readiness_score"] == 100

    def test_no_findings_readiness_label_high(self, client, db):
        scan = _create_completed_scan(client, "nf4")
        _mark_scan_completed(db, scan["id"])
        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert "High" in data["readiness_label"]


class TestDashboardWithFindings:
    """Completed scan with quantum-vulnerable findings."""

    def test_vulnerable_findings_reduce_readiness(self, client, db):
        scan = _create_completed_scan(client, "vf1")
        _mark_scan_completed(db, scan["id"])
        _add_finding(db, scan["id"], QuantumStatus.vulnerable, risk_score=85.0)
        _add_finding(db, scan["id"], QuantumStatus.vulnerable, risk_score=80.0)

        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert data["total_findings"] == 2
        assert data["quantum_relevant_findings"] == 2
        assert data["quantum_readiness_score"] < 100

    def test_algorithm_distribution_populated(self, client, db):
        scan = _create_completed_scan(client, "vf2")
        _mark_scan_completed(db, scan["id"])
        _add_finding(db, scan["id"], QuantumStatus.vulnerable)
        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert len(data["algorithm_distribution"]) >= 1
        assert data["algorithm_distribution"][0]["family"] == "RSA"
        assert data["algorithm_distribution"][0]["count"] == 1

    def test_safe_findings_increase_readiness(self, client, db):
        """All safe findings → high readiness."""
        s1 = _create_completed_scan(client, "sf1")
        s2 = _create_completed_scan(client, "sf2")
        _mark_scan_completed(db, s1["id"])
        _mark_scan_completed(db, s2["id"])

        for _ in range(3):
            _add_finding(db, s1["id"], QuantumStatus.vulnerable, 80.0)

        for _ in range(3):
            _add_finding(db, s2["id"], QuantumStatus.safe, 5.0)

        d1 = client.get(f"/api/dashboard?scan_id={s1['id']}").json()
        d2 = client.get(f"/api/dashboard?scan_id={s2['id']}").json()
        assert d2["quantum_readiness_score"] > d1["quantum_readiness_score"]


class TestDashboardSeverityDistribution:
    """Risk severity distribution from persisted RiskAssessment."""

    def test_severity_distribution_uses_risk_assessment(self, client, db):
        scan = _create_completed_scan(client, "sd1")
        _mark_scan_completed(db, scan["id"])

        fid = _add_finding(db, scan["id"], QuantumStatus.vulnerable)
        _add_risk_assessment(db, scan["id"], [{
            "finding_id": fid,
            "quantum_migration_score": 90.0,
            "quantum_migration_severity": "Critical",
            "migration_priority": "immediate",
        }])

        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        sev_map = {s["severity"]: s["count"] for s in data["severity_distribution"]}
        assert sev_map.get("Critical", 0) == 1

    def test_multiple_risk_levels_appear(self, client, db):
        scan = _create_completed_scan(client, "sd2")
        _mark_scan_completed(db, scan["id"])

        f1 = _add_finding(db, scan["id"], QuantumStatus.vulnerable)
        f2 = _add_finding(db, scan["id"], QuantumStatus.borderline)
        f3 = _add_finding(db, scan["id"], QuantumStatus.safe)

        _add_risk_assessment(db, scan["id"], [
            {"finding_id": f1, "quantum_migration_score": 88.0, "quantum_migration_severity": "Critical", "migration_priority": "immediate"},
            {"finding_id": f2, "quantum_migration_score": 45.0, "quantum_migration_severity": "Moderate", "migration_priority": "near_term"},
            {"finding_id": f3, "quantum_migration_score": 5.0, "quantum_migration_severity": "Low", "migration_priority": "low"},
        ])

        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        sev_map = {s["severity"]: s["count"] for s in data["severity_distribution"]}
        assert sev_map.get("Critical", 0) >= 1
        assert sev_map.get("Moderate", 0) >= 1


class TestQuantumReadinessScore:
    """Pure-unit tests for the _compute_readiness formula."""

    def test_no_data_returns_100(self):
        score, m = _compute_readiness(0, 0, None, 0, 0)
        assert score == 100
        assert m.s_exposure == 1.0
        assert m.s_risk_inv == 1.0
        assert m.s_progress == 1.0

    def test_all_vulnerable_no_progress_low_score(self):
        # 4 vulnerable, avg risk 80, 0 migrated/4 roadmap
        score, _ = _compute_readiness(4, 4, 80.0, 4, 0)
        # S_exposure=0, S_risk_inv=0.2, S_progress=0 → 0+5+0 = 5
        assert score == 5

    def test_all_safe_and_migrated_returns_100(self):
        # 4 safe findings, avg risk 0, all 4 roadmap items MIGRATED
        score, _ = _compute_readiness(4, 0, 0.0, 4, 4)
        # S_exposure=1, S_risk_inv=1, S_progress=1 → 60+25+15 = 100
        assert score == 100

    def test_partial_progress_increases_score(self):
        # Same findings, half migrated vs none migrated
        score_none, _ = _compute_readiness(2, 2, 70.0, 4, 0)
        score_half, _ = _compute_readiness(2, 2, 70.0, 4, 2)
        assert score_half > score_none

    def test_score_clamped_to_100(self):
        score, _ = _compute_readiness(0, 0, None, 0, 0)
        assert 0 <= score <= 100

    def test_score_clamped_to_0(self):
        # Worst case: 100% vulnerable, avg_risk=100, 0 migrated of many items
        score, _ = _compute_readiness(10, 10, 100.0, 10, 0)
        assert score >= 0

    def test_methodology_components_sum_to_100_weights(self):
        """Weight sanity: 60 + 25 + 15 = 100."""
        from app.routers.dashboard import ReadinessMethodology
        assert ReadinessMethodology.__fields__  # is a pydantic model
        _, m = _compute_readiness(1, 1, 50.0, 2, 1)
        total_weight = (
            m.component_exposure_weight
            + m.component_risk_weight
            + m.component_progress_weight
        )
        assert abs(total_weight - 1.0) < 1e-9


class TestReadinessChangesWithState:
    """Readiness score changes deterministically as DB state changes."""

    def test_adding_vulnerable_finding_decreases_score(self, client, db):
        scan = _create_completed_scan(client, "rc1")
        _mark_scan_completed(db, scan["id"])

        d_before = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        _add_finding(db, scan["id"], QuantumStatus.vulnerable, 90.0)
        d_after = client.get(f"/api/dashboard?scan_id={scan['id']}").json()

        assert d_after["quantum_readiness_score"] < d_before["quantum_readiness_score"]

    def test_advancing_roadmap_stage_increases_score(self, client, db):
        scan = _create_completed_scan(client, "rc2")
        _mark_scan_completed(db, scan["id"])

        fid = _add_finding(db, scan["id"], QuantumStatus.vulnerable, 80.0)
        rid = _add_roadmap_item(db, scan["id"], fid, wave=1, stage="DISCOVERED")

        d_before = client.get(f"/api/dashboard?scan_id={scan['id']}").json()

        # Advance to MIGRATED
        item = db.get(RoadmapItemORM, rid)
        item.stage = "MIGRATED"
        db.commit()

        d_after = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert d_after["quantum_readiness_score"] > d_before["quantum_readiness_score"]


class TestMigrationStatus:
    """Migration progress and stage distribution."""

    def test_stage_distribution_reflects_persisted_stages(self, client, db):
        scan = _create_completed_scan(client, "ms1")
        _mark_scan_completed(db, scan["id"])

        f1 = _add_finding(db, scan["id"], QuantumStatus.vulnerable)
        f2 = _add_finding(db, scan["id"], QuantumStatus.vulnerable)
        _add_roadmap_item(db, scan["id"], f1, wave=1, stage="ASSESSED")
        _add_roadmap_item(db, scan["id"], f2, wave=1, stage="MIGRATED")

        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        stage_map = {s["stage"]: s["count"] for s in data["stage_distribution"]}
        assert stage_map.get("ASSESSED", 0) == 1
        assert stage_map.get("MIGRATED", 0) == 1

    def test_migration_progress_pct_nonzero_when_items_exist(self, client, db):
        scan = _create_completed_scan(client, "ms2")
        _mark_scan_completed(db, scan["id"])

        fid = _add_finding(db, scan["id"], QuantumStatus.vulnerable)
        _add_roadmap_item(db, scan["id"], fid, wave=1, stage="PLANNED")

        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert data["migration_progress_pct"] > 0.0

    def test_wave_distribution_matches_roadmap_priority(self, client, db):
        scan = _create_completed_scan(client, "ms3")
        _mark_scan_completed(db, scan["id"])

        f1 = _add_finding(db, scan["id"], QuantumStatus.vulnerable)
        f2 = _add_finding(db, scan["id"], QuantumStatus.borderline)
        _add_roadmap_item(db, scan["id"], f1, wave=1)
        _add_roadmap_item(db, scan["id"], f2, wave=2)

        data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        wave_map = {w["wave"]: w["count"] for w in data["wave_distribution"]}
        assert wave_map.get(1, 0) == 1
        assert wave_map.get(2, 0) == 1


class TestRoadmapStageRegressionDashboard:
    """Regression: dashboard must not break roadmap stage persistence."""

    def test_dashboard_does_not_reset_roadmap_stages(self, client, db):
        """Calling GET /api/dashboard must NOT write to roadmap_items."""
        scan = _create_completed_scan(client, "rr1")
        _mark_scan_completed(db, scan["id"])

        fid = _add_finding(db, scan["id"], QuantumStatus.vulnerable, 80.0)
        rid = _add_roadmap_item(db, scan["id"], fid, wave=1, stage="PLANNED")

        # Call dashboard twice
        client.get(f"/api/dashboard?scan_id={scan['id']}")
        client.get(f"/api/dashboard?scan_id={scan['id']}")

        # Stage must still be PLANNED
        db.expire_all()
        item = db.get(RoadmapItemORM, rid)
        assert item.stage == "PLANNED"

    def test_dashboard_404_for_unknown_scan(self, client):
        r = client.get(f"/api/dashboard?scan_id={new_uuid()}")
        assert r.status_code == 404
