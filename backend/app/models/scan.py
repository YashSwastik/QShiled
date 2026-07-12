"""
Scan model — one scan execution against an Application's assets.
"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class ScanStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ScanType(str, enum.Enum):
    source_code = "source_code"
    certificate = "certificate"
    config = "config"
    mixed = "mixed"


class Scan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scans"

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scan_type: Mapped[ScanType] = mapped_column(
        SAEnum(ScanType, native_enum=False),
        default=ScanType.source_code,
        nullable=False,
    )
    status: Mapped[ScanStatus] = mapped_column(
        SAEnum(ScanStatus, native_enum=False),
        default=ScanStatus.queued,
        nullable=False,
        index=True,
    )

    # Progress / results
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finding_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error capture
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Upload metadata (populated by ingestion endpoint)
    upload_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    upload_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(  # noqa: F821
        "Application", back_populates="scans"
    )
    findings: Mapped[list["CryptoFinding"]] = relationship(  # noqa: F821
        "CryptoFinding", back_populates="scan", cascade="all, delete-orphan"
    )
    risk_assessment: Mapped["RiskAssessment | None"] = relationship(  # noqa: F821
        "RiskAssessment", back_populates="scan", uselist=False, cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(  # noqa: F821
        "Report", back_populates="scan", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Scan id={self.id} status={self.status}>"
