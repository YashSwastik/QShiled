"""
MigrationRecommendation + RoadmapItem models.

MigrationRecommendation: per-algorithm NIST-aligned replacement advice (static reference).
RoadmapItem: a prioritised actionable task derived from a CryptoFinding.
"""
import enum
from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class EffortEstimate(str, enum.Enum):
    low = "low"        # Config change / library swap
    medium = "medium"  # Code changes in <1 week
    high = "high"      # Architectural change or significant refactor


class RoadmapItemStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    deferred = "deferred"


class MigrationRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Per-algorithm static NIST-aligned recommendation.
    Seeded from the algorithm registry. One record per vulnerable algorithm family.
    """
    __tablename__ = "migration_recommendations"

    algorithm_family: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    replacement_algorithm: Mapped[str] = mapped_column(String(128), nullable=False)
    nist_standard: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "FIPS 203"
    nist_reference_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    migration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_quantum_safe_replacement: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<MigrationRecommendation {self.algorithm_family} → {self.replacement_algorithm}>"


class RoadmapItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One actionable migration task, linked to a specific CryptoFinding.
    Priority is computed by the analyzer (lower number = higher priority).
    """
    __tablename__ = "roadmap_items"

    scan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("crypto_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    priority: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    effort_estimate: Mapped[EffortEstimate] = mapped_column(
        SAEnum(EffortEstimate, native_enum=False),
        default=EffortEstimate.medium,
        nullable=False,
    )
    replacement_algorithm: Mapped[str] = mapped_column(String(128), nullable=False)
    nist_standard: Mapped[str | None] = mapped_column(String(64), nullable=True)
    migration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RoadmapItemStatus] = mapped_column(
        SAEnum(RoadmapItemStatus, native_enum=False),
        default=RoadmapItemStatus.pending,
        nullable=False,
        index=True,
    )

    # Relationships
    finding: Mapped["CryptoFinding"] = relationship(  # noqa: F821
        "CryptoFinding", back_populates="roadmap_items"
    )

    def __repr__(self) -> str:
        return f"<RoadmapItem id={self.id} priority={self.priority} status={self.status}>"
