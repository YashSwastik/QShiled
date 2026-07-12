"""
Asset model — a file or certificate submitted for scanning.
"""
import enum
from sqlalchemy import String, Text, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class AssetType(str, enum.Enum):
    source_code = "source_code"
    certificate = "certificate"
    config_file = "config_file"
    unknown = "unknown"


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        SAEnum(AssetType, native_enum=False),
        default=AssetType.unknown,
        nullable=False,
        index=True,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Relative path once stored (never absolute, never returned to client)
    stored_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(  # noqa: F821
        "Application", back_populates="assets"
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} filename={self.original_filename!r}>"
