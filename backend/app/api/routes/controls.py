import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_access, require_roles
from app.core.database import get_db
from app.core.risk_scoring import clasificar_nivel
from app.models.asset import Asset
from app.models.control import Control, ControlFrequency, ControlStatus
from app.models.framework import Requirement
from app.models.risk import Risk
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.control import (
    AssetSummary,
    ControlCreate,
    ControlDetailRead,
    ControlRead,
    ControlUpdate,
    RequirementSummary,
    RiskSummary,
)

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _obtener_control_o_404(db: Session, control_id: uuid.UUID, organization_id: uuid.UUID) -> Control:
    control = (
        db.query(Control)
        .filter(Control.id == control_id, Control.organization_id == organization_id)
        .first()
    )
    if control is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control no encontrado.")
    return control


def _construir_detalle(control: Control) -> ControlDetailRead:
    return ControlDetailRead(
        **ControlRead.model_validate(control).model_dump(),
        risks=[
            RiskSummary(id=r.id, title=r.title, inherent_level=clasificar_nivel(r.inherent_score))
            for r in control.risks
        ],
        assets=[AssetSummary.model_validate(a) for a in control.assets],
        requirements=[
            RequirementSummary(
                id=req.id,
                code=req.code,
                name=req.name,
                framework_id=req.framework_id,
                framework_short_name=req.framework.short_name,
            )
            for req in control.requirements
        ],
    )


@router.post("", response_model=ControlRead, status_code=status.HTTP_201_CREATED)
def create_control(
    payload: ControlCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Control:
    ya_existe = (
        db.query(Control)
        .filter(
            Control.organization_id == current_user.organization_id,
            Control.control_id == payload.control_id,
        )
        .first()
    )
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un control con ese código en tu organización.",
        )

    control = Control(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(control)
    db.commit()
    db.refresh(control)
    return control


@router.get("", response_model=Page[ControlRead])
def list_controls(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="controls:read")),
    search: str | None = Query(default=None, description="Busca en código, nombre y descripción"),
    category: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    status_: ControlStatus | None = Query(default=None, alias="status"),
    frequency: ControlFrequency | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ControlRead]:
    consulta = db.query(Control).filter(Control.organization_id == actor.organization_id)

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            or_(
                Control.name.ilike(patron),
                Control.description.ilike(patron),
                Control.control_id.ilike(patron),
            )
        )
    if category:
        consulta = consulta.filter(Control.category.ilike(f"%{category}%"))
    if owner:
        consulta = consulta.filter(Control.owner.ilike(f"%{owner}%"))
    if status_ is not None:
        consulta = consulta.filter(Control.status == status_)
    if frequency is not None:
        consulta = consulta.filter(Control.frequency == frequency)

    total = consulta.count()
    controles = (
        consulta.order_by(Control.control_id).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(items=controles, total=total, page=page, page_size=page_size)


@router.get("/{control_id}", response_model=ControlDetailRead)
def get_control(
    control_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="controls:read")),
) -> ControlDetailRead:
    control = _obtener_control_o_404(db, control_id, actor.organization_id)
    return _construir_detalle(control)


@router.patch("/{control_id}", response_model=ControlRead)
def update_control(
    control_id: uuid.UUID,
    payload: ControlUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Control:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)

    datos = payload.model_dump(exclude_unset=True)
    if "control_id" in datos and datos["control_id"] != control.control_id:
        duplicado = (
            db.query(Control)
            .filter(
                Control.organization_id == current_user.organization_id,
                Control.control_id == datos["control_id"],
                Control.id != control.id,
            )
            .first()
        )
        if duplicado is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un control con ese código en tu organización.",
            )

    for campo, valor in datos.items():
        setattr(control, campo, valor)

    db.commit()
    db.refresh(control)
    return control


@router.delete("/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_control(
    control_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)
    db.delete(control)
    db.commit()


@router.post("/{control_id}/risks", response_model=ControlDetailRead, status_code=status.HTTP_201_CREATED)
def link_risk(
    control_id: uuid.UUID,
    risk_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> ControlDetailRead:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)
    riesgo = (
        db.query(Risk)
        .filter(Risk.id == risk_id, Risk.organization_id == current_user.organization_id)
        .first()
    )
    if riesgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Riesgo no encontrado.")
    if riesgo not in control.risks:
        control.risks.append(riesgo)
        db.commit()
        db.refresh(control)
    return _construir_detalle(control)


@router.delete("/{control_id}/risks/{risk_id}", response_model=ControlDetailRead)
def unlink_risk(
    control_id: uuid.UUID,
    risk_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> ControlDetailRead:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)
    control.risks = [r for r in control.risks if r.id != risk_id]
    db.commit()
    db.refresh(control)
    return _construir_detalle(control)


@router.post(
    "/{control_id}/assets", response_model=ControlDetailRead, status_code=status.HTTP_201_CREATED
)
def link_asset(
    control_id: uuid.UUID,
    asset_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> ControlDetailRead:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)
    activo = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.organization_id == current_user.organization_id)
        .first()
    )
    if activo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado.")
    if activo not in control.assets:
        control.assets.append(activo)
        db.commit()
        db.refresh(control)
    return _construir_detalle(control)


@router.delete("/{control_id}/assets/{asset_id}", response_model=ControlDetailRead)
def unlink_asset(
    control_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> ControlDetailRead:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)
    control.assets = [a for a in control.assets if a.id != asset_id]
    db.commit()
    db.refresh(control)
    return _construir_detalle(control)


@router.post(
    "/{control_id}/requirements",
    response_model=ControlDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def link_requirement(
    control_id: uuid.UUID,
    requirement_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> ControlDetailRead:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)
    requisito = (
        db.query(Requirement)
        .filter(
            Requirement.id == requirement_id,
            Requirement.organization_id == current_user.organization_id,
        )
        .first()
    )
    if requisito is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisito no encontrado.")
    if requisito not in control.requirements:
        control.requirements.append(requisito)
        db.commit()
        db.refresh(control)
    return _construir_detalle(control)


@router.delete("/{control_id}/requirements/{requirement_id}", response_model=ControlDetailRead)
def unlink_requirement(
    control_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> ControlDetailRead:
    control = _obtener_control_o_404(db, control_id, current_user.organization_id)
    control.requirements = [r for r in control.requirements if r.id != requirement_id]
    db.commit()
    db.refresh(control)
    return _construir_detalle(control)
