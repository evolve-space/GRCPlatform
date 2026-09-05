from fastapi.testclient import TestClient

from app.models.integration_token import IntegrationToken
from app.models.organization import Organization
from app.models.user import User

from .conftest import auth_headers


def _payload(**overrides) -> dict:
    base = {"name": "Servidor MCP", "scopes": ["risks:read", "dashboard:read"]}
    base.update(overrides)
    return base


# --- Creación ---


def test_admin_puede_crear_token(client: TestClient, admin_org_a: User, organizacion_a: Organization):
    response = client.post("/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == str(organizacion_a.id)
    assert body["scopes"] == ["dashboard:read", "risks:read"]
    assert "token" in body
    assert body["token"].startswith("grc_")
    assert "token_hash" not in body
    assert body["token_prefix"] == body["token"][:12]


def test_scope_invalido_es_rechazado(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload(scopes=["nope:read"])
    )
    assert response.status_code == 422


def test_sin_scopes_es_rechazado(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload(scopes=[])
    )
    assert response.status_code == 422


def test_organization_id_del_cliente_es_ignorado(
    client: TestClient, admin_org_a: User, organizacion_a: Organization, organizacion_b: Organization
):
    response = client.post(
        "/api/v1/integration-tokens",
        headers=auth_headers(admin_org_a),
        json={**_payload(), "organization_id": str(organizacion_b.id)},
    )
    assert response.status_code == 201
    assert response.json()["organization_id"] == str(organizacion_a.id)


# --- Listado (nunca expone el secreto) ---


def test_listar_tokens_nunca_incluye_secreto(client: TestClient, admin_org_a: User):
    client.post("/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload())
    response = client.get("/api/v1/integration-tokens", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert "token" not in item
        assert "token_hash" not in item
        assert "token_prefix" in item


# --- Revocación ---


def test_admin_puede_revocar_token(client: TestClient, admin_org_a: User):
    creado = client.post("/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload())
    token_id = creado.json()["id"]
    response = client.delete(f"/api/v1/integration-tokens/{token_id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 204

    listado = client.get("/api/v1/integration-tokens", headers=auth_headers(admin_org_a)).json()
    item = next(i for i in listado["items"] if i["id"] == token_id)
    assert item["is_active"] is False
    assert item["revoked_at"] is not None


def test_revocar_token_inexistente_devuelve_404(client: TestClient, admin_org_a: User):
    response = client.delete(
        "/api/v1/integration-tokens/00000000-0000-0000-0000-000000000000", headers=auth_headers(admin_org_a)
    )
    assert response.status_code == 404


# --- RBAC ---


def test_grc_manager_puede_leer_pero_no_crear(client: TestClient, grc_manager_org_a: User):
    assert client.get("/api/v1/integration-tokens", headers=auth_headers(grc_manager_org_a)).status_code == 200
    assert (
        client.post(
            "/api/v1/integration-tokens", headers=auth_headers(grc_manager_org_a), json=_payload()
        ).status_code
        == 403
    )


def test_analyst_no_tiene_acceso(client: TestClient, analyst_org_a: User):
    assert client.get("/api/v1/integration-tokens", headers=auth_headers(analyst_org_a)).status_code == 403
    assert (
        client.post("/api/v1/integration-tokens", headers=auth_headers(analyst_org_a), json=_payload()).status_code
        == 403
    )


def test_viewer_no_tiene_acceso(client: TestClient, viewer_org_a: User):
    assert client.get("/api/v1/integration-tokens", headers=auth_headers(viewer_org_a)).status_code == 403


def test_grc_manager_no_puede_revocar(client: TestClient, admin_org_a: User, grc_manager_org_a: User):
    creado = client.post("/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload())
    token_id = creado.json()["id"]
    response = client.delete(f"/api/v1/integration-tokens/{token_id}", headers=auth_headers(grc_manager_org_a))
    assert response.status_code == 403


# --- Multi-tenancy ---


def test_no_se_puede_revocar_token_de_otra_organizacion(
    client: TestClient, admin_org_a: User, integration_token_org_b: tuple[str, IntegrationToken]
):
    _secreto, token_b = integration_token_org_b
    response = client.delete(f"/api/v1/integration-tokens/{token_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


def test_listado_no_incluye_tokens_de_otra_organizacion(
    client: TestClient,
    admin_org_a: User,
    integration_token_org_a: tuple[str, IntegrationToken],
    integration_token_org_b: tuple[str, IntegrationToken],
):
    _secreto_a, token_a = integration_token_org_a
    _secreto_b, token_b = integration_token_org_b
    response = client.get("/api/v1/integration-tokens", headers=auth_headers(admin_org_a))
    ids = {item["id"] for item in response.json()["items"]}
    assert str(token_a.id) in ids
    assert str(token_b.id) not in ids


# --- Auditoría ---


def test_creacion_y_revocacion_generan_evento_de_auditoria(client: TestClient, admin_org_a: User):
    creado = client.post("/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload())
    token_id = creado.json()["id"]
    client.delete(f"/api/v1/integration-tokens/{token_id}", headers=auth_headers(admin_org_a))

    response = client.get(
        f"/api/v1/audit-logs?entity_type=integration_token&entity_id={token_id}",
        headers=auth_headers(admin_org_a),
    )
    acciones = {item["action"] for item in response.json()["items"]}
    assert "integration_token_created" in acciones
    assert "integration_token_revoked" in acciones


def test_secreto_nunca_aparece_en_auditoria(client: TestClient, admin_org_a: User):
    creado = client.post("/api/v1/integration-tokens", headers=auth_headers(admin_org_a), json=_payload())
    secreto = creado.json()["token"]
    response = client.get("/api/v1/audit-logs?action=integration_token_created", headers=auth_headers(admin_org_a))
    assert secreto not in response.text
