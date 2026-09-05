from fastapi.testclient import TestClient

from app.models.organization import Organization
from app.models.user import User

from .conftest import auth_headers


def test_admin_puede_crear_usuario_en_su_organizacion(
    client: TestClient, admin_org_a: User, organizacion_a: Organization
):
    response = client.post(
        "/api/v1/users",
        headers=auth_headers(admin_org_a),
        json={
            "email": "nuevo.usuario@example.com",
            "password": "OtraClave123!",
            "full_name": "Nuevo Usuario de Prueba",
            "role": "analyst",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "nuevo.usuario@example.com"
    assert body["organization_id"] == str(organizacion_a.id)
    assert "hashed_password" not in body


def test_no_se_puede_crear_usuario_con_email_duplicado(client: TestClient, admin_org_a: User):
    payload = {
        "email": admin_org_a.email,
        "password": "OtraClave123!",
        "full_name": "Duplicado",
        "role": "viewer",
    }
    response = client.post("/api/v1/users", headers=auth_headers(admin_org_a), json=payload)
    assert response.status_code == 409


def test_usuario_sin_rol_admin_no_puede_crear_usuarios(client: TestClient, viewer_org_a: User):
    response = client.post(
        "/api/v1/users",
        headers=auth_headers(viewer_org_a),
        json={
            "email": "otro@example.com",
            "password": "OtraClave123!",
            "full_name": "Otro",
            "role": "viewer",
        },
    )
    assert response.status_code == 403


def test_organization_id_del_payload_se_ignora(
    client: TestClient, admin_org_a: User, organizacion_a: Organization, organizacion_b: Organization
):
    """El organization_id nunca debe tomarse del cuerpo de la petición, solo del usuario autenticado."""
    response = client.post(
        "/api/v1/users",
        headers=auth_headers(admin_org_a),
        json={
            "email": "intento.cruzado@example.com",
            "password": "OtraClave123!",
            "full_name": "Intento Cruzado",
            "role": "viewer",
            "organization_id": str(organizacion_b.id),
        },
    )
    assert response.status_code == 201
    assert response.json()["organization_id"] == str(organizacion_a.id)


def test_admin_solo_ve_usuarios_de_su_propia_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    response = client.get("/api/v1/users", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    emails = {usuario["email"] for usuario in response.json()}
    assert admin_org_a.email in emails
    assert admin_org_b.email not in emails


def test_admin_no_puede_obtener_usuario_de_otra_organizacion(
    client: TestClient, admin_org_a: User, admin_org_b: User
):
    response = client.get(f"/api/v1/users/{admin_org_b.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 404


def test_admin_puede_obtener_usuario_de_su_propia_organizacion(
    client: TestClient, admin_org_a: User, viewer_org_a: User
):
    response = client.get(f"/api/v1/users/{viewer_org_a.id}", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    assert response.json()["email"] == viewer_org_a.email


def test_organizations_me_devuelve_solo_la_propia(
    client: TestClient, admin_org_a: User, organizacion_a: Organization
):
    response = client.get("/api/v1/organizations/me", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    assert response.json()["id"] == str(organizacion_a.id)
