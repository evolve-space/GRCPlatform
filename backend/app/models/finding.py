import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.asset import AssetCriticality, _enum_values
from app.models.associations import (
    finding_assets,
    finding_controls,
    finding_evidence,
    finding_requirements,
    finding_risks,
)

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.control import Control
    from app.models.evidence import Evidence
    from app.models.framework import Requirement
    from app.models.organization import Organization
    from app.models.remediation_action import RemediationAction
    from app.models.risk import Risk
    from app.models.user import User


class FindingType(str, enum.Enum):
    AUDIT_INTERNAL = "audit_internal"
    AUDIT_EXTERNAL = "audit_external"
    RISK_ASSESSMENT = "risk_assessment"
    INCIDENT = "incident"
    CONTROL_REVIEW = "control_review"
    COMPLIANCE = "compliance"
    VENDOR = "vendor"
    OTHER = "other"


class FindingSource(str, enum.Enum):
    AUDIT = "audit"
    RISK_ASSESSMENT = "risk_assessment"
    CONTROL = "control"
    COMPLIANCE = "compliance"
    INCIDENT = "incident"
    VENDOR = "vendor"
    MANUAL = "manual"


class FindingStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    REMEDIATION = "remediation"
    PENDING_VALIDATION = "pending_validation"
    CLOSED = "closed"
    ACCEPTED = "accepted"


# Estados en los que un hallazgo ya no se considera "abierto" a efectos de vencimiento.
FINDING_STATUSES_NO_VENCIBLES = (FindingStatus.CLOSED, FindingStatus.ACCEPTED)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("organization_id", "finding_id", name="uq_findings_org_finding_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    finding_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    finding_type: Mapped[FindingType] = mapped_column(
        Enum(FindingType, name="finding_type", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    # Reutiliza el mismo enum que Asset.criticality (Baja/Media/Alta/Crítica):
    # misma escala, mismas etiquetas, evita duplicar un tipo idéntico.
    severity: Mapped[AssetCriticality] = mapped_column(
        Enum(AssetCriticality, name="asset_criticality", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="finding_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=FindingStatus.OPEN,
    )
    source: Mapped[FindingSource] = mapped_column(
        Enum(FindingSource, name="finding_source", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)

    discovered_at: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="findings")
    created_by: Mapped["User | None"] = relationship()

    risks: Mapped[list["Risk"]] = relationship(secondary=finding_risks)
    controls: Mapped[list["Control"]] = relationship(secondary=finding_controls)
    assets: Mapped[list["Asset"]] = relationship(secondary=finding_assets)
    requirements: Mapped[list["Requirement"]] = relationship(secondary=finding_requirements)
    evidence: Mapped[list["Evidence"]] = relationship(secondary=finding_evidence)

    actions: Mapped[list["RemediationAction"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )
