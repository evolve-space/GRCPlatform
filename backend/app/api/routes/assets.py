import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.asset import Asset, AssetCriticality, AssetStatus, AssetType, DataClassification
from app.models.user import User, UserRole
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.schemas.common import Page

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _obtener_activo_o_404(db: Session, asset_id: uuid.UUID, current_user: User) -> Asset:
    activo = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.organization_id == current_user.organization_id)
        .first()
    )
    if activo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado.")
    return activo


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Asset:
    activo = Asset(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(activo)
    db.commit()
    db.refresh(activo)
    return activo


@router.get("", response_model=Page[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    search: str | None = Query(default=None, description="Busca en nombre y descripción"),
    asset_type: AssetType | None = Query(default=None),
    criticality: AssetCriticality | None = Query(default=None),
    data_classification: DataClassification | None = Query(default=None),
    status_: AssetStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[AssetRead]:
    consulta = db.query(Asset).filter(Asset.organization_id == current_user.organization_id)

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(or_(Asset.name.ilike(patron), Asset.description.ilike(patron)))
    if asset_type is not None:
        consulta = consulta.filter(Asset.asset_type == asset_type)
    if criticality is not None:
        consulta = consulta.filter(Asset.criticality == criticality)
    if data_classification is not None:
        consulta = consulta.filter(Asset.data_classification == data_classification)
    if status_ is not None:
        consulta = consulta.filter(Asset.status == status_)

    total = consulta.count()
    activos = (
        consulta.order_by(Asset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(items=activos, total=total, page=page, page_size=page_size)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> Asset:
    return _obtener_activo_o_404(db, asset_id, current_user)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Asset:
    activo = _obtener_activo_o_404(db, asset_id, current_user)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(activo, campo, valor)
    db.commit()
    db.refresh(activo)
    return activo


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    activo = _obtener_activo_o_404(db, asset_id, current_user)
    db.delete(activo)
    db.commit()
