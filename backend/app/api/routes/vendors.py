import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_access, require_roles
from app.core.audit import registrar_evento
from app.core.database import get_db
from app.models.asset import AssetCriticality, DataClassification
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.risk import Risk
from app.models.user import User, UserRole
from app.models.vendor import VENDOR_UPCOMING_WINDOW_DAYS, Vendor, VendorDueDiligenceStatus, VendorStatus
from app.schemas.common import Page
from app.schemas.control import RiskSummary
from app.schemas.evidence import EvidenceSummary
from app.schemas.finding import ActionSummary, FindingSummary
from app.schemas.vendor import VendorCreate, VendorDetailRead, VendorRead, VendorUpdate
from app.core.risk_scoring import clasificar_nivel

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _ip_del_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def _obtener_proveedor_o_404(db: Session, vendor_id: uuid.UUID, organization_id: uuid.UUID) -> Vendor:
    proveedor = (
        db.query(Vendor)
        .filter(Vendor.id == vendor_id, Vendor.organization_id == organization_id)
        .first()
    )
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")
    return proveedor


def _construir_detalle(proveedor: Vendor) -> VendorDetailRead:
    base = VendorRead.model_validate(proveedor)
    acciones: list[ActionSummary] = []
    for hallazgo in proveedor.findings:
        for accion in hallazgo.actions:
            acciones.append(
                ActionSummary(
                    id=accion.id,
                    action_id=accion.action_id,
                    title=accion.title,
                    owner=accion.owner,
                    priority=accion.priority,
                    status=accion.status.value,
                    due_date=accion.due_date,
                    is_overdue=accion.status.value not in ("completed", "cancelled")
                    and accion.due_date < date.today(),
                )
            )
    return VendorDetailRead(
        **base.model_dump(
            exclude={"is_review_overdue", "is_review_due_soon", "is_contract_expired", "is_contract_expiring_soon"}
        ),
        risks=[
            RiskSummary(id=r.id, title=r.title, inherent_level=clasificar_nivel(r.inherent_score))
            for r in proveedor.risks
        ],
        evidence=[EvidenceSummary(id=e.id, name=e.name, classification=e.classification) for e in proveedor.evidence],
        findings=[
            FindingSummary(id=f.id, finding_id=f.finding_id, title=f.title, severity=f.severity, status=f.status)
            for f in proveedor.findings
        ],
        actions=acciones,
    )


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Vendor:
    ya_existe = (
        db.query(Vendor)
        .filter(
            Vendor.organization_id == current_user.organization_id,
            Vendor.vendor_id == payload.vendor_id,
        )
        .first()
    )
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un proveedor con ese código en tu organización.",
        )

    proveedor = Vendor(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(proveedor)
    db.flush()  # asigna proveedor.id (default de cliente) antes de auditar la creación
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="create_vendor",
        entity_type="vendor",
        entity_id=proveedor.id,
        ip_address=_ip_del_cliente(request),
        details={"vendor_id": payload.vendor_id, "status": payload.status.value},
    )
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.get("", response_model=Page[VendorRead])
def list_vendors(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="vendors:read")),
    search: str | None = Query(default=None, description="Busca en código, nombre y razón social"),
    status_: VendorStatus | None = Query(default=None, alias="status"),
    criticality: AssetCriticality | None = Query(default=None),
    data_classification: DataClassification | None = Query(default=None),
    due_diligence_status: VendorDueDiligenceStatus | None = Query(default=None),
    review_overdue: bool | None = Query(default=None),
    review_due_soon: bool | None = Query(default=None),
    contract_expired: bool | None = Query(default=None),
    contract_expiring_soon: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[VendorRead]:
    consulta = db.query(Vendor).filter(Vendor.organization_id == actor.organization_id)

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            or_(
                Vendor.name.ilike(patron),
                Vendor.legal_name.ilike(patron),
                Vendor.vendor_id.ilike(patron),
            )
        )
    if status_ is not None:
        consulta = consulta.filter(Vendor.status == status_)
    if criticality is not None:
        consulta = consulta.filter(Vendor.criticality == criticality)
    if data_classification is not None:
        consulta = consulta.filter(Vendor.data_classification == data_classification)
    if due_diligence_status is not None:
        consulta = consulta.filter(Vendor.due_diligence_status == due_diligence_status)

    hoy = date.today()
    limite_proximo = hoy + timedelta(days=VENDOR_UPCOMING_WINDOW_DAYS)

    if review_overdue is True:
        consulta = consulta.filter(Vendor.next_security_review_date.isnot(None), Vendor.next_security_review_date < hoy)
    elif review_overdue is False:
        consulta = consulta.filter(
            or_(Vendor.next_security_review_date.is_(None), Vendor.next_security_review_date >= hoy)
        )
    if review_due_soon is True:
        consulta = consulta.filter(
            Vendor.next_security_review_date.isnot(None),
            Vendor.next_security_review_date >= hoy,
            Vendor.next_security_review_date <= limite_proximo,
        )
    if contract_expired is True:
        consulta = consulta.filter(Vendor.contract_end_date.isnot(None), Vendor.contract_end_date < hoy)
    elif contract_expired is False:
        consulta = consulta.filter(or_(Vendor.contract_end_date.is_(None), Vendor.contract_end_date >= hoy))
    if contract_expiring_soon is True:
        consulta = consulta.filter(
            Vendor.contract_end_date.isnot(None),
            Vendor.contract_end_date >= hoy,
            Vendor.contract_end_date <= limite_proximo,
        )

    total = consulta.count()
    proveedores = (
        consulta.order_by(Vendor.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(items=proveedores, total=total, page=page, page_size=page_size)


@router.get("/{vendor_id}", response_model=VendorDetailRead)
def get_vendor(
    vendor_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="vendors:read")),
) -> VendorDetailRead:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, actor.organization_id)
    return _construir_detalle(proveedor)


@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Vendor:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)

    datos = payload.model_dump(exclude_unset=True)

    if "vendor_id" in datos and datos["vendor_id"] != proveedor.vendor_id:
        duplicado = (
            db.query(Vendor)
            .filter(
                Vendor.organization_id == current_user.organization_id,
                Vendor.vendor_id == datos["vendor_id"],
                Vendor.id != proveedor.id,
            )
            .first()
        )
        if duplicado is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un proveedor con ese código en tu organización.",
            )

    estado_original = proveedor.status

    for campo, valor in datos.items():
        setattr(proveedor, campo, valor)

    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="update_vendor",
        entity_type="vendor",
        entity_id=proveedor.id,
        ip_address=_ip_del_cliente(request),
        details={"changed_fields": list(datos.keys())},
    )
    if "status" in datos and datos["status"] != estado_original:
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="change_vendor_status",
            entity_type="vendor",
            entity_id=proveedor.id,
            ip_address=_ip_del_cliente(request),
            details={"from": estado_original.value, "to": datos["status"].value},
        )

    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(
    vendor_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="delete_vendor",
        entity_type="vendor",
        entity_id=proveedor.id,
        ip_address=_ip_del_cliente(request),
        details={"vendor_id": proveedor.vendor_id},
    )
    db.delete(proveedor)
    db.commit()


# --- Relaciones GRC (sub-recursos) ---


@router.post("/{vendor_id}/risks", response_model=VendorDetailRead, status_code=status.HTTP_201_CREATED)
def link_risk(
    vendor_id: uuid.UUID,
    request: Request,
    risk_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> VendorDetailRead:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)
    riesgo = (
        db.query(Risk)
        .filter(Risk.id == risk_id, Risk.organization_id == current_user.organization_id)
        .first()
    )
    if riesgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Riesgo no encontrado.")
    if riesgo not in proveedor.risks:
        proveedor.risks.append(riesgo)
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="link_vendor_risk",
            entity_type="vendor",
            entity_id=proveedor.id,
            ip_address=_ip_del_cliente(request),
            details={"risk_id": str(risk_id)},
        )
        db.commit()
        db.refresh(proveedor)
    return _construir_detalle(proveedor)


@router.delete("/{vendor_id}/risks/{risk_id}", response_model=VendorDetailRead)
def unlink_risk(
    vendor_id: uuid.UUID,
    risk_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> VendorDetailRead:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)
    proveedor.risks = [r for r in proveedor.risks if r.id != risk_id]
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="unlink_vendor_risk",
        entity_type="vendor",
        entity_id=proveedor.id,
        ip_address=_ip_del_cliente(request),
        details={"risk_id": str(risk_id)},
    )
    db.commit()
    db.refresh(proveedor)
    return _construir_detalle(proveedor)


@router.post("/{vendor_id}/evidence", response_model=VendorDetailRead, status_code=status.HTTP_201_CREATED)
def link_evidence(
    vendor_id: uuid.UUID,
    request: Request,
    evidence_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> VendorDetailRead:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)
    evidencia = (
        db.query(Evidence)
        .filter(Evidence.id == evidence_id, Evidence.organization_id == current_user.organization_id)
        .first()
    )
    if evidencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada.")
    if evidencia not in proveedor.evidence:
        proveedor.evidence.append(evidencia)
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="link_vendor_evidence",
            entity_type="vendor",
            entity_id=proveedor.id,
            ip_address=_ip_del_cliente(request),
            details={"evidence_id": str(evidence_id)},
        )
        db.commit()
        db.refresh(proveedor)
    return _construir_detalle(proveedor)


@router.delete("/{vendor_id}/evidence/{evidence_id}", response_model=VendorDetailRead)
def unlink_evidence(
    vendor_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> VendorDetailRead:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)
    proveedor.evidence = [e for e in proveedor.evidence if e.id != evidence_id]
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="unlink_vendor_evidence",
        entity_type="vendor",
        entity_id=proveedor.id,
        ip_address=_ip_del_cliente(request),
        details={"evidence_id": str(evidence_id)},
    )
    db.commit()
    db.refresh(proveedor)
    return _construir_detalle(proveedor)


@router.post("/{vendor_id}/findings", response_model=VendorDetailRead, status_code=status.HTTP_201_CREATED)
def link_finding(
    vendor_id: uuid.UUID,
    request: Request,
    finding_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> VendorDetailRead:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)
    hallazgo = (
        db.query(Finding)
        .filter(Finding.id == finding_id, Finding.organization_id == current_user.organization_id)
        .first()
    )
    if hallazgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hallazgo no encontrado.")
    if hallazgo not in proveedor.findings:
        proveedor.findings.append(hallazgo)
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="link_vendor_finding",
            entity_type="vendor",
            entity_id=proveedor.id,
            ip_address=_ip_del_cliente(request),
            details={"finding_id": str(finding_id)},
        )
        db.commit()
        db.refresh(proveedor)
    return _construir_detalle(proveedor)


@router.delete("/{vendor_id}/findings/{finding_id}", response_model=VendorDetailRead)
def unlink_finding(
    vendor_id: uuid.UUID,
    finding_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> VendorDetailRead:
    proveedor = _obtener_proveedor_o_404(db, vendor_id, current_user.organization_id)
    proveedor.findings = [f for f in proveedor.findings if f.id != finding_id]
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="unlink_vendor_finding",
        entity_type="vendor",
        entity_id=proveedor.id,
        ip_address=_ip_del_cliente(request),
        details={"finding_id": str(finding_id)},
    )
    db.commit()
    db.refresh(proveedor)
    return _construir_detalle(proveedor)
