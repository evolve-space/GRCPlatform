"""Configuración del servidor MCP, leída exclusivamente de variables de
entorno. Nunca hardcodear aquí una URL, un token ni ningún secreto: el
servidor MCP se comporta como un cliente externo de GRCPlatform, igual que
cualquier otra integración."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class McpSettings:
    api_base_url: str
    api_token: str
    transport: str
    http_port: int


def _requerido(nombre: str) -> str:
    valor = os.environ.get(nombre)
    if not valor:
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria {nombre}. "
            "El servidor MCP no puede arrancar sin credenciales de integración; "
            "ver docs/MCP.md."
        )
    return valor


def cargar_configuracion() -> McpSettings:
    return McpSettings(
        api_base_url=os.environ.get("GRC_API_BASE_URL", "http://localhost:8000").rstrip("/"),
        api_token=_requerido("GRC_MCP_TOKEN"),
        transport=os.environ.get("MCP_TRANSPORT", "stdio"),
        http_port=int(os.environ.get("MCP_HTTP_PORT", "8001")),
    )
