import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.asset import _enum_values

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.organization import Organization


class RiskTreatment(str, enum.Enum):
    MITIGATE = "mitigate"
    AVOID = "avoid"
    TRANSFER = "transfer"
    ACCEPT = "accept"


class RiskStatus(str, enum.Enum):
    IDENTIFIED = "identified"
    IN_EVALUATION = "in_evaluation"
    IN_TREATMENT = "in_treatment"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint("likelihood BETWEEN 1 AND 5", name="ck_risks_likelihood_range"),
        CheckConstraint("impact BETWEEN 1 AND 5", name="ck_risks_impact_range"),
        CheckConstraint(
            "residual_likelihood IS NULL OR residual_likelihood BETWEEN 1 AND 5",
            name="ck_risks_residual_likelihood_range",
        ),
        CheckConstraint(
            "residual_impact IS NULL OR residual_impact BETWEEN 1 AND 5",
            name="ck_risks_residual_impact_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )

    category: Mapped[str] = mapped_column(String(255), nullable=False)
    threat: Mapped[str] = mapped_column(String(255), nullable=False)
    vulnerability: Mapped[str] = mapped_column(String(255), nullable=False)

    likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    inherent_score: Mapped[int] = mapped_column(Integer, nullable=False)

    treatment: Mapped[RiskTreatment] = mapped_column(
        Enum(RiskTreatment, name="risk_treatment", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[RiskStatus] = mapped_column(
        Enum(RiskStatus, name="risk_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=RiskStatus.IDENTIFIED,
    )

    residual_likelihood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_impact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="risks")
    asset: Mapped["Asset | None"] = relationship(back_populates="risks")
