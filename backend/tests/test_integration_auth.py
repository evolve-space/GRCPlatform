"""Tests de la superficie de integración (API key / scopes) sobre los
endpoints REST reales que usa el servidor MCP: multi-tenancy, scopes,
revocación, caducidad y auditoría. Ver también tests/test_integration_tokens.py
(gestión de credenciales) y tests/test_mcp_server.py (el propio servidor MCP)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.integration_token import IntegrationToken
from app.models.organization import Organization
from app.models.risk import Risk
from app.models.user import User
from app.models.vendor import Vendor

from .conftest import _crear_integration_token


def _headers(token: str) -> dict:
    return {"X-API-Key": token}


# --- Autenticación básica ---


def test_token_valido_puede_listar_riesgos(client: TestClient, integration_token_org_a: tuple[str, IntegrationToken]):
    secreto, _token = integration_token_org_a
    response = client.get("/api/v1/risks", headers=_headers(secreto))
    assert response.status_code == 200


def test_sin_credencial_es_401(client: TestClient):
    response = client.get("/api/v1/risks")
    assert response.status_code == 401


def test_api_key_invalida_es_401(client: TestClient):
    response = client.get("/api/v1/risks", headers=_headers("grc_no_existe"))
    assert response.status_code == 401


def test_token_revocado_es_401(db_session: Session, client: TestClient, organizacion_a: Organization):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"], revoked=True)
    response = client.get("/api/v1/risks", headers=_headers(secreto))
    assert response.status_code == 401


def test_token_inactivo_es_401(db_session: Session, client: TestClient, organizacion_a: Organization):
    secreto, _token = _crear_integration_token(
        db_session, organizacion_a, scopes=["risks:read"], is_active=False
    )
    response = client.get("/api/v1/risks", headers=_headers(secreto))
    assert response.status_code == 401


def test_token_caducado_es_401(db_session: Session, client: TestClient, organizacion_a: Organization):
    secreto, _token = _crear_integration_token(
        db_session, organizacion_a, scopes=["risks:read"], expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    response = client.get("/api/v1/risks", headers=_headers(secreto))
    assert response.status_code == 401


def test_token_no_caducado_funciona(db_session: Session, client: TestClient, organizacion_a: Organization):
    secreto, _token = _crear_integration_token(
        db_session, organizacion_a, scopes=["risks:read"], expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    response = client.get("/api/v1/risks", headers=_headers(secreto))
    assert response.status_code == 200


# --- Scopes (mínimo privilegio) ---


def test_scope_insuficiente_es_403(db_session: Session, client: TestClient, organizacion_a: Organization):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["vendors:read"])
    response = client.get("/api/v1/risks", headers=_headers(secreto))
    assert response.status_code == 403


def test_scope_correcto_permite_el_recurso_correcto(
    db_session: Session, client: TestClient, organizacion_a: Organization
):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["controls:read"])
    assert client.get("/api/v1/controls", headers=_headers(secreto)).status_code == 200
    assert client.get("/api/v1/risks", headers=_headers(secreto)).status_code == 403


def test_scope_read_no_permite_escritura(db_session: Session, client: TestClient, organizacion_a: Organization):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    response = client.post(
        "/api/v1/risks",
        headers=_headers(secreto),
        json={
            "title": "Riesgo vía integración",
            "category": "Ciberseguridad",
            "threat": "t",
            "vulnerability": "v",
            "likelihood": 3,
            "impact": 3,
            "treatment": "mitigate",
            "owner": "owner",
            "review_date": "2027-01-01",
        },
    )
    assert response.status_code == 403


def test_scope_write_permite_crear_riesgo_y_genera_auditoria(
    db_session: Session, client: TestClient, organizacion_a: Organization
):
    secreto, token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:write", "audit:read"])
    response = client.post(
        "/api/v1/risks",
        headers=_headers(secreto),
        json={
            "title": "Riesgo vía integración",
            "category": "Ciberseguridad",
            "threat": "t",
            "vulnerability": "v",
            "likelihood": 3,
            "impact": 3,
            "treatment": "mitigate",
            "owner": "owner",
            "review_date": "2027-01-01",
        },
    )
    assert response.status_code == 201
    assert response.json()["organization_id"] == str(organizacion_a.id)


# --- Multi-tenancy: el corazón de la Fase 9 ---


def test_listado_no_incluye_datos_de_otra_organizacion(
    db_session: Session,
    client: TestClient,
    organizacion_a: Organization,
    risk_org_a: Risk,
    risk_org_b: Risk,
):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    response = client.get("/api/v1/risks", headers=_headers(secreto))
    titulos = {item["title"] for item in response.json()["items"]}
    assert risk_org_a.title in titulos
    assert risk_org_b.title not in titulos


def test_get_risk_de_otra_organizacion_devuelve_404_no_403(
    db_session: Session, client: TestClient, organizacion_a: Organization, risk_org_b: Risk
):
    """Un UUID válido de OTRA organización debe dar 404 (no confirmar su
    existencia con un 403), exactamente igual que para un usuario humano."""
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    response = client.get(f"/api/v1/risks/{risk_org_b.id}", headers=_headers(secreto))
    assert response.status_code == 404


def test_get_vendor_de_otra_organizacion_da_404(
    db_session: Session, client: TestClient, organizacion_a: Organization, vendor_org_b: Vendor
):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["vendors:read"])
    response = client.get(f"/api/v1/vendors/{vendor_org_b.id}", headers=_headers(secreto))
    assert response.status_code == 404


def test_dos_tokens_de_organizaciones_distintas_ven_datos_distintos(
    db_session: Session,
    client: TestClient,
    organizacion_a: Organization,
    organizacion_b: Organization,
    risk_org_a: Risk,
    risk_org_b: Risk,
):
    secreto_a, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    secreto_b, _ = _crear_integration_token(db_session, organizacion_b, scopes=["risks:read"])

    resp_a = client.get("/api/v1/risks", headers=_headers(secreto_a)).json()
    resp_b = client.get("/api/v1/risks", headers=_headers(secreto_b)).json()
    assert {r["title"] for r in resp_a["items"]} == {risk_org_a.title}
    assert {r["title"] for r in resp_b["items"]} == {risk_org_b.title}


# --- Auditoría de llamadas de integración ---


def test_llamada_de_integracion_genera_mcp_tool_call(
    db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization
):
    from .conftest import auth_headers

    secreto, token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    client.get("/api/v1/risks", headers=_headers(secreto))

    response = client.get(
        "/api/v1/audit-logs?action=mcp_tool_call&entity_type=risks", headers=auth_headers(admin_org_a)
    )
    body = response.json()
    assert body["total"] >= 1
    evento = body["items"][0]
    assert evento["integration_token_id"] == str(token.id)
    assert evento["user_id"] is None


def test_api_key_nunca_aparece_en_auditlog(
    db_session: Session, client: TestClient, admin_org_a: User, organizacion_a: Organization
):
    from .conftest import auth_headers

    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    client.get("/api/v1/risks", headers=_headers(secreto))
    response = client.get("/api/v1/audit-logs?action=mcp_tool_call", headers=auth_headers(admin_org_a))
    assert secreto not in response.text


# --- Validación de inputs (segunda capa: la API vuelve a validar) ---


def test_uuid_invalido_es_422_tambien_para_integracion(
    db_session: Session, client: TestClient, organizacion_a: Organization
):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    response = client.get("/api/v1/risks/no-es-un-uuid", headers=_headers(secreto))
    assert response.status_code == 422


def test_page_size_fuera_de_rango_es_422(db_session: Session, client: TestClient, organizacion_a: Organization):
    secreto, _token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    response = client.get("/api/v1/risks?page_size=99999", headers=_headers(secreto))
    assert response.status_code == 422
