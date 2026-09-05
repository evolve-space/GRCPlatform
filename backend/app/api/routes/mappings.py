import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.framework import FrameworkMapping, Requirement
from app.models.user import User, UserRole
from app.schemas.mapping import FrameworkMappingCreate, FrameworkMappingRead, RequirementBrief

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _requisito_de_la_organizacion(
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


def _resumen(requisito: Requirement) -> RequirementBrief:
    return RequirementBrief(
        id=requisito.id,
        code=requisito.code,
        name=requisito.name,
        framework_id=requisito.framework_id,
        framework_short_name=requisito.framework.short_name,
    )


def _construir_lectura(mapping: FrameworkMapping) -> FrameworkMappingRead:
    return FrameworkMappingRead(
        id=mapping.id,
        organization_id=mapping.organization_id,
        source_requirement=_resumen(mapping.source_requirement),
        target_requirement=_resumen(mapping.target_requirement),
        notes=mapping.notes,
        created_at=mapping.created_at,
    )


def _obtener_mapping_o_404(
    db: Session, mapping_id: uuid.UUID, current_user: User
) -> FrameworkMapping:
    mapping = (
        db.query(FrameworkMapping)
        .filter(
            FrameworkMapping.id == mapping_id,
            FrameworkMapping.organization_id == current_user.organization_id,
        )
        .first()
    )
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping no encontrado.")
    return mapping


@router.post("", response_model=FrameworkMappingRead, status_code=status.HTTP_201_CREATED)
def create_mapping(
    payload: FrameworkMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FrameworkMappingRead:
    if payload.source_requirement_id == payload.target_requirement_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un requisito no puede mapearse consigo mismo.",
        )

    origen = _requisito_de_la_organizacion(db, payload.source_requirement_id, current_user)
    destino = _requisito_de_la_organizacion(db, payload.target_requirement_id, current_user)

    if origen.framework_id == destino.framework_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un mapping debe relacionar requisitos de marcos de cumplimiento distintos.",
        )

    ya_existe = (
        db.query(FrameworkMapping)
        .filter(
            FrameworkMapping.organization_id == current_user.organization_id,
            FrameworkMapping.source_requirement_id == origen.id,
            FrameworkMapping.target_requirement_id == destino.id,
        )
        .first()
    )
    if ya_existe is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese mapping ya existe.")

    mapping = FrameworkMapping(
        organization_id=current_user.organization_id,
        source_requirement_id=origen.id,
        target_requirement_id=destino.id,
        notes=payload.notes,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return _construir_lectura(mapping)


@router.get("", response_model=list[FrameworkMappingRead])
def list_mappings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    requirement_id: uuid.UUID | None = Query(default=None),
) -> list[FrameworkMappingRead]:
    consulta = db.query(FrameworkMapping).filter(
        FrameworkMapping.organization_id == current_user.organization_id
    )
    if requirement_id is not None:
        consulta = consulta.filter(
            or_(
                FrameworkMapping.source_requirement_id == requirement_id,
                FrameworkMapping.target_requirement_id == requirement_id,
            )
        )
    return [_construir_lectura(m) for m in consulta.all()]


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(
    mapping_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    mapping = _obtener_mapping_o_404(db, mapping_id, current_user)
    db.delete(mapping)
    db.commit()
