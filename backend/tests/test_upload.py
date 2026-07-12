"""
Phase B security tests — Secure File Ingestion.

Tests:
  1. Valid ZIP upload → scan created, file_count correct
  2. Valid single file upload → scan created
  3. Nested supported files inside ZIP
  4. Unsupported file extension → scan failed state
  5. Malformed ZIP → scan failed state
  6. ZIP entry with ../ traversal → IngestionError raised
  7. Absolute-path archive entry → IngestionError raised
  8. Oversized upload
  9. Empty archive
  10. Cleanup behavior (no leftover temp dirs)
  11. Invalid application reference → 404

All tests use the real ingestion service (unit-level) and the HTTP endpoint.
"""
import io
import os
import zipfile
import tempfile

import pytest

from app.services.ingestion import ingest_upload, IngestionError, ALLOWED_EXTENSIONS


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_zip(entries: dict[str, bytes]) -> bytes:
    """Build an in-memory ZIP with given {path: content} entries."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _upload(client, application_id: str, filename: str, content: bytes):
    return client.post(
        "/api/scans/upload",
        data={"application_id": application_id},
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
    )


# ── Fixtures from conftest ─────────────────────────────────────────────────────

def _make_stack(client):
    """Create org → project → application and return app_id."""
    org = client.post("/api/organizations", json={"name": "Test", "slug": f"test-{os.urandom(4).hex()}"}).json()
    project = client.post("/api/projects", json={"organization_id": org["id"], "name": "P"}).json()
    app = client.post("/api/applications", json={"project_id": project["id"], "name": "A"}).json()
    return app["id"]


# ════════════════════════════════════════════════════════════════════════════
# Unit tests for ingestion service (no HTTP)
# ════════════════════════════════════════════════════════════════════════════

class TestIngestionUnit:

    def test_valid_zip_single_py(self):
        data = _make_zip({"main.py": b"import os"})
        result = ingest_upload("upload.zip", io.BytesIO(data))
        assert result.file_count == 1
        assert result.upload_type == "zip"
        assert result.supported_files[0].endswith("main.py")

    def test_valid_zip_nested_files(self):
        data = _make_zip({
            "src/auth.py": b"import ssl",
            "src/config.yaml": b"key: value",
            "ignored.exe": b"binary",
        })
        result = ingest_upload("repo.zip", io.BytesIO(data))
        assert result.file_count == 2
        assert any("auth.py" in f for f in result.supported_files)
        assert any("config.yaml" in f for f in result.supported_files)
        assert any("ignored.exe" in f for f in result.skipped_files)

    def test_valid_single_py(self):
        result = ingest_upload("main.py", io.BytesIO(b"import hashlib"))
        assert result.file_count == 1
        assert result.upload_type == "single_file"

    def test_valid_single_pem(self):
        result = ingest_upload("cert.pem", io.BytesIO(b"-----BEGIN CERTIFICATE-----"))
        assert result.file_count == 1

    def test_unsupported_extension_single(self):
        with pytest.raises(IngestionError, match="not supported"):
            ingest_upload("payload.exe", io.BytesIO(b"MZ"))

    def test_malformed_zip(self):
        with pytest.raises(IngestionError, match="valid ZIP"):
            ingest_upload("bad.zip", io.BytesIO(b"not a zip file at all"))

    def test_empty_archive(self):
        # Build ZIP with only a directory entry
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.mkdir("emptydir") if hasattr(zf, 'mkdir') else zf.writestr("emptydir/", "")
        with pytest.raises(IngestionError, match="empty"):
            ingest_upload("empty.zip", io.BytesIO(buf.getvalue()))

    def test_zip_path_traversal_dotdot(self):
        """ZIP entry with ../ must be rejected."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            info = zipfile.ZipInfo("../../evil.py")
            zf.writestr(info, b"evil code")
        with pytest.raises(IngestionError, match="traversal"):
            ingest_upload("traversal.zip", io.BytesIO(buf.getvalue()))

    def test_zip_absolute_path(self):
        """ZIP entry with absolute path must be rejected (absolute check or escape check)."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            info = zipfile.ZipInfo("/etc/passwd")
            zf.writestr(info, b"root:x:0:0")
        with pytest.raises(IngestionError):
            ingest_upload("absolute.zip", io.BytesIO(buf.getvalue()))

    def test_oversized_upload(self):
        large = b"x" * (1024 * 1024)  # 1 MB
        with pytest.raises(IngestionError, match="exceeds"):
            ingest_upload("big.py", io.BytesIO(large), max_bytes=512)

    def test_empty_file(self):
        with pytest.raises(IngestionError, match="empty"):
            ingest_upload("main.py", io.BytesIO(b""))

    def test_cleanup_no_leftover_temp(self):
        """No temp directories should persist after ingestion."""
        import tempfile as _tf
        tmp_before = set(os.listdir(_tf.gettempdir()))
        data = _make_zip({"main.py": b"import os"})
        ingest_upload("upload.zip", io.BytesIO(data))
        tmp_after = set(os.listdir(_tf.gettempdir()))
        leftover = {d for d in (tmp_after - tmp_before) if d.startswith("qshield_ingest_")}
        assert not leftover, f"Temp dirs not cleaned up: {leftover}"

    def test_cleanup_on_error(self):
        """Temp dirs must be cleaned even when ingestion fails."""
        import tempfile as _tf
        tmp_before = set(os.listdir(_tf.gettempdir()))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            info = zipfile.ZipInfo("../../evil.py")
            zf.writestr(info, b"evil")
        try:
            ingest_upload("traversal.zip", io.BytesIO(buf.getvalue()))
        except IngestionError:
            pass
        tmp_after = set(os.listdir(_tf.gettempdir()))
        leftover = {d for d in (tmp_after - tmp_before) if d.startswith("qshield_ingest_")}
        assert not leftover, f"Temp dirs leaked on error: {leftover}"


# ════════════════════════════════════════════════════════════════════════════
# HTTP endpoint integration tests
# ════════════════════════════════════════════════════════════════════════════

class TestUploadEndpoint:

    def test_valid_zip_creates_completed_scan(self, client):
        app_id = _make_stack(client)
        data = _make_zip({"auth.py": b"import ssl", "config.yaml": b"k: v"})
        r = _upload(client, app_id, "repo.zip", data)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["status"] == "completed"
        assert d["file_count"] == 2
        assert d["upload_type"] == "zip"
        assert d["upload_name"] == "repo.zip"

    def test_valid_single_file(self, client):
        app_id = _make_stack(client)
        r = _upload(client, app_id, "main.py", b"import hashlib")
        assert r.status_code == 201
        d = r.json()
        assert d["status"] == "completed"
        assert d["file_count"] == 1
        assert d["upload_type"] == "single_file"

    def test_unsupported_extension_scan_failed(self, client):
        app_id = _make_stack(client)
        r = _upload(client, app_id, "payload.exe", b"MZ binary")
        assert r.status_code == 201
        d = r.json()
        assert d["status"] == "failed"
        assert d["error_message"] is not None

    def test_malformed_zip_scan_failed(self, client):
        app_id = _make_stack(client)
        r = _upload(client, app_id, "bad.zip", b"not a zip")
        assert r.status_code == 201
        d = r.json()
        assert d["status"] == "failed"

    def test_traversal_zip_scan_failed(self, client):
        app_id = _make_stack(client)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(zipfile.ZipInfo("../../evil.py"), b"evil")
        r = _upload(client, app_id, "evil.zip", buf.getvalue())
        assert r.status_code == 201
        assert r.json()["status"] == "failed"

    def test_invalid_application_returns_404(self, client):
        data = _make_zip({"main.py": b"code"})
        r = _upload(client, "no-such-app-id", "repo.zip", data)
        assert r.status_code == 404

    def test_scan_status_after_upload(self, client):
        app_id = _make_stack(client)
        data = _make_zip({"app.py": b"import os"})
        scan = _upload(client, app_id, "app.zip", data).json()
        r = client.get(f"/api/scans/{scan['id']}/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "completed"
        assert d["upload_name"] == "app.zip"

    def test_empty_archive_scan_failed(self, client):
        app_id = _make_stack(client)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("emptydir/", "")
        r = _upload(client, app_id, "empty.zip", buf.getvalue())
        assert r.status_code == 201
        assert r.json()["status"] == "failed"
