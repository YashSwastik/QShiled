"""
RiskAssessment model — aggregate risk summary for a completed Scan.

Stores QShield Explainable Migration Prioritization Methodology results.
Quantum migration risk and classical/legacy security risk are stored separately.
"""
from sqlalchemy import String, Float, Integer, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class RiskAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_assessments"

    scan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # 1-to-1 with Scan
        index=True,
    )

    # ── Quantum migration aggregate (0-100) ────────────────────────────────
    overall_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)      # NEW
    cryptographic_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Counts by quantum status ───────────────────────────────────────────
    vulnerable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    borderline_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unknown_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    legacy_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)  # NEW

    # ── Distribution & breakdowns ──────────────────────────────────────────
    # e.g. {"RSA": 5, "ECC": 2, "AES": 8}
    algorithm_family_distribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Average factor contributions: {"crypto_vulnerability": 18.2, ...}
    risk_factor_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Per-finding scores (list of dicts): [{finding_id, algorithm, score, severity, ...}]
    per_finding_scores: Mapped[list | None] = mapped_column(JSON, nullable=True)         # NEW
    # Top-priority finding IDs (ordered list)
    top_priority_finding_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)   # NEW

    # ── Methodology metadata ───────────────────────────────────────────────
    methodology_version: Mapped[str | None] = mapped_column(String(32), nullable=True)   # NEW
    # Human-readable summary sentence (deterministic template, NOT LLM)
    summary_text: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="risk_assessment")  # noqa: F821

    def __repr__(self) -> str:
        return f"<RiskAssessment id={self.id} score={self.overall_risk_score}>"
