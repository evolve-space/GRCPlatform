"""Herramientas MCP: Hallazgos. Requieren scope `findings:read`."""

from typing import Any

from client import GRCApiClient, GRCApiError
from schemas.enums import Criticality, FindingStatus

from ._util import error_payload


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def list_findings(
        search: str | None = None,
        severity: Criticality | None = None,
        status: FindingStatus | None = None,
        overdue: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Lista los hallazgos de la organización, con búsqueda y filtros.

        Args:
            search: Texto a buscar en código, título o descripción del hallazgo.
            severity: Severidad del hallazgo (low, medium, high, critical).
            status: Estado del hallazgo.
            overdue: true=solo hallazgos con la fecha límite vencida y aún abiertos.
            page: Número de página (empieza en 1).
            page_size: Resultados por página (máximo 100).
        """
        try:
            return await client.list_findings(
                search=search, severity=severity, status=status, overdue=overdue, page=page, page_size=page_size
            )
        except GRCApiError as exc:
            return error_payload(exc)
