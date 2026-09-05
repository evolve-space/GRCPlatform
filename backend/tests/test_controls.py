from fastapi.testclient import TestClient

from app.models.asset import Asset
from app.models.control import Control
from app.models.organization import Organization
from app.models.risk import Risk
from app.models.user import User

from .conftest import auth_headers


def _payload_control(**overrides) -> dict:
    base = {
        "control_id": "CTRL-100",
        "name": "Control de prueba",
        "description": "Descripción del control de prueba",
        "objective": "Objetivo del control de prueba",
        "category": "Ciberseguridad",
        "owner": "Responsable de pruebas",
        "status": "not_implemented",
        "frequency": "annual",
    }
    base.update(overrides)
    return base


def test_crear_control(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = client.post(
        "/api/v1/controls", headers=auth_headers(admin_org_a), json=_payload_control()
    )
    assert response.status_code == 201
    body = response.json()
    assert body["control_id"] == "CTRL-100"
    assert body["organization_id"] == str(organizacion_a.id)


def test_no_se_puede_crear_control_con_codigo_duplicado(client: TestClient, admin_org_a: User):
    client.post("/api/v1/controls", headers=auth_headers(admin_org_a), json=_payload_control())
    response = client.post(
        "/api/v1/controls", headers=auth_headers(admin_org_a), json=_payload_control()
    )
    assert response.status_code == 409


def test_viewer_no_puede_crear_control(client: TestClient, viewer_org_a: User):
    response = client.post(
        "/api/v1/controls", headers=auth_headers(viewer_org_a), json=_payload_control()
    )
    assert response.status_code == 403


def test_analyst_puede_crear_control(client: TestClient, analyst_org_a: User):
    response = client.post(
        "/api/v1/controls", headers=auth_headers(analyst_org_a), json=_payload_control()
    )
    assert response.status_code == 201


def test_listar_controles(client: TestClient, admin_org_a: User, control_org_a: Control):
    response = client.get("/api/v1/controls", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    codigos = {item["control_id"] for item in response.json()["items"]}
    assert control_org_a.control_id in codigos


def test_obtener_control_incluye_relaciones_vacias(
    client: TestClient, admin_org_a: User, control_org_a: Control
):
    response = client.get(f"/api/v1/controls/{control_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["risks"] == []
    assert body["assets"] == []
    assert body["requirements"] == []


def test_actualizar_control_valida_estado_y_frecuencia(
    client: TestClient, admin_org_a: User, control_org_a: Control
):
    response = client.patch(
        f"/api/v1/controls/{control_org_a.id}",
        headers=auth_headers(admin_org_a),
        json={"status": "implemented", "frequency": "monthly"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "implemented"
    assert body["frequency"] == "monthly"


def test_estado_invalido_es_rechazado(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/controls",
        headers=auth_headers(admin_org_a),
        json=_payload_control(status="estado-inventado"),
    )
    assert response.status_code == 422


def test_frecuencia_invalida_es_rechazada(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/controls",
        headers=auth_headers(admin_org_a),
        json=_payload_control(frequency="frecuencia-inventada"),
    )
    assert response.status_code == 422


def test_eliminar_control(client: TestClient, admin_org_a: User, control_org_a: Control):
    response = client.delete(f"/api/v1/controls/{control_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204
    consulta = client.get(f"/api/v1/controls/{control_org_a.id}", headers=auth_headers(admin_org_a))
    assert consulta.status_code == 404


def test_analyst_no_puede_eliminar_control(
    client: TestClient, analyst_org_a: User, control_org_a: Control
):
    response = client.delete(
        f"/api/v1/controls/{control_org_a.id}", headers=auth_headers(analyst_org_a)
    )
    assert response.status_code == 403


def test_busqueda_y_filtro_por_categoria(client: TestClient, admin_org_a: User, control_org_a: Control):
    response = client.get(
        "/api/v1/controls", headers=auth_headers(admin_org_a), params={"search": "pruebas A"}
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    sin_resultados = client.get(
        "/api/v1/controls", headers=auth_headers(admin_org_a), params={"category": "Categoría inexistente"}
    )
    assert sin_resultados.json()["total"] == 0


def test_aislamiento_de_controles_entre_organizaciones(
    client: TestClient, admin_org_a: User, control_org_b: Control
):
    response = client.get(f"/api/v1/controls/{control_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404

    listado = client.get("/api/v1/controls", headers=auth_headers(admin_org_a))
    codigos = {item["control_id"] for item in listado.json()["items"]}
    assert control_org_b.control_id not in codigos


def test_vincular_y_desvincular_riesgo(
    client: TestClient, admin_org_a: User, control_org_a: Control, risk_org_a: Risk
):
    response = client.post(
        f"/api/v1/controls/{control_org_a.id}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_a.id)},
    )
    assert response.status_code == 201
    assert any(r["id"] == str(risk_org_a.id) for r in response.json()["risks"])

    response = client.delete(
        f"/api/v1/controls/{control_org_a.id}/risks/{risk_org_a.id}",
        headers=auth_headers(admin_org_a),
    )
    assert response.status_code == 200
    assert response.json()["risks"] == []


def test_no_se_puede_vincular_riesgo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, control_org_a: Control, risk_org_b: Risk
):
    response = client.post(
        f"/api/v1/controls/{control_org_a.id}/risks",
        headers=auth_headers(admin_org_a),
        json={"risk_id": str(risk_org_b.id)},
    )
    assert response.status_code == 404


def test_vincular_y_desvincular_activo(
    client: TestClient, admin_org_a: User, control_org_a: Control, asset_org_a: Asset
):
    response = client.post(
        f"/api/v1/controls/{control_org_a.id}/assets",
        headers=auth_headers(admin_org_a),
        json={"asset_id": str(asset_org_a.id)},
    )
    assert response.status_code == 201
    assert any(a["id"] == str(asset_org_a.id) for a in response.json()["assets"])

    response = client.delete(
        f"/api/v1/controls/{control_org_a.id}/assets/{asset_org_a.id}",
        headers=auth_headers(admin_org_a),
    )
    assert response.status_code == 200
    assert response.json()["assets"] == []


def test_no_se_puede_vincular_activo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, control_org_a: Control, asset_org_b: Asset
):
    response = client.post(
        f"/api/v1/controls/{control_org_a.id}/assets",
        headers=auth_headers(admin_org_a),
        json={"asset_id": str(asset_org_b.id)},
    )
    assert response.status_code == 404


def test_vincular_requisito(
    client: TestClient, admin_org_a: User, control_org_a: Control, requirement_org_a
):
    response = client.post(
        f"/api/v1/controls/{control_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json={"requirement_id": str(requirement_org_a.id)},
    )
    assert response.status_code == 201
    assert any(r["id"] == str(requirement_org_a.id) for r in response.json()["requirements"])


def test_no_se_puede_vincular_requisito_de_otra_organizacion(
    client: TestClient, admin_org_a: User, control_org_a: Control, requirement_org_b
):
    response = client.post(
        f"/api/v1/controls/{control_org_a.id}/requirements",
        headers=auth_headers(admin_org_a),
        json={"requirement_id": str(requirement_org_b.id)},
    )
    assert response.status_code == 404
