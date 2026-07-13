"""
Phase 1 integration tests — CRUD verification for:
Organization, Project, Application, Scan

In-memory DB and TestClient are set up in conftest.py.
"""
import pytest
from fastapi.testclient import TestClient


# ── Data helpers ──────────────────────────────────────────────────────────────

def make_org(client: TestClient, slug: str = "acme", name: str = "Acme Corp") -> dict:
    r = client.post("/api/organizations", json={"name": name, "slug": slug})
    assert r.status_code == 201, r.text
    return r.json()


def make_project(client: TestClient, org_id: str, name: str = "Audit Q3") -> dict:
    r = client.post("/api/projects", json={"organization_id": org_id, "name": name})
    assert r.status_code == 201, r.text
    return r.json()


def make_app(client: TestClient, project_id: str, name: str = "Gateway") -> dict:
    r = client.post("/api/applications", json={
        "project_id": project_id,
        "name": name,
        "business_criticality": "critical",
        "environment": "production",
        "internet_exposed": True,
        "data_sensitivity": "restricted",
        "confidentiality_requirement": "long_term",
        "data_lifetime_years": 10,
    })
    assert r.status_code == 201, r.text
    return r.json()


def make_scan(client: TestClient, app_id: str, name: str = "Scan 1") -> dict:
    r = client.post("/api/scans", json={"application_id": app_id, "name": name})
    assert r.status_code == 201, r.text
    return r.json()


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Organization ──────────────────────────────────────────────────────────────

def test_create_organization(client):
    r = client.post("/api/organizations", json={"name": "Test Org", "slug": "test-org"})
    assert r.status_code == 201
    d = r.json()
    assert d["name"] == "Test Org" and d["slug"] == "test-org"
    assert "id" in d and "created_at" in d


def test_org_duplicate_slug(client):
    make_org(client, "dup-org")
    r = client.post("/api/organizations", json={"name": "Another", "slug": "dup-org"})
    assert r.status_code == 409


def test_org_invalid_slug(client):
    r = client.post("/api/organizations", json={"name": "Bad", "slug": "Bad Slug!"})
    assert r.status_code == 422


def test_list_organizations(client):
    make_org(client)
    r = client.get("/api/organizations")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ── Project ───────────────────────────────────────────────────────────────────

def test_create_project(client):
    org = make_org(client)
    r = client.post("/api/projects", json={"organization_id": org["id"], "name": "P1"})
    assert r.status_code == 201
    d = r.json()
    assert d["status"] == "active" and d["organization_id"] == org["id"]


def test_project_bad_org(client):
    r = client.post("/api/projects", json={"organization_id": "nope", "name": "X"})
    assert r.status_code == 404


def test_list_projects(client):
    org = make_org(client)
    make_project(client, org["id"])
    r = client.get(f"/api/projects?organization_id={org['id']}")
    assert r.status_code == 200 and r.json()["total"] >= 1


def test_get_project(client):
    org = make_org(client)
    p = make_project(client, org["id"])
    r = client.get(f"/api/projects/{p['id']}")
    assert r.status_code == 200 and r.json()["id"] == p["id"]


def test_get_project_not_found(client):
    assert client.get("/api/projects/does-not-exist").status_code == 404


def test_update_project(client):
    org = make_org(client)
    p = make_project(client, org["id"])
    r = client.patch(f"/api/projects/{p['id']}", json={"status": "completed"})
    assert r.status_code == 200 and r.json()["status"] == "completed"


def test_delete_project(client):
    org = make_org(client)
    p = make_project(client, org["id"])
    assert client.delete(f"/api/projects/{p['id']}").status_code == 204
    assert client.get(f"/api/projects/{p['id']}").status_code == 404


# ── Application ───────────────────────────────────────────────────────────────

def test_create_application(client):
    org = make_org(client)
    p = make_project(client, org["id"])
    r = client.post("/api/applications", json={
        "project_id": p["id"], "name": "Auth",
        "business_criticality": "high", "environment": "production",
        "internet_exposed": True, "data_sensitivity": "restricted",
        "confidentiality_requirement": "long_term", "data_lifetime_years": 15,
    })
    assert r.status_code == 201
    d = r.json()
    assert d["business_criticality"] == "high" and d["internet_exposed"] is True


def test_application_bad_project(client):
    r = client.post("/api/applications", json={"project_id": "bad", "name": "X"})
    assert r.status_code == 404


def test_list_applications(client):
    org = make_org(client); p = make_project(client, org["id"]); make_app(client, p["id"])
    r = client.get(f"/api/applications?project_id={p['id']}")
    assert r.status_code == 200 and r.json()["total"] >= 1


def test_get_application(client):
    org = make_org(client); p = make_project(client, org["id"]); a = make_app(client, p["id"])
    r = client.get(f"/api/applications/{a['id']}")
    assert r.status_code == 200 and r.json()["id"] == a["id"]


def test_update_application(client):
    org = make_org(client); p = make_project(client, org["id"]); a = make_app(client, p["id"])
    r = client.patch(f"/api/applications/{a['id']}", json={"internet_exposed": False, "data_lifetime_years": 3})
    assert r.status_code == 200
    d = r.json()
    assert d["internet_exposed"] is False and d["data_lifetime_years"] == 3


def test_delete_application(client):
    org = make_org(client); p = make_project(client, org["id"]); a = make_app(client, p["id"])
    assert client.delete(f"/api/applications/{a['id']}").status_code == 204
    assert client.get(f"/api/applications/{a['id']}").status_code == 404


# ── Scan ──────────────────────────────────────────────────────────────────────

def test_create_scan(client):
    org = make_org(client); p = make_project(client, org["id"]); a = make_app(client, p["id"])
    r = client.post("/api/scans", json={"application_id": a["id"], "name": "Scan 1", "scan_type": "source_code"})
    assert r.status_code == 201
    d = r.json()
    assert d["status"] == "queued" and d["file_count"] == 0 and d["overall_risk_score"] is None


def test_scan_bad_app(client):
    r = client.post("/api/scans", json={"application_id": "no-app", "name": "X"})
    assert r.status_code == 404


def test_scan_status(client):
    org = make_org(client); p = make_project(client, org["id"]); a = make_app(client, p["id"])
    scan = make_scan(client, a["id"])
    r = client.get(f"/api/scans/{scan['id']}/status")
    assert r.status_code == 200 and r.json()["status"] == "queued"


def test_delete_scan(client):
    org = make_org(client); p = make_project(client, org["id"]); a = make_app(client, p["id"])
    scan = make_scan(client, a["id"])
    assert client.delete(f"/api/scans/{scan['id']}").status_code == 204
    assert client.get(f"/api/scans/{scan['id']}").status_code == 404


def test_list_scans(client):
    org = make_org(client); p = make_project(client, org["id"]); a = make_app(client, p["id"])
    make_scan(client, a["id"])
    r = client.get(f"/api/scans?application_id={a['id']}")
    assert r.status_code == 200 and r.json()["total"] >= 1


# ── Stub endpoints ────────────────────────────────────────────────────────────

def test_stub_endpoints(client):
    # /api/risk is now a real endpoint; calling without scan_id returns 422 (validation error)
    r = client.get("/api/risk")
    assert r.status_code == 422  # missing required scan_id param

    # Remaining stubs still return 200 with a phase/detail key
    for path in ["/api/roadmap", "/api/pqc-lab", "/api/reports"]:
        r = client.get(path)
        assert r.status_code == 200 and "phase" in r.json()
