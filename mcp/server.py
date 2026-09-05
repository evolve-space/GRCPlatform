"""Punto de entrada del servidor MCP de GRCPlatform.

Arquitectura obligatoria (ver docs/MCP.md y docs/ARCHITECTURE.md):

    Claude / cliente MCP -> este servidor MCP -> HTTP (httpx) -> REST API
    FastAPI -> autorizacion/RBAC -> multi-tenancy -> AuditLog -> PostgreSQL

Este proceso NUNCA importa ``sqlalchemy`` ni ``app.models``, y no recibe
``DATABASE_URL`` ni ninguna credencial de PostgreSQL: todo el acceso a datos
pasa por ``client.GRCApiClient``, que habla exclusivamente HTTP con la REST
API de GRCPlatform usando una credencial de integracion (API key).

Transporte: ``stdio`` para uso local (Claude Desktop u otro cliente MCP
lanzando este script como subproceso) o ``streamable-http`` para el
despliegue en Docker, segun la variable de entorno ``MCP_TRANSPORT``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server import MCPServer

from client import GRCApiClient
from config import cargar_configuracion
from tools import register_all_tools

settings = cargar_configuracion()
client = GRCApiClient(settings)


@asynccontextmanager
async def _lifespan(_server: MCPServer) -> AsyncIterator[None]:
    try:
        yield None
    finally:
        await client.aclose()


mcp = MCPServer(
    name="grcplatform",
    description=(
        "Acceso de solo lectura (y creacion de riesgos) a GRCPlatform: riesgos, "
        "controles, evidencias, hallazgos, acciones de remediacion, proveedores "
        "(TPRM), dashboard y Compliance Score. Toda operacion pasa por la REST "
        "API de GRCPlatform con autenticacion por API key y aislamiento "
        "multi-tenant; nunca accede directamente a PostgreSQL."
    ),
    lifespan=_lifespan,
)

register_all_tools(mcp, client)


if __name__ == "__main__":
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=settings.http_port)
