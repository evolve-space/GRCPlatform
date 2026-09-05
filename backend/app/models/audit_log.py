import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.integration_token import IntegrationToken
    from app.models.user import User


class AuditLog(Base):
    """Registro de auditoría de operaciones sensibles.

    Creado en la Fase 5 como escritura únicamente; la Fase 7 añade el
    endpoint de consulta (``GET /api/v1/audit-logs``) y la pantalla de
    frontend, sin necesidad de migrar el modelo. La Fase 9 añade
    ``integration_token_id`` para distinguir un evento generado por una
    integración (MCP u otro cliente API) de uno generado por un usuario
    humano: como mucho uno de ``user_id``/``integration_token_id`` está
    relleno en una misma fila, nunca ambos.

    ``action`` y ``entity_type`` son texto libre (no enum) para no requerir
    una migración cada vez que se añada un nuevo tipo de evento. Nunca debe
    registrarse aquí una contraseña, un token, un secreto ni el contenido de
    un archivo. No existe (ni debe existir) ningún endpoint de escritura
    público sobre este modelo: la única forma de generar una entrada es
    ``registrar_evento`` desde el propio backend, en la misma transacción que
    la operación que audita.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    integration_token_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("integration_tokens.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User | None"] = relationship()
    integration_token: Mapped["IntegrationToken | None"] = relationship()
