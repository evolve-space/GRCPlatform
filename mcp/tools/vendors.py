"""Herramientas MCP: Proveedores (TPRM). Requieren scope `vendors:read`."""

from typing import Any

from client import GRCApiClient, GRCApiError
from schemas.enums import Criticality, VendorDueDiligenceStatus, VendorStatus

from ._util import error_payload


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def list_vendors(
        search: str | None = None,
        status: VendorStatus | None = None,
        criticality: Criticality | None = None,
        due_diligence_status: VendorDueDiligenceStatus | None = None,
        review_overdue: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Lista los proveedores de la organización, con búsqueda y filtros.

        Args:
            search: Texto a buscar en código, nombre o razón social.
            status: Estado de la relación con el proveedor.
            criticality: Criticidad del proveedor (low, medium, high, critical).
            due_diligence_status: Estado de la evaluación de due diligence.
            review_overdue: true=solo proveedores con la revisión de seguridad vencida.
            page: Número de página (empieza en 1).
            page_size: Resultados por página (máximo 100).
        """
        try:
            return await client.list_vendors(
                search=search,
                status=status,
                criticality=criticality,
                due_diligence_status=due_diligence_status,
                review_overdue=review_overdue,
                page=page,
                page_size=page_size,
            )
        except GRCApiError as exc:
            return error_payload(exc)

    @mcp.tool()
    async def get_vendor(vendor_id: str) -> dict[str, Any]:
        """Obtiene el detalle de un proveedor: ficha, contrato, due diligence,
        y sus riesgos, evidencias, hallazgos y acciones de remediación
        relacionados.

        Args:
            vendor_id: UUID del proveedor, tal como aparece en `list_vendors`.
        """
        try:
            return await client.get_vendor(vendor_id)
        except GRCApiError as exc:
            return error_payload(exc)
