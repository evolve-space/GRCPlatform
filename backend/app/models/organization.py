import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.control import Control
    from app.models.evidence import Evidence
    from app.models.finding import Finding
    from app.models.framework import Framework
    from app.models.integration_token import IntegrationToken
    from app.models.remediation_action import RemediationAction
    from app.models.risk import Risk
    from app.models.user import User
    from app.models.vendor import Vendor


class Organization(Base):
    """Empresa u organización propietaria de sus propios datos dentro de la plataforma."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    risks: Mapped[list["Risk"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    controls: Mapped[list["Control"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    frameworks: Mapped[list["Framework"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    remediation_actions: Mapped[list["RemediationAction"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    vendors: Mapped[list["Vendor"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    integration_tokens: Mapped[list["IntegrationToken"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
