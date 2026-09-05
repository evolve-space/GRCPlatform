import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.control import ControlFrequency, ControlStatus


class ControlCreate(BaseModel):
    control_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    objective: str | None = None
    category: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=255)
    status: ControlStatus = ControlStatus.NOT_IMPLEMENTED
    frequency: ControlFrequency


class ControlUpdate(BaseModel):
    control_id: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    objective: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=255)
    owner: str | None = Field(default=None, min_length=1, max_length=255)
    status: ControlStatus | None = None
    frequency: ControlFrequency | None = None


class ControlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    control_id: str
    name: str
    description: str | None
    objective: str | None
    category: str
    owner: str
    status: ControlStatus
    frequency: ControlFrequency
    created_at: datetime
    updated_at: datetime


class RiskSummary(BaseModel):
    id: uuid.UUID
    title: str
    inherent_level: str


class AssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    criticality: str


class RequirementSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    framework_id: uuid.UUID
    framework_short_name: str


class ControlDetailRead(ControlRead):
    risks: list[RiskSummary] = []
    assets: list[AssetSummary] = []
    requirements: list[RequirementSummary] = []
