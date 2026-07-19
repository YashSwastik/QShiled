"""
tests/test_reports.py — Part 12: Reports API
=============================================

Follows the project-standard test pattern (mirrors test_dashboard.py):
  - Uses conftest.py global get_db override + TEST_SESSION
  - Creates test data via HTTP API (org → project → app → scan) and direct DB writes
  - clean_db autouse fixture clears data between tests

Coverage:
  ✓ GET /api/reports — no scan_id (returns list)
  ✓ GET /api/reports?scan_id= — with completed scan
  ✓ GET /api/reports/executive?scan_id= — JSON preview
  ✓ GET /api/reports/inventory?scan_id= — JSON preview
  ✓ GET /api/reports/roadmap?scan_id=   — JSON preview
  ✓ GET /api/reports/executive/pdf?scan_id= — PDF response (magic bytes)
  ✓ GET /api/reports/inventory/pdf?scan_id= — PDF response
  ✓ GET /api/reports/roadmap/pdf?scan_id=   — PDF response
  ✓ GET /api/reports/all?scan_id= — ZIP with exactly 3 PDFs
  ✓ 404 for nonexistent scan
  ✓ 409 for non-completed scan
  ✓ Empty project (no findings) — reports still generate
  ✓ Readiness score matches dashboard endpoint
  ✓ Inventory findings match findings API
  ✓ No private key material in inventory data
"""
from __future__ import annotations

import io
import re
import zipfile
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.scan import Scan, ScanStatus
from app.models.finding import CryptoFinding, QuantumStatus, FindingCategory
from app.models.risk_assessment import RiskAssessment
from app.models.base import new_uuid
from datetime import datetime, timezone


# ── Module-scoped client + db (same pattern as test_dashboard.py) ──────────────

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    from tests.conftest import TEST_SESSION
    session = TEST_SESSION()
    try:
        yield session
    finally:
        session.close()


# ── Helper: create scan via HTTP API (same pattern as test_dashboard.py) ───────

def _create_completed_scan(client: TestClient, suffix: str | None = None) -> dict:
    """Create org → project → app → scan via HTTP. Returns scan dict."""
    s = suffix or uuid.uuid4().hex[:8]

    org = client.post("/api/organizations", json={"name": f"RptOrg{s}", "slug": f"rpto{s}"})
    assert org.status_code in (200, 201), org.text
    org_id = org.json()["id"]

    proj = client.post("/api/projects", json={"name": f"RptProj{s}", "organization_id": org_id})
    assert proj.status_code in (200, 201), proj.text
    proj_id = proj.json()["id"]

    application = client.post("/api/applications", json={
        "name": f"RptApp{s}", "project_id": proj_id,
        "business_criticality": "high", "internet_exposed": True,
        "confidentiality_requirement": "long_term",
        "data_sensitivity": "restricted", "environment": "production",
    })
    assert application.status_code in (200, 201), application.text

    scan = client.post("/api/scans", json={
        "application_id": application.json()["id"],
        "name": f"RptScan{s}", "scan_type": "source_code",
    })
    assert scan.status_code in (200, 201), scan.text
    return scan.json()


def _mark_completed(db_session, scan_id: str) -> None:
    scan = db_session.get(Scan, scan_id)
    scan.status = ScanStatus.completed
    scan.completed_at = datetime.now(timezone.utc)
    scan.finding_count = 0
    db_session.commit()


# Map short category names to FindingCategory enum values
_CAT_MAP = {
    "public_key":  "QUANTUM_VULNERABLE_PUBLIC_KEY",
    "symmetric":   "SYMMETRIC",
    "hash":        "HASH",
    "legacy":      "LEGACY_DEPRECATED",
    "post_quantum": "POST_QUANTUM",
}


def _add_finding(db_session, scan_id: str, algorithm: str, qs: str, category: str) -> str:
    fid = new_uuid()
    cat_val = _CAT_MAP.get(category, category)  # resolve shorthand or use as-is
    db_session.add(CryptoFinding(
        id=fid, scan_id=scan_id,
        algorithm=algorithm, algorithm_family=algorithm.split("-")[0],
        category=FindingCategory(cat_val),
        quantum_status=QuantumStatus(qs),
        key_size=2048, usage_context="signing",
        file_path=f"src/{algorithm.lower().replace('-','_')}.py",
        line_number=10, confidence=0.9,
    ))
    db_session.commit()
    return fid


def _add_risk_assessment(db_session, scan_id: str, per_finding: list[dict]) -> None:
    existing = db_session.query(RiskAssessment).filter(RiskAssessment.scan_id == scan_id).first()
    if existing:
        existing.per_finding_scores = per_finding
        db_session.commit()
        return
    db_session.add(RiskAssessment(
        id=new_uuid(), scan_id=scan_id,
        per_finding_scores=per_finding,
    ))
    db_session.commit()


# ── Tests: list endpoint ──────────────────────────────────────────────────────

class TestReportsList:
    def test_list_no_scan_id_returns_200(self, client):
        r = client.get("/api/reports")
        assert r.status_code == 200
        data = r.json()
        assert "completed_scans" in data
        assert data["scan_id"] is None

    def test_list_with_completed_scan(self, client, db):
        scan = _create_completed_scan(client, "ls1")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports?scan_id={scan['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["scan_id"] == scan["id"]
        assert data["scan_ready"] is True
        keys = {rpt["key"] for rpt in data["available_reports"]}
        assert keys == {"executive", "inventory", "roadmap"}

    def test_list_with_unknown_scan(self, client):
        r = client.get("/api/reports?scan_id=nonexistent-id")
        # List endpoint is permissive — returns 200 with scan_ready=False
        assert r.status_code == 200


# ── Tests: executive preview ──────────────────────────────────────────────────

class TestExecutivePreview:
    def test_preview_returns_200(self, client, db):
        scan = _create_completed_scan(client, "ex1")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/executive?scan_id={scan['id']}")
        assert r.status_code == 200

    def test_preview_has_dashboard(self, client, db):
        scan = _create_completed_scan(client, "ex2")
        _mark_completed(db, scan["id"])
        data = client.get(f"/api/reports/executive?scan_id={scan['id']}").json()
        assert "dashboard" in data
        assert "quantum_readiness_score" in data["dashboard"]
        assert 0 <= data["dashboard"]["quantum_readiness_score"] <= 100

    def test_preview_has_recommendations(self, client, db):
        scan = _create_completed_scan(client, "ex3")
        _mark_completed(db, scan["id"])
        data = client.get(f"/api/reports/executive?scan_id={scan['id']}").json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_readiness_score_matches_dashboard_endpoint(self, client, db):
        """Readiness score must exactly match /api/dashboard for same scan."""
        scan = _create_completed_scan(client, "ex4")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [{
            "finding_id": fid, "quantum_migration_score": 85.0,
            "quantum_migration_severity": "Critical", "migration_priority": "critical",
        }])
        exec_data = client.get(f"/api/reports/executive?scan_id={scan['id']}").json()
        dash_data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        assert exec_data["dashboard"]["quantum_readiness_score"] == dash_data["quantum_readiness_score"]

    def test_preview_404_unknown_scan(self, client):
        r = client.get("/api/reports/executive?scan_id=does-not-exist")
        assert r.status_code == 404

    def test_preview_409_for_running_scan(self, client, db):
        scan = _create_completed_scan(client, "ex5")
        # Leave scan in running state (do not call _mark_completed)
        s = db.get(Scan, scan["id"])
        s.status = ScanStatus.running
        db.commit()
        r = client.get(f"/api/reports/executive?scan_id={scan['id']}")
        assert r.status_code == 409

    def test_empty_scan_preview_200(self, client, db):
        scan = _create_completed_scan(client, "ex6")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/executive?scan_id={scan['id']}")
        assert r.status_code == 200
        assert r.json()["dashboard"]["total_findings"] == 0


# ── Tests: inventory preview ──────────────────────────────────────────────────

class TestInventoryPreview:
    def test_preview_returns_200(self, client, db):
        scan = _create_completed_scan(client, "iv1")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/inventory?scan_id={scan['id']}")
        assert r.status_code == 200

    def test_preview_has_findings(self, client, db):
        scan = _create_completed_scan(client, "iv2")
        _mark_completed(db, scan["id"])
        _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_finding(db, scan["id"], "AES-256", "safe", "symmetric")
        data = client.get(f"/api/reports/inventory?scan_id={scan['id']}").json()
        assert "findings" in data
        assert len(data["findings"]) == 2

    def test_findings_match_findings_api(self, client, db):
        """Finding IDs in report must match /api/findings for same scan."""
        scan = _create_completed_scan(client, "iv3")
        _mark_completed(db, scan["id"])
        _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        inv_data = client.get(f"/api/reports/inventory?scan_id={scan['id']}").json()
        findings_data = client.get(f"/api/findings?scan_id={scan['id']}&page_size=200").json()
        inv_ids = {f["id"] for f in inv_data["findings"]}
        api_ids = {f["id"] for f in findings_data["items"]}
        assert inv_ids == api_ids

    def test_severity_map_present_when_risk_exists(self, client, db):
        scan = _create_completed_scan(client, "iv4")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [{
            "finding_id": fid, "quantum_migration_score": 80.0,
            "quantum_migration_severity": "Critical", "migration_priority": "critical",
        }])
        data = client.get(f"/api/reports/inventory?scan_id={scan['id']}").json()
        assert "severity_map" in data
        assert fid in data["severity_map"]

    def test_preview_404_unknown_scan(self, client):
        r = client.get("/api/reports/inventory?scan_id=does-not-exist")
        assert r.status_code == 404

    def test_empty_scan_returns_empty_findings(self, client, db):
        scan = _create_completed_scan(client, "iv5")
        _mark_completed(db, scan["id"])
        data = client.get(f"/api/reports/inventory?scan_id={scan['id']}").json()
        assert data["findings"] == []

    def test_no_private_key_material_in_findings(self, client, db):
        """Evidence fields must not contain private key material."""
        scan = _create_completed_scan(client, "iv6")
        _mark_completed(db, scan["id"])
        _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        data = client.get(f"/api/reports/inventory?scan_id={scan['id']}").json()
        for f in data["findings"]:
            for key in ["algorithm", "file_path", "usage_context"]:
                val = str(f.get(key) or "")
                assert "PRIVATE KEY" not in val
                assert "-----BEGIN" not in val


# ── Tests: roadmap preview ────────────────────────────────────────────────────

class TestRoadmapPreview:
    def test_preview_returns_200(self, client, db):
        scan = _create_completed_scan(client, "rm1")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/roadmap?scan_id={scan['id']}")
        assert r.status_code == 200

    def test_preview_has_roadmap_items(self, client, db):
        scan = _create_completed_scan(client, "rm2")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [{
            "finding_id": fid, "quantum_migration_score": 85.0,
            "quantum_migration_severity": "Critical", "migration_priority": "critical",
        }])
        data = client.get(f"/api/reports/roadmap?scan_id={scan['id']}").json()
        assert "roadmap" in data
        assert "items" in data["roadmap"]
        assert len(data["roadmap"]["items"]) > 0

    def test_preview_has_wave_summaries(self, client, db):
        scan = _create_completed_scan(client, "rm3")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [{
            "finding_id": fid, "quantum_migration_score": 85.0,
            "quantum_migration_severity": "Critical", "migration_priority": "critical",
        }])
        data = client.get(f"/api/reports/roadmap?scan_id={scan['id']}").json()
        assert "wave_summaries" in data["roadmap"]

    def test_preview_has_recommendations_list(self, client, db):
        scan = _create_completed_scan(client, "rm4")
        _mark_completed(db, scan["id"])
        data = client.get(f"/api/reports/roadmap?scan_id={scan['id']}").json()
        assert isinstance(data["recommendations"], list)

    def test_preview_404_unknown_scan(self, client):
        r = client.get("/api/reports/roadmap?scan_id=does-not-exist")
        assert r.status_code == 404

    def test_empty_scan_roadmap_items_empty(self, client, db):
        scan = _create_completed_scan(client, "rm5")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/roadmap?scan_id={scan['id']}")
        assert r.status_code == 200
        assert r.json()["roadmap"]["items"] == []


# ── Tests: PDF downloads ──────────────────────────────────────────────────────

class TestPdfDownloads:
    def _assert_pdf(self, response):
        assert response.status_code == 200
        assert "pdf" in response.headers.get("content-type", "")
        assert response.content[:4] == b"%PDF"

    def test_executive_pdf(self, client, db):
        scan = _create_completed_scan(client, "pd1")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/executive/pdf?scan_id={scan['id']}")
        self._assert_pdf(r)
        assert "Executive_Report" in r.headers.get("content-disposition", "")

    def test_inventory_pdf(self, client, db):
        scan = _create_completed_scan(client, "pd2")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/inventory/pdf?scan_id={scan['id']}")
        self._assert_pdf(r)
        assert "Technical_Inventory_Report" in r.headers.get("content-disposition", "")

    def test_roadmap_pdf(self, client, db):
        scan = _create_completed_scan(client, "pd3")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/roadmap/pdf?scan_id={scan['id']}")
        self._assert_pdf(r)
        assert "Migration_Roadmap_Report" in r.headers.get("content-disposition", "")

    def test_executive_pdf_with_findings(self, client, db):
        scan = _create_completed_scan(client, "pd4")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [{
            "finding_id": fid, "quantum_migration_score": 85.0,
            "quantum_migration_severity": "Critical", "migration_priority": "critical",
        }])
        r = client.get(f"/api/reports/executive/pdf?scan_id={scan['id']}")
        self._assert_pdf(r)

    def test_inventory_pdf_with_findings(self, client, db):
        scan = _create_completed_scan(client, "pd5")
        _mark_completed(db, scan["id"])
        _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_finding(db, scan["id"], "SHA-1", "borderline", "hash")
        r = client.get(f"/api/reports/inventory/pdf?scan_id={scan['id']}")
        self._assert_pdf(r)

    def test_empty_scan_pdfs_still_generated(self, client, db):
        """PDFs must be generated cleanly even with no findings."""
        scan = _create_completed_scan(client, "pd6")
        _mark_completed(db, scan["id"])
        for ep in ["executive", "inventory", "roadmap"]:
            r = client.get(f"/api/reports/{ep}/pdf?scan_id={scan['id']}")
            self._assert_pdf(r)

    def test_pdf_404_unknown_scan(self, client):
        for ep in ["executive", "inventory", "roadmap"]:
            r = client.get(f"/api/reports/{ep}/pdf?scan_id=nonexistent")
            assert r.status_code == 404

    def test_pdf_409_running_scan(self, client, db):
        scan = _create_completed_scan(client, "pd7")
        s = db.get(Scan, scan["id"])
        s.status = ScanStatus.running
        db.commit()
        for ep in ["executive", "inventory", "roadmap"]:
            r = client.get(f"/api/reports/{ep}/pdf?scan_id={scan['id']}")
            assert r.status_code == 409


# ── Tests: ZIP bundle ──────────────────────────────────────────────────────────

class TestZipBundle:
    def test_zip_returns_200_and_zip_content_type(self, client, db):
        scan = _create_completed_scan(client, "zp1")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/all?scan_id={scan['id']}")
        assert r.status_code == 200
        assert "zip" in r.headers.get("content-type", "")

    def test_zip_contains_exactly_three_pdfs(self, client, db):
        scan = _create_completed_scan(client, "zp2")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/all?scan_id={scan['id']}")
        buf = io.BytesIO(r.content)
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
        assert len(names) == 3
        assert any("Executive_Report" in n for n in names)
        assert any("Technical_Inventory_Report" in n for n in names)
        assert any("Migration_Roadmap_Report" in n for n in names)

    def test_zip_pdfs_are_valid_pdfs(self, client, db):
        scan = _create_completed_scan(client, "zp3")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/all?scan_id={scan['id']}")
        buf = io.BytesIO(r.content)
        with zipfile.ZipFile(buf, "r") as zf:
            for name in zf.namelist():
                assert zf.read(name)[:4] == b"%PDF", f"{name} is not a valid PDF"

    def test_zip_filename_contains_qshield_reports(self, client, db):
        scan = _create_completed_scan(client, "zp4")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/all?scan_id={scan['id']}")
        cd = r.headers.get("content-disposition", "")
        assert "QShield_Reports" in cd

    def test_zip_empty_scan_still_produces_three_pdfs(self, client, db):
        scan = _create_completed_scan(client, "zp5")
        _mark_completed(db, scan["id"])
        r = client.get(f"/api/reports/all?scan_id={scan['id']}")
        assert r.status_code == 200
        buf = io.BytesIO(r.content)
        with zipfile.ZipFile(buf, "r") as zf:
            assert len(zf.namelist()) == 3

    def test_zip_with_multiple_findings(self, client, db):
        scan = _create_completed_scan(client, "zp6")
        _mark_completed(db, scan["id"])
        fid1 = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        fid2 = _add_finding(db, scan["id"], "AES-256", "safe", "symmetric")
        _add_risk_assessment(db, scan["id"], [
            {"finding_id": fid1, "quantum_migration_score": 85.0, "quantum_migration_severity": "Critical", "migration_priority": "critical"},
            {"finding_id": fid2, "quantum_migration_score": 5.0, "quantum_migration_severity": "Low", "migration_priority": "low"},
        ])
        r = client.get(f"/api/reports/all?scan_id={scan['id']}")
        assert r.status_code == 200
        buf = io.BytesIO(r.content)
        with zipfile.ZipFile(buf, "r") as zf:
            assert len(zf.namelist()) == 3

    def test_zip_404_unknown_scan(self, client):
        r = client.get("/api/reports/all?scan_id=nonexistent")
        assert r.status_code == 404

    def test_zip_409_running_scan(self, client, db):
        scan = _create_completed_scan(client, "zp7")
        s = db.get(Scan, scan["id"])
        s.status = ScanStatus.running
        db.commit()
        r = client.get(f"/api/reports/all?scan_id={scan['id']}")
        assert r.status_code == 409


# ── Tests: data consistency ────────────────────────────────────────────────────

class TestDataConsistency:
    def test_readiness_score_in_valid_range(self, client, db):
        scan = _create_completed_scan(client, "dc1")
        _mark_completed(db, scan["id"])
        data = client.get(f"/api/reports/executive?scan_id={scan['id']}").json()
        assert 0 <= data["dashboard"]["quantum_readiness_score"] <= 100

    def test_severity_map_ids_are_real_finding_ids(self, client, db):
        scan = _create_completed_scan(client, "dc2")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [
            {"finding_id": fid, "quantum_migration_score": 80.0,
             "quantum_migration_severity": "Critical", "migration_priority": "critical"}
        ])
        inv_data = client.get(f"/api/reports/inventory?scan_id={scan['id']}").json()
        finding_ids = {f["id"] for f in inv_data["findings"]}
        sev_ids = set(inv_data["severity_map"].keys())
        # All severity map IDs correspond to real findings
        assert sev_ids.issubset(finding_ids)

    def test_roadmap_stages_are_valid(self, client, db):
        scan = _create_completed_scan(client, "dc3")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [
            {"finding_id": fid, "quantum_migration_score": 85.0,
             "quantum_migration_severity": "Critical", "migration_priority": "critical"}
        ])
        data = client.get(f"/api/reports/roadmap?scan_id={scan['id']}").json()
        valid = {"DISCOVERED","ASSESSED","PLANNED","PILOT","TRANSITION","VALIDATION","MIGRATED"}
        for item in data["roadmap"]["items"]:
            assert item["stage"] in valid

    def test_executive_and_dashboard_consistent(self, client, db):
        scan = _create_completed_scan(client, "dc4")
        _mark_completed(db, scan["id"])
        fid = _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_risk_assessment(db, scan["id"], [
            {"finding_id": fid, "quantum_migration_score": 75.0,
             "quantum_migration_severity": "High", "migration_priority": "high"}
        ])
        exec_data = client.get(f"/api/reports/executive?scan_id={scan['id']}").json()
        dash_data = client.get(f"/api/dashboard?scan_id={scan['id']}").json()
        # Total findings must match
        assert exec_data["dashboard"]["total_findings"] == dash_data["total_findings"]
        # Readiness score must match
        assert exec_data["dashboard"]["quantum_readiness_score"] == dash_data["quantum_readiness_score"]

    def test_inventory_quantum_status_correct(self, client, db):
        scan = _create_completed_scan(client, "dc5")
        _mark_completed(db, scan["id"])
        _add_finding(db, scan["id"], "RSA-2048", "vulnerable", "public_key")
        _add_finding(db, scan["id"], "AES-256", "safe", "symmetric")
        inv = client.get(f"/api/reports/inventory?scan_id={scan['id']}").json()
        qs_vals = {f["quantum_status"] for f in inv["findings"]}
        assert "vulnerable" in qs_vals
        assert "safe" in qs_vals
