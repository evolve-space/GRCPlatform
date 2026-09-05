"""Herramientas MCP: Dashboard y Compliance Score.

Ambas llaman directamente a los endpoints REST ya existentes
(`/api/v1/dashboard/summary`, `/api/v1/dashboard/compliance`) — el MCP
nunca recalcula el Compliance Score ni ninguna agregación por su cuenta; la
lógica de negocio permanece siempre en el backend."""

from typing import Any

from client import GRCApiClient, GRCApiError

from ._util import error_payload


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def get_dashboard_summary() -> dict[str, Any]:
        """Obtiene el resumen del Dashboard GRC: KPIs principales (riesgos
        críticos/altos, hallazgos abiertos, acciones vencidas, evidencias
        próximas a caducar, proveedores críticos), el Compliance Score
        global con su desglose, y la lista priorizada "Requiere atención".
        Requiere el scope `dashboard:read`.
        """
        try:
            return await client.get_dashboard_summary()
        except GRCApiError as exc:
            return error_payload(exc)

    @mcp.tool()
    async def get_compliance_summary(
        framework_id: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Obtiene el estado de cumplimiento: distribución de controles por
        estado y categoría, controles implementados sin evidencia vigente,
        el Compliance Score global (con desglose por Controles/Evidencias/
        Hallazgos/Remediación) y el score específico de cada framework de
        cumplimiento (p. ej. ISO 27001, NIST CSF). Requiere el scope
        `compliance:read`.

        Args:
            framework_id: UUID de un framework para acotar el desglose de
                controles a él (opcional; el Compliance Score global y la
                lista de scores por framework no cambian con este filtro).
            category: Categoría de control para acotar el desglose (opcional).
        """
        try:
            return await client.get_compliance_summary(framework_id=framework_id, category=category)
        except GRCApiError as exc:
            return error_payload(exc)
