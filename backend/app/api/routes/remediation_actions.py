import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_access, require_roles
from app.core.audit import registrar_evento
from app.core.database import get_db
from app.models.asset import AssetCriticality
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingStatus
from app.models.remediation_action import ActionStatus, RemediationAction
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.evidence import EvidenceSummary
from app.schemas.remediation_action import (
    RemediationActionCreate,
    RemediationActionDetailRead,
    RemediationActionRead,
    RemediationActionUpdate,
)

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _ip_del_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def _obtener_accion_o_404(db: Session, action_id: uuid.UUID, current_user: User) -> RemediationAction:
    accion = (
        db.query(RemediationAction)
        .filter(
            RemediationAction.id == action_id,
            RemediationAction.organization_id == current_user.organization_id,
        )
        .first()
    )
    if accion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acción no encontrada.")
    return accion


def _construir_detalle(accion: RemediationAction) -> RemediationActionDetailRead:
    base = RemediationActionRead.model_validate(accion)
    return RemediationActionDetailRead(
        **base.model_dump(exclude={"is_overdue"}),
        evidence=[EvidenceSummary(id=e.id, name=e.name, classification=e.classification) for e in accion.evidence],
    )


@router.post("", response_model=RemediationActionRead, status_code=status.HTTP_201_CREATED)
def create_action(
    payload: RemediationActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> RemediationAction:
    hallazgo = (
        db.query(Finding)
        .filter(Finding.id == payload.finding_id, Finding.organization_id == current_user.organization_id)
        .first()
    )
    if hallazgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hallazgo no encontrado.")
    if hallazgo.status == FindingStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pueden añadir acciones a un hallazgo cerrado. Reábrelo primero.",
        )

    ya_existe = (
        db.query(RemediationAction)
        .filter(
            RemediationAction.organization_id == current_user.organization_id,
            RemediationAction.action_id == payload.action_id,
        )
        .first()
    )
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una acción con ese código en tu organización.",
        )

    accion = RemediationAction(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        completed_at=date.today() if payload.status == ActionStatus.COMPLETED else None,
        **payload.model_dump(),
    )
    db.add(accion)
    db.flush()  # asigna accion.id (default de cliente) antes de auditar la creación
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="create_action",
        entity_type="remediation_action",
        entity_id=accion.id,
        ip_address=_ip_del_cliente(request),
        details={"action_id": payload.action_id, "finding_id": str(payload.finding_id)},
    )
    db.commit()
    db.refresh(accion)
    return accion


@router.get("", response_model=Page[RemediationActionRead])
def list_actions(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="remediation:read")),
    search: str | None = Query(default=None, description="Busca en código, título y descripción"),
    status_: ActionStatus | None = Query(default=None, alias="status"),
    priority: AssetCriticality | None = Query(default=None),
    owner: str | None = Query(default=None),
    finding_id: uuid.UUID | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[RemediationActionRead]:
    consulta = db.query(RemediationAction).filter(
        RemediationAction.organization_id == actor.organization_id
    )

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            or_(
                RemediationAction.title.ilike(patron),
                RemediationAction.description.ilike(patron),
                RemediationAction.action_id.ilike(patron),
            )
        )
    if status_ is not None:
        consulta = consulta.filter(RemediationAction.status == status_)
    if priority is not None:
        consulta = consulta.filter(RemediationAction.priority == priority)
    if owner:
        consulta = consulta.filter(RemediationAction.owner.ilike(f"%{owner}%"))
    if finding_id is not None:
        consulta = consulta.filter(RemediationAction.finding_id == finding_id)

    hoy = date.today()
    if overdue is True:
        consulta = consulta.filter(
            RemediationAction.due_date < hoy, RemediationAction.status.notin_(["completed", "cancelled"])
        )
    elif overdue is False:
        consulta = consulta.filter(
            or_(
                RemediationAction.due_date >= hoy,
                RemediationAction.status.in_(["completed", "cancelled"]),
            )
        )

    total = consulta.count()
    acciones = (
        consulta.order_by(RemediationAction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Page(items=acciones, total=total, page=page, page_size=page_size)


@router.get("/{action_id}", response_model=RemediationActionDetailRead)
def get_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> RemediationActionDetailRead:
    accion = _obtener_accion_o_404(db, action_id, current_user)
    return _construir_detalle(accion)


@router.patch("/{action_id}", response_model=RemediationActionRead)
def update_action(
    action_id: uuid.UUID,
    payload: RemediationActionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> RemediationAction:
    accion = _obtener_accion_o_404(db, action_id, current_user)

    datos = payload.model_dump(exclude_unset=True)

    if "action_id" in datos and datos["action_id"] != accion.action_id:
        duplicado = (
            db.query(RemediationAction)
            .filter(
                RemediationAction.organization_id == current_user.organization_id,
                RemediationAction.action_id == datos["action_id"],
                RemediationAction.id != accion.id,
            )
            .first()
        )
        if duplicado is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una acción con ese código en tu organización.",
            )

    estado_original = accion.status
    status_resultante = datos.get("status", accion.status)

    for campo, valor in datos.items():
        setattr(accion, campo, valor)

    if status_resultante == ActionStatus.COMPLETED and estado_original != ActionStatus.COMPLETED:
        accion.completed_at = date.today()
    elif status_resultante != ActionStatus.COMPLETED and estado_original == ActionStatus.COMPLETED:
        accion.completed_at = None

    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="update_action",
        entity_type="remediation_action",
        entity_id=accion.id,
        ip_address=_ip_del_cliente(request),
        details={"changed_fields": list(datos.keys())},
    )
    if status_resultante == ActionStatus.COMPLETED and estado_original != ActionStatus.COMPLETED:
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="complete_action",
            entity_type="remediation_action",
            entity_id=accion.id,
            ip_address=_ip_del_cliente(request),
        )

    db.commit()
    db.refresh(accion)
    return accion


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action(
    action_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    accion = _obtener_accion_o_404(db, action_id, current_user)
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="delete_action",
        entity_type="remediation_action",
        entity_id=accion.id,
        ip_address=_ip_del_cliente(request),
        details={"action_id": accion.action_id},
    )
    db.delete(accion)
    db.commit()


@router.post(
    "/{action_id}/evidence", response_model=RemediationActionDetailRead, status_code=status.HTTP_201_CREATED
)
def link_evidence(
    action_id: uuid.UUID,
    evidence_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> RemediationActionDetailRead:
    accion = _obtener_accion_o_404(db, action_id, current_user)
    evidencia = (
        db.query(Evidence)
        .filter(Evidence.id == evidence_id, Evidence.organization_id == current_user.organization_id)
        .first()
    )
    if evidencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada.")
    if evidencia not in accion.evidence:
        accion.evidence.append(evidencia)
        db.commit()
        db.refresh(accion)
    return _construir_detalle(accion)


@router.delete("/{action_id}/evidence/{evidence_id}", response_model=RemediationActionDetailRead)
def unlink_evidence(
    action_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> RemediationActionDetailRead:
    accion = _obtener_accion_o_404(db, action_id, current_user)
    accion.evidence = [e for e in accion.evidence if e.id != evidence_id]
    db.commit()
    db.refresh(accion)
    return _construir_detalle(accion)
