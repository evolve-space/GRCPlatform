import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.framework import FrameworkStatus


class FrameworkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    short_name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    version: str = Field(min_length=1, max_length=50)
    status: FrameworkStatus = FrameworkStatus.ACTIVE


class FrameworkUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    short_name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    version: str | None = Field(default=None, min_length=1, max_length=50)
    status: FrameworkStatus | None = None


class FrameworkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    short_name: str
    description: str | None
    version: str
    status: FrameworkStatus
    created_at: datetime
    updated_at: datetime


class ComplianceSummary(BaseModel):
    implemented: int
    partially_implemented: int
    not_implemented: int
    not_applicable: int
    total_requirements: int
    requirements_with_control: int


class FrameworkDetailRead(FrameworkRead):
    compliance_summary: ComplianceSummary
