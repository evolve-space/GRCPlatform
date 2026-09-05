import math
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.asset import AssetCriticality, DataClassification
from app.models.control import Control, ControlFrequency, ControlStatus
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingSource, FindingStatus, FindingType
from app.models.framework import Framework, FrameworkStatus, Requirement
from app.models.organization import Organization
from app.models.remediation_action import ActionStatus, RemediationAction
from app.models.risk import Risk, RiskStatus, RiskTreatment
from app.models.user import User
from app.models.vendor import Vendor, VendorDueDiligenceStatus, VendorStatus

from .conftest import auth_headers

HOY = date.today()


# --- Helpers de creación de datos controlados ---


def _riesgo(db: Session, org: Organization, likelihood: int, impact: int, **overrides) -> Risk:
    datos = {
        "organization_id": org.id,
        "title": f"Riesgo L{likelihood}I{impact}-{overrides.get('title_suffix', id(overrides))}",
        "category": "Ciberseguridad",
        "threat": "t",
        "vulnerability": "v",
        "likelihood": likelihood,
        "impact": impact,
        "inherent_score": likelihood * impact,
        "treatment": overrides.get("treatment", RiskTreatment.MITIGATE),
        "owner": "owner",
        "review_date": overrides.get("review_date", HOY + timedelta(days=30)),
        "status": overrides.get("status", RiskStatus.IDENTIFIED),
    }
    riesgo = Risk(**datos)
    db.add(riesgo)
    db.commit()
    db.refresh(riesgo)
    return riesgo


def _control(db: Session, org: Organization, status_: ControlStatus, control_id: str, category: str = "cat") -> Control:
    control = Control(
        organization_id=org.id,
        control_id=control_id,
        name=f"Control {control_id}",
        category=category,
        owner="owner",
        status=status_,
        frequency=ControlFrequency.ANNUAL,
    )
    db.add(control)
    db.commit()
    db.refresh(control)
    return control


def _evidencia(db: Session, org: Organization, name: str, expires_at: date | None = None, status_=None) -> Evidence:
    from app.core.storage import storage_service
    import hashlib

    contenido = f"contenido {name}".encode()
    storage_key = storage_service.generar_storage_key(org.id, ".txt")
    storage_service.guardar(storage_key, contenido)
    evidencia = Evidence(
        organization_id=org.id,
        name=name,
        original_filename="f.txt",
        storage_key=storage_key,
        mime_type="text/plain",
        file_size=len(contenido),
        sha256=hashlib.sha256(contenido).hexdigest(),
        classification=DataClassification.INTERNAL,
        evidence_type="Prueba",
        collected_at=HOY - timedelta(days=10),
        expires_at=expires_at,
    )
    if status_ is not None:
        evidencia.status = status_
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    return evidencia


def _hallazgo(db: Session, org: Organization, severity: AssetCriticality, status_: FindingStatus, finding_id: str, due_date: date | None = None) -> Finding:
    hallazgo = Finding(
        organization_id=org.id,
        finding_id=finding_id,
        title=f"Hallazgo {finding_id}",
        finding_type=FindingType.OTHER,
        severity=severity,
        status=status_,
        source=FindingSource.MANUAL,
        owner="owner",
        discovered_at=HOY - timedelta(days=10),
        due_date=due_date or HOY + timedelta(days=10),
    )
    db.add(hallazgo)
    db.commit()
    db.refresh(hallazgo)
    return hallazgo


def _accion(db: Session, org: Organization, hallazgo: Finding, status_: ActionStatus, action_id: str, priority=AssetCriticality.MEDIUM, due_date: date | None = None) -> RemediationAction:
    accion = RemediationAction(
        organization_id=org.id,
        finding_id=hallazgo.id,
        action_id=action_id,
        title=f"Accion {action_id}",
        owner="owner",
        status=status_,
        priority=priority,
        due_date=due_date or HOY + timedelta(days=10),
        completed_at=HOY if status_ == ActionStatus.COMPLETED else None,
    )
    db.add(accion)
    db.commit()
    db.refresh(accion)
    return accion


def _proveedor(db: Session, org: Organization, vendor_id: str, criticality=AssetCriticality.MEDIUM, status_=VendorStatus.ACTIVE, due_diligence=VendorDueDiligenceStatus.PENDING, next_review: date | None = None) -> Vendor:
    proveedor = Vendor(
        organization_id=org.id,
        vendor_id=vendor_id,
        name=f"Proveedor {vendor_id}",
        category="cat",
        owner="owner",
        criticality=criticality,
        data_classification=DataClassification.INTERNAL,
        status=status_,
        due_diligence_status=due_diligence,
        relationship_start_date=HOY - timedelta(days=100),
        next_security_review_date=next_review,
    )
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


def _aprox(a, b, tol=0.1):
    return a is not None and b is not None and math.isclose(a, b, abs_tol=tol)


# --- /dashboard/summary ---


def test_summary_estructura_basica_sin_datos(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["risks_critical"] == 0
    assert body["compliance_score"]["score"] is None  # sin controles todavía
    assert body["attention"] == []
    assert "generated_at" in body


def test_summary_kpis_reales(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _riesgo(db_session, organizacion_a, 5, 5)  # score 25 -> critico
    _riesgo(db_session, organizacion_a, 4, 3)  # score 12 -> alto
    hallazgo = _hallazgo(db_session, organizacion_a, AssetCriticality.CRITICAL, FindingStatus.OPEN, "FND-S1")
    _accion(db_session, organizacion_a, hallazgo, ActionStatus.PENDING, "ACT-S1", due_date=HOY - timedelta(days=1))
    _evidencia(db_session, organizacion_a, "Ev vencida pronto", expires_at=HOY + timedelta(days=5))
    _proveedor(db_session, organizacion_a, "VEN-S1", criticality=AssetCriticality.CRITICAL)

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["kpis"]["risks_critical"] == 1
    assert body["kpis"]["risks_high"] == 1
    assert body["kpis"]["findings_critical_open"] == 1
    assert body["kpis"]["actions_overdue"] == 1
    assert body["kpis"]["evidence_expiring_soon"] == 1
    assert body["kpis"]["vendors_critical"] == 1
    assert len(body["attention"]) > 0


# --- /dashboard/risks ---


def test_riesgos_por_nivel(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _riesgo(db_session, organizacion_a, 1, 2)  # score 2 -> bajo
    _riesgo(db_session, organizacion_a, 2, 3)  # score 6 -> medio
    _riesgo(db_session, organizacion_a, 4, 3)  # score 12 -> alto
    _riesgo(db_session, organizacion_a, 5, 5)  # score 25 -> critico

    response = client.get("/api/v1/dashboard/risks", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total"] == 4
    assert body["by_level"] == {"bajo": 1, "medio": 1, "alto": 1, "critico": 1}


def test_riesgos_vencidos_y_proximos(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _riesgo(db_session, organizacion_a, 1, 1, review_date=HOY - timedelta(days=5))
    _riesgo(db_session, organizacion_a, 1, 1, review_date=HOY + timedelta(days=10))
    _riesgo(db_session, organizacion_a, 1, 1, review_date=HOY + timedelta(days=200))

    response = client.get("/api/v1/dashboard/risks", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["review_overdue"] == 1
    assert body["review_due_soon"] == 1


def test_riesgos_filtro_por_tratamiento(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _riesgo(db_session, organizacion_a, 1, 1, treatment=RiskTreatment.ACCEPT)
    _riesgo(db_session, organizacion_a, 1, 1, treatment=RiskTreatment.MITIGATE)

    response = client.get("/api/v1/dashboard/risks?treatment=accept", headers=auth_headers(admin_org_a))
    assert response.json()["total"] == 1


# --- /dashboard/compliance ---


def test_compliance_controles_mixtos(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    # 10 controles: 6 implementados, 2 parciales, 1 no implementado, 1 no aplicable
    for i in range(6):
        _control(db_session, organizacion_a, ControlStatus.IMPLEMENTED, f"IMP-{i}")
    for i in range(2):
        _control(db_session, organizacion_a, ControlStatus.PARTIALLY_IMPLEMENTED, f"PAR-{i}")
    _control(db_session, organizacion_a, ControlStatus.NOT_IMPLEMENTED, "NOI-0")
    _control(db_session, organizacion_a, ControlStatus.NOT_APPLICABLE, "NA-0")

    response = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total_controls"] == 10
    assert body["by_status"]["implemented"] == 6
    assert body["by_status"]["not_applicable"] == 1
    esperado = (6 * 1.0 + 2 * 0.5 + 1 * 0.0) / 9 * 100
    assert _aprox(body["compliance_score"]["controls_pct"], esperado)


def test_compliance_implementado_sin_evidencia(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    con_evidencia = _control(db_session, organizacion_a, ControlStatus.IMPLEMENTED, "CON-EV")
    sin_evidencia = _control(db_session, organizacion_a, ControlStatus.IMPLEMENTED, "SIN-EV")
    evidencia = _evidencia(db_session, organizacion_a, "Ev vigente")
    evidencia.controls.append(con_evidencia)
    db_session.commit()

    response = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["implemented_without_evidence"] == 1
    assert _aprox(body["compliance_score"]["evidence_pct"], 50.0)  # 1 de 2 aplicables tiene evidencia
    assert sin_evidencia.control_id == "SIN-EV"


def test_compliance_evidencia_caducada_no_cuenta(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    control = _control(db_session, organizacion_a, ControlStatus.IMPLEMENTED, "CAD-1")
    evidencia_caducada = _evidencia(db_session, organizacion_a, "Ev caducada", expires_at=HOY - timedelta(days=1))
    evidencia_caducada.controls.append(control)
    db_session.commit()

    response = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["implemented_without_evidence"] == 1


def test_compliance_sin_controles_es_sin_datos(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total_controls"] == 0
    assert body["compliance_score"]["score"] is None
    assert body["compliance_score"]["level"] is None


def test_compliance_score_por_framework(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    framework = Framework(
        organization_id=organizacion_a.id, name="Marco X", short_name="MX", version="1.0", status=FrameworkStatus.ACTIVE
    )
    db_session.add(framework)
    db_session.commit()
    db_session.refresh(framework)

    requisito = Requirement(
        organization_id=organizacion_a.id, framework_id=framework.id, code="R1", name="Requisito 1", category="cat"
    )
    db_session.add(requisito)
    db_session.commit()
    db_session.refresh(requisito)

    control = _control(db_session, organizacion_a, ControlStatus.IMPLEMENTED, "FW-1")
    control.requirements.append(requisito)
    db_session.commit()

    response = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_a))
    body = response.json()
    marco = next(f for f in body["frameworks"] if f["short_name"] == "MX")
    assert marco["controls_pct"] == 100.0
    assert marco["score"] is not None


def test_compliance_framework_sin_requisitos_es_sin_datos(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    framework = Framework(
        organization_id=organizacion_a.id, name="Marco vacío", short_name="MV", version="1.0", status=FrameworkStatus.ACTIVE
    )
    db_session.add(framework)
    db_session.commit()

    response = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_a))
    body = response.json()
    marco = next(f for f in body["frameworks"] if f["short_name"] == "MV")
    assert marco["score"] is None


def test_compliance_filtro_por_framework_id(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    framework = Framework(
        organization_id=organizacion_a.id, name="Marco Y", short_name="MY", version="1.0", status=FrameworkStatus.ACTIVE
    )
    db_session.add(framework)
    db_session.commit()
    db_session.refresh(framework)
    requisito = Requirement(
        organization_id=organizacion_a.id, framework_id=framework.id, code="R1", name="R1", category="cat"
    )
    db_session.add(requisito)
    db_session.commit()
    db_session.refresh(requisito)

    control_del_marco = _control(db_session, organizacion_a, ControlStatus.IMPLEMENTED, "DEL-MARCO")
    control_del_marco.requirements.append(requisito)
    _control(db_session, organizacion_a, ControlStatus.NOT_IMPLEMENTED, "FUERA-MARCO")
    db_session.commit()

    response = client.get(f"/api/v1/dashboard/compliance?framework_id={framework.id}", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total_controls"] == 1


def test_compliance_framework_id_inexistente_devuelve_404(client: TestClient, admin_org_a: User):
    response = client.get(
        "/api/v1/dashboard/compliance?framework_id=00000000-0000-0000-0000-000000000000",
        headers=auth_headers(admin_org_a),
    )
    assert response.status_code == 404


# --- /dashboard/evidence ---


def test_evidencias_distribucion(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _evidencia(db_session, organizacion_a, "activa sin caducidad")
    _evidencia(db_session, organizacion_a, "proxima a caducar", expires_at=HOY + timedelta(days=10))
    _evidencia(db_session, organizacion_a, "caducada", expires_at=HOY - timedelta(days=10))

    response = client.get("/api/v1/dashboard/evidence", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total"] == 3
    assert body["expiring_soon"] == 1
    assert body["expired"] == 1
    assert len(body["needs_attention"]) == 2


def test_evidencias_sin_datos(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/dashboard/evidence", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total"] == 0
    assert body["needs_attention"] == []


# --- /dashboard/remediation ---


def test_remediacion_tasa_calculada(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    hallazgo = _hallazgo(db_session, organizacion_a, AssetCriticality.HIGH, FindingStatus.OPEN, "FND-R1")
    _accion(db_session, organizacion_a, hallazgo, ActionStatus.COMPLETED, "ACT-R1")
    _accion(db_session, organizacion_a, hallazgo, ActionStatus.COMPLETED, "ACT-R2")
    _accion(db_session, organizacion_a, hallazgo, ActionStatus.PENDING, "ACT-R3")
    _accion(db_session, organizacion_a, hallazgo, ActionStatus.PENDING, "ACT-R4")

    response = client.get("/api/v1/dashboard/remediation", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["actions_total"] == 4
    assert body["remediation_rate_pct"] == 50.0


def test_remediacion_sin_acciones_es_sin_datos(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _hallazgo(db_session, organizacion_a, AssetCriticality.LOW, FindingStatus.OPEN, "FND-R2")
    response = client.get("/api/v1/dashboard/remediation", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["actions_total"] == 0
    assert body["remediation_rate_pct"] is None


def test_remediacion_hallazgos_vencidos_y_criticos(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _hallazgo(db_session, organizacion_a, AssetCriticality.CRITICAL, FindingStatus.OPEN, "FND-R3", due_date=HOY - timedelta(days=1))
    _hallazgo(db_session, organizacion_a, AssetCriticality.CRITICAL, FindingStatus.CLOSED, "FND-R4", due_date=HOY - timedelta(days=1))

    response = client.get("/api/v1/dashboard/remediation", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["findings_overdue"] == 1  # el cerrado no cuenta como vencido
    assert body["findings_critical_open"] == 1


# --- /dashboard/vendors ---


def test_proveedores_distribucion(db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization):
    _proveedor(db_session, organizacion_a, "VEN-D1", criticality=AssetCriticality.CRITICAL, status_=VendorStatus.ACTIVE)
    _proveedor(db_session, organizacion_a, "VEN-D2", status_=VendorStatus.SUSPENDED)
    _proveedor(db_session, organizacion_a, "VEN-D3", due_diligence=VendorDueDiligenceStatus.PENDING)
    _proveedor(db_session, organizacion_a, "VEN-D4", next_review=HOY - timedelta(days=5))
    _proveedor(db_session, organizacion_a, "VEN-D5", next_review=HOY + timedelta(days=10))

    response = client.get("/api/v1/dashboard/vendors", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total"] == 5
    assert body["critical"] == 1
    assert body["suspended"] == 1
    assert body["review_overdue"] == 1
    assert body["review_due_soon"] == 1


def test_proveedores_sin_datos(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/dashboard/vendors", headers=auth_headers(admin_org_a))
    body = response.json()
    assert body["total"] == 0
    assert body["by_criticality"] == {}


# --- Multi-tenancy ---


def test_multitenancy_summary_no_mezcla_datos(
    db_session: Session, client: TestClient, admin_org_a: User, admin_org_b: User, organizacion_a: Organization, organizacion_b: Organization
):
    _riesgo(db_session, organizacion_a, 5, 5)
    _riesgo(db_session, organizacion_b, 5, 5)
    _riesgo(db_session, organizacion_b, 5, 5)

    resp_a = client.get("/api/v1/dashboard/summary", headers=auth_headers(admin_org_a)).json()
    resp_b = client.get("/api/v1/dashboard/summary", headers=auth_headers(admin_org_b)).json()
    assert resp_a["kpis"]["risks_critical"] == 1
    assert resp_b["kpis"]["risks_critical"] == 2


def test_multitenancy_compliance_score_independiente(
    db_session: Session, client: TestClient, admin_org_a: User, admin_org_b: User, organizacion_a: Organization, organizacion_b: Organization
):
    _control(db_session, organizacion_a, ControlStatus.IMPLEMENTED, "A-1")
    _control(db_session, organizacion_b, ControlStatus.NOT_IMPLEMENTED, "B-1")

    resp_a = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_a)).json()
    resp_b = client.get("/api/v1/dashboard/compliance", headers=auth_headers(admin_org_b)).json()
    assert resp_a["compliance_score"]["controls_pct"] == 100.0
    assert resp_b["compliance_score"]["controls_pct"] == 0.0


def test_multitenancy_vendor_filter_de_otra_org_devuelve_404(client: TestClient, admin_org_a: User, vendor_org_b: Vendor):
    response = client.get(f"/api/v1/dashboard/risks?vendor_id={vendor_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


# --- RBAC ---


def test_rbac_todos_los_roles_pueden_leer(
    client: TestClient, admin_org_a: User, grc_manager_org_a: User, analyst_org_a: User, viewer_org_a: User
):
    for endpoint in [
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/risks",
        "/api/v1/dashboard/compliance",
        "/api/v1/dashboard/evidence",
        "/api/v1/dashboard/remediation",
        "/api/v1/dashboard/vendors",
    ]:
        for usuario in [admin_org_a, grc_manager_org_a, analyst_org_a, viewer_org_a]:
            response = client.get(endpoint, headers=auth_headers(usuario))
            assert response.status_code == 200, f"{endpoint} falló para rol {usuario.role}"


def test_no_autenticado_es_rechazado(client: TestClient):
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


def test_uuid_invalido_devuelve_422(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/dashboard/risks?vendor_id=no-es-un-uuid", headers=auth_headers(admin_org_a))
    assert response.status_code == 422


def test_enum_invalido_devuelve_422(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/dashboard/vendors?status=no_valido", headers=auth_headers(admin_org_a))
    assert response.status_code == 422


def test_nunca_devuelve_nan_ni_error_500_con_organizacion_vacia(client: TestClient, admin_org_a: User):
    for endpoint in [
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/risks",
        "/api/v1/dashboard/compliance",
        "/api/v1/dashboard/evidence",
        "/api/v1/dashboard/remediation",
        "/api/v1/dashboard/vendors",
    ]:
        response = client.get(endpoint, headers=auth_headers(admin_org_a))
        assert response.status_code == 200
        texto = response.text
        assert "NaN" not in texto
        assert "Infinity" not in texto
