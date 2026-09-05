import uuid
from datetime import datetime

from pydantic import BaseModel


class ActorSummary(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str


class IntegrationActorSummary(BaseModel):
    id: uuid.UUID
    name: str


class AuditLogRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID | None
    integration_token_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    ip_address: str | None
    details: dict | None
    created_at: datetime
    actor: ActorSummary | None = None
    integration_actor: IntegrationActorSummary | None = None


class AuditLogMeta(BaseModel):
    actions: list[str]
    entity_types: list[str]
