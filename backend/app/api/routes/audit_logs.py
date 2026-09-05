import uuid
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.audit_log import ActorSummary, AuditLogMeta, AuditLogRead, IntegrationActorSummary
from app.schemas.common import Page

router = APIRouter()

# Lectura restringida a roles de gestión/supervisión (principio de mínimo
# privilegio): el registro de auditoría es una herramienta de gobierno y
# cumplimiento, no una funcionalidad operativa del día a día de un Analyst,
# y Viewer no tiene ningún acceso a él. Ver docs/SECURITY.md.
_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _a_lectura(log: AuditLog) -> AuditLogRead:
    actor = None
    if log.user is not None:
        actor = ActorSummary(id=log.user.id, email=log.user.email, full_name=log.user.full_name)
    integration_actor = None
    if log.integration_token is not None:
        integration_actor = IntegrationActorSummary(id=log.integration_token.id, name=log.integration_token.name)
    return AuditLogRead(
        id=log.id,
        organization_id=log.organization_id,
        user_id=log.user_id,
        integration_token_id=log.integration_token_id,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        ip_address=log.ip_address,
        details=log.details,
        created_at=log.created_at,
        actor=actor,
        integration_actor=integration_actor,
    )


@router.get("", response_model=Page[AuditLogRead])
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    action: str | None = Query(default=None, description="Nombre exacto del evento, p. ej. create_vendor"),
    entity_type: str | None = Query(default=None, description="p. ej. vendor, finding, remediation_action"),
    entity_id: uuid.UUID | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None, description="Actor que realizó la acción"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[AuditLogRead]:
    consulta = db.query(AuditLog).filter(AuditLog.organization_id == current_user.organization_id)

    if action:
        consulta = consulta.filter(AuditLog.action == action)
    if entity_type:
        consulta = consulta.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        consulta = consulta.filter(AuditLog.entity_id == entity_id)
    if user_id is not None:
        consulta = consulta.filter(AuditLog.user_id == user_id)
    if date_from is not None:
        consulta = consulta.filter(AuditLog.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        consulta = consulta.filter(AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    total = consulta.count()
    registros = (
        consulta.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(items=[_a_lectura(r) for r in registros], total=total, page=page, page_size=page_size)


@router.get("/meta", response_model=AuditLogMeta)
def get_audit_log_meta(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> AuditLogMeta:
    """Valores distintos de acción/entidad ya registrados en la organización,
    para poblar los desplegables de filtro del frontend sin hardcodear una
    lista que quedaría desactualizada cada vez que un módulo añada un evento."""
    acciones = (
        db.query(AuditLog.action)
        .filter(AuditLog.organization_id == current_user.organization_id)
        .distinct()
        .order_by(AuditLog.action)
        .all()
    )
    entidades = (
        db.query(AuditLog.entity_type)
        .filter(AuditLog.organization_id == current_user.organization_id)
        .distinct()
        .order_by(AuditLog.entity_type)
        .all()
    )
    return AuditLogMeta(actions=[a[0] for a in acciones], entity_types=[e[0] for e in entidades])
