"""Normalización de errores de la API para integraciones externas (Fase 9).

Toda excepción HTTP explícita (`HTTPException`, lanzada ~150 veces en los
routers existentes con `detail="mensaje en español"`) y cualquier error no
controlado se devuelven siempre con la misma forma:

    {"detail": {"code": "RESOURCE_NOT_FOUND", "message": "Riesgo no encontrado."}}

en vez de un `detail` de texto plano. Esto permite a un cliente de
integración (MCP u otro) distinguir el tipo de error por código sin
depender de comparar el texto del mensaje (que además está en español).

Deliberadamente NO se toca el formato de `RequestValidationError` (los 422
automáticos de Pydantic por payload inválido): son ya una lista estructurada
por campo definida por FastAPI/Pydantic, estándar y bien soportada por
herramientas de generación de clientes; envolverla también habría mezclado
"error de esquema" con "error de negocio" sin aportar valor real. Ver
docs/API.md para la distinción documentada.

Los errores no controlados (código 500) nunca devuelven la traza, el SQL ni
ninguna ruta interna al cliente: se registran con `logger.exception` en el
servidor y se responde un mensaje genérico.
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("grcplatform")

_CODIGOS_POR_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


def _codigo_para(status_code: int) -> str:
    return _CODIGOS_POR_STATUS.get(status_code, "ERROR")


def registrar_manejadores_de_error(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _manejar_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        detalle = exc.detail
        if isinstance(detalle, dict) and "code" in detalle and "message" in detalle:
            cuerpo = detalle
        else:
            cuerpo = {"code": _codigo_para(exc.status_code), "message": str(detalle)}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": cuerpo},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def _manejar_excepcion_no_controlada(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error no controlado en %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "INTERNAL_ERROR",
                    "message": "Ha ocurrido un error interno. Inténtalo de nuevo.",
                }
            },
        )
