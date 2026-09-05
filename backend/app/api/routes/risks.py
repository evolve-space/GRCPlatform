import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_access, require_roles
from app.core.audit import registrar_evento
from app.core.database import get_db
from app.core.risk_scoring import calcular_score
from app.models.asset import Asset
from app.models.risk import Risk, RiskStatus, RiskTreatment
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.risk import RiskCreate, RiskRead, RiskUpdate

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)

_RANGOS_NIVEL = {
    "bajo": (1, 4),
    "medio": (5, 9),
    "alto": (10, 16),
    "critico": (17, 25),
}


def _ip_del_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def _obtener_riesgo_o_404(db: Session, risk_id: uuid.UUID, organization_id: uuid.UUID) -> Risk:
    riesgo = (
        db.query(Risk)
        .filter(Risk.id == risk_id, Risk.organization_id == organization_id)
        .first()
    )
    if riesgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Riesgo no encontrado.")
    return riesgo


def _validar_activo_de_la_organizacion(
    db: Session, asset_id: uuid.UUID | None, organization_id: uuid.UUID
) -> None:
    if asset_id is None:
        return
    activo = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.organization_id == organization_id)
        .first()
    )
    if activo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado.")


def _recalcular_scores(riesgo: Risk) -> None:
    riesgo.inherent_score = calcular_score(riesgo.likelihood, riesgo.impact)
    if riesgo.residual_likelihood is not None and riesgo.residual_impact is not None:
        riesgo.residual_score = calcular_score(riesgo.residual_likelihood, riesgo.residual_impact)
    else:
        riesgo.residual_score = None


@router.post("", response_model=RiskRead, status_code=status.HTTP_201_CREATED)
def create_risk(
    payload: RiskCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_ESCRITURA, scope="risks:write")),
) -> Risk:
    _validar_activo_de_la_organizacion(db, payload.asset_id, actor.organization_id)

    riesgo = Risk(organization_id=actor.organization_id, **payload.model_dump())
    _recalcular_scores(riesgo)

    db.add(riesgo)
    db.flush()
    registrar_evento(
        db,
        organization_id=actor.organization_id,
        user_id=actor.id,
        integration_token_id=actor.integration.id if actor.integration else None,
        action="create_risk",
        entity_type="risk",
        entity_id=riesgo.id,
        ip_address=_ip_del_cliente(request),
        details={"title": riesgo.title},
    )
    db.commit()
    db.refresh(riesgo)
    return riesgo


@router.get("", response_model=Page[RiskRead])
def list_risks(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="risks:read")),
    search: str | None = Query(default=None, description="Busca en título y descripción"),
    category: str | None = Query(default=None),
    status_: RiskStatus | None = Query(default=None, alias="status"),
    treatment: RiskTreatment | None = Query(default=None),
    asset_id: uuid.UUID | None = Query(default=None),
    level: str | None = Query(default=None, description="bajo, medio, alto o critico"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[RiskRead]:
    consulta = db.query(Risk).filter(Risk.organization_id == actor.organization_id)

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(or_(Risk.title.ilike(patron), Risk.description.ilike(patron)))
    if category:
        consulta = consulta.filter(Risk.category.ilike(f"%{category}%"))
    if status_ is not None:
        consulta = consulta.filter(Risk.status == status_)
    if treatment is not None:
        consulta = consulta.filter(Risk.treatment == treatment)
    if asset_id is not None:
        consulta = consulta.filter(Risk.asset_id == asset_id)
    if level is not None:
        rango = _RANGOS_NIVEL.get(level.lower())
        if rango is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El nivel debe ser: bajo, medio, alto o critico.",
            )
        consulta = consulta.filter(Risk.inherent_score.between(*rango))

    total = consulta.count()
    riesgos = (
        consulta.order_by(Risk.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(items=riesgos, total=total, page=page, page_size=page_size)


@router.get("/{risk_id}", response_model=RiskRead)
def get_risk(
    risk_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="risks:read")),
) -> Risk:
    return _obtener_riesgo_o_404(db, risk_id, actor.organization_id)


@router.patch("/{risk_id}", response_model=RiskRead)
def update_risk(
    risk_id: uuid.UUID,
    payload: RiskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Risk:
    riesgo = _obtener_riesgo_o_404(db, risk_id, current_user.organization_id)

    datos = payload.model_dump(exclude_unset=True)
    if "asset_id" in datos:
        _validar_activo_de_la_organizacion(db, datos["asset_id"], current_user.organization_id)

    for campo, valor in datos.items():
        setattr(riesgo, campo, valor)

    _recalcular_scores(riesgo)

    db.commit()
    db.refresh(riesgo)
    return riesgo


@router.delete("/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_risk(
    risk_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    riesgo = _obtener_riesgo_o_404(db, risk_id, current_user.organization_id)
    db.delete(riesgo)
    db.commit()
