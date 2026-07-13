"""
Upload router — POST /api/scans/upload

Full pipeline:
  1. Validate application_id reference
  2. Validate and securely ingest the upload  (ingestion service)
  3. Create Scan record (running)
  4. Run Crypto Discovery Engine              (scanner engine)
  5. Persist CryptoFinding records
  6. Update scan counters and status (completed | failed)
  7. Return scan metadata

No files are permanently stored on disk.
No source files are executed under any circumstances.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.application import Application
from app.models.finding import CryptoFinding, DetectionMethod
from app.models.base import new_uuid
from app.schemas.upload import UploadScanResponse
from app.services.ingestion import ingest_upload, IngestionError
from app.services.scanner.engine import run_scan
from app.services.scanner.rules import QuantumStatus as RuleQuantumStatus
from app.models.finding import QuantumStatus as DBQuantumStatus
from app.models.finding import DetectionMethod as DBDetectionMethod

router = APIRouter(prefix="/scans", tags=["scans"])


def _map_quantum_status(rqs: str) -> DBQuantumStatus:
    """Map rule-layer QuantumStatus str to DB enum."""
    mapping = {
        "vulnerable":  DBQuantumStatus.vulnerable,
        "safe":        DBQuantumStatus.safe,
        "borderline":  DBQuantumStatus.borderline,
        "deprecated":  DBQuantumStatus.unknown,   # stored as 'unknown' in DB; legacy_note carries reason
        "unknown":     DBQuantumStatus.unknown,
        "hybrid":      DBQuantumStatus.hybrid,
    }
    return mapping.get(rqs, DBQuantumStatus.unknown)


def _map_detection_method(method: str) -> DBDetectionMethod:
    if method == "ast":
        return DBDetectionMethod.ast
    if method == "cert_parse":
        return DBDetectionMethod.cert_parse
    return DBDetectionMethod.regex


@router.post(
    "/upload",
    response_model=UploadScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Securely upload source files or ZIP and run crypto discovery",
)
def upload_for_scan(
    application_id: str = Form(..., description="ID of the target application"),
    file: UploadFile = File(..., description="ZIP archive or single supported file"),
    db: Session = Depends(get_db),
):
    """
    Complete upload + scan pipeline.

    - Validates and ingests the upload (secure, temp-cleaned)
    - Runs deterministic Crypto Discovery Engine
    - Persists CryptoFinding rows
    - Returns scan record with file_count and finding_count
    - Never executes uploaded content
    - Never stores raw private keys or credentials
    """
    # ── 1. Validate application ──────────────────────────────────────────────
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Application '{application_id}' not found",
        )

    original_filename = file.filename or "upload"

    # ── 2. Create Scan record in RUNNING state ───────────────────────────────
    scan = Scan(
        id=new_uuid(),
        application_id=application_id,
        name=f"Scan of {original_filename}",
        scan_type=ScanType.mixed,
        status=ScanStatus.running,
        upload_name=original_filename,
        upload_type="unknown",
        started_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.commit()

    # ── 3. Ingest upload ─────────────────────────────────────────────────────
    try:
        result = ingest_upload(
            filename=original_filename,
            file_obj=file.file,
        )
    except IngestionError as exc:
        scan.status = ScanStatus.failed
        scan.error_message = str(exc)
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        return scan
    except Exception:
        scan.status = ScanStatus.failed
        scan.error_message = "Unexpected error during file processing."
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        return scan

    # Update scan with ingestion metadata
    scan.file_count = result.file_count
    scan.upload_type = result.upload_type
    scan.upload_name = result.upload_name
    db.commit()

    # ── 4. Run Crypto Discovery Engine ───────────────────────────────────────
    try:
        raw_findings = run_scan(result.file_contents)
    except Exception as exc:
        scan.status = ScanStatus.failed
        scan.error_message = f"Scanner error: {exc}"
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        return scan

    # ── 5. Persist findings ──────────────────────────────────────────────────
    finding_count = 0
    for rf in raw_findings:
        finding = CryptoFinding(
            id=new_uuid(),
            scan_id=scan.id,
            file_path=rf.file_path,
            line_number=rf.line_number,
            raw_snippet=rf.evidence,           # already masked by scanner
            algorithm=rf.algorithm,
            algorithm_family=rf.algorithm_family,
            key_size=rf.key_size,
            usage_context=rf.usage_context,
            quantum_status=_map_quantum_status(rf.quantum_status.value if hasattr(rf.quantum_status, "value") else str(rf.quantum_status)),
            detection_method=_map_detection_method(rf.detection_method),
            confidence=rf.confidence,
            nist_recommendation=rf.nist_recommendation or None,
        )
        db.add(finding)
        finding_count += 1

    # ── 6. Complete scan ─────────────────────────────────────────────────────
    scan.status = ScanStatus.completed
    scan.finding_count = finding_count
    scan.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(scan)

    return scan
