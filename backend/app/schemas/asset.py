import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.asset import AssetCriticality, AssetStatus, AssetType, DataClassification


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    asset_type: AssetType
    owner: str = Field(min_length=1, max_length=255)
    criticality: AssetCriticality
    data_classification: DataClassification
    status: AssetStatus = AssetStatus.ACTIVE


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    asset_type: AssetType | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=255)
    criticality: AssetCriticality | None = None
    data_classification: DataClassification | None = None
    status: AssetStatus | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    asset_type: AssetType
    owner: str
    criticality: AssetCriticality
    data_classification: DataClassification
    status: AssetStatus
    created_at: datetime
    updated_at: datetime
