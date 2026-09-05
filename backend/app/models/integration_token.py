import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User

# Scopes válidos. Lista cerrada y explícita (no un string libre) para que una
# integración nunca pueda "inventarse" un permiso que no exista en la API.
INTEGRATION_TOKEN_PREFIX_LEN = 12

VALID_SCOPES = frozenset(
    {
        "risks:read",
        "risks:write",
        "controls:read",
        "evidence:read",
        "findings:read",
        "remediation:read",
        "vendors:read",
        "dashboard:read",
        "compliance:read",
        "audit:read",
    }
)


class IntegrationToken(Base):
    """Credencial de integración (API key) para clientes no humanos (p. ej. el
    servidor MCP). Nunca se almacena el secreto en texto plano: solo su hash
    SHA-256 (`token_hash`), suficiente porque el secreto es de alta entropía
    generado por el servidor (a diferencia de una contraseña humana, no
    necesita un hash lento tipo bcrypt para resistir fuerza bruta offline) y
    permite una búsqueda por igualdad indexada en cada petición sin
    recalcular un hash costoso. Ver docs/SECURITY.md."""

    __tablename__ = "integration_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    token_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="integration_tokens")
    created_by: Mapped["User | None"] = relationship()
