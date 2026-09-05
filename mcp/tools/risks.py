"""Herramientas MCP: Riesgos. Requieren scope `risks:read` (lectura) o
`risks:write` (creación) en la credencial de integración configurada."""

from typing import Any

from client import GRCApiClient, GRCApiError
from schemas.enums import RiskLevel, RiskStatus, RiskTreatment

from ._util import error_payload


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def list_risks(
        search: str | None = None,
        level: RiskLevel | None = None,
        status: RiskStatus | None = None,
        treatment: RiskTreatment | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Lista los riesgos de la organización, con búsqueda y filtros.

        Args:
            search: Texto a buscar en el título o la descripción del riesgo.
            level: Nivel de riesgo inherente (bajo, medio, alto, critico).
            status: Estado del riesgo.
            treatment: Estrategia de tratamiento del riesgo.
            page: Número de página (empieza en 1).
            page_size: Resultados por página (máximo 100).
        """
        try:
            return await client.list_risks(
                search=search, level=level, status=status, treatment=treatment, page=page, page_size=page_size
            )
        except GRCApiError as exc:
            return error_payload(exc)

    @mcp.tool()
    async def get_risk(risk_id: str) -> dict[str, Any]:
        """Obtiene el detalle completo de un riesgo por su identificador (UUID).

        Args:
            risk_id: UUID del riesgo, tal como aparece en `list_risks`.
        """
        try:
            return await client.get_risk(risk_id)
        except GRCApiError as exc:
            return error_payload(exc)

    @mcp.tool()
    async def create_risk(
        title: str,
        category: str,
        threat: str,
        vulnerability: str,
        likelihood: int,
        impact: int,
        treatment: RiskTreatment,
        owner: str,
        review_date: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Crea un nuevo riesgo en la organización de la credencial de integración.

        El score de riesgo (likelihood × impact) y su nivel se calculan
        siempre en el backend; esta herramienta nunca puede fijarlos
        directamente. Requiere el scope `risks:write`.

        Args:
            title: Título breve del riesgo.
            category: Categoría del riesgo (p. ej. Ciberseguridad).
            threat: Amenaza que origina el riesgo.
            vulnerability: Vulnerabilidad que la amenaza explotaría.
            likelihood: Probabilidad, de 1 (muy baja) a 5 (muy alta).
            impact: Impacto, de 1 (muy bajo) a 5 (muy alto).
            treatment: Estrategia de tratamiento (mitigate, avoid, transfer, accept).
            owner: Responsable del riesgo.
            review_date: Fecha de próxima revisión, formato AAAA-MM-DD.
            description: Descripción opcional del riesgo.
        """
        try:
            return await client.create_risk(
                {
                    "title": title,
                    "description": description,
                    "category": category,
                    "threat": threat,
                    "vulnerability": vulnerability,
                    "likelihood": likelihood,
                    "impact": impact,
                    "treatment": treatment,
                    "owner": owner,
                    "review_date": review_date,
                }
            )
        except GRCApiError as exc:
            return error_payload(exc)
