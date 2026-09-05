import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.associations import control_assets, control_requirements, control_risks
from app.models.asset import _enum_values

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.framework import Requirement
    from app.models.organization import Organization
    from app.models.risk import Risk


class ControlStatus(str, enum.Enum):
    NOT_IMPLEMENTED = "not_implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IMPLEMENTED = "implemented"
    NOT_APPLICABLE = "not_applicable"


class ControlFrequency(str, enum.Enum):
    CONTINUOUS = "continuous"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    AD_HOC = "ad_hoc"


class Control(Base):
    __tablename__ = "controls"
    __table_args__ = (
        UniqueConstraint("organization_id", "control_id", name="uq_controls_org_control_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ControlStatus] = mapped_column(
        Enum(ControlStatus, name="control_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=ControlStatus.NOT_IMPLEMENTED,
    )
    frequency: Mapped[ControlFrequency] = mapped_column(
        Enum(ControlFrequency, name="control_frequency", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="controls")
    risks: Mapped[list["Risk"]] = relationship(secondary=control_risks)
    assets: Mapped[list["Asset"]] = relationship(secondary=control_assets)
    requirements: Mapped[list["Requirement"]] = relationship(
        secondary=control_requirements, back_populates="controls"
    )
