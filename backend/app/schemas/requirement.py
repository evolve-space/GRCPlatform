import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RequirementCreate(BaseModel):
    parent_requirement_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)


class RequirementUpdate(BaseModel):
    parent_requirement_id: uuid.UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    framework_id: uuid.UUID
    parent_requirement_id: uuid.UUID | None
    code: str
    name: str
    description: str | None
    category: str | None
    created_at: datetime
    updated_at: datetime
