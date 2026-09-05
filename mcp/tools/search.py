"""Herramienta MCP: búsqueda unificada. Reutiliza el filtro `search` que ya
existe en cada endpoint de listado (no es un endpoint REST nuevo ni una
lógica de búsqueda distinta) — simplemente llama a cinco endpoints ya
existentes en paralelo y agrupa los resultados por categoría.

Si la credencial de integración no tiene el scope de una categoría
concreta, esa categoría se devuelve como lista vacía con una nota, en vez
de hacer fallar toda la búsqueda por un único recurso sin permiso."""

import asyncio
from typing import Any

from client import GRCApiClient, GRCApiError


async def _buscar_categoria(coro: Any) -> tuple[list[Any], str | None]:
    try:
        resultado = await coro
        return resultado.get("items", []), None
    except GRCApiError as exc:
        return [], f"[{exc.code}] {exc.message}"


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def search_grc(query: str, page_size: int = 5) -> dict[str, Any]:
        """Busca un texto en riesgos, controles, evidencias, hallazgos y
        proveedores a la vez, y devuelve los resultados agrupados por
        categoría. Útil para preguntas amplias como "¿qué hay sobre MFA?".
        Cada categoría requiere su propio scope de lectura; si la
        credencial no tiene acceso a una categoría, esa categoría se
        devuelve vacía con una nota, sin afectar al resto.

        Args:
            query: Texto a buscar.
            page_size: Resultados máximos por categoría (por defecto 5).
        """
        (riesgos, nota_riesgos), (controles, nota_controles), (evidencias, nota_evidencias), (
            hallazgos,
            nota_hallazgos,
        ), (proveedores, nota_proveedores) = await asyncio.gather(
            _buscar_categoria(client.list_risks(search=query, page_size=page_size)),
            _buscar_categoria(client.list_controls(search=query, page_size=page_size)),
            _buscar_categoria(client.list_evidence(search=query, page_size=page_size)),
            _buscar_categoria(client.list_findings(search=query, page_size=page_size)),
            _buscar_categoria(client.list_vendors(search=query, page_size=page_size)),
        )
        return {
            "query": query,
            "riesgos": {"items": riesgos, "nota": nota_riesgos},
            "controles": {"items": controles, "nota": nota_controles},
            "evidencias": {"items": evidencias, "nota": nota_evidencias},
            "hallazgos": {"items": hallazgos, "nota": nota_hallazgos},
            "proveedores": {"items": proveedores, "nota": nota_proveedores},
        }
