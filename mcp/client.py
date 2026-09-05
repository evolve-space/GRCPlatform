"""Cliente HTTP hacia la REST API de GRCPlatform.

Este es el ÚNICO punto de acceso a los datos de GRCPlatform desde el
servidor MCP. No existe ninguna importación de ``sqlalchemy`` ni de los
modelos del backend (``app.models``) en todo el paquete ``mcp/`` — el
servidor MCP se comporta exactamente como cualquier otro cliente externo de
la API, autenticado con una credencial de integración (API key), nunca con
una conexión directa a PostgreSQL.

Nota de imports: los módulos de este directorio se importan de forma
ABSOLUTA (``from config import ...``, no ``from .config import ...``)
porque el contenedor Docker copia el CONTENIDO de ``mcp/`` directamente a
``/app`` (mismo patrón que ``backend/`` y ``frontend/``), quedando
``client.py``/``config.py``/``server.py`` como módulos sueltos en la raíz
del `sys.path`, no dentro de un paquete llamado ``mcp``. Esto es deliberado:
si este directorio se importara como paquete ``mcp``, colisionaría con el
SDK oficial ``mcp`` (PyPI) del que depende ``server.py``.
"""

from __future__ import annotations

from typing import Any, Self

import httpx

from config import McpSettings


class GRCApiError(Exception):
    """Error devuelto por la REST API, ya normalizado (Fase 9: `{code, message}`)."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[{status_code} {code}] {message}")


def _extraer_error(response: httpx.Response) -> GRCApiError:
    try:
        cuerpo = response.json()
        detalle = cuerpo.get("detail")
    except ValueError:
        detalle = None

    if isinstance(detalle, dict):
        return GRCApiError(response.status_code, detalle.get("code", "ERROR"), detalle.get("message", "Error"))
    if isinstance(detalle, str):
        return GRCApiError(response.status_code, "ERROR", detalle)
    if isinstance(detalle, list):
        mensajes = "; ".join(str(item.get("msg", item)) for item in detalle)
        return GRCApiError(response.status_code, "VALIDATION_ERROR", mensajes or "Error de validación.")
    return GRCApiError(response.status_code, "ERROR", "Error desconocido de la API de GRCPlatform.")


class GRCApiClient:
    """Cliente asíncrono, autenticado con API key (`X-API-Key`), hacia
    `/api/v1/...`. Cada método corresponde 1:1 a un endpoint REST real
    (nunca recalcula lógica de negocio del lado del MCP)."""

    def __init__(self, settings: McpSettings, *, transport: httpx.AsyncBaseTransport | None = None):
        # `transport` solo se usa en tests (p. ej. `httpx.ASGITransport` para
        # llamar a la app FastAPI real en proceso, sin un socket TCP real);
        # en producción es siempre None y httpx abre una conexión real por
        # `base_url`.
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url,
            headers={"X-API-Key": settings.api_token},
            timeout=15.0,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        limpio = {k: v for k, v in (params or {}).items() if v is not None}
        response = await self._client.get(path, params=limpio)
        if response.status_code >= 400:
            raise _extraer_error(response)
        result: dict[str, Any] = response.json()
        return result

    async def _post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(path, json=json_body)
        if response.status_code >= 400:
            raise _extraer_error(response)
        result: dict[str, Any] = response.json()
        return result

    # --- Riesgos ---

    async def list_risks(
        self,
        *,
        search: str | None = None,
        level: str | None = None,
        status: str | None = None,
        treatment: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/v1/risks",
            {"search": search, "level": level, "status": status, "treatment": treatment, "page": page, "page_size": page_size},
        )

    async def get_risk(self, risk_id: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/risks/{risk_id}")

    async def create_risk(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/api/v1/risks", payload)

    # --- Controles ---

    async def list_controls(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/v1/controls",
            {"search": search, "category": category, "status": status, "page": page, "page_size": page_size},
        )

    async def get_control(self, control_id: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/controls/{control_id}")

    # --- Evidencias ---

    async def list_evidence(
        self,
        *,
        search: str | None = None,
        classification: str | None = None,
        status: str | None = None,
        evidence_type: str | None = None,
        expired: bool | None = None,
        expiring_within_days: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/v1/evidence",
            {
                "search": search,
                "classification": classification,
                "status": status,
                "evidence_type": evidence_type,
                "expired": expired,
                "expiring_within_days": expiring_within_days,
                "page": page,
                "page_size": page_size,
            },
        )

    async def get_evidence(self, evidence_id: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/evidence/{evidence_id}")

    # --- Hallazgos ---

    async def list_findings(
        self,
        *,
        search: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        finding_type: str | None = None,
        overdue: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/v1/findings",
            {
                "search": search,
                "severity": severity,
                "status": status,
                "finding_type": finding_type,
                "overdue": overdue,
                "page": page,
                "page_size": page_size,
            },
        )

    # --- Acciones de remediación ---

    async def list_remediation_actions(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        finding_id: str | None = None,
        overdue: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/v1/remediation-actions",
            {
                "status": status,
                "priority": priority,
                "finding_id": finding_id,
                "overdue": overdue,
                "page": page,
                "page_size": page_size,
            },
        )

    # --- Proveedores ---

    async def list_vendors(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        criticality: str | None = None,
        due_diligence_status: str | None = None,
        review_overdue: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._get(
            "/api/v1/vendors",
            {
                "search": search,
                "status": status,
                "criticality": criticality,
                "due_diligence_status": due_diligence_status,
                "review_overdue": review_overdue,
                "page": page,
                "page_size": page_size,
            },
        )

    async def get_vendor(self, vendor_id: str) -> dict[str, Any]:
        return await self._get(f"/api/v1/vendors/{vendor_id}")

    # --- Dashboard / Compliance ---

    async def get_dashboard_summary(self) -> dict[str, Any]:
        return await self._get("/api/v1/dashboard/summary")

    async def get_compliance_summary(
        self, *, framework_id: str | None = None, category: str | None = None
    ) -> dict[str, Any]:
        return await self._get("/api/v1/dashboard/compliance", {"framework_id": framework_id, "category": category})
