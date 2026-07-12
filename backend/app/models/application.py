"""
Application model — a concrete software system with business context.

Business criticality, internet exposure, data sensitivity etc. drive risk weighting
in the analyzer. These fields are supplied by the user at onboarding time.
"""
import enum
from sqlalchemy import String, Text, Boolean, ForeignKey, Enum as SAEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class BusinessCriticality(str, enum.Enum):
    critical = "critical"    # Outage = business-stopping
    high = "high"            # Significant financial/operational impact
    medium = "medium"        # Moderate impact
    low = "low"              # Minimal impact


class Environment(str, enum.Enum):
    production = "production"
    staging = "staging"
    development = "development"
    research = "research"


class DataSensitivity(str, enum.Enum):
    top_secret = "top_secret"    # Government/classified
    restricted = "restricted"    # PII, financial, health
    internal = "internal"        # Internal business data
    public = "public"            # No sensitivity


class ConfidentialityRequirement(str, enum.Enum):
    long_term = "long_term"      # >10 years: needs harvest-now protection now
    medium_term = "medium_term"  # 1-10 years
    short_term = "short_term"    # <1 year


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Business Context (drives risk factor weighting) ────────────────────
    business_criticality: Mapped[BusinessCriticality] = mapped_column(
        SAEnum(BusinessCriticality, native_enum=False),
        default=BusinessCriticality.medium,
        nullable=False,
    )
    environment: Mapped[Environment] = mapped_column(
        SAEnum(Environment, native_enum=False),
        default=Environment.production,
        nullable=False,
    )
    internet_exposed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_sensitivity: Mapped[DataSensitivity] = mapped_column(
        SAEnum(DataSensitivity, native_enum=False),
        default=DataSensitivity.internal,
        nullable=False,
    )
    confidentiality_requirement: Mapped[ConfidentialityRequirement] = mapped_column(
        SAEnum(ConfidentialityRequirement, native_enum=False),
        default=ConfidentialityRequirement.medium_term,
        nullable=False,
    )
    # Estimated years the protected data must remain confidential
    data_lifetime_years: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # Owner team / contact
    owner_team: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="applications"
    )
    assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        "Asset", back_populates="application", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship(  # noqa: F821
        "Scan", back_populates="application", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} name={self.name!r}>"
