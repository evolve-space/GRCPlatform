"""Registro de eventos de auditoría.

Punto único de escritura del Audit Log para toda la aplicación. La consulta
del registro (``GET /api/v1/audit-logs``, con filtros y RBAC) se implementa
en ``app/api/routes/audit_logs.py`` (Fase 7).
"""

import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def registrar_evento(
    db: Session,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
    integration_token_id: uuid.UUID | None = None,
) -> None:
    """Añade una entrada de auditoría a la sesión (no hace commit por sí sola).

    Se añade a la misma sesión/transacción que la operación que audita, para
    que ambas se confirmen o se deshagan juntas. Nunca debe pasarse en
    ``details`` una contraseña, un token, un secreto ni el contenido de un archivo.

    ``user_id`` e ``integration_token_id`` son mutuamente excluyentes: un
    evento generado por un usuario humano rellena ``user_id``; uno generado
    por una integración (MCP u otro cliente API) rellena
    ``integration_token_id`` y deja ``user_id`` a ``None``.
    """
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            integration_token_id=integration_token_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            details=details,
        )
    )
