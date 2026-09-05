import hashlib
import uuid
from datetime import date, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_access, require_roles
from app.core.audit import registrar_evento
from app.core.config import settings
from app.core.database import get_db
from app.core.file_validation import ArchivoInvalido, determinar_tipo_seguro, sanear_nombre_original
from app.core.risk_scoring import clasificar_nivel
from app.core.storage import storage_service
from app.models.asset import Asset, DataClassification
from app.models.control import Control
from app.models.evidence import Evidence, EvidenceStatus
from app.models.framework import Requirement
from app.models.risk import Risk
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.control import AssetSummary, RequirementSummary, RiskSummary
from app.schemas.evidence import (
    ControlSummary,
    EvidenceDetailRead,
    EvidenceMetadata,
    EvidenceRead,
    EvidenceUpdate,
    IntegrityCheckResult,
)

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)
_ROLES_ESCRITURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST)
_ROLES_ELIMINACION = (UserRole.ADMIN, UserRole.GRC_MANAGER)


def _ip_del_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def _obtener_evidencia_o_404(db: Session, evidence_id: uuid.UUID, organization_id: uuid.UUID) -> Evidence:
    evidencia = (
        db.query(Evidence)
        .filter(Evidence.id == evidence_id, Evidence.organization_id == organization_id)
        .first()
    )
    if evidencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada.")
    return evidencia


def _construir_detalle(evidencia: Evidence) -> EvidenceDetailRead:
    base = EvidenceRead.model_validate(evidencia)
    return EvidenceDetailRead(
        **base.model_dump(exclude={"is_expired", "effective_status"}),
        controls=[
            ControlSummary(id=c.id, control_id=c.control_id, name=c.name) for c in evidencia.controls
        ],
        risks=[
            RiskSummary(id=r.id, title=r.title, inherent_level=clasificar_nivel(r.inherent_score))
            for r in evidencia.risks
        ],
        assets=[AssetSummary.model_validate(a) for a in evidencia.assets],
        requirements=[
            RequirementSummary(
                id=req.id,
                code=req.code,
                name=req.name,
                framework_id=req.framework_id,
                framework_short_name=req.framework.short_name,
            )
            for req in evidencia.requirements
        ],
    )


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    classification: DataClassification = Form(...),
    evidence_type: str = Form(...),
    collected_at: date = Form(...),
    expires_at: date | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Evidence:
    try:
        metadata = EvidenceMetadata(
            name=name,
            description=description,
            classification=classification,
            evidence_type=evidence_type,
            collected_at=collected_at,
            expires_at=expires_at,
        )
    except ValidationError as exc:
        mensajes = [error["msg"] for error in exc.errors()]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(mensajes)
        ) from None

    contenido = await file.read()

    try:
        nombre_saneado = sanear_nombre_original(file.filename or "")
        mime_type, extension = determinar_tipo_seguro(
            nombre_saneado, contenido, settings.max_evidence_file_size_bytes
        )
    except ArchivoInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None

    sha256_hex = hashlib.sha256(contenido).hexdigest()
    storage_key = storage_service.generar_storage_key(current_user.organization_id, extension)
    storage_service.guardar(storage_key, contenido)

    try:
        evidencia = Evidence(
            organization_id=current_user.organization_id,
            name=metadata.name,
            description=metadata.description,
            original_filename=nombre_saneado,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(contenido),
            sha256=sha256_hex,
            classification=metadata.classification,
            evidence_type=metadata.evidence_type,
            collected_at=metadata.collected_at,
            expires_at=metadata.expires_at,
            uploaded_by_id=current_user.id,
        )
        db.add(evidencia)
        db.flush()  # asigna evidencia.id (default de cliente) antes de auditar la creación
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="upload_evidence",
            entity_type="evidence",
            entity_id=evidencia.id,
            ip_address=_ip_del_cliente(request),
            details={
                "original_filename": nombre_saneado,
                "size": len(contenido),
                "classification": metadata.classification.value,
            },
        )
        db.commit()
    except Exception:
        storage_service.eliminar(storage_key)
        raise

    db.refresh(evidencia)
    return evidencia


@router.get("", response_model=Page[EvidenceRead])
def list_evidence(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="evidence:read")),
    search: str | None = Query(default=None, description="Busca en nombre, descripción y archivo"),
    classification: DataClassification | None = Query(default=None),
    status_: EvidenceStatus | None = Query(default=None, alias="status"),
    evidence_type: str | None = Query(default=None),
    expired: bool | None = Query(default=None, description="true=solo caducadas, false=solo vigentes"),
    expiring_within_days: int | None = Query(default=None, ge=1, le=3650),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[EvidenceRead]:
    consulta = db.query(Evidence).filter(Evidence.organization_id == actor.organization_id)

    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            or_(
                Evidence.name.ilike(patron),
                Evidence.description.ilike(patron),
                Evidence.original_filename.ilike(patron),
            )
        )
    if classification is not None:
        consulta = consulta.filter(Evidence.classification == classification)
    if status_ is not None:
        consulta = consulta.filter(Evidence.status == status_)
    if evidence_type:
        consulta = consulta.filter(Evidence.evidence_type.ilike(f"%{evidence_type}%"))

    hoy = date.today()
    if expired is True:
        consulta = consulta.filter(Evidence.expires_at.isnot(None), Evidence.expires_at < hoy)
    elif expired is False:
        consulta = consulta.filter(or_(Evidence.expires_at.is_(None), Evidence.expires_at >= hoy))
    if expiring_within_days is not None:
        limite = hoy + timedelta(days=expiring_within_days)
        consulta = consulta.filter(
            Evidence.expires_at.isnot(None), Evidence.expires_at >= hoy, Evidence.expires_at <= limite
        )

    total = consulta.count()
    evidencias = (
        consulta.order_by(Evidence.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Page(items=evidencias, total=total, page=page, page_size=page_size)


@router.get("/{evidence_id}", response_model=EvidenceDetailRead)
def get_evidence(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="evidence:read")),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, actor.organization_id)
    return _construir_detalle(evidencia)


@router.patch("/{evidence_id}", response_model=EvidenceRead)
def update_evidence(
    evidence_id: uuid.UUID,
    payload: EvidenceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Evidence:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)

    datos = payload.model_dump(exclude_unset=True)
    if "expires_at" in datos or "collected_at" in datos:
        nueva_recopilacion = datos.get("collected_at", evidencia.collected_at)
        nueva_expiracion = datos.get("expires_at", evidencia.expires_at)
        if nueva_expiracion is not None and nueva_recopilacion is not None and nueva_expiracion < nueva_recopilacion:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La fecha de expiración no puede ser anterior a la de recopilación.",
            )

    for campo, valor in datos.items():
        setattr(evidencia, campo, valor)

    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="update_evidence_metadata",
        entity_type="evidence",
        entity_id=evidencia.id,
        ip_address=_ip_del_cliente(request),
        details={"changed_fields": list(datos.keys())},
    )

    db.commit()
    db.refresh(evidencia)
    return evidencia


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ELIMINACION)),
) -> None:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    storage_key = evidencia.storage_key

    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="delete_evidence",
        entity_type="evidence",
        entity_id=evidencia.id,
        ip_address=_ip_del_cliente(request),
        details={"name": evidencia.name, "original_filename": evidencia.original_filename},
    )
    db.delete(evidencia)
    db.commit()

    storage_service.eliminar(storage_key)


def _content_disposition(nombre_archivo: str) -> str:
    """Genera un header Content-Disposition seguro, con soporte para nombres con acentos (RFC 6266)."""
    ascii_fallback = nombre_archivo.encode("ascii", "ignore").decode("ascii").replace('"', "'")
    if not ascii_fallback:
        ascii_fallback = "evidencia"
    codificado = quote(nombre_archivo)
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{codificado}'


@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> Response:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)

    try:
        contenido = storage_service.leer(evidencia.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El archivo de la evidencia no está disponible en el almacenamiento.",
        ) from None

    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="download_evidence",
        entity_type="evidence",
        entity_id=evidencia.id,
        ip_address=_ip_del_cliente(request),
        details={"original_filename": evidencia.original_filename},
    )
    db.commit()

    return Response(
        content=contenido,
        media_type=evidencia.mime_type,
        headers={
            "Content-Disposition": _content_disposition(evidencia.original_filename),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{evidence_id}/integrity", response_model=IntegrityCheckResult)
def check_integrity(
    evidence_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
) -> IntegrityCheckResult:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)

    try:
        contenido = storage_service.leer(evidencia.storage_key)
    except FileNotFoundError:
        registrar_evento(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="verify_integrity",
            entity_type="evidence",
            entity_id=evidencia.id,
            ip_address=_ip_del_cliente(request),
            details={"result": "not_found"},
        )
        db.commit()
        return IntegrityCheckResult(status="not_found", sha256_stored=evidencia.sha256, sha256_calculated=None)

    calculado = hashlib.sha256(contenido).hexdigest()
    resultado = "ok" if calculado == evidencia.sha256 else "mismatch"

    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="verify_integrity",
        entity_type="evidence",
        entity_id=evidencia.id,
        ip_address=_ip_del_cliente(request),
        details={"result": resultado},
    )
    db.commit()

    return IntegrityCheckResult(status=resultado, sha256_stored=evidencia.sha256, sha256_calculated=calculado)


# --- Relaciones GRC (sub-recursos) ---


@router.post(
    "/{evidence_id}/controls", response_model=EvidenceDetailRead, status_code=status.HTTP_201_CREATED
)
def link_control(
    evidence_id: uuid.UUID,
    control_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    control = (
        db.query(Control)
        .filter(Control.id == control_id, Control.organization_id == current_user.organization_id)
        .first()
    )
    if control is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control no encontrado.")
    if control not in evidencia.controls:
        evidencia.controls.append(control)
        db.commit()
        db.refresh(evidencia)
    return _construir_detalle(evidencia)


@router.delete("/{evidence_id}/controls/{control_id}", response_model=EvidenceDetailRead)
def unlink_control(
    evidence_id: uuid.UUID,
    control_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    evidencia.controls = [c for c in evidencia.controls if c.id != control_id]
    db.commit()
    db.refresh(evidencia)
    return _construir_detalle(evidencia)


@router.post("/{evidence_id}/risks", response_model=EvidenceDetailRead, status_code=status.HTTP_201_CREATED)
def link_risk(
    evidence_id: uuid.UUID,
    risk_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    riesgo = (
        db.query(Risk)
        .filter(Risk.id == risk_id, Risk.organization_id == current_user.organization_id)
        .first()
    )
    if riesgo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Riesgo no encontrado.")
    if riesgo not in evidencia.risks:
        evidencia.risks.append(riesgo)
        db.commit()
        db.refresh(evidencia)
    return _construir_detalle(evidencia)


@router.delete("/{evidence_id}/risks/{risk_id}", response_model=EvidenceDetailRead)
def unlink_risk(
    evidence_id: uuid.UUID,
    risk_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    evidencia.risks = [r for r in evidencia.risks if r.id != risk_id]
    db.commit()
    db.refresh(evidencia)
    return _construir_detalle(evidencia)


@router.post(
    "/{evidence_id}/assets", response_model=EvidenceDetailRead, status_code=status.HTTP_201_CREATED
)
def link_asset(
    evidence_id: uuid.UUID,
    asset_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    activo = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.organization_id == current_user.organization_id)
        .first()
    )
    if activo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado.")
    if activo not in evidencia.assets:
        evidencia.assets.append(activo)
        db.commit()
        db.refresh(evidencia)
    return _construir_detalle(evidencia)


@router.delete("/{evidence_id}/assets/{asset_id}", response_model=EvidenceDetailRead)
def unlink_asset(
    evidence_id: uuid.UUID,
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    evidencia.assets = [a for a in evidencia.assets if a.id != asset_id]
    db.commit()
    db.refresh(evidencia)
    return _construir_detalle(evidencia)


@router.post(
    "/{evidence_id}/requirements",
    response_model=EvidenceDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def link_requirement(
    evidence_id: uuid.UUID,
    requirement_id: uuid.UUID = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
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
    if requisito not in evidencia.requirements:
        evidencia.requirements.append(requisito)
        db.commit()
        db.refresh(evidencia)
    return _construir_detalle(evidencia)


@router.delete("/{evidence_id}/requirements/{requirement_id}", response_model=EvidenceDetailRead)
def unlink_requirement(
    evidence_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> EvidenceDetailRead:
    evidencia = _obtener_evidencia_o_404(db, evidence_id, current_user.organization_id)
    evidencia.requirements = [r for r in evidencia.requirements if r.id != requirement_id]
    db.commit()
    db.refresh(evidencia)
    return _construir_detalle(evidencia)
