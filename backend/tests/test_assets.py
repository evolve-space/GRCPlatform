from fastapi.testclient import TestClient

from app.models.asset import Asset
from app.models.organization import Organization
from app.models.user import User

from .conftest import auth_headers

PAYLOAD_ACTIVO = {
    "name": "Nuevo activo de prueba",
    "description": "Descripción de prueba",
    "asset_type": "application",
    "owner": "Responsable de pruebas",
    "criticality": "high",
    "data_classification": "confidential",
    "status": "active",
}


def test_admin_puede_crear_activo(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = client.post("/api/v1/assets", headers=auth_headers(admin_org_a), json=PAYLOAD_ACTIVO)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == PAYLOAD_ACTIVO["name"]
    assert body["organization_id"] == str(organizacion_a.id)


def test_analyst_puede_crear_activo(client: TestClient, analyst_org_a: User):
    response = client.post("/api/v1/assets", headers=auth_headers(analyst_org_a), json=PAYLOAD_ACTIVO)
    assert response.status_code == 201


def test_viewer_no_puede_crear_activo(client: TestClient, viewer_org_a: User):
    response = client.post("/api/v1/assets", headers=auth_headers(viewer_org_a), json=PAYLOAD_ACTIVO)
    assert response.status_code == 403


def test_viewer_puede_listar_activos(client: TestClient, viewer_org_a: User, asset_org_a: Asset):
    response = client.get("/api/v1/assets", headers=auth_headers(viewer_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    nombres = {item["name"] for item in body["items"]}
    assert asset_org_a.name in nombres


def test_obtener_activo_por_id(client: TestClient, admin_org_a: User, asset_org_a: Asset):
    response = client.get(f"/api/v1/assets/{asset_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    assert response.json()["id"] == str(asset_org_a.id)


def test_actualizar_activo(client: TestClient, admin_org_a: User, asset_org_a: Asset):
    response = client.patch(
        f"/api/v1/assets/{asset_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"criticality": "critical", "status": "inactive"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["criticality"] == "critical"
    assert body["status"] == "inactive"
    assert body["name"] == asset_org_a.name  # no tocado, se mantiene


def test_eliminar_activo(client: TestClient, admin_org_a: User, asset_org_a: Asset):
    response = client.delete(f"/api/v1/assets/{asset_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204

    consulta = client.get(f"/api/v1/assets/{asset_org_a.id}", headers=auth_headers(admin_org_a))
    assert consulta.status_code == 404


def test_analyst_no_puede_eliminar_activo(client: TestClient, analyst_org_a: User, asset_org_a: Asset):
    response = client.delete(f"/api/v1/assets/{asset_org_a.id}", headers=auth_headers(analyst_org_a))
    assert response.status_code == 403


def test_busqueda_de_activos_por_nombre(client: TestClient, admin_org_a: User, asset_org_a: Asset):
    response = client.get(
        "/api/v1/assets", headers=auth_headers(admin_org_a), params={"search": "pruebas A"}
    )
    assert response.status_code == 200
    nombres = {item["name"] for item in response.json()["items"]}
    assert asset_org_a.name in nombres


def test_filtro_por_criticidad_sin_resultados(client: TestClient, admin_org_a: User, asset_org_a: Asset):
    response = client.get(
        "/api/v1/assets", headers=auth_headers(admin_org_a), params={"criticality": "low"}
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_aislamiento_de_activos_entre_organizaciones(
    client: TestClient, admin_org_a: User, asset_org_b: Asset
):
    response = client.get(f"/api/v1/assets/{asset_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404

    listado = client.get("/api/v1/assets", headers=auth_headers(admin_org_a))
    nombres = {item["name"] for item in listado.json()["items"]}
    assert asset_org_b.name not in nombres
