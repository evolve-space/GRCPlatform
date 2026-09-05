"""Herramientas MCP: Controles. Requieren scope `controls:read`."""

from typing import Any

from client import GRCApiClient, GRCApiError
from schemas.enums import ControlStatus

from ._util import error_payload


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def list_controls(
        search: str | None = None,
        category: str | None = None,
        status: ControlStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Lista los controles de la organización, con búsqueda y filtros.

        Args:
            search: Texto a buscar en código, nombre o descripción del control.
            category: Categoría del control (p. ej. Control de acceso).
            status: Estado de implementación del control.
            page: Número de página (empieza en 1).
            page_size: Resultados por página (máximo 100).
        """
        try:
            return await client.list_controls(search=search, category=category, status=status, page=page, page_size=page_size)
        except GRCApiError as exc:
            return error_payload(exc)

    @mcp.tool()
    async def get_control(control_id: str) -> dict[str, Any]:
        """Obtiene el detalle de un control (identificación, nombre, estado,
        frecuencia, responsable) y sus relaciones con riesgos, activos y
        requisitos de cumplimiento.

        Args:
            control_id: UUID del control, tal como aparece en `list_controls`.
        """
        try:
            return await client.get_control(control_id)
        except GRCApiError as exc:
            return error_payload(exc)
