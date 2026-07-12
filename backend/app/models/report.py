"""
Report model — exportable CBOM report for a completed Scan.
"""
import enum
from sqlalchemy import String, Text, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class ReportFormat(str, enum.Enum):
    json = "json"
    pdf = "pdf"   # Phase 6+


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    scan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    format: Mapped[ReportFormat] = mapped_column(
        SAEnum(ReportFormat, native_enum=False),
        default=ReportFormat.json,
        nullable=False,
    )
    # Schema version for forward-compat (CycloneDX-style CBOM)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)
    finding_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Serialised report content (JSON string for json format)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="report")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Report id={self.id} format={self.format} scan_id={self.scan_id}>"
