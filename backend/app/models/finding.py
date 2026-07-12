"""
CryptoFinding model — a single detected cryptographic primitive (one CBOM entry).
"""
import enum
from sqlalchemy import String, Text, Integer, Float, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class QuantumStatus(str, enum.Enum):
    vulnerable = "vulnerable"    # Classical asymmetric: RSA, ECDSA, DH, etc.
    safe = "safe"                # AES-256, ChaCha20, SHA-512, PQC algorithms
    borderline = "borderline"    # AES-128, SHA-256 — halved by Grover
    unknown = "unknown"          # Unrecognised / insufficient info
    hybrid = "hybrid"            # Transitional hybrid scheme


class DetectionMethod(str, enum.Enum):
    regex = "regex"              # confidence ~0.7
    ast = "ast"                  # confidence ~0.9
    cert_parse = "cert_parse"    # confidence 1.0


class CryptoFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crypto_findings"

    scan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Detection metadata ─────────────────────────────────────────────────
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Algorithm data ─────────────────────────────────────────────────────
    algorithm: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    algorithm_family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_context: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ── Classification ─────────────────────────────────────────────────────
    quantum_status: Mapped[QuantumStatus] = mapped_column(
        SAEnum(QuantumStatus, native_enum=False),
        default=QuantumStatus.unknown,
        nullable=False,
        index=True,
    )
    detection_method: Mapped[DetectionMethod] = mapped_column(
        SAEnum(DetectionMethod, native_enum=False),
        default=DetectionMethod.regex,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    # ── Risk ───────────────────────────────────────────────────────────────
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    # JSON dict: { "base_weight": 0.9, "key_size_factor": 0.8, ... }
    risk_factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Recommendation (FK to MigrationRecommendation set post-analysis) ──
    nist_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")  # noqa: F821
    roadmap_items: Mapped[list["RoadmapItem"]] = relationship(  # noqa: F821
        "RoadmapItem", back_populates="finding", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CryptoFinding id={self.id} algorithm={self.algorithm!r} status={self.quantum_status}>"
