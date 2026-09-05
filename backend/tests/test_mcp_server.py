"""Tests del propio servidor MCP (paquete `mcp/` en la raíz del repo), NO de
la superficie REST directamente (eso ya está cubierto en
tests/test_integration_auth.py). Aquí se invocan las herramientas MCP reales
(`mcp/tools/*.py`, tal cual las usa `mcp/server.py`) para demostrar la cadena
completa exigida por la Fase 9:

    herramienta MCP -> GRCApiClient (httpx) -> FastAPI real -> Actor/
    require_access (autenticación + RBAC + scopes) -> aislamiento
    multi-tenant -> AuditLog -> PostgreSQL de pruebas

Simplificaciones respecto al despliegue real, y por qué son seguras:

1. Transporte: en vez de un socket TCP contra un contenedor separado, se usa
   `httpx.ASGITransport(app=app)`, que invoca la MISMA app FastAPI en el
   mismo proceso. Autenticación por API key, RBAC por scopes, aislamiento
   multi-tenant, generación de AuditLog y base de datos son exactamente el
   mismo código que en producción; nada de la lógica de negocio se mockea.

2. SDK MCP: `register_all_tools(mcp, client)` necesita un objeto con un
   método `.tool()` estilo decorador. Aquí se usa `_RegistroDeHerramientas`,
   un sustituto mínimo que solo GUARDA la función decorada (ni genera ni
   valida JSON Schema) — no el SDK real `mcp.server.MCPServer`. Motivo: se
   comprobó empíricamente que instalar el SDK real (`mcp==2.1.1`) en el
   mismo entorno que el backend fijado (FastAPI 0.115.6 + Pydantic 2.10.4)
   produce un `ResolutionImpossible` de pip (conflicto real de versiones
   transitivas de Starlette/Pydantic) — no se puede relajar el pin del
   backend solo para tests cruzados. El propio servidor MCP en producción
   (`mcp/server.py`) usa el SDK real sin ningún sustituto, en su propio
   contenedor con su propio `mcp/requirements.txt`; la equivalencia de
   `_RegistroDeHerramientas.call_tool()` con `MCPServer.call_tool()` (llamar
   a la función registrada con los argumentos dados y devolver su resultado)
   se verifica aparte, con el SDK real, en `mcp/tests/test_sdk_registro.py`.
   Lo único que este sustituto NO ejercita es la validación de esquema del
   propio SDK — la segunda capa de validación (la REST API) sigue siendo
   siempre real y se comprueba explícitamente más abajo.

El paquete `mcp/` se añade a `sys.path` tal cual queda en el contenedor
Docker (ver `mcp/Dockerfile`: `COPY . .` sobre `WORKDIR /app`), es decir,
`client.py`/`config.py`/`tools/` como módulos sueltos — nunca como paquete
`mcp`."""

import asyncio
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.risk import Risk

from .conftest import _crear_integration_token

_MCP_DIR = Path(__file__).resolve().parents[2] / "mcp"
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

from client import GRCApiClient  # noqa: E402
from config import McpSettings  # noqa: E402
from tools import register_all_tools  # noqa: E402


class _RegistroDeHerramientas:
    """Sustituto mínimo de `mcp.server.MCPServer` para estos tests (ver
    docstring del módulo): solo registra y despacha, sin tocar la lógica de
    negocio de GRCPlatform ni el cliente HTTP real."""

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def tool(self, *_args: Any, **_kwargs: Any):
        def _decorador(fn: Any) -> Any:
            self._tools[fn.__name__] = fn
            return fn

        return _decorador

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self._tools[name](**arguments)


@pytest.fixture()
def api_transport(db_session: Session) -> httpx.ASGITransport:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transporte = httpx.ASGITransport(app=app)
    yield transporte
    app.dependency_overrides.clear()


async def _invocar(nombre_tool: str, argumentos: dict, *, secreto: str, transport: httpx.ASGITransport):
    settings = McpSettings(api_base_url="http://testserver", api_token=secreto, transport="stdio", http_port=8001)
    api_client = GRCApiClient(settings, transport=transport)
    servidor = _RegistroDeHerramientas()
    register_all_tools(servidor, api_client)
    try:
        return await servidor.call_tool(nombre_tool, argumentos)
    finally:
        await api_client.aclose()


def _llamar(nombre_tool: str, argumentos: dict, *, secreto: str, transport: httpx.ASGITransport):
    return asyncio.run(_invocar(nombre_tool, argumentos, secreto=secreto, transport=transport))


# --- Cadena completa MCP -> REST -> RBAC -> DB ---


def test_list_risks_via_mcp_aisla_por_organizacion(
    db_session: Session,
    api_transport: httpx.ASGITransport,
    organizacion_a: Organization,
    organizacion_b: Organization,
    risk_org_a: Risk,
    risk_org_b: Risk,
):
    secreto_a, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    secreto_b, _ = _crear_integration_token(db_session, organizacion_b, scopes=["risks:read"])

    resultado_a = _llamar("list_risks", {}, secreto=secreto_a, transport=api_transport)
    resultado_b = _llamar("list_risks", {}, secreto=secreto_b, transport=api_transport)

    titulos_a = {r["title"] for r in resultado_a["items"]}
    titulos_b = {r["title"] for r in resultado_b["items"]}
    assert titulos_a == {risk_org_a.title}
    assert titulos_b == {risk_org_b.title}


def test_get_risk_de_otra_organizacion_via_mcp_da_404_no_403(
    db_session: Session,
    api_transport: httpx.ASGITransport,
    organizacion_a: Organization,
    risk_org_b: Risk,
):
    """Un UUID válido pero de OTRA organización, pasado manualmente a la
    herramienta MCP, nunca debe confirmar su existencia con un 403: debe
    comportarse exactamente igual que para un usuario humano y devolver 404."""
    secreto, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    resultado = _llamar("get_risk", {"risk_id": str(risk_org_b.id)}, secreto=secreto, transport=api_transport)

    payload = resultado
    assert payload["error"] is True
    assert payload["status_code"] == 404


def test_scope_insuficiente_via_mcp_da_403(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    secreto, _ = _crear_integration_token(db_session, organizacion_a, scopes=["vendors:read"])
    resultado = _llamar("list_risks", {}, secreto=secreto, transport=api_transport)

    payload = resultado
    assert payload["error"] is True
    assert payload["status_code"] == 403


def test_token_revocado_via_mcp_da_401(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    secreto, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"], revoked=True)
    resultado = _llamar("list_risks", {}, secreto=secreto, transport=api_transport)

    payload = resultado
    assert payload["error"] is True
    assert payload["status_code"] == 401


def test_token_caducado_via_mcp_da_401(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    from datetime import datetime, timedelta, timezone

    secreto, _ = _crear_integration_token(
        db_session, organizacion_a, scopes=["risks:read"], expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    resultado = _llamar("list_risks", {}, secreto=secreto, transport=api_transport)

    payload = resultado
    assert payload["error"] is True
    assert payload["status_code"] == 401


def test_uuid_invalido_via_mcp_no_hace_crashear_el_tool(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    """La API REST vuelve a validar el UUID independientemente del esquema
    de la herramienta MCP (doble capa de validación, deliberada)."""
    secreto, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    resultado = _llamar("get_risk", {"risk_id": "no-es-un-uuid"}, secreto=secreto, transport=api_transport)

    payload = resultado
    assert payload["error"] is True
    assert payload["status_code"] == 422


def test_pagination_invalida_via_mcp_no_hace_crashear_el_tool(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    secreto, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    resultado = _llamar("list_risks", {"page_size": 99999}, secreto=secreto, transport=api_transport)

    payload = resultado
    assert payload["error"] is True
    assert payload["status_code"] == 422


def test_llamada_mcp_genera_evento_de_auditoria(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    secreto, token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    _llamar("list_risks", {}, secreto=secreto, transport=api_transport)

    eventos = (
        db_session.execute(
            select(AuditLog).where(AuditLog.integration_token_id == token.id, AuditLog.action == "mcp_tool_call")
        )
        .scalars()
        .all()
    )
    assert len(eventos) == 1
    assert eventos[0].user_id is None


def test_secreto_del_token_nunca_aparece_en_la_respuesta_del_tool(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    secreto, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    resultado = _llamar("list_risks", {}, secreto=secreto, transport=api_transport)
    assert secreto not in str(resultado)


# --- Herramienta de escritura: create_risk ---


def test_create_risk_via_mcp_persiste_en_la_organizacion_del_token_y_audita(
    db_session: Session,
    api_transport: httpx.ASGITransport,
    organizacion_a: Organization,
):
    secreto, token = _crear_integration_token(db_session, organizacion_a, scopes=["risks:write"])
    resultado = _llamar(
        "create_risk",
        {
            "title": "Riesgo creado vía MCP",
            "category": "operational",
            "threat": "Fallo de proveedor crítico",
            "vulnerability": "Sin plan de contingencia",
            "likelihood": 3,
            "impact": 4,
            "treatment": "mitigate",
            "owner": "Responsable de pruebas",
            "review_date": "2026-12-31",
        },
        secreto=secreto,
        transport=api_transport,
    )

    payload = resultado
    assert "error" not in payload
    assert payload["title"] == "Riesgo creado vía MCP"

    riesgo_creado = db_session.get(Risk, payload["id"])
    assert riesgo_creado is not None
    assert riesgo_creado.organization_id == organizacion_a.id

    eventos = (
        db_session.execute(
            select(AuditLog).where(
                AuditLog.integration_token_id == token.id,
                AuditLog.action == "create_risk",
            )
        )
        .scalars()
        .all()
    )
    assert len(eventos) == 1


def test_create_risk_via_mcp_con_scope_de_solo_lectura_da_403(
    db_session: Session, api_transport: httpx.ASGITransport, organizacion_a: Organization
):
    secreto, _ = _crear_integration_token(db_session, organizacion_a, scopes=["risks:read"])
    resultado = _llamar(
        "create_risk",
        {
            "title": "No debería crearse",
            "category": "operational",
            "threat": "x",
            "vulnerability": "y",
            "likelihood": 1,
            "impact": 1,
            "treatment": "accept",
            "owner": "Nadie",
            "review_date": "2026-12-31",
        },
        secreto=secreto,
        transport=api_transport,
    )
    payload = resultado
    assert payload["error"] is True
    assert payload["status_code"] == 403


# La prueba arquitectónica "el servidor MCP nunca accede directamente a
# PostgreSQL" vive en mcp/tests/test_no_direct_db_access.py: no necesita
# base de datos ni FastAPI, así que corre de forma autónoma junto con el
# resto de tests unitarios del paquete mcp/.
