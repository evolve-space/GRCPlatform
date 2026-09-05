from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import User

from .conftest import auth_headers


def test_login_correcto(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_org_a.email, "password": "Password123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_contrasena_incorrecta(client: TestClient, admin_org_a: User):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_org_a.email, "password": "contraseña-equivocada"},
    )
    assert response.status_code == 401


def test_login_usuario_inexistente(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "no-existe@example.com", "password": "cualquiera"},
    )
    assert response.status_code == 401


def test_jwt_valido_devuelve_usuario_actual(client: TestClient, admin_org_a: User):
    response = client.get("/api/v1/auth/me", headers=auth_headers(admin_org_a))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == admin_org_a.email
    assert body["role"] == "admin"
    assert "hashed_password" not in body
    assert "password" not in body


def test_jwt_invalido_es_rechazado(client: TestClient):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer token-invalido-y-manipulado"}
    )
    assert response.status_code == 401


def test_jwt_expirado_es_rechazado(client: TestClient, admin_org_a: User):
    token_expirado = create_access_token(
        subject=str(admin_org_a.id), expires_delta=timedelta(minutes=-5)
    )
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_expirado}"}
    )
    assert response.status_code == 401


def test_sin_token_es_rechazado(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
