import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.associations import control_requirements
from app.models.control import Control, ControlStatus
from app.models.framework import Framework, FrameworkStatus, Requirement
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.framework import (
    ComplianceSummary,
    FrameworkCreate,
    FrameworkDetailRead,
    FrameworkRead,
    FrameworkUpdate,
)
from app.schemas.requirement import RequirementCreate, RequirementRead

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _obtener_framework_o_404(db: Session, framework_id: uuid.UUID, current_user: User) -> Framework:
    framework = (
        db.query(Framework)
        .filter(
            Framework.id == framework_id, Framework.organization_id == current_user.organization_id
        )
        .first()
    )
    if framework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Marco de cumplimiento no encontrado."
        )
    return framework


def _calcular_resumen_cumplimiento(db: Session, framework: Framework) -> ComplianceSummary:
    requirement_ids = [r.id for r in framework.requirements]
    if not requirement_ids:
        return ComplianceSummary(
            implemented=0,
            partially_implemented=0,
            not_implemented=0,
            not_applicable=0,
            total_requirements=0,
            requirements_with_control=0,
        )

    controles = (
        db.query(Control)
        .join(control_requirements, Control.id == control_requirements.c.control_id)
        .filter(control_requirements.c.requirement_id.in_(requirement_ids))
        .distinct()
        .all()
    )
    conteo = dict.fromkeys(ControlStatus, 0)
    for control in controles:
        conteo[control.status] += 1

    requisitos_con_control = (
        db.query(control_requirements.c.requirement_id)
        .filter(control_requirements.c.requirement_id.in_(requirement_ids))
        .distinct()
        .count()
    )

    return ComplianceSummary(
        implemented=conteo[ControlStatus.IMPLEMENTED],
        partially_implemented=conteo[ControlStatus.PARTIALLY_IMPLEMENTED],
        not_implemented=conteo[ControlStatus.NOT_IMPLEMENTED],
        not_applicable=conteo[ControlStatus.NOT_APPLICABLE],
        total_requirements=len(requirement_ids),
        requirements_with_control=requisitos_con_control,
    )


@router.post("", response_model=FrameworkRead, status_code=status.HTTP_201_CREATED)
def create_framework(
    payload: FrameworkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Framework:
    ya_existe = (
        db.query(Framework)
        .filter(
            Framework.organization_id == current_user.organization_id,
            Framework.short_name == payload.short_name,
        )
        .first()
    )
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un marco de cumplimiento con ese nombre corto en tu organización.",
        )
    framework = Framework(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(framework)
    db.commit()
    db.refresh(framework)
    return framework


@router.get("", response_model=list[FrameworkRead])
def list_frameworks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    status_: FrameworkStatus | None = Query(default=None, alias="status"),
) -> list[Framework]:
    consulta = db.query(Framework).filter(Framework.organization_id == current_user.organization_id)
    if status_ is not None:
        consulta = consulta.filter(Framework.status == status_)
    return consulta.order_by(Framework.short_name).all()


@router.get("/{framework_id}", response_model=FrameworkDetailRead)
def get_framework(
    framework_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> FrameworkDetailRead:
    framework = _obtener_framework_o_404(db, framework_id, current_user)
    resumen = _calcular_resumen_cumplimiento(db, framework)
    return FrameworkDetailRead(
        **FrameworkRead.model_validate(framework).model_dump(), compliance_summary=resumen
    )


@router.patch("/{framework_id}", response_model=FrameworkRead)
def update_framework(
    framework_id: uuid.UUID,
    payload: FrameworkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Framework:
    framework = _obtener_framework_o_404(db, framework_id, current_user)

    datos = payload.model_dump(exclude_unset=True)
    if "short_name" in datos and datos["short_name"] != framework.short_name:
        duplicado = (
            db.query(Framework)
            .filter(
                Framework.organization_id == current_user.organization_id,
                Framework.short_name == datos["short_name"],
                Framework.id != framework.id,
            )
            .first()
        )
        if duplicado is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un marco de cumplimiento con ese nombre corto en tu organización.",
            )

    for campo, valor in datos.items():
        setattr(framework, campo, valor)
    db.commit()
    db.refresh(framework)
    return framework


@router.delete("/{framework_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_framework(
    framework_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    framework = _obtener_framework_o_404(db, framework_id, current_user)
    db.delete(framework)
    db.commit()


@router.post(
    "/{framework_id}/requirements",
    response_model=RequirementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement(
    framework_id: uuid.UUID,
    payload: RequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Requirement:
    framework = _obtener_framework_o_404(db, framework_id, current_user)

    if payload.parent_requirement_id is not None:
        padre = (
            db.query(Requirement)
            .filter(
                Requirement.id == payload.parent_requirement_id,
                Requirement.organization_id == current_user.organization_id,
                Requirement.framework_id == framework.id,
            )
            .first()
        )
        if padre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El requisito padre indicado no existe en este marco de cumplimiento.",
            )

    ya_existe = (
        db.query(Requirement)
        .filter(Requirement.framework_id == framework.id, Requirement.code == payload.code)
        .first()
    )
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un requisito con ese código en este marco de cumplimiento.",
        )

    requisito = Requirement(
        organization_id=current_user.organization_id,
        framework_id=framework.id,
        **payload.model_dump(),
    )
    db.add(requisito)
    db.commit()
    db.refresh(requisito)
    return requisito


@router.get("/{framework_id}/requirements", response_model=Page[RequirementRead])
def list_requirements(
    framework_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    parent_requirement_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Page[RequirementRead]:
    framework = _obtener_framework_o_404(db, framework_id, current_user)
    consulta = db.query(Requirement).filter(Requirement.framework_id == framework.id)

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            or_(
                Requirement.name.ilike(patron),
                Requirement.description.ilike(patron),
                Requirement.code.ilike(patron),
            )
        )
    if category:
        consulta = consulta.filter(Requirement.category.ilike(f"%{category}%"))
    if parent_requirement_id is not None:
        consulta = consulta.filter(Requirement.parent_requirement_id == parent_requirement_id)

    total = consulta.count()
    requisitos = (
        consulta.order_by(Requirement.code).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(items=requisitos, total=total, page=page, page_size=page_size)
