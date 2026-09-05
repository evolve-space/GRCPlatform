# API REST de GRCPlatform

> Documento vivo. Cubre los aspectos transversales de la API (autenticación,
> paginación, errores, credenciales de integración y scopes) introducidos o
> normalizados en la Fase 9. El listado completo de endpoints por módulo
> (Activos, Riesgos, Controles, Evidencias, Hallazgos, Proveedores, Dashboard,
> etc.) está en el [README](../README.md); aquí no se repite.

## Documentación interactiva (OpenAPI)

FastAPI genera la especificación OpenAPI automáticamente a partir del propio
código (rutas, esquemas Pydantic, dependencias de seguridad):

- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- JSON crudo: `GET /openapi.json`

Todo endpoint, parámetro, esquema de petición/respuesta y los dos esquemas de
seguridad (`HTTPBearer` para JWT, `APIKeyHeader` para `X-API-Key`) quedan
documentados sin mantenimiento manual adicional.

## Autenticación: dos identidades, un mismo backend

GRCPlatform distingue dos tipos de **actor** (`app/api/deps.py`, clase
`Actor`), pero el mismo endpoint, la misma autorización por organización y el
mismo registro de auditoría se aplican a ambos:

| | Humano (frontend) | Integración (MCP u otro cliente) |
|---|---|---|
| Credencial | JWT (`Authorization: Bearer ...`) | API key (`X-API-Key: grc_...`) |
| Obtención | `POST /api/v1/auth/login` | `POST /api/v1/integration-tokens` (rol Admin) |
| Autorización | Rol (`admin`/`grc_manager`/`analyst`/`viewer`) | Scopes de la credencial |
| Organización | `User.organization_id` | `IntegrationToken.organization_id` |
| Auditoría | `AuditLog.user_id` | `AuditLog.integration_token_id` |

Un endpoint puede aceptar solo JWT (la mayoría, sin cambios respecto a fases
anteriores), o ambos (los que necesita el servidor MCP: listados/detalle de
riesgos, controles, evidencias, hallazgos, acciones, proveedores, resumen de
dashboard, cumplimiento, y creación de riesgos). Nunca al revés: no hay
ningún endpoint que acepte API key pero no JWT.

## Paginación

Todos los listados devuelven el mismo sobre:

```json
{
  "items": [ ... ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

`page` empieza en 1. `page_size` tiene un máximo (100 en la mayoría de
listados) validado por FastAPI/Pydantic: un valor fuera de rango responde
`422` antes de tocar la base de datos, nunca se trunca silenciosamente.

## Formato de error normalizado

Desde la Fase 9, toda respuesta de error basada en `HTTPException` (401, 403,
404, 409, 422 de negocio, 500, etc.) tiene esta forma, sin excepción:

```json
{
  "detail": {
    "code": "NOT_FOUND",
    "message": "Riesgo no encontrado."
  }
}
```

- `code` es una cadena estable en mayúsculas (`UNAUTHORIZED`, `FORBIDDEN`,
  `NOT_FOUND`, `CONFLICT`, `VALIDATION_ERROR`, `INTERNAL_ERROR`, ...),
  pensada para lógica de cliente (`if code == "NOT_FOUND"`).
- `message` es un texto en español pensado para mostrarse tal cual al
  usuario o al modelo que invoca una herramienta MCP.
- **Nunca** incluye traza de pila, SQL, rutas de archivo del servidor ni
  ningún secreto. Implementado en `app/core/errors.py` mediante manejadores
  globales de FastAPI (`registrar_manejadores_de_error`), sin tocar los
  puntos individuales donde se lanza `HTTPException`.

**Excepción deliberada**: los errores nativos de validación de Pydantic/
FastAPI (`422` por un campo con tipo o formato incorrecto antes de llegar a
la lógica de negocio) mantienen el formato nativo de FastAPI
(`{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`), no el formato
`{code, message}`. Motivo: es un mecanismo distinto (validación de esquema,
no una decisión de negocio), ya es razonablemente consumible por máquina, y
normalizarlo habría exigido tocar/probar de nuevo cientos de casos de
validación sin aportar valor real. El cliente MCP (`mcp/client.py`) entiende
ambos formatos.

## Filtros

Cada listado admite sus propios filtros por query string (ver README y
Swagger para el detalle por módulo). Todos siguen la misma convención:

- Los filtros de enum (`status`, `level`, `criticality`, `treatment`, ...)
  usan los mismos `Enum`/`StrEnum` que los modelos — un valor no válido
  responde `422`.
- `search` es una búsqueda de texto simple (no full-text) sobre los campos
  relevantes de cada entidad (título, código, nombre...).
- Los filtros de fecha/vencimiento (`overdue`, `expired`,
  `expiring_within_days`, `review_overdue`, ...) se calculan siempre en el
  backend contra la fecha del servidor; nunca se aceptan como valores fijos
  del cliente.

## Credenciales de integración (API keys)

`POST/GET/DELETE /api/v1/integration-tokens` — gestión de credenciales para
clientes no humanos (el servidor MCP u otras integraciones futuras).
Restringido a JWT humano: **Admin** puede crear/revocar, **Admin** y
**GRC Manager** pueden listar; **Analyst** y **Viewer** no tienen acceso.

- `POST` crea una credencial y devuelve el **secreto en texto plano una única
  vez**, en el campo `token` (formato `grc_<43 caracteres aleatorios>`).
  GRCPlatform nunca vuelve a mostrarlo: solo se persiste su hash SHA-256
  (`token_hash`) y un prefijo de 12 caracteres (`token_prefix`, solo para que
  un humano reconozca visualmente cuál es cuál en un listado).
- `GET` lista las credenciales de la organización (metadatos únicamente:
  nombre, prefijo, scopes, estado, fechas — nunca el secreto).
- `DELETE /{id}` revoca (`revoked_at`, `is_active=False`); una credencial
  revocada responde `401` en cualquier endpoint, inmediatamente.
- Se usa como cualquier otra API key: cabecera `X-API-Key: <secreto>` en
  cada petición.

### Scopes (mínimo privilegio)

Lista cerrada, validada por el backend (`app/models/integration_token.py`,
`VALID_SCOPES`) — una credencial nunca puede "inventarse" un permiso:

`risks:read`, `risks:write`, `controls:read`, `evidence:read`,
`findings:read`, `remediation:read`, `vendors:read`, `dashboard:read`,
`compliance:read`, `audit:read`.

Una petición con una credencial válida pero sin el scope necesario responde
`403 Forbidden` con un mensaje que nombra el scope que falta. Una credencial
solo puede tener los scopes que se le asignaron explícitamente al crearla (o
los que un Admin decida al rotarla — no hay edición parcial, solo
creación/revocación, para mantener el modelo simple y auditable).

### Aislamiento multi-tenant, también para integraciones

Una credencial de integración pertenece a una única organización
(`IntegrationToken.organization_id`, fijada por el backend a partir del JWT
del Admin que la crea — nunca aceptada del cliente). Con ella, un intento de
acceder a un recurso de **otra** organización responde `404` — nunca `403` —
exactamente igual que para un usuario humano, incluso pasando manualmente un
UUID válido de esa otra organización. Cubierto por
`backend/tests/test_integration_auth.py` y
`backend/tests/test_mcp_server.py`.

### Ejemplo de petición autenticada con API key

```bash
curl -H "X-API-Key: grc_TU_SECRETO" \
     "http://localhost:8000/api/v1/risks?level=critico&page=1&page_size=20"
```

```json
{
  "items": [
    {
      "id": "62248af7-7154-4f5b-8482-ff7cb35f6d5f",
      "title": "Fuga de datos de clientes por credenciales débiles",
      "inherent_level": "critico",
      "status": "in_treatment"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

## Registro de auditoría de integraciones

Cada petición autenticada con API key genera automáticamente un evento
`mcp_tool_call` en `AuditLog` (centralizado en `require_access()`,
`app/api/deps.py` — no depende de que cada endpoint recuerde auditar). El
evento registra: la credencial usada (`integration_token_id`, nunca
`user_id`), el scope exigido, método y ruta, organización, IP de origen y
marca de tiempo. Consultable vía `GET /api/v1/audit-logs` igual que el resto
de eventos (ver [SECURITY.md](SECURITY.md)).

## Ver también

- [MCP.md](MCP.md) — el servidor MCP como cliente de esta API.
- [ARCHITECTURE.md](ARCHITECTURE.md) — por qué MCP nunca accede a PostgreSQL
  directamente.
- [SECURITY.md](SECURITY.md) — modelo de seguridad completo.
