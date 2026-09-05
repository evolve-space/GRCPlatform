from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.risk import Risk
from app.models.user import User
from app.models.vendor import Vendor

from .conftest import auth_headers


def _payload_proveedor(**overrides) -> dict:
    base = {
        "vendor_id": "VEN-100",
        "name": "Proveedor de prueba",
        "legal_name": "Proveedor de Prueba S.L.",
        "description": "Descripción del proveedor de prueba",
        "category": "Servicios cloud",
        "owner": "Responsable de pruebas",
        "criticality": "high",
        "data_classification": "confidential",
        "status": "active",
        "due_diligence_status": "approved",
        "relationship_start_date": "2027-01-01",
        "contract_end_date": "2028-01-01",
        "last_security_review_date": "2027-01-01",
        "next_security_review_date": "2028-01-01",
    }
    base.update(overrides)
    return base


# --- Creación y validación ---


def test_crear_proveedor_valido(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    assert response.status_code == 201
    body = response.json()
    assert body["vendor_id"] == "VEN-100"
    assert body["organization_id"] == str(organizacion_a.id)
    assert body["status"] == "active"


def test_no_se_puede_crear_proveedor_con_codigo_duplicado(client: TestClient, admin_org_a: User):
    client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    response = client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    assert response.status_code == 409


def test_criticidad_invalida_es_rechazada(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor(criticality="urgente")
    )
    assert response.status_code == 422


def test_estado_invalido_es_rechazado(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor(status="pausado")
    )
    assert response.status_code == 422


def test_clasificacion_datos_invalida_es_rechazada(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor(data_classification="secreta")
    )
    assert response.status_code == 422


def test_due_diligence_invalida_es_rechazada(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(due_diligence_status="no_valido"),
    )
    assert response.status_code == 422


def test_fin_contrato_anterior_a_inicio_es_rechazado(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(relationship_start_date="2027-06-01", contract_end_date="2027-01-01"),
    )
    assert response.status_code == 422


def test_proxima_revision_anterior_a_ultima_es_rechazada(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(last_security_review_date="2027-06-01", next_security_review_date="2027-01-01"),
    )
    assert response.status_code == 422


def test_organization_id_del_cliente_es_ignorado(
    client: TestClient, admin_org_a: User, organizacion_a: Organization, organizacion_b: Organization
):
    response = client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json={**_payload_proveedor(), "organization_id": str(organizacion_b.id)},
    )
    assert response.status_code == 201
    assert response.json()["organization_id"] == str(organizacion_a.id)


# --- CRUD ---


def test_listar_proveedores(client: TestClient, admin_org_a: User, vendor_org_a: Vendor):
    response = client.get("/api/v1/vendors", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    codigos = {item["vendor_id"] for item in response.json()["items"]}
    assert vendor_org_a.vendor_id in codigos


def test_obtener_detalle_con_relaciones_vacias(client: TestClient, admin_org_a: User, vendor_org_a: Vendor):
    response = client.get(f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["risks"] == []
    assert body["evidence"] == []
    assert body["findings"] == []
    assert body["actions"] == []


def test_editar_proveedor(client: TestClient, admin_org_a: User, vendor_org_a: Vendor):
    response = client.patch(
        f"/api/v1/vendors/{vendor_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"name": "Nombre actualizado", "status": "suspended"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Nombre actualizado"
    assert body["status"] == "suspended"


def test_editar_proveedor_inexistente_devuelve_404(client: TestClient, admin_org_a: User):
    response = client.patch(
        "/api/v1/vendors/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(admin_org_a),
        json={"name": "x"},
    )
    assert response.status_code == 404


def test_eliminar_proveedor(client: TestClient, admin_org_a: User, vendor_org_a: Vendor):
    response = client.delete(f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204
    assert client.get(f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(admin_org_a)).status_code == 404


# --- Filtros y paginación ---


def test_filtro_por_estado(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor(vendor_id="VEN-A", status="active")
    )
    client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(vendor_id="VEN-B", status="suspended"),
    )
    response = client.get("/api/v1/vendors?status=suspended", headers=auth_headers(admin_org_a))
    codigos = {item["vendor_id"] for item in response.json()["items"]}
    assert codigos == {"VEN-B"}


def test_filtro_por_criticidad(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(vendor_id="VEN-C", criticality="critical"),
    )
    response = client.get("/api/v1/vendors?criticality=critical", headers=auth_headers(admin_org_a))
    codigos = {item["vendor_id"] for item in response.json()["items"]}
    assert "VEN-C" in codigos


def test_filtro_revision_vencida(client: TestClient, admin_org_a: User):
    hoy = date.today()
    client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(
            vendor_id="VEN-VENCIDA",
            relationship_start_date=(hoy - timedelta(days=400)).isoformat(),
            last_security_review_date=(hoy - timedelta(days=400)).isoformat(),
            next_security_review_date=(hoy - timedelta(days=10)).isoformat(),
        ),
    )
    client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(
            vendor_id="VEN-VIGENTE",
            relationship_start_date=(hoy - timedelta(days=400)).isoformat(),
            last_security_review_date=(hoy - timedelta(days=400)).isoformat(),
            next_security_review_date=(hoy + timedelta(days=200)).isoformat(),
        ),
    )
    response = client.get("/api/v1/vendors?review_overdue=true", headers=auth_headers(admin_org_a))
    codigos = {item["vendor_id"] for item in response.json()["items"]}
    assert "VEN-VENCIDA" in codigos
    assert "VEN-VIGENTE" not in codigos

    detalle = client.get("/api/v1/vendors", headers=auth_headers(admin_org_a)).json()
    vencida = next(i for i in detalle["items"] if i["vendor_id"] == "VEN-VENCIDA")
    assert vencida["is_review_overdue"] is True
    vigente = next(i for i in detalle["items"] if i["vendor_id"] == "VEN-VIGENTE")
    assert vigente["is_review_overdue"] is False


def test_filtro_revision_proxima(client: TestClient, admin_org_a: User):
    hoy = date.today()
    client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(
            vendor_id="VEN-PROXIMA",
            relationship_start_date=(hoy - timedelta(days=400)).isoformat(),
            last_security_review_date=(hoy - timedelta(days=300)).isoformat(),
            next_security_review_date=(hoy + timedelta(days=10)).isoformat(),
        ),
    )
    response = client.get("/api/v1/vendors?review_due_soon=true", headers=auth_headers(admin_org_a))
    codigos = {item["vendor_id"] for item in response.json()["items"]}
    assert "VEN-PROXIMA" in codigos


def test_filtro_contrato_vencido(client: TestClient, admin_org_a: User):
    hoy = date.today()
    client.post(
        "/api/v1/vendors",
        headers=auth_headers(admin_org_a),
        json=_payload_proveedor(
            vendor_id="VEN-CONT-VENCIDO",
            relationship_start_date=(hoy - timedelta(days=400)).isoformat(),
            last_security_review_date=(hoy - timedelta(days=400)).isoformat(),
            next_security_review_date=(hoy - timedelta(days=5)).isoformat(),
            contract_end_date=(hoy - timedelta(days=5)).isoformat(),
        ),
    )
    response = client.get("/api/v1/vendors?contract_expired=true", headers=auth_headers(admin_org_a))
    codigos = {item["vendor_id"] for item in response.json()["items"]}
    assert "VEN-CONT-VENCIDO" in codigos


def test_paginacion(client: TestClient, admin_org_a: User):
    for i in range(3):
        client.post(
            "/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor(vendor_id=f"VEN-PAG-{i}")
        )
    response = client.get("/api/v1/vendors?page=1&page_size=2", headers=auth_headers(admin_org_a))
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] >= 3


# --- Relaciones ---


def test_vincular_y_desvincular_riesgo(client: TestClient, admin_org_a: User, vendor_org_a: Vendor, risk_org_a: Risk):
    response = client.post(
        f"/api/v1/vendors/{vendor_org_a.id}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_a.id)},
    )
    assert response.status_code == 201
    assert len(response.json()["risks"]) == 1

    response = client.delete(
        f"/api/v1/vendors/{vendor_org_a.id}/risks/{risk_org_a.id}", headers=auth_headers(admin_org_a)
    )
    assert response.status_code == 200
    assert response.json()["risks"] == []


def test_vincular_y_desvincular_evidencia(
    client: TestClient, admin_org_a: User, vendor_org_a: Vendor, evidence_org_a: Evidence
):
    response = client.post(
        f"/api/v1/vendors/{vendor_org_a.id}/evidence",
        headers=auth_headers(admin_org_a),
        json={"evidence_id": str(evidence_org_a.id)},
    )
    assert response.status_code == 201
    assert len(response.json()["evidence"]) == 1

    response = client.delete(
        f"/api/v1/vendors/{vendor_org_a.id}/evidence/{evidence_org_a.id}", headers=auth_headers(admin_org_a)
    )
    assert response.status_code == 200
    assert response.json()["evidence"] == []


def test_vincular_y_desvincular_hallazgo(
    client: TestClient, admin_org_a: User, vendor_org_a: Vendor, finding_org_a: Finding
):
    response = client.post(
        f"/api/v1/vendors/{vendor_org_a.id}/findings",
        headers=auth_headers(admin_org_a),
        json={"finding_id": str(finding_org_a.id)},
    )
    assert response.status_code == 201
    assert len(response.json()["findings"]) == 1

    response = client.delete(
        f"/api/v1/vendors/{vendor_org_a.id}/findings/{finding_org_a.id}", headers=auth_headers(admin_org_a)
    )
    assert response.status_code == 200
    assert response.json()["findings"] == []


def test_vincular_riesgo_inexistente_devuelve_404(client: TestClient, admin_org_a: User, vendor_org_a: Vendor):
    response = client.post(
        f"/api/v1/vendors/{vendor_org_a.id}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404


# --- Multi-tenancy / cross-tenant (IDOR) ---


def test_no_se_puede_ver_proveedor_de_otra_organizacion(
    client: TestClient, admin_org_a: User, vendor_org_b: Vendor
):
    response = client.get(f"/api/v1/vendors/{vendor_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


def test_no_se_puede_editar_proveedor_de_otra_organizacion(
    client: TestClient, admin_org_a: User, vendor_org_b: Vendor
):
    response = client.patch(
        f"/api/v1/vendors/{vendor_org_b.id}", headers=auth_headers(admin_org_a), json={"name": "hackeado"}
    )
    assert response.status_code == 404


def test_no_se_puede_eliminar_proveedor_de_otra_organizacion(
    client: TestClient, admin_org_a: User, vendor_org_b: Vendor
):
    response = client.delete(f"/api/v1/vendors/{vendor_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


def test_no_se_puede_vincular_riesgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, vendor_org_a: Vendor, risk_org_b: Risk
):
    response = client.post(
        f"/api/v1/vendors/{vendor_org_a.id}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_b.id)},
    )
    assert response.status_code == 404


def test_no_se_puede_vincular_evidencia_de_otra_organizacion(
    client: TestClient, admin_org_a: User, vendor_org_a: Vendor, evidence_org_b: Evidence
):
    response = client.post(
        f"/api/v1/vendors/{vendor_org_a.id}/evidence",
        headers=auth_headers(admin_org_a),
        json={"evidence_id": str(evidence_org_b.id)},
    )
    assert response.status_code == 404


def test_no_se_puede_vincular_hallazgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, vendor_org_a: Vendor, finding_org_b: Finding
):
    response = client.post(
        f"/api/v1/vendors/{vendor_org_a.id}/findings",
        headers=auth_headers(admin_org_a),
        json={"finding_id": str(finding_org_b.id)},
    )
    assert response.status_code == 404


def test_proveedores_de_otra_organizacion_no_aparecen_en_listado(
    client: TestClient, admin_org_a: User, vendor_org_a: Vendor, vendor_org_b: Vendor
):
    response = client.get("/api/v1/vendors", headers=auth_headers(admin_org_a))
    codigos = {item["vendor_id"] for item in response.json()["items"]}
    assert vendor_org_a.vendor_id in codigos
    assert vendor_org_b.vendor_id not in codigos


# --- RBAC ---


def test_viewer_no_puede_crear_proveedor(client: TestClient, viewer_org_a: User):
    response = client.post("/api/v1/vendors", headers=auth_headers(viewer_org_a), json=_payload_proveedor())
    assert response.status_code == 403


def test_viewer_puede_leer_proveedores(client: TestClient, viewer_org_a: User, vendor_org_a: Vendor):
    response = client.get("/api/v1/vendors", headers=auth_headers(viewer_org_a))
    assert response.status_code == 200


def test_viewer_no_puede_editar_proveedor(client: TestClient, viewer_org_a: User, vendor_org_a: Vendor):
    response = client.patch(
        f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(viewer_org_a), json={"name": "x"}
    )
    assert response.status_code == 403


def test_viewer_no_puede_eliminar_proveedor(client: TestClient, viewer_org_a: User, vendor_org_a: Vendor):
    response = client.delete(f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(viewer_org_a))
    assert response.status_code == 403


def test_analyst_puede_crear_y_editar(client: TestClient, analyst_org_a: User, vendor_org_a: Vendor):
    response = client.post("/api/v1/vendors", headers=auth_headers(analyst_org_a), json=_payload_proveedor())
    assert response.status_code == 201
    response = client.patch(
        f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(analyst_org_a), json={"name": "editado"}
    )
    assert response.status_code == 200


def test_analyst_no_puede_eliminar_proveedor(client: TestClient, analyst_org_a: User, vendor_org_a: Vendor):
    response = client.delete(f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(analyst_org_a))
    assert response.status_code == 403


def test_grc_manager_puede_eliminar_proveedor(client: TestClient, grc_manager_org_a: User, vendor_org_a: Vendor):
    response = client.delete(f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(grc_manager_org_a))
    assert response.status_code == 204


def test_admin_puede_todo(client: TestClient, admin_org_a: User, vendor_org_a: Vendor):
    assert client.get("/api/v1/vendors", headers=auth_headers(admin_org_a)).status_code == 200
    assert (
        client.patch(
            f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(admin_org_a), json={"name": "x"}
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/vendors/{vendor_org_a.id}", headers=auth_headers(admin_org_a)).status_code == 204


# --- Seguridad adicional ---


def test_acceso_no_autenticado_es_rechazado(client: TestClient):
    response = client.get("/api/v1/vendors")
    assert response.status_code == 401


def test_id_invalido_devuelve_422(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/vendors/no-es-un-uuid", headers=auth_headers(admin_org_a))
    assert response.status_code == 422
