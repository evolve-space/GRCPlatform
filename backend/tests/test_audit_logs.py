from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.organization import Organization
from app.models.user import User

from .conftest import auth_headers


def _payload_proveedor(**overrides) -> dict:
    base = {
        "vendor_id": "VEN-AUDIT-100",
        "name": "Proveedor para auditoría",
        "category": "Servicios cloud",
        "owner": "Responsable de pruebas",
        "criticality": "high",
        "data_classification": "confidential",
        "status": "active",
        "due_diligence_status": "approved",
        "relationship_start_date": "2027-01-01",
    }
    base.update(overrides)
    return base


# --- Consulta y generación de eventos ---


def test_operacion_sobre_vendor_genera_evento_consultable(client: TestClient, admin_org_a: User):
    creado = client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    vendor_id = creado.json()["id"]

    response = client.get(
        f"/api/v1/audit-logs?entity_type=vendor&entity_id={vendor_id}", headers=auth_headers(admin_org_a)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["action"] == "create_vendor" for item in body["items"])


def test_filtro_por_accion(client: TestClient, admin_org_a: User):
    creado = client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    vendor_id = creado.json()["id"]
    client.patch(f"/api/v1/vendors/{vendor_id}", headers=auth_headers(admin_org_a), json={"name": "cambiado"})

    response = client.get("/api/v1/audit-logs?action=update_vendor", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["action"] == "update_vendor"


def test_filtro_por_tipo_de_entidad(client: TestClient, admin_org_a: User, finding_org_a):
    response = client.get("/api/v1/audit-logs?entity_type=finding", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["entity_type"] == "finding"


def test_filtro_por_usuario_actor(client: TestClient, admin_org_a: User):
    client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    response = client.get(
        f"/api/v1/audit-logs?user_id={admin_org_a.id}", headers=auth_headers(admin_org_a)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["user_id"] == str(admin_org_a.id)


def test_filtro_por_rango_de_fechas(client: TestClient, admin_org_a: User):
    client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    hoy = date.today()
    response = client.get(
        f"/api/v1/audit-logs?date_from={hoy.isoformat()}&date_to={hoy.isoformat()}",
        headers=auth_headers(admin_org_a),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    ayer = hoy - timedelta(days=1)
    anteayer = hoy - timedelta(days=2)
    response_vacio = client.get(
        f"/api/v1/audit-logs?date_from={anteayer.isoformat()}&date_to={ayer.isoformat()}",
        headers=auth_headers(admin_org_a),
    )
    assert response_vacio.json()["total"] == 0


def test_orden_mas_reciente_primero(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor(vendor_id="VEN-ORD-1")
    )
    client.post(
        "/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor(vendor_id="VEN-ORD-2")
    )
    response = client.get("/api/v1/audit-logs?page_size=100", headers=auth_headers(admin_org_a))
    fechas = [item["created_at"] for item in response.json()["items"]]
    assert fechas == sorted(fechas, reverse=True)


def test_paginacion(client: TestClient, admin_org_a: User):
    for i in range(5):
        client.post(
            "/api/v1/vendors",
            headers=auth_headers(admin_org_a),
            json=_payload_proveedor(vendor_id=f"VEN-PAG-AUDIT-{i}"),
        )
    response = client.get("/api/v1/audit-logs?page=1&page_size=3", headers=auth_headers(admin_org_a))
    assert len(response.json()["items"]) == 3


def test_actor_incluye_email_y_nombre(client: TestClient, admin_org_a: User):
    client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    response = client.get("/api/v1/audit-logs?action=create_vendor", headers=auth_headers(admin_org_a))
    item = response.json()["items"][0]
    assert item["actor"]["email"] == admin_org_a.email
    assert item["actor"]["full_name"] == admin_org_a.full_name


def test_nunca_expone_secretos_en_details(client: TestClient, admin_org_a: User):
    client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    response = client.get("/api/v1/audit-logs", headers=auth_headers(admin_org_a))
    for item in response.json()["items"]:
        detalles = str(item.get("details") or {})
        assert "password" not in detalles.lower()
        assert "hashed_password" not in detalles.lower()
        assert "token" not in detalles.lower()


def test_endpoint_meta_devuelve_acciones_y_entidades(client: TestClient, admin_org_a: User):
    client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())
    response = client.get("/api/v1/audit-logs/meta", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert "create_vendor" in body["actions"]
    assert "vendor" in body["entity_types"]


# --- Multi-tenancy ---


def test_aislamiento_por_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User, organizacion_b: Organization
):
    client.post("/api/v1/vendors", headers=auth_headers(admin_org_a), json=_payload_proveedor())

    response_b = client.get("/api/v1/audit-logs", headers=auth_headers(admin_org_b))
    for item in response_b.json()["items"]:
        assert item["organization_id"] == str(organizacion_b.id)


# --- RBAC ---


def test_viewer_no_tiene_acceso(client: TestClient, viewer_org_a: User):
    response = client.get("/api/v1/audit-logs", headers=auth_headers(viewer_org_a))
    assert response.status_code == 403


def test_analyst_no_tiene_acceso(client: TestClient, analyst_org_a: User):
    response = client.get("/api/v1/audit-logs", headers=auth_headers(analyst_org_a))
    assert response.status_code == 403


def test_grc_manager_tiene_acceso(client: TestClient, grc_manager_org_a: User):
    response = client.get("/api/v1/audit-logs", headers=auth_headers(grc_manager_org_a))
    assert response.status_code == 200


def test_admin_tiene_acceso(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/audit-logs", headers=auth_headers(admin_org_a))
    assert response.status_code == 200


def test_acceso_no_autenticado_es_rechazado(client: TestClient):
    response = client.get("/api/v1/audit-logs")
    assert response.status_code == 401


# --- Inmutabilidad: no debe existir ningún endpoint de escritura ---


def test_no_existe_creacion_manual(client: TestClient, admin_org_a: User):
    response = client.post("/api/v1/audit-logs", headers=auth_headers(admin_org_a), json={"action": "x"})
    assert response.status_code in (404, 405)


def test_no_existe_modificacion(client: TestClient, admin_org_a: User):
    response = client.patch(
        "/api/v1/audit-logs/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(admin_org_a),
        json={"action": "x"},
    )
    assert response.status_code in (404, 405)


def test_no_existe_eliminacion(client: TestClient, admin_org_a: User):
    response = client.delete(
        "/api/v1/audit-logs/00000000-0000-0000-0000-000000000000", headers=auth_headers(admin_org_a)
    )
    assert response.status_code in (404, 405)
