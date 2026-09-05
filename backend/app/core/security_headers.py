"""Cabeceras de seguridad HTTP aplicadas a toda respuesta (Fase 10:
hardening). Cada cabecera mitiga una clase de ataque concreta contra el
navegador que consume esta API (el frontend, y cualquier otro cliente web):

- ``X-Content-Type-Options: nosniff`` — evita que el navegador reinterprete
  el `Content-Type` declarado (p. ej. tratar una evidencia subida como HTML
  ejecutable).
- ``X-Frame-Options: DENY`` — evita que la API (o `/docs`) se incruste en un
  `<iframe>` de otro origen (clickjacking).
- ``Referrer-Policy: strict-origin-when-cross-origin`` — no filtra rutas
  completas (que pueden incluir IDs) a orígenes externos.
- ``Permissions-Policy`` — desactiva APIs de navegador que esta API nunca
  necesita (geolocalización, cámara, micrófono).
- ``Content-Security-Policy`` — estricta para toda la API (que solo
  responde JSON, donde una CSP no tiene efecto real pero tampoco hace daño
  tenerla) y algo más permisiva únicamente en `/docs` y `/redoc`: el HTML
  que genera FastAPI para Swagger UI/ReDoc incluye un `<script>` inline
  para arrancar la interfaz, así que esas dos rutas necesitan
  `'unsafe-inline'` en `script-src` para poder ejecutarlo — verificado en
  un navegador real tras introducir la cabecera (sin esta excepción,
  `/docs` queda en blanco por bloqueo de CSP).
- ``Strict-Transport-Security`` — solo en producción (`ENVIRONMENT=production`),
  donde TLS lo termina el reverse proxy (ver docs/DEPLOYMENT.md); en
  desarrollo, sin HTTPS, esta cabecera no tendría sentido y podría causar
  confusión en el navegador si se prueba luego en local con HTTP.

No se introduce como middleware de terceros: es simple y explícito a
propósito, evitando una dependencia nueva para un puñado de cabeceras
estáticas."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.core.config import settings

_CSP_API = "default-src 'none'; frame-ancestors 'none'"

_CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

_RUTAS_DOCS = {"/docs", "/redoc", "/docs/oauth2-redirect"}


def registrar_cabeceras_de_seguridad(app: FastAPI) -> None:
    @app.middleware("http")
    async def _anadir_cabeceras(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            _CSP_DOCS if request.url.path in _RUTAS_DOCS else _CSP_API
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
