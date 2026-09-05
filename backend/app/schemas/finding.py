import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.asset import AssetCriticality
from app.models.finding import FINDING_STATUSES_NO_VENCIBLES, FindingSource, FindingStatus, FindingType
from app.schemas.control import AssetSummary, RequirementSummary, RiskSummary
from app.schemas.evidence import ControlSummary, EvidenceSummary


class FindingCreate(BaseModel):
    finding_id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    finding_type: FindingType
    severity: AssetCriticality
    source: FindingSource
    owner: str = Field(min_length=1, max_length=255)
    discovered_at: date
    due_date: date
    status: FindingStatus = FindingStatus.OPEN
    resolution_summary: str | None = None

    @model_validator(mode="after")
    def _fecha_limite_no_anterior_a_descubrimiento(self) -> "FindingCreate":
        if self.due_date < self.discovered_at:
            raise ValueError("La fecha límite no puede ser anterior a la fecha de descubrimiento.")
        return self


class FindingUpdate(BaseModel):
    finding_id: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    finding_type: FindingType | None = None
    severity: AssetCriticality | None = None
    source: FindingSource | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=255)
    discovered_at: date | None = None
    due_date: date | None = None
    status: FindingStatus | None = None
    resolution_summary: str | None = None


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    finding_id: str
    title: str
    description: str | None
    finding_type: FindingType
    severity: AssetCriticality
    status: FindingStatus
    source: FindingSource
    owner: str
    discovered_at: date
    due_date: date
    closed_at: date | None
    resolution_summary: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        return self.status not in FINDING_STATUSES_NO_VENCIBLES and self.due_date < date.today()


class ActionSummary(BaseModel):
    id: uuid.UUID
    action_id: str
    title: str
    owner: str
    priority: AssetCriticality
    status: str
    due_date: date
    is_overdue: bool


class FindingSummary(BaseModel):
    id: uuid.UUID
    finding_id: str
    title: str
    severity: AssetCriticality
    status: FindingStatus


class FindingDetailRead(FindingRead):
    risks: list[RiskSummary] = []
    controls: list[ControlSummary] = []
    assets: list[AssetSummary] = []
    requirements: list[RequirementSummary] = []
    evidence: list[EvidenceSummary] = []
    actions: list[ActionSummary] = []
