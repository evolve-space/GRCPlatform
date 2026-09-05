import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.asset import AssetCriticality
from app.models.remediation_action import ACTION_STATUSES_NO_VENCIBLES, ActionStatus
from app.schemas.evidence import EvidenceSummary


class RemediationActionCreate(BaseModel):
    finding_id: uuid.UUID
    action_id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    owner: str = Field(min_length=1, max_length=255)
    priority: AssetCriticality
    due_date: date
    status: ActionStatus = ActionStatus.PENDING
    completion_notes: str | None = None


class RemediationActionUpdate(BaseModel):
    action_id: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=255)
    priority: AssetCriticality | None = None
    due_date: date | None = None
    status: ActionStatus | None = None
    completion_notes: str | None = None


class RemediationActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    finding_id: uuid.UUID
    action_id: str
    title: str
    description: str | None
    owner: str
    status: ActionStatus
    priority: AssetCriticality
    due_date: date
    completed_at: date | None
    completion_notes: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        return self.status not in ACTION_STATUSES_NO_VENCIBLES and self.due_date < date.today()


class RemediationActionDetailRead(RemediationActionRead):
    evidence: list[EvidenceSummary] = []
