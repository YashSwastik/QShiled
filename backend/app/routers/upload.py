"""
Upload router — POST /api/scans/upload

Implements secure multi-part file ingestion:
  1. Validate application_id reference
  2. Validate upload (size, extension, ZIP safety)
  3. Create Scan record (processing → completed | failed)
  4. Return scan metadata

No files are permanently stored. Temp dirs are cleaned up by the ingestion service.
No source files are executed under any circumstances.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.application import Application
from app.models.base import new_uuid
from app.schemas.upload import UploadScanResponse
from app.services.ingestion import ingest_upload, IngestionError

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post(
    "/upload",
    response_model=UploadScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Securely upload source files or ZIP for scanning",
)
def upload_for_scan(
    application_id: str = Form(..., description="ID of the target application"),
    file: UploadFile = File(..., description="ZIP archive or single supported file"),
    db: Session = Depends(get_db),
):
    """
    Validates and ingests an uploaded file. Creates a Scan record.

    - For ZIP: extracts safely with path-traversal prevention
    - For single files: validates extension allowlist
    - Returns scan metadata; does NOT run cryptographic analysis yet
    - Never executes uploaded content
    """
    # Validate application exists
    app_obj = db.get(Application, application_id)
    if not app_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Application '{application_id}' not found",
        )

    original_filename = file.filename or "upload"

    # Create scan record in PROCESSING state
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

    # Run ingestion — safe, synchronous, temp-cleaned
    try:
        result = ingest_upload(
            filename=original_filename,
            file_obj=file.file,
        )
        # Update scan with results
        scan.status = ScanStatus.completed
        scan.file_count = result.file_count
        scan.upload_type = result.upload_type
        scan.upload_name = result.upload_name
        scan.completed_at = datetime.now(timezone.utc)

    except IngestionError as exc:
        scan.status = ScanStatus.failed
        scan.error_message = str(exc)
        scan.completed_at = datetime.now(timezone.utc)

    except Exception:
        scan.status = ScanStatus.failed
        scan.error_message = "Unexpected error during file processing."
        scan.completed_at = datetime.now(timezone.utc)

    finally:
        db.commit()
        db.refresh(scan)

    return scan
