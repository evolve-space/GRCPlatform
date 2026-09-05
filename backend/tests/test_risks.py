from fastapi.testclient import TestClient

from app.models.asset import Asset
from app.models.organization import Organization
from app.models.user import User

from .conftest import auth_headers


def _payload_riesgo(**overrides) -> dict:
    base = {
        "title": "Riesgo de prueba",
        "description": "Descripción del riesgo de prueba",
        "category": "Ciberseguridad",
        "threat": "Amenaza de prueba",
        "vulnerability": "Vulnerabilidad de prueba",
        "likelihood": 3,
        "impact": 4,
        "treatment": "mitigate",
        "owner": "Responsable de pruebas",
        "review_date": "2027-01-01",
        "status": "identified",
    }
    base.update(overrides)
    return base


def test_crear_riesgo(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = client.post(
        "/api/v1/risks", headers=auth_headers(admin_org_a), json=_payload_riesgo()
    )
    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == str(organizacion_a.id)
    assert body["title"] == "Riesgo de prueba"


def test_calculo_correcto_del_riesgo_inherente(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/risks",
        headers=auth_headers(admin_org_a),
        json=_payload_riesgo(likelihood=5, impact=5),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["inherent_score"] == 25
    assert body["inherent_level"] == "critico"


def test_el_score_enviado_por_el_cliente_se_ignora(client: TestClient, admin_org_a: User):
    """El backend debe recalcular el score siempre, aunque el cliente envíe uno manipulado."""
    payload = _payload_riesgo(likelihood=1, impact=1)
    payload["inherent_score"] = 999
    response = client.post("/api/v1/risks", headers=auth_headers(admin_org_a), json=payload)
    assert response.status_code == 201
    assert response.json()["inherent_score"] == 1


def test_calculo_correcto_del_riesgo_residual(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/risks",
        headers=auth_headers(admin_org_a),
        json=_payload_riesgo(likelihood=5, impact=5, residual_likelihood=2, residual_impact=3),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["residual_score"] == 6
    assert body["residual_level"] == "medio"


def test_residual_requiere_probabilidad_e_impacto_juntos(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/risks",
        headers=auth_headers(admin_org_a),
        json=_payload_riesgo(residual_likelihood=2),
    )
    assert response.status_code == 422


def test_clasificacion_de_niveles_de_riesgo(client: TestClient, admin_org_a: User):
    casos = [
        (1, 1, "bajo"),
        (2, 3, "medio"),
        (4, 4, "alto"),
        (5, 5, "critico"),
    ]
    for likelihood, impact, nivel_esperado in casos:
        response = client.post(
            "/api/v1/risks",
            headers=auth_headers(admin_org_a),
            json=_payload_riesgo(
                title=f"Riesgo {likelihood}x{impact}", likelihood=likelihood, impact=impact
            ),
        )
        assert response.status_code == 201
        assert response.json()["inherent_level"] == nivel_esperado


def test_validacion_likelihood_impact_fuera_de_rango(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/risks", headers=auth_headers(admin_org_a), json=_payload_riesgo(likelihood=6)
    )
    assert response.status_code == 422

    response = client.post(
        "/api/v1/risks", headers=auth_headers(admin_org_a), json=_payload_riesgo(impact=0)
    )
    assert response.status_code == 422


def test_relacion_riesgo_activo_de_la_misma_organizacion(
    client: TestClient, admin_org_a: User, asset_org_a: Asset
):
    response = client.post(
        "/api/v1/risks",
        headers=auth_headers(admin_org_a),
        json=_payload_riesgo(asset_id=str(asset_org_a.id)),
    )
    assert response.status_code == 201
    assert response.json()["asset_id"] == str(asset_org_a.id)


def test_no_se_puede_relacionar_riesgo_con_activo_de_otra_organizacion(
    client: TestClient, admin_org_a: User, asset_org_b: Asset
):
    response = client.post(
        "/api/v1/risks",
        headers=auth_headers(admin_org_a),
        json=_payload_riesgo(asset_id=str(asset_org_b.id)),
    )
    assert response.status_code == 404


def test_viewer_no_puede_crear_riesgo(client: TestClient, viewer_org_a: User):
    response = client.post(
        "/api/v1/risks", headers=auth_headers(viewer_org_a), json=_payload_riesgo()
    )
    assert response.status_code == 403


def test_analyst_puede_crear_riesgo(client: TestClient, analyst_org_a: User):
    response = client.post(
        "/api/v1/risks", headers=auth_headers(analyst_org_a), json=_payload_riesgo()
    )
    assert response.status_code == 201


def test_actualizar_riesgo_recalcula_score(client: TestClient, admin_org_a: User):
    creado = client.post(
        "/api/v1/risks", headers=auth_headers(admin_org_a), json=_payload_riesgo(likelihood=2, impact=2)
    ).json()
    assert creado["inherent_score"] == 4

    actualizado = client.patch(
        f"/api/v1/risks/{creado['id']}", headers=auth_headers(admin_org_a), json={"likelihood": 5}
    )
    assert actualizado.status_code == 200
    body = actualizado.json()
    assert body["inherent_score"] == 10
    assert body["inherent_level"] == "alto"


def test_eliminar_riesgo(client: TestClient, admin_org_a: User):
    creado = client.post(
        "/api/v1/risks", headers=auth_headers(admin_org_a), json=_payload_riesgo()
    ).json()

    response = client.delete(f"/api/v1/risks/{creado['id']}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204

    consulta = client.get(f"/api/v1/risks/{creado['id']}", headers=auth_headers(admin_org_a))
    assert consulta.status_code == 404


def test_aislamiento_de_riesgos_entre_organizaciones(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    creado = client.post(
        "/api/v1/risks", headers=auth_headers(admin_org_b), json=_payload_riesgo(title="Riesgo de B")
    )
    assert creado.status_code == 201
    risk_id = creado.json()["id"]

    consulta_cruzada = client.get(f"/api/v1/risks/{risk_id}", headers=auth_headers(admin_org_a))
    assert consulta_cruzada.status_code == 404

    listado = client.get("/api/v1/risks", headers=auth_headers(admin_org_a))
    titulos = {item["title"] for item in listado.json()["items"]}
    assert "Riesgo de B" not in titulos


def test_filtro_por_nivel_de_riesgo(client: TestClient, admin_org_a: User):
    client.post(
        "/api/v1/risks",
        headers=auth_headers(admin_org_a),
        json=_payload_riesgo(title="Riesgo crítico filtrado", likelihood=5, impact=5),
    )
    client.post(
        "/api/v1/risks",
        headers=auth_headers(admin_org_a),
        json=_payload_riesgo(title="Riesgo bajo filtrado", likelihood=1, impact=1),
    )

    response = client.get(
        "/api/v1/risks", headers=auth_headers(admin_org_a), params={"level": "critico"}
    )
    assert response.status_code == 200
    titulos = {item["title"] for item in response.json()["items"]}
    assert "Riesgo crítico filtrado" in titulos
    assert "Riesgo bajo filtrado" not in titulos
