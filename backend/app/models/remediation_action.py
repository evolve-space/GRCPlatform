import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.asset import AssetCriticality, _enum_values
from app.models.associations import remediation_action_evidences

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.finding import Finding
    from app.models.organization import Organization
    from app.models.user import User


class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Estados en los que una acción ya no se considera "activa" a efectos de vencimiento.
ACTION_STATUSES_NO_VENCIBLES = (ActionStatus.COMPLETED, ActionStatus.CANCELLED)


class RemediationAction(Base):
    __tablename__ = "remediation_actions"
    __table_args__ = (
        UniqueConstraint("organization_id", "action_id", name="uq_remediation_actions_org_action_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )

    action_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=ActionStatus.PENDING,
    )
    # Reutiliza el mismo enum que Asset.criticality / Finding.severity.
    priority: Mapped[AssetCriticality] = mapped_column(
        Enum(AssetCriticality, name="asset_criticality", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )

    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="remediation_actions")
    finding: Mapped["Finding"] = relationship(back_populates="actions")
    created_by: Mapped["User | None"] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(secondary=remediation_action_evidences)
