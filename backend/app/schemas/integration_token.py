import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.integration_token import VALID_SCOPES


class IntegrationTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(min_length=1)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def _scopes_validos(cls, valor: list[str]) -> list[str]:
        invalidos = sorted(set(valor) - VALID_SCOPES)
        if invalidos:
            raise ValueError(f"Scopes no reconocidos: {', '.join(invalidos)}")
        # Sin duplicados, orden estable para respuestas deterministas.
        return sorted(set(valor))


class IntegrationTokenRead(BaseModel):
    """Nunca incluye el secreto ni su hash: solo metadatos."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    token_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_by_id: uuid.UUID | None
    revoked_at: datetime | None
    created_at: datetime


class IntegrationTokenCreated(IntegrationTokenRead):
    """Devuelto SOLO en la respuesta de creación: incluye el secreto en texto
    plano una única vez. No existe ningún endpoint que lo devuelva después."""

    token: str
