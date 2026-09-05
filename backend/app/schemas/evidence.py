import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.asset import DataClassification
from app.models.evidence import EvidenceStatus
from app.schemas.control import AssetSummary, RequirementSummary, RiskSummary


class ControlSummary(BaseModel):
    id: uuid.UUID
    control_id: str
    name: str


class EvidenceSummary(BaseModel):
    id: uuid.UUID
    name: str
    classification: DataClassification


class EvidenceMetadata(BaseModel):
    """Metadatos de una evidencia recibidos junto al archivo (multipart/form-data)."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    classification: DataClassification
    evidence_type: str = Field(min_length=1, max_length=255)
    collected_at: date
    expires_at: date | None = None

    @model_validator(mode="after")
    def _expiracion_posterior_a_recopilacion(self) -> "EvidenceMetadata":
        if self.expires_at is not None and self.expires_at < self.collected_at:
            raise ValueError("La fecha de expiración no puede ser anterior a la de recopilación.")
        return self


class EvidenceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    classification: DataClassification | None = None
    evidence_type: str | None = Field(default=None, min_length=1, max_length=255)
    status: EvidenceStatus | None = None
    collected_at: date | None = None
    expires_at: date | None = None


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    original_filename: str
    mime_type: str
    file_size: int
    sha256: str
    classification: DataClassification
    status: EvidenceStatus
    evidence_type: str
    collected_at: date
    expires_at: date | None
    uploaded_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < date.today()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effective_status(self) -> str:
        if self.status == EvidenceStatus.ARCHIVED:
            return "archived"
        if self.is_expired:
            return "expired"
        return "active"


class EvidenceDetailRead(EvidenceRead):
    controls: list[ControlSummary] = []
    risks: list[RiskSummary] = []
    assets: list[AssetSummary] = []
    requirements: list[RequirementSummary] = []


class IntegrityCheckResult(BaseModel):
    status: str  # "ok" | "mismatch" | "not_found"
    sha256_stored: str
    sha256_calculated: str | None
