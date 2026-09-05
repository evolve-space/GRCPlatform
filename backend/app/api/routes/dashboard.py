"""Endpoints de Dashboard/Analytics.

Principio de rendimiento: cada endpoint hace un número FIJO y pequeño de
consultas SQL (una por tabla relevante, más alguna consulta de unión puntual
para evidencia-por-control), nunca una consulta por fila de resultado. Las
agregaciones por nivel/estado/categoría se calculan en Python sobre listas ya
cargadas en memoria (el volumen de datos de una organización GRC — decenas o
cientos de filas por tabla — hace esto más simple y mantenible que replicar
en SQL la lógica de clasificación ya centralizada en `risk_scoring.py` /
`compliance_score.py`, sin introducir un problema N+1: el número de consultas
no crece con el número de filas).
"""

import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import false, or_
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_access, require_roles
from app.core.compliance_score import (
    calcular_compliance_score,
    calcular_pct_controles,
    calcular_pct_evidencias,
    calcular_pct_hallazgos,
    calcular_pct_remediacion,
)
from app.core.database import get_db
from app.core.risk_scoring import clasificar_nivel
from app.models.associations import control_requirements, evidence_controls
from app.models.control import Control, ControlStatus
from app.models.evidence import Evidence, EvidenceStatus
from app.models.finding import FINDING_STATUSES_NO_VENCIBLES, Finding, FindingStatus
from app.models.framework import Framework
from app.models.remediation_action import ACTION_STATUSES_NO_VENCIBLES, ActionStatus, RemediationAction
from app.models.risk import Risk, RiskStatus, RiskTreatment
from app.models.user import User, UserRole
from app.models.vendor import VENDOR_UPCOMING_WINDOW_DAYS, Vendor, VendorDueDiligenceStatus, VendorStatus
from app.schemas.dashboard import (
    AttentionItem,
    ComplianceDashboard,
    ComplianceScoreBreakdown,
    ControlsByStatus,
    DashboardSummary,
    EvidenceAttentionItem,
    EvidenceDashboard,
    FrameworkScore,
    KpiCounts,
    RemediationDashboard,
    RiskDashboard,
    RiskLevelCounts,
    VendorDashboard,
)

router = APIRouter()

_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER, UserRole.ANALYST, UserRole.VIEWER)

# Número máximo de elementos por categoría en la lista "Requiere atención".
_ATENCION_POR_CATEGORIA = 3
_ATENCION_MAXIMO = 10

_ORDEN_SEVERIDAD = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _obtener_vendor_o_404(db: Session, vendor_id: uuid.UUID, organization_id: uuid.UUID) -> Vendor:
    proveedor = (
        db.query(Vendor)
        .filter(Vendor.id == vendor_id, Vendor.organization_id == organization_id)
        .first()
    )
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")
    return proveedor


def _obtener_framework_o_404(db: Session, framework_id: uuid.UUID, organization_id: uuid.UUID) -> Framework:
    framework = (
        db.query(Framework)
        .filter(Framework.id == framework_id, Framework.organization_id == organization_id)
        .first()
    )
    if framework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Marco de cumplimiento no encontrado."
        )
    return framework


# --- Controles ↔ Evidencia vigente (bloque reutilizado por /compliance y /summary) ---


def _controles_con_evidencia_vigente(db: Session, organization_id: uuid.UUID, control_ids: list[uuid.UUID]) -> set:
    """IDs de control con al menos una Evidence ACTIVE y no caducada vinculada.

    "Vigente" = `status == active` y (`expires_at` es nulo o no ha pasado);
    misma lógica que `EvidenceRead.effective_status` en `schemas/evidence.py`,
    replicada aquí como filtro SQL para no traer evidencias a Python.
    """
    if not control_ids:
        return set()
    hoy = date.today()
    filas = (
        db.query(evidence_controls.c.control_id)
        .join(Evidence, Evidence.id == evidence_controls.c.evidence_id)
        .filter(
            evidence_controls.c.control_id.in_(control_ids),
            Evidence.organization_id == organization_id,
            Evidence.status == EvidenceStatus.ACTIVE,
            or_(Evidence.expires_at.is_(None), Evidence.expires_at >= hoy),
        )
        .distinct()
        .all()
    )
    return {fila[0] for fila in filas}


def _pct_controles_y_evidencia(controles: list[Control], con_evidencia_vigente: set) -> tuple[float | None, float | None]:
    conteo_estado = Counter(c.status for c in controles)
    controles_pct = calcular_pct_controles(dict(conteo_estado))
    aplicables_evidencia = [
        c for c in controles if c.status in (ControlStatus.IMPLEMENTED, ControlStatus.PARTIALLY_IMPLEMENTED)
    ]
    con_evidencia_aplicables = sum(1 for c in aplicables_evidencia if c.id in con_evidencia_vigente)
    evidencias_pct = calcular_pct_evidencias(len(aplicables_evidencia), con_evidencia_aplicables)
    return controles_pct, evidencias_pct


def _compliance_score_global(db: Session, organization_id: uuid.UUID) -> ComplianceScoreBreakdown:
    controles = db.query(Control).filter(Control.organization_id == organization_id).all()
    con_evidencia_vigente = _controles_con_evidencia_vigente(db, organization_id, [c.id for c in controles])
    controles_pct, evidencias_pct = _pct_controles_y_evidencia(controles, con_evidencia_vigente)

    hallazgos = db.query(Finding).filter(Finding.organization_id == organization_id).all()
    abiertos = [f for f in hallazgos if f.status not in FINDING_STATUSES_NO_VENCIBLES]
    hallazgos_pct = calcular_pct_hallazgos(Counter(f.severity.value for f in abiertos))

    acciones = (
        db.query(RemediationAction).filter(RemediationAction.organization_id == organization_id).all()
    )
    completadas = sum(1 for a in acciones if a.status == ActionStatus.COMPLETED)
    remediacion_pct = calcular_pct_remediacion(completadas, len(acciones))

    score, nivel = calcular_compliance_score(
        controles_pct=controles_pct,
        evidencias_pct=evidencias_pct,
        hallazgos_pct=hallazgos_pct,
        remediacion_pct=remediacion_pct,
    )
    return ComplianceScoreBreakdown(
        controls_pct=controles_pct,
        evidence_pct=evidencias_pct,
        findings_pct=hallazgos_pct,
        remediation_pct=remediacion_pct,
        score=score,
        level=nivel,
    )


def _score_por_framework(db: Session, organization_id: uuid.UUID, framework: Framework) -> FrameworkScore:
    """Score de un framework concreto, usando solo Controles(40%) y
    Evidencias(20%) — normalizados 2:1 — a través de la cadena real
    Framework → Requirement → Control → Evidence. Hallazgos/Remediación se
    excluyen deliberadamente de este score: el etiquetado Finding↔Requirement
    es opcional y disperso en los datos actuales, y usarlo produciría un
    score por framework potencialmente engañoso (ver docs/SECURITY.md)."""
    requirement_ids = [r.id for r in framework.requirements]
    if not requirement_ids:
        return FrameworkScore(
            id=framework.id,
            short_name=framework.short_name,
            name=framework.name,
            controls_pct=None,
            evidence_pct=None,
            score=None,
            level=None,
        )
    controles = (
        db.query(Control)
        .join(control_requirements, Control.id == control_requirements.c.control_id)
        .filter(
            Control.organization_id == organization_id,
            control_requirements.c.requirement_id.in_(requirement_ids),
        )
        .distinct()
        .all()
    )
    con_evidencia_vigente = _controles_con_evidencia_vigente(db, organization_id, [c.id for c in controles])
    controles_pct, evidencias_pct = _pct_controles_y_evidencia(controles, con_evidencia_vigente)
    score, nivel = calcular_compliance_score(
        controles_pct=controles_pct, evidencias_pct=evidencias_pct, hallazgos_pct=None, remediacion_pct=None
    )
    return FrameworkScore(
        id=framework.id,
        short_name=framework.short_name,
        name=framework.name,
        controls_pct=controles_pct,
        evidence_pct=evidencias_pct,
        score=score,
        level=nivel,
    )


# --- Endpoints ---


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="dashboard:read")),
) -> DashboardSummary:
    hoy = date.today()

    riesgos = db.query(Risk).filter(Risk.organization_id == actor.organization_id).all()
    riesgos_criticos = [r for r in riesgos if clasificar_nivel(r.inherent_score) == "critico"]
    riesgos_altos = [r for r in riesgos if clasificar_nivel(r.inherent_score) == "alto"]

    hallazgos = db.query(Finding).filter(Finding.organization_id == actor.organization_id).all()
    hallazgos_abiertos = [f for f in hallazgos if f.status not in FINDING_STATUSES_NO_VENCIBLES]
    hallazgos_criticos_abiertos = [f for f in hallazgos_abiertos if f.severity.value == "critical"]

    acciones = (
        db.query(RemediationAction).filter(RemediationAction.organization_id == actor.organization_id).all()
    )
    acciones_vencidas = [
        a for a in acciones if a.status not in ACTION_STATUSES_NO_VENCIBLES and a.due_date < hoy
    ]

    evidencias = db.query(Evidence).filter(Evidence.organization_id == actor.organization_id).all()
    limite_evidencia = hoy + timedelta(days=30)
    evidencias_proximas = [
        e
        for e in evidencias
        if e.status == EvidenceStatus.ACTIVE and e.expires_at is not None and hoy <= e.expires_at <= limite_evidencia
    ]
    evidencias_caducadas = [
        e for e in evidencias if e.status == EvidenceStatus.ACTIVE and e.expires_at is not None and e.expires_at < hoy
    ]

    proveedores = db.query(Vendor).filter(Vendor.organization_id == actor.organization_id).all()
    proveedores_criticos = [v for v in proveedores if v.criticality.value == "critical"]
    proveedores_revision_vencida = [
        v for v in proveedores if v.next_security_review_date is not None and v.next_security_review_date < hoy
    ]

    kpis = KpiCounts(
        risks_critical=len(riesgos_criticos),
        risks_high=len(riesgos_altos),
        findings_open=len(hallazgos_abiertos),
        findings_critical_open=len(hallazgos_criticos_abiertos),
        actions_overdue=len(acciones_vencidas),
        evidence_expiring_soon=len(evidencias_proximas),
        vendors_critical=len(proveedores_criticos),
    )

    controles_todos = db.query(Control).filter(Control.organization_id == actor.organization_id).all()
    control_evidencia = _controles_con_evidencia_vigente(db, actor.organization_id, [c.id for c in controles_todos])
    controles_pct, evidencias_pct = _pct_controles_y_evidencia(controles_todos, control_evidencia)
    hallazgos_pct = calcular_pct_hallazgos(Counter(f.severity.value for f in hallazgos_abiertos))
    completadas = sum(1 for a in acciones if a.status == ActionStatus.COMPLETED)
    remediacion_pct = calcular_pct_remediacion(completadas, len(acciones))
    score, nivel = calcular_compliance_score(
        controles_pct=controles_pct, evidencias_pct=evidencias_pct, hallazgos_pct=hallazgos_pct, remediacion_pct=remediacion_pct
    )
    compliance_score = ComplianceScoreBreakdown(
        controls_pct=controles_pct,
        evidence_pct=evidencias_pct,
        findings_pct=hallazgos_pct,
        remediation_pct=remediacion_pct,
        score=score,
        level=nivel,
    )

    atencion: list[AttentionItem] = []
    for r in sorted(riesgos_criticos, key=lambda x: -x.inherent_score)[:_ATENCION_POR_CATEGORIA]:
        atencion.append(
            AttentionItem(
                kind="risk", id=r.id, label=r.title, detail="Riesgo crítico", severity="critical",
                link="/riesgos?level=critico",
            )
        )
    for f in sorted(hallazgos_criticos_abiertos, key=lambda x: x.due_date)[:_ATENCION_POR_CATEGORIA]:
        atencion.append(
            AttentionItem(
                kind="finding", id=f.id, label=f"{f.finding_id} — {f.title}", detail="Hallazgo crítico abierto",
                severity="critical", link="/hallazgos?severity=critical",
            )
        )
    for a in sorted(acciones_vencidas, key=lambda x: x.due_date)[:_ATENCION_POR_CATEGORIA]:
        atencion.append(
            AttentionItem(
                kind="action", id=a.id, label=f"{a.action_id} — {a.title}",
                detail=f"Vencida desde {a.due_date.isoformat()}", severity="high", link="/acciones?overdue=true",
            )
        )
    for e in sorted(evidencias_caducadas, key=lambda x: x.expires_at or date.max)[:_ATENCION_POR_CATEGORIA]:
        atencion.append(
            AttentionItem(
                kind="evidence", id=e.id, label=e.name, detail="Evidencia caducada", severity="medium",
                link="/evidencias?caducidad=caducadas",
            )
        )
    for v in sorted(proveedores_revision_vencida, key=lambda x: x.next_security_review_date or date.max)[:_ATENCION_POR_CATEGORIA]:
        atencion.append(
            AttentionItem(
                kind="vendor", id=v.id, label=f"{v.vendor_id} — {v.name}", detail="Revisión de seguridad vencida",
                severity="high", link="/proveedores?review_overdue=true",
            )
        )
    atencion.sort(key=lambda item: _ORDEN_SEVERIDAD.get(item.severity, 4))
    atencion = atencion[:_ATENCION_MAXIMO]

    return DashboardSummary(
        generated_at=datetime.now(timezone.utc), kpis=kpis, compliance_score=compliance_score, attention=atencion
    )


@router.get("/risks", response_model=RiskDashboard)
def get_risks_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    status_: RiskStatus | None = Query(default=None, alias="status"),
    treatment: RiskTreatment | None = Query(default=None),
    vendor_id: uuid.UUID | None = Query(default=None),
) -> RiskDashboard:
    consulta = db.query(Risk).filter(Risk.organization_id == current_user.organization_id)
    if status_ is not None:
        consulta = consulta.filter(Risk.status == status_)
    if treatment is not None:
        consulta = consulta.filter(Risk.treatment == treatment)
    if vendor_id is not None:
        proveedor = _obtener_vendor_o_404(db, vendor_id, current_user.organization_id)
        ids_vinculados = [r.id for r in proveedor.risks]
        consulta = consulta.filter(Risk.id.in_(ids_vinculados)) if ids_vinculados else consulta.filter(false())

    riesgos = consulta.all()
    niveles = Counter(clasificar_nivel(r.inherent_score) for r in riesgos)
    hoy = date.today()
    limite = hoy + timedelta(days=30)

    return RiskDashboard(
        total=len(riesgos),
        by_level=RiskLevelCounts(
            bajo=niveles.get("bajo", 0), medio=niveles.get("medio", 0),
            alto=niveles.get("alto", 0), critico=niveles.get("critico", 0),
        ),
        by_status=dict(Counter(r.status.value for r in riesgos)),
        by_treatment=dict(Counter(r.treatment.value for r in riesgos)),
        review_overdue=sum(1 for r in riesgos if r.review_date < hoy),
        review_due_soon=sum(1 for r in riesgos if hoy <= r.review_date <= limite),
    )


@router.get("/compliance", response_model=ComplianceDashboard)
def get_compliance_dashboard(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_access(roles=_ROLES_LECTURA, scope="compliance:read")),
    framework_id: uuid.UUID | None = Query(default=None, description="Filtra el desglose de controles a este framework"),
    category: str | None = Query(default=None),
) -> ComplianceDashboard:
    consulta = db.query(Control).filter(Control.organization_id == actor.organization_id)
    if category:
        consulta = consulta.filter(Control.category == category)
    if framework_id is not None:
        framework = _obtener_framework_o_404(db, framework_id, actor.organization_id)
        requirement_ids = [r.id for r in framework.requirements]
        if requirement_ids:
            control_ids = {
                fila[0]
                for fila in db.query(control_requirements.c.control_id)
                .filter(control_requirements.c.requirement_id.in_(requirement_ids))
                .distinct()
                .all()
            }
        else:
            control_ids = set()
        consulta = consulta.filter(Control.id.in_(control_ids)) if control_ids else consulta.filter(false())

    controles_filtrados = consulta.all()
    conteo_estado = Counter(c.status for c in controles_filtrados)
    con_evidencia_filtrados = _controles_con_evidencia_vigente(db, actor.organization_id, [c.id for c in controles_filtrados])
    sin_evidencia = sum(
        1 for c in controles_filtrados if c.status == ControlStatus.IMPLEMENTED and c.id not in con_evidencia_filtrados
    )

    frameworks = db.query(Framework).filter(Framework.organization_id == actor.organization_id).all()
    scores_framework = [_score_por_framework(db, actor.organization_id, fw) for fw in frameworks]

    return ComplianceDashboard(
        total_controls=len(controles_filtrados),
        by_status=ControlsByStatus(
            not_implemented=conteo_estado.get(ControlStatus.NOT_IMPLEMENTED, 0),
            partially_implemented=conteo_estado.get(ControlStatus.PARTIALLY_IMPLEMENTED, 0),
            implemented=conteo_estado.get(ControlStatus.IMPLEMENTED, 0),
            not_applicable=conteo_estado.get(ControlStatus.NOT_APPLICABLE, 0),
        ),
        by_category=dict(Counter(c.category for c in controles_filtrados)),
        implemented_without_evidence=sin_evidencia,
        compliance_score=_compliance_score_global(db, actor.organization_id),
        frameworks=scores_framework,
    )


@router.get("/evidence", response_model=EvidenceDashboard)
def get_evidence_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    classification: str | None = Query(default=None),
    evidence_type: str | None = Query(default=None),
    vendor_id: uuid.UUID | None = Query(default=None),
) -> EvidenceDashboard:
    consulta = db.query(Evidence).filter(Evidence.organization_id == current_user.organization_id)
    if classification:
        consulta = consulta.filter(Evidence.classification == classification)
    if evidence_type:
        consulta = consulta.filter(Evidence.evidence_type == evidence_type)
    if vendor_id is not None:
        proveedor = _obtener_vendor_o_404(db, vendor_id, current_user.organization_id)
        ids_vinculados = [e.id for e in proveedor.evidence]
        consulta = consulta.filter(Evidence.id.in_(ids_vinculados)) if ids_vinculados else consulta.filter(false())

    evidencias = consulta.all()
    hoy = date.today()
    limite = hoy + timedelta(days=30)

    activas = [e for e in evidencias if e.status == EvidenceStatus.ACTIVE]
    archivadas = [e for e in evidencias if e.status == EvidenceStatus.ARCHIVED]
    caducadas = [e for e in activas if e.expires_at is not None and e.expires_at < hoy]
    proximas = [e for e in activas if e.expires_at is not None and hoy <= e.expires_at <= limite]

    atencion = sorted(
        [e for e in caducadas + proximas],
        key=lambda e: e.expires_at or date.max,
    )[:_ATENCION_MAXIMO]

    return EvidenceDashboard(
        total=len(evidencias),
        active=len(activas),
        archived=len(archivadas),
        expiring_soon=len(proximas),
        expired=len(caducadas),
        by_classification=dict(Counter(e.classification.value for e in evidencias)),
        by_type=dict(Counter(e.evidence_type for e in evidencias)),
        needs_attention=[
            EvidenceAttentionItem(
                id=e.id,
                name=e.name,
                status="expired" if e in caducadas else "expiring_soon",
                classification=e.classification.value,
                expires_at=e.expires_at.isoformat() if e.expires_at else None,
            )
            for e in atencion
        ],
    )


@router.get("/remediation", response_model=RemediationDashboard)
def get_remediation_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    finding_severity: str | None = Query(default=None),
    finding_status: FindingStatus | None = Query(default=None),
    action_status: ActionStatus | None = Query(default=None),
    action_priority: str | None = Query(default=None),
    vendor_id: uuid.UUID | None = Query(default=None),
) -> RemediationDashboard:
    hoy = date.today()

    consulta_f = db.query(Finding).filter(Finding.organization_id == current_user.organization_id)
    consulta_a = db.query(RemediationAction).filter(RemediationAction.organization_id == current_user.organization_id)

    if vendor_id is not None:
        proveedor = _obtener_vendor_o_404(db, vendor_id, current_user.organization_id)
        finding_ids_vinculados = [f.id for f in proveedor.findings]
        consulta_f = consulta_f.filter(Finding.id.in_(finding_ids_vinculados)) if finding_ids_vinculados else consulta_f.filter(false())
        if finding_ids_vinculados:
            consulta_a = consulta_a.filter(RemediationAction.finding_id.in_(finding_ids_vinculados))
        else:
            consulta_a = consulta_a.filter(false())

    if finding_severity:
        consulta_f = consulta_f.filter(Finding.severity == finding_severity)
    if finding_status is not None:
        consulta_f = consulta_f.filter(Finding.status == finding_status)
    if action_status is not None:
        consulta_a = consulta_a.filter(RemediationAction.status == action_status)
    if action_priority:
        consulta_a = consulta_a.filter(RemediationAction.priority == action_priority)

    hallazgos = consulta_f.all()
    acciones = consulta_a.all()

    hallazgos_abiertos = [f for f in hallazgos if f.status not in FINDING_STATUSES_NO_VENCIBLES]
    hallazgos_vencidos = [f for f in hallazgos_abiertos if f.due_date < hoy]
    hallazgos_criticos_abiertos = [f for f in hallazgos_abiertos if f.severity.value == "critical"]

    acciones_vencidas = [a for a in acciones if a.status not in ACTION_STATUSES_NO_VENCIBLES and a.due_date < hoy]
    completadas = sum(1 for a in acciones if a.status == ActionStatus.COMPLETED)

    return RemediationDashboard(
        findings_total=len(hallazgos),
        findings_by_severity=dict(Counter(f.severity.value for f in hallazgos)),
        findings_by_status=dict(Counter(f.status.value for f in hallazgos)),
        findings_overdue=len(hallazgos_vencidos),
        findings_critical_open=len(hallazgos_criticos_abiertos),
        actions_total=len(acciones),
        actions_by_status=dict(Counter(a.status.value for a in acciones)),
        actions_by_priority=dict(Counter(a.priority.value for a in acciones)),
        actions_overdue=len(acciones_vencidas),
        remediation_rate_pct=calcular_pct_remediacion(completadas, len(acciones)),
    )


@router.get("/vendors", response_model=VendorDashboard)
def get_vendors_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    criticality: str | None = Query(default=None),
    status_: VendorStatus | None = Query(default=None, alias="status"),
    due_diligence_status: VendorDueDiligenceStatus | None = Query(default=None),
) -> VendorDashboard:
    consulta = db.query(Vendor).filter(Vendor.organization_id == current_user.organization_id)
    if criticality:
        consulta = consulta.filter(Vendor.criticality == criticality)
    if status_ is not None:
        consulta = consulta.filter(Vendor.status == status_)
    if due_diligence_status is not None:
        consulta = consulta.filter(Vendor.due_diligence_status == due_diligence_status)

    proveedores = consulta.all()
    hoy = date.today()
    limite = hoy + timedelta(days=VENDOR_UPCOMING_WINDOW_DAYS)

    return VendorDashboard(
        total=len(proveedores),
        active=sum(1 for v in proveedores if v.status == VendorStatus.ACTIVE),
        critical=sum(1 for v in proveedores if v.criticality.value == "critical"),
        suspended=sum(1 for v in proveedores if v.status == VendorStatus.SUSPENDED),
        due_diligence_pending=sum(
            1 for v in proveedores if v.due_diligence_status == VendorDueDiligenceStatus.PENDING
        ),
        review_overdue=sum(
            1 for v in proveedores if v.next_security_review_date is not None and v.next_security_review_date < hoy
        ),
        review_due_soon=sum(
            1
            for v in proveedores
            if v.next_security_review_date is not None and hoy <= v.next_security_review_date <= limite
        ),
        by_criticality=dict(Counter(v.criticality.value for v in proveedores)),
        by_due_diligence=dict(Counter(v.due_diligence_status.value for v in proveedores)),
    )
