import uuid
from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.asset import AssetCriticality, DataClassification
from app.models.vendor import VENDOR_UPCOMING_WINDOW_DAYS, VendorDueDiligenceStatus, VendorStatus
from app.schemas.evidence import EvidenceSummary
from app.schemas.finding import ActionSummary, FindingSummary
from app.schemas.control import RiskSummary


class VendorCreate(BaseModel):
    vendor_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=255)
    criticality: AssetCriticality
    data_classification: DataClassification
    status: VendorStatus = VendorStatus.PROSPECT
    due_diligence_status: VendorDueDiligenceStatus = VendorDueDiligenceStatus.PENDING
    relationship_start_date: date
    contract_end_date: date | None = None
    last_security_review_date: date | None = None
    next_security_review_date: date | None = None

    @model_validator(mode="after")
    def _fechas_coherentes(self) -> "VendorCreate":
        if self.contract_end_date is not None and self.contract_end_date < self.relationship_start_date:
            raise ValueError(
                "La fecha de finalización de contrato no puede ser anterior al inicio de la relación."
            )
        if (
            self.last_security_review_date is not None
            and self.next_security_review_date is not None
            and self.next_security_review_date < self.last_security_review_date
        ):
            raise ValueError("La próxima revisión no puede ser anterior a la última revisión.")
        return self


class VendorUpdate(BaseModel):
    vendor_id: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=255)
    owner: str | None = Field(default=None, min_length=1, max_length=255)
    criticality: AssetCriticality | None = None
    data_classification: DataClassification | None = None
    status: VendorStatus | None = None
    due_diligence_status: VendorDueDiligenceStatus | None = None
    relationship_start_date: date | None = None
    contract_end_date: date | None = None
    last_security_review_date: date | None = None
    next_security_review_date: date | None = None


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    vendor_id: str
    name: str
    legal_name: str | None
    description: str | None
    category: str
    owner: str
    criticality: AssetCriticality
    data_classification: DataClassification
    status: VendorStatus
    due_diligence_status: VendorDueDiligenceStatus
    relationship_start_date: date
    contract_end_date: date | None
    last_security_review_date: date | None
    next_security_review_date: date | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_review_overdue(self) -> bool:
        return self.next_security_review_date is not None and self.next_security_review_date < date.today()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_review_due_soon(self) -> bool:
        if self.next_security_review_date is None:
            return False
        hoy = date.today()
        limite = hoy + timedelta(days=VENDOR_UPCOMING_WINDOW_DAYS)
        return hoy <= self.next_security_review_date <= limite

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_contract_expired(self) -> bool:
        return self.contract_end_date is not None and self.contract_end_date < date.today()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_contract_expiring_soon(self) -> bool:
        if self.contract_end_date is None:
            return False
        hoy = date.today()
        limite = hoy + timedelta(days=VENDOR_UPCOMING_WINDOW_DAYS)
        return hoy <= self.contract_end_date <= limite


class VendorDetailRead(VendorRead):
    risks: list[RiskSummary] = []
    evidence: list[EvidenceSummary] = []
    findings: list[FindingSummary] = []
    # Derivado de los hallazgos vinculados (Finding -> RemediationAction ya es 1:N):
    # no se duplica como una relación M2M propia de Vendor.
    actions: list[ActionSummary] = []
