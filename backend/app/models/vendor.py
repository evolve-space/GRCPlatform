import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.asset import AssetCriticality, DataClassification, _enum_values
from app.models.associations import vendor_evidence, vendor_findings, vendor_risks

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.finding import Finding
    from app.models.organization import Organization
    from app.models.risk import Risk
    from app.models.user import User


class VendorStatus(str, enum.Enum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class VendorDueDiligenceStatus(str, enum.Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    REJECTED = "rejected"
    EXPIRED = "expired"


# Ventana (en días) a partir de la cual una revisión/contrato se considera
# "próximo a vencer". Umbral fijo y razonable para evitar sobreingeniería
# (un parámetro configurable por petición no aporta valor real aquí).
VENDOR_UPCOMING_WINDOW_DAYS = 30


class Vendor(Base):
    """Proveedor / tercero (Third-Party Risk Management).

    Vendor representa el TERCERO en sí (ficha, contrato, ciclo de vida,
    due diligence). El riesgo asociado a ese tercero se modela reutilizando
    la entidad ``Risk`` ya existente (relación M2M), en lugar de duplicar un
    segundo motor de scoring: evita mantener dos fuentes de verdad para
    "cuánto riesgo supone esto".
    """

    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("organization_id", "vendor_id", name="uq_vendors_org_vendor_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    vendor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)

    # Reutiliza los mismos enums que Asset (misma escala, mismas etiquetas).
    criticality: Mapped[AssetCriticality] = mapped_column(
        Enum(AssetCriticality, name="asset_criticality", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )
    data_classification: Mapped[DataClassification] = mapped_column(
        Enum(DataClassification, name="data_classification", native_enum=True, values_callable=_enum_values),
        nullable=False,
    )

    status: Mapped[VendorStatus] = mapped_column(
        Enum(VendorStatus, name="vendor_status", native_enum=True, values_callable=_enum_values),
        nullable=False,
        default=VendorStatus.PROSPECT,
    )
    due_diligence_status: Mapped[VendorDueDiligenceStatus] = mapped_column(
        Enum(
            VendorDueDiligenceStatus,
            name="vendor_due_diligence_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=VendorDueDiligenceStatus.PENDING,
    )

    relationship_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    contract_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_security_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_security_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="vendors")
    created_by: Mapped["User | None"] = relationship()

    risks: Mapped[list["Risk"]] = relationship(secondary=vendor_risks)
    evidence: Mapped[list["Evidence"]] = relationship(secondary=vendor_evidence)
    findings: Mapped[list["Finding"]] = relationship(secondary=vendor_findings)
