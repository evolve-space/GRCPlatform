import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_access, require_roles
from app.core.audit import registrar_evento
from app.core.database import get_db
from app.core.risk_scoring import clasificar_nivel
from app.models.asset import Asset, AssetCriticality
from app.models.control import Control
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingSource, FindingStatus, FindingType
from app.models.framework import Requirement
from app.models.risk import Risk
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.control import AssetSummary, RequirementSummary, RiskSummary
from app.schemas.evidence import ControlSummary, EvidenceSummary
from app.schemas.finding import (
    ActionSummary,
    FindingCreate,
    FindingDetailRead,
    FindingRead,
    FindingUpdate,
)

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _ip_del_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def _obtener_hallazgo_o_404(db: Session, finding_id: uuid.UUID, current_user: User) -> Finding:
    hallazgo = (
        db.query(Finding)
        .filter(Finding.id == finding_id, Finding.organization_id == current_user.organization_id)
        .first()
    )
    if hallazgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hallazgo no encontrado.")
    return hallazgo


def _construir_detalle(hallazgo: Finding) -> FindingDetailRead:
    base = FindingRead.model_validate(hallazgo)
    return FindingDetailRead(
        **base.model_dump(exclude={"is_overdue"}),
        risks=[
            RiskSummary(id=r.id, title=r.title, inherent_level=clasificar_nivel(r.inherent_score))
            for r in hallazgo.risks
        ],
        controls=[ControlSummary(id=c.id, control_id=c.control_id, name=c.name) for c in hallazgo.controls],
        assets=[AssetSummary.model_validate(a) for a in hallazgo.assets],
        requirements=[
            RequirementSummary(
                id=req.id,
                code=req.code,
                name=req.name,
                framework_id=req.framework_id,
                framework_short_name=req.framework.short_name,
            )
            for req in hallazgo.requirements
        ],
        evidence=[EvidenceSummary(id=e.id, name=e.name, classification=e.classification) for e in hallazgo.evidence],
        actions=[
            ActionSummary(
                id=a.id,
                action_id=a.action_id,
                title=a.title,
                owner=a.owner,
                priority=a.priority,
                status=a.status.value,
                due_date=a.due_date,
                is_overdue=a.status.value not in ("completed", "cancelled") and a.due_date < date.today(),
            )
            for a in hallazgo.actions
        ],
    )


def _validar_cierre(status_resultante: FindingStatus, resolution_summary_resultante: str | None) -> None:
    if status_resultante == FindingStatus.CLOSED and not resolution_summary_resultante:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Se requiere un resumen de resolución (resolution_summary) para cerrar un hallazgo.",
        )


@router.post("", response_model=FindingRead, status_code=status.HTTP_201_CREATED)
def create_finding(
    payload: FindingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Finding:
    ya_existe = (
        db.query(Finding)
        .filter(
            Finding.organization_id == current_user.organization_id,
            Finding.finding_id == payload.finding_id,
        )
        .first()
    )
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un hallazgo con ese código en tu organización.",
        )

    _validar_cierre(payload.status, payload.resolution_summary)

    hallazgo = Finding(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        closed_at=date.today() if payload.status == FindingStatus.CLOSED else None,
        **payload.model_dump(),
    )
    db.add(hallazgo)
    db.flush()  # asigna hallazgo.id (default de cliente) antes de auditar la creación
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="create_finding",
        entity_type="finding",
        entity_id=hallazgo.id,
        ip_address=_ip_del_cliente(request),
        details={"finding_id": payload.finding_id, "severity": payload.severity.value},
    )
    db.commit()
    db.refresh(hallazgo)
    return hallazgo


@router.get("", response_model=Page[FindingRead])
def list_findings(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="findings:read")),
    search: str | None = Query(default=None, description="Busca en código, título y descripción"),
    severity: AssetCriticality | None = Query(default=None),
    status_: FindingStatus | None = Query(default=None, alias="status"),
    finding_type: FindingType | None = Query(default=None),
    source: FindingSource | None = Query(default=None),
    owner: str | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    risk_id: uuid.UUID | None = Query(default=None),
    control_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[FindingRead]:
    consulta = db.query(Finding).filter(Finding.organization_id == actor.organization_id)

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            or_(
                Finding.title.ilike(patron),
                Finding.description.ilike(patron),
                Finding.finding_id.ilike(patron),
            )
        )
    if severity:
        consulta = consulta.filter(Finding.severity == severity)
    if status_ is not None:
        consulta = consulta.filter(Finding.status == status_)
    if finding_type is not None:
        consulta = consulta.filter(Finding.finding_type == finding_type)
    if source is not None:
        consulta = consulta.filter(Finding.source == source)
    if owner:
        consulta = consulta.filter(Finding.owner.ilike(f"%{owner}%"))
    if risk_id is not None:
        consulta = consulta.filter(Finding.risks.any(Risk.id == risk_id))
    if control_id is not None:
        consulta = consulta.filter(Finding.controls.any(Control.id == control_id))

    hoy = date.today()
    if overdue is True:
        consulta = consulta.filter(
            Finding.due_date < hoy, Finding.status.notin_(["closed", "accepted"])
        )
    elif overdue is False:
        consulta = consulta.filter(
            or_(Finding.due_date >= hoy, Finding.status.in_(["closed", "accepted"]))
        )

    total = consulta.count()
    hallazgos = (
        consulta.order_by(Finding.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(items=hallazgos, total=total, page=page, page_size=page_size)


@router.get("/{finding_id}", response_model=FindingDetailRead)
def get_finding(
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    return _construir_detalle(hallazgo)


@router.patch("/{finding_id}", response_model=FindingRead)
def update_finding(
    finding_id: uuid.UUID,
    payload: FindingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Finding:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)

    datos = payload.model_dump(exclude_unset=True)

    if "finding_id" in datos and datos["finding_id"] != hallazgo.finding_id:
        duplicado = (
            db.query(Finding)
            .filter(
                Finding.organization_id == current_user.organization_id,
                Finding.finding_id == datos["finding_id"],
                Finding.id != hallazgo.id,
            )
            .first()
        )
        if duplicado is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un hallazgo con ese código en tu organización.",
            )

    estado_original = hallazgo.status
    status_resultante = datos.get("status", hallazgo.status)
    resolution_resultante = datos.get("resolution_summary", hallazgo.resolution_summary)
    _validar_cierre(status_resultante, resolution_resultante)

    for campo, valor in datos.items():
        setattr(hallazgo, campo, valor)

    if status_resultante == FindingStatus.CLOSED and estado_original != FindingStatus.CLOSED:
        hallazgo.closed_at = date.today()
    elif status_resultante != FindingStatus.CLOSED and estado_original == FindingStatus.CLOSED:
        hallazgo.closed_at = None

    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="update_finding",
        entity_type="finding",
        entity_id=hallazgo.id,
        ip_address=_ip_del_cliente(request),
        details={"changed_fields": list(datos.keys())},
    )
    if status_resultante == FindingStatus.CLOSED and estado_original != FindingStatus.CLOSED:
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="close_finding",
            entity_type="finding",
            entity_id=hallazgo.id,
            ip_address=_ip_del_cliente(request),
        )

    db.commit()
    db.refresh(hallazgo)
    return hallazgo


@router.delete("/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_finding(
    finding_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="delete_finding",
        entity_type="finding",
        entity_id=hallazgo.id,
        ip_address=_ip_del_cliente(request),
        details={"finding_id": hallazgo.finding_id},
    )
    db.delete(hallazgo)
    db.commit()


# --- Relaciones GRC (sub-recursos) ---


@router.post("/{finding_id}/risks", response_model=FindingDetailRead, status_code=status.HTTP_201_CREATED)
def link_risk(
    finding_id: uuid.UUID,
    risk_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    riesgo = (
        db.query(Risk)
        .filter(Risk.id == risk_id, Risk.organization_id == current_user.organization_id)
        .first()
    )
    if riesgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Riesgo no encontrado.")
    if riesgo not in hallazgo.risks:
        hallazgo.risks.append(riesgo)
        db.commit()
        db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.delete("/{finding_id}/risks/{risk_id}", response_model=FindingDetailRead)
def unlink_risk(
    finding_id: uuid.UUID,
    risk_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    hallazgo.risks = [r for r in hallazgo.risks if r.id != risk_id]
    db.commit()
    db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.post(
    "/{finding_id}/controls", response_model=FindingDetailRead, status_code=status.HTTP_201_CREATED
)
def link_control(
    finding_id: uuid.UUID,
    control_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    control = (
        db.query(Control)
        .filter(Control.id == control_id, Control.organization_id == current_user.organization_id)
        .first()
    )
    if control is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control no encontrado.")
    if control not in hallazgo.controls:
        hallazgo.controls.append(control)
        db.commit()
        db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.delete("/{finding_id}/controls/{control_id}", response_model=FindingDetailRead)
def unlink_control(
    finding_id: uuid.UUID,
    control_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    hallazgo.controls = [c for c in hallazgo.controls if c.id != control_id]
    db.commit()
    db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.post("/{finding_id}/assets", response_model=FindingDetailRead, status_code=status.HTTP_201_CREATED)
def link_asset(
    finding_id: uuid.UUID,
    asset_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    activo = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.organization_id == current_user.organization_id)
        .first()
    )
    if activo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado.")
    if activo not in hallazgo.assets:
        hallazgo.assets.append(activo)
        db.commit()
        db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.delete("/{finding_id}/assets/{asset_id}", response_model=FindingDetailRead)
def unlink_asset(
    finding_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    hallazgo.assets = [a for a in hallazgo.assets if a.id != asset_id]
    db.commit()
    db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.post(
    "/{finding_id}/requirements",
    response_model=FindingDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def link_requirement(
    finding_id: uuid.UUID,
    requirement_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
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
    if requisito not in hallazgo.requirements:
        hallazgo.requirements.append(requisito)
        db.commit()
        db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.delete("/{finding_id}/requirements/{requirement_id}", response_model=FindingDetailRead)
def unlink_requirement(
    finding_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    hallazgo.requirements = [r for r in hallazgo.requirements if r.id != requirement_id]
    db.commit()
    db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.post(
    "/{finding_id}/evidence", response_model=FindingDetailRead, status_code=status.HTTP_201_CREATED
)
def link_evidence(
    finding_id: uuid.UUID,
    evidence_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    evidencia = (
        db.query(Evidence)
        .filter(Evidence.id == evidence_id, Evidence.organization_id == current_user.organization_id)
        .first()
    )
    if evidencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada.")
    if evidencia not in hallazgo.evidence:
        hallazgo.evidence.append(evidencia)
        db.commit()
        db.refresh(hallazgo)
    return _construir_detalle(hallazgo)


@router.delete("/{finding_id}/evidence/{evidence_id}", response_model=FindingDetailRead)
def unlink_evidence(
    finding_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> FindingDetailRead:
    hallazgo = _obtener_hallazgo_o_404(db, finding_id, current_user)
    hallazgo.evidence = [e for e in hallazgo.evidence if e.id != evidence_id]
    db.commit()
    db.refresh(hallazgo)
    return _construir_detalle(hallazgo)
