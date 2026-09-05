import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.associations import control_requirements
from app.models.asset import _enum_values

if TYPE_CHECKING:
    from app.models.control import Control
    from app.models.organization import Organization


class FrameworkStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Framework(Base):
    __tablename__ = "frameworks"
    __table_args__ = (
        UniqueConstraint("organization_id", "short_name", name="uq_frameworks_org_short_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[FrameworkStatus] = mapped_column(
        Enum(FrameworkStatus, name="framework_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=FrameworkStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="frameworks")
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="framework", cascade="all, delete-orphan"
    )


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        UniqueConstraint("framework_id", "code", name="uq_requirements_framework_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    framework_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    framework: Mapped["Framework"] = relationship(back_populates="requirements")
    controls: Mapped[list["Control"]] = relationship(
        secondary=control_requirements, back_populates="requirements"
    )


class FrameworkMapping(Base):
    """Correspondencia/apoyo entre requisitos de dos marcos distintos.

    No implica equivalencia legal automática entre ambos requisitos.
    """

    __tablename__ = "framework_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_requirement_id", "target_requirement_id", name="uq_framework_mappings_pair"
        ),
        CheckConstraint(
            "source_requirement_id != target_requirement_id", name="ck_framework_mappings_no_self"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False
    )
    target_requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_requirement: Mapped["Requirement"] = relationship(foreign_keys=[source_requirement_id])
    target_requirement: Mapped["Requirement"] = relationship(foreign_keys=[target_requirement_id])
