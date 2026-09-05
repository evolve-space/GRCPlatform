import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FrameworkMappingCreate(BaseModel):
    source_requirement_id: uuid.UUID
    target_requirement_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=2000)


class RequirementBrief(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    framework_id: uuid.UUID
    framework_short_name: str


class FrameworkMappingRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    source_requirement: RequirementBrief
    target_requirement: RequirementBrief
    notes: str | None
    created_at: datetime
