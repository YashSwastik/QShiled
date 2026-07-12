"""
Pydantic v2 schemas for the upload/ingestion endpoint.
"""
from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import OrmBase
from app.models.scan import ScanStatus, ScanType


class UploadScanResponse(OrmBase):
    """Returned after a successful upload + scan record creation."""
    id: str
    application_id: str
    name: str
    scan_type: ScanType
    status: ScanStatus
    file_count: int
    upload_name: str
    upload_type: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime
