"""Smoke test con el SDK MCP REAL (`mcp.server.MCPServer`), sin la app
FastAPI del backend (evita el conflicto de dependencias documentado en
`backend/tests/test_mcp_server.py`). Verifica que `MCPServer.tool()` +
`MCPServer.call_tool()` invocan la función registrada con los argumentos
dados y devuelven su valor de retorno en `structured_content` — el
comportamiento que `backend/tests/test_mcp_server.py` asume al sustituir el
SDK por `_RegistroDeHerramientas` para poder ejercitar la app FastAPI real
sin ese conflicto de dependencias."""

from typing import Any

import pytest
from mcp.server import MCPServer


@pytest.mark.asyncio
async def test_call_tool_invoca_la_funcion_registrada_con_sus_argumentos():
    """Misma firma de retorno (`dict[str, Any]`) que usan las herramientas
    reales en `mcp/tools/*.py`: con ella el SDK sí rellena
    `structured_content`, que es lo que asumen esos módulos."""
    servidor: MCPServer = MCPServer(name="test")

    @servidor.tool()
    async def sumar(a: int, b: int) -> dict[str, Any]:
        """Suma dos números.

        Args:
            a: primer sumando.
            b: segundo sumando.
        """
        return {"resultado": a + b}

    resultado = await servidor.call_tool("sumar", {"a": 2, "b": 3})

    assert resultado.structured_content == {"resultado": 5}
    assert resultado.is_error is False
