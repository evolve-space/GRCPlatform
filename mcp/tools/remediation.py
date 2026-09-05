"""Herramientas MCP: Acciones de remediación. Requieren scope `remediation:read`."""

from typing import Any

from client import GRCApiClient, GRCApiError
from schemas.enums import ActionStatus, Criticality

from ._util import error_payload


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def list_remediation_actions(
        status: ActionStatus | None = None,
        priority: Criticality | None = None,
        finding_id: str | None = None,
        overdue: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Lista las acciones de remediación, con filtros de estado, prioridad y vencimiento.

        Args:
            status: Estado de la acción.
            priority: Prioridad de la acción (low, medium, high, critical).
            finding_id: UUID del hallazgo al que pertenece la acción.
            overdue: true=solo acciones con la fecha límite vencida y aún no completadas.
            page: Número de página (empieza en 1).
            page_size: Resultados por página (máximo 100).
        """
        try:
            return await client.list_remediation_actions(
                status=status, priority=priority, finding_id=finding_id, overdue=overdue, page=page, page_size=page_size
            )
        except GRCApiError as exc:
            return error_payload(exc)
