"""Herramientas MCP: Evidencias. Requieren scope `evidence:read`.

Nunca exponen el contenido binario del archivo — solo metadatos (nombre,
SHA-256, MIME, tamaño, clasificación, fechas, relaciones), igual que
`EvidenceRead`/`EvidenceDetailRead` en la REST API."""

from typing import Any

from client import GRCApiClient, GRCApiError
from schemas.enums import DataClassification
from schemas.enums import EvidenceStatus as EvidenceStatusLiteral

from ._util import error_payload


def register(mcp: Any, client: GRCApiClient) -> None:
    @mcp.tool()
    async def list_evidence(
        search: str | None = None,
        classification: DataClassification | None = None,
        status: EvidenceStatusLiteral | None = None,
        evidence_type: str | None = None,
        expired: bool | None = None,
        expiring_within_days: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Lista evidencias, con búsqueda y filtros de clasificación, estado y caducidad.

        Args:
            search: Texto a buscar en nombre, descripción o archivo.
            classification: Clasificación de datos de la evidencia.
            status: Estado almacenado (active, archived) — no confundir con
                la caducidad, que se deriva siempre de `expires_at`.
            evidence_type: Tipo de evidencia (p. ej. Política, Certificado).
            expired: true=solo caducadas, false=solo vigentes.
            expiring_within_days: Solo evidencias que caducan en los próximos N días.
            page: Número de página (empieza en 1).
            page_size: Resultados por página (máximo 100).
        """
        try:
            return await client.list_evidence(
                search=search,
                classification=classification,
                status=status,
                evidence_type=evidence_type,
                expired=expired,
                expiring_within_days=expiring_within_days,
                page=page,
                page_size=page_size,
            )
        except GRCApiError as exc:
            return error_payload(exc)

    @mcp.tool()
    async def get_evidence(evidence_id: str) -> dict[str, Any]:
        """Obtiene los metadatos completos de una evidencia: SHA-256, tipo
        MIME, tamaño, clasificación, fechas de recogida/caducidad y las
        entidades (controles, riesgos, activos, requisitos) a las que está
        vinculada. Nunca devuelve el contenido del archivo.

        Args:
            evidence_id: UUID de la evidencia, tal como aparece en `list_evidence`.
        """
        try:
            return await client.get_evidence(evidence_id)
        except GRCApiError as exc:
            return error_payload(exc)
