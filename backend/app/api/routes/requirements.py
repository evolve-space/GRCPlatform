import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.framework import Requirement
from app.models.user import User, UserRole
from app.schemas.requirement import RequirementRead, RequirementUpdate

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)


def _obtener_requisito_o_404(
    db: Session, requirement_id: uuid.UUID, current_user: User
) -> Requirement:
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
    return requisito


@router.get("/{requirement_id}", response_model=RequirementRead)
def get_requirement(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> Requirement:
    return _obtener_requisito_o_404(db, requirement_id, current_user)


@router.patch("/{requirement_id}", response_model=RequirementRead)
def update_requirement(
    requirement_id: uuid.UUID,
    payload: RequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Requirement:
    requisito = _obtener_requisito_o_404(db, requirement_id, current_user)

    datos = payload.model_dump(exclude_unset=True)
    if "parent_requirement_id" in datos and datos["parent_requirement_id"] is not None:
        if datos["parent_requirement_id"] == requisito.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Un requisito no puede ser su propio padre.",
            )
        padre = (
            db.query(Requirement)
            .filter(
                Requirement.id == datos["parent_requirement_id"],
                Requirement.organization_id == current_user.organization_id,
                Requirement.framework_id == requisito.framework_id,
            )
            .first()
        )
        if padre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El requisito padre indicado no existe en este marco de cumplimiento.",
            )

    for campo, valor in datos.items():
        setattr(requisito, campo, valor)

    db.commit()
    db.refresh(requisito)
    return requisito
