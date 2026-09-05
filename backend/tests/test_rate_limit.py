"""Tests del rate limiting (Fase 10: hardening) — fuerza bruta en login y
abuso de credenciales de integración (por IP y por token). Los límites reales
(`app/core/rate_limit.py`, `app/api/routes/auth.py`, `app/api/deps.py`) se
rebajan con `monkeypatch` para que las pruebas sean rápidas y deterministas,
sin depender de esperar ventanas de tiempo reales."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization

from .conftest import _crear_integration_token


def _headers(token: str) -> dict:
    return {"X-API-Key": token}


def test_login_supera_el_limite_de_intentos_da_429(client: TestClient, monkeypatch, viewer_org_a) -> None:
    import app.api.routes.auth as auth_module

    monkeypatch.setattr(auth_module, "_LIMITE_INTENTOS_LOGIN", 3)

    for _ in range(3):
        response = client.post(
            "/api/v1/auth/login", data={"username": "no-existe@example.com", "password": "x"}
        )
        assert response.status_code == 401

    response = client.post("/api/v1/auth/login", data={"username": "no-existe@example.com", "password": "x"})
    assert response.status_code == 429


def test_login_correcto_tambien_cuenta_para_el_limite(client: TestClient, monkeypatch, viewer_org_a) -> None:
    import app.api.routes.auth as auth_module

    monkeypatch.setattr(auth_module, "_LIMITE_INTENTOS_LOGIN", 2)

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login", data={"username": viewer_org_a.email, "password": "Password123!"}
        )
        assert response.status_code == 200

    response = client.post(
        "/api/v1/auth/login", data={"username": viewer_org_a.email, "password": "Password123!"}
    )
    assert response.status_code == 429


def test_intentos_de_api_key_por_ip_supera_el_limite_da_429(client: TestClient, monkeypatch) -> None:
    import app.api.deps as deps_module

    monkeypatch.setattr(deps_module, "_LIMITE_INTENTOS_API_KEY_POR_IP", 3)

    for _ in range(3):
        response = client.get("/api/v1/risks", headers=_headers("grc_no_existe"))
        assert response.status_code == 401

    response = client.get("/api/v1/risks", headers=_headers("grc_no_existe"))
    assert response.status_code == 429


def test_peticiones_con_token_valido_superan_su_limite_da_429(
    db_session: Session, client: TestClient, monkeypatch, organizacion_a: Organization
) -> None:
    import app.api.deps as deps_module

    monkeypatch.setattr(deps_module, "_LIMITE_PETICIONES_POR_TOKEN", 3)

    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])

    for _ in range(3):
        response = client.get("/api/v1/risks", headers=_headers(secreto))
        assert response.status_code == 200

    response = client.get("/api/v1/risks", headers=_headers(secreto))
    assert response.status_code == 429


def test_token_distinto_no_se_ve_afectado_por_el_limite_de_otro(
    db_session: Session, client: TestClient, monkeypatch, organizacion_a: Organization
) -> None:
    import app.api.deps as deps_module

    monkeypatch.setattr(deps_module, "_LIMITE_PETICIONES_POR_TOKEN", 2)

    secreto_agotado, _t1 = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    secreto_fresco, _t2 = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])

    for _ in range(2):
        assert client.get("/api/v1/risks", headers=_headers(secreto_agotado)).status_code == 200
    assert client.get("/api/v1/risks", headers=_headers(secreto_agotado)).status_code == 429

    # Un token distinto tiene su propio contador — el límite del primero no
    # afecta a un segundo cliente de integración legítimo.
    assert client.get("/api/v1/risks", headers=_headers(secreto_fresco)).status_code == 200


def test_respuesta_429_usa_el_formato_de_error_normalizado(client: TestClient, monkeypatch, viewer_org_a) -> None:
    import app.api.routes.auth as auth_module

    monkeypatch.setattr(auth_module, "_LIMITE_INTENTOS_LOGIN", 1)

    client.post("/api/v1/auth/login", data={"username": "x@example.com", "password": "x"})
    response = client.post("/api/v1/auth/login", data={"username": "x@example.com", "password": "x"})

    assert response.status_code == 429
    detalle = response.json()["detail"]
    assert detalle["code"] == "RATE_LIMITED"
    assert "message" in detalle
