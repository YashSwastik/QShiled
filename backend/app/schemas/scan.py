"""
Pydantic v2 schemas for Scan and CryptoFinding.
"""
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field
from app.schemas.common import OrmBase
from app.models.scan import ScanStatus, ScanType
from app.models.finding import QuantumStatus, DetectionMethod


# ── Scan ──────────────────────────────────────────────────────────────────────

class ScanCreate(BaseModel):
    application_id: str
    name: Annotated[str, Field(min_length=1, max_length=255)]
    scan_type: ScanType = ScanType.source_code


class ScanStatusResponse(OrmBase):
    id: str
    status: ScanStatus
    file_count: int
    finding_count: int
    overall_risk_score: float | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    upload_name: str | None = None
    upload_type: str | None = None


class ScanResponse(OrmBase):
    id: str
    application_id: str
    name: str
    scan_type: ScanType
    status: ScanStatus
    file_count: int
    finding_count: int
    overall_risk_score: float | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    upload_name: str | None = None
    upload_type: str | None = None
    created_at: datetime
    updated_at: datetime


class ScanListResponse(OrmBase):
    total: int
    items: list[ScanResponse]


# ── CryptoFinding ─────────────────────────────────────────────────────────────

class FindingResponse(OrmBase):
    id: str
    scan_id: str
    file_path: str
    line_number: int | None
    raw_snippet: str | None
    algorithm: str
    algorithm_family: str
    key_size: int | None
    usage_context: str | None
    quantum_status: QuantumStatus
    detection_method: DetectionMethod
    confidence: float
    risk_score: float | None
    risk_factors: dict | None
    nist_recommendation: str | None
    created_at: datetime


class FindingListResponse(OrmBase):
    total: int
    items: list[FindingResponse]
