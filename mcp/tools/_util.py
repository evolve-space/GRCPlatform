"""Utilidad compartida por todas las herramientas MCP: convierte un error
de la REST API (`GRCApiError`) en un resultado estructurado que la
herramienta puede devolver sin propagar una excepción cruda ni una traza al
cliente MCP. Cada herramienta decide si un error concreto (p. ej. 404) debe
comunicarse como "no encontrado" en lenguaje natural."""

from typing import Any

from client import GRCApiError


def error_payload(exc: GRCApiError) -> dict[str, Any]:
    return {"error": True, "status_code": exc.status_code, "code": exc.code, "message": exc.message}
