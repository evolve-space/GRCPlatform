import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.risk import Risk


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class AssetType(str, enum.Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    SERVER = "server"
    ENDPOINT = "endpoint"
    DATABASE = "database"
    SERVICE = "service"
    INFORMATION = "information"
    PROCESS = "process"
    VENDOR = "vendor"
    OTHER = "other"


class AssetCriticality(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataClassification(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AssetStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DECOMMISSIONED = "decommissioned"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    criticality: Mapped[AssetCriticality] = mapped_column(
        Enum(AssetCriticality, name="asset_criticality", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    data_classification: Mapped[DataClassification] = mapped_column(
        Enum(DataClassification, name="data_classification", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=AssetStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="assets")
    risks: Mapped[list["Risk"]] = relationship(back_populates="asset")
