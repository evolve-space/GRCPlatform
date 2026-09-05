import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.asset import DataClassification, _enum_values
from app.models.associations import (
    evidence_assets,
    evidence_controls,
    evidence_requirements,
    evidence_risks,
)

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.control import Control
    from app.models.framework import Requirement
    from app.models.organization import Organization
    from app.models.risk import Risk
    from app.models.user import User


class EvidenceStatus(str, enum.Enum):
    """Estado editable de la evidencia. "Caducada" NO es un valor de este enum:
    se deriva siempre de ``expires_at`` en el momento de la respuesta, nunca
    se almacena ni puede fijarlo el cliente."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (UniqueConstraint("storage_key", name="uq_evidence_storage_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    classification: Mapped[DataClassification] = mapped_column(
        Enum(DataClassification, name="data_classification", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=EvidenceStatus.ACTIVE,
    )
    evidence_type: Mapped[str] = mapped_column(String(255), nullable=False)

    collected_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="evidence")
    uploaded_by: Mapped["User | None"] = relationship()

    controls: Mapped[list["Control"]] = relationship(secondary=evidence_controls)
    risks: Mapped[list["Risk"]] = relationship(secondary=evidence_risks)
    assets: Mapped[list["Asset"]] = relationship(secondary=evidence_assets)
    requirements: Mapped[list["Requirement"]] = relationship(secondary=evidence_requirements)
