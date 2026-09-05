# Servidor MCP de GRCPlatform

**El servidor MCP no accede directamente a PostgreSQL. Todas las operaciones
pasan por la API REST de GRCPlatform.**

Esto no es una preferencia de estilo: es una regla arquitectónica obligatoria
(ver [ARCHITECTURE.md](ARCHITECTURE.md) para el razonamiento completo) y está
verificada automáticamente en
`mcp/tests/test_no_direct_db_access.py` — ningún módulo de `mcp/` importa
`sqlalchemy` ni modelos del backend, `mcp/requirements.txt` no incluye ningún
driver de PostgreSQL, y ningún módulo lee `DATABASE_URL`.

## Arquitectura

```
Claude / cliente MCP
        │  (protocolo MCP: stdio o streamable-http)
        ▼
  Servidor MCP (mcp/server.py)
        │  httpx + X-API-Key
        ▼
  REST API de GRCPlatform (FastAPI)
        │  Actor / require_access (autenticación + RBAC + scopes)
        ▼
  Multi-tenancy + lógica de negocio
        │
        ▼
  AuditLog (evento mcp_tool_call)
        │
        ▼
     PostgreSQL
```

El servidor MCP es, desde el punto de vista del backend, un cliente HTTP más
— exactamente como el frontend, salvo que se autentica con una API key
(`X-API-Key`) en vez de un JWT de usuario. Nunca recalcula lógica de negocio
(el Compliance Score, los niveles de riesgo, los estados derivados de
proveedor, etc. se calculan siempre en el backend); las herramientas MCP solo
traducen la llamada de una herramienta a una petición HTTP y su respuesta de
vuelta a un resultado estructurado.

## Transporte

| Transporte | Uso | Configuración |
|---|---|---|
| `stdio` | Desarrollo local / Claude Desktop, que lanza `python server.py` como subproceso | `MCP_TRANSPORT=stdio` (por defecto) |
| `streamable-http` | Despliegue en Docker (`grcplatform-mcp`), expuesto como servicio HTTP independiente | `MCP_TRANSPORT=streamable-http` |

`mcp/server.py` decide el transporte a partir de `MCP_TRANSPORT` y, para
`streamable-http`, escucha en `0.0.0.0:${MCP_HTTP_PORT}` (por defecto 8001),
en la ruta `/mcp`.

## Configuración (variables de entorno)

Ninguna se hardcodea; `mcp/config.py` las lee todas y falla al arrancar con un
mensaje claro si falta `GRC_MCP_TOKEN`:

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `GRC_MCP_TOKEN` | Sí | — | Secreto de la credencial de integración (`grc_...`), creada vía `POST /api/v1/integration-tokens`. |
| `GRC_API_BASE_URL` | No | `http://localhost:8000` | Base URL de la REST API. En Docker: `http://backend:8000`. |
| `MCP_TRANSPORT` | No | `stdio` | `stdio` o `streamable-http`. |
| `MCP_HTTP_PORT` | No | `8001` | Puerto de escucha cuando el transporte es `streamable-http`. |

## Autenticación y autorización

El servidor MCP se autentica ante la REST API con **una única credencial de
integración** (una API key con un conjunto fijo de scopes), igual que
cualquier otro cliente de integración — no hay un usuario humano detrás de
cada llamada. Esa credencial:

- Pertenece a **una** organización (aislamiento multi-tenant, ver más abajo).
- Tiene un conjunto de **scopes** explícito y auditable
  (`risks:read`, `risks:write`, `controls:read`, `evidence:read`,
  `findings:read`, `remediation:read`, `vendors:read`, `dashboard:read`,
  `compliance:read`). Una herramienta MCP que necesite un scope no concedido
  recibe `403` de la REST API — la herramienta lo devuelve como un resultado
  estructurado (`{"error": true, "status_code": 403, ...}`), nunca como una
  excepción no controlada.
- Puede revocarse en cualquier momento (`DELETE /api/v1/integration-tokens/{id}`)
  sin tocar el servidor MCP: la siguiente llamada responde `401`.

Ver [API.md](API.md#credenciales-de-integración-api-keys) para el ciclo de
vida completo de una credencial.

## Multi-tenancy

Igual que un usuario humano, la credencial usada por el servidor MCP
pertenece a una única organización, fijada por el backend en el momento en
que un Admin la crea — nunca se acepta un `organization_id` del propio
servidor MCP ni de la herramienta. Un intento de leer un recurso de **otra**
organización (por ejemplo, pasando manualmente el UUID de un riesgo ajeno a
`get_risk`) responde `404`, nunca `403` — no se confirma ni se niega la
existencia del recurso. Verificado en
`backend/tests/test_mcp_server.py::test_get_risk_de_otra_organizacion_via_mcp_da_404_no_403`
y demostrado en vivo contra el contenedor Docker real (ver más abajo).

## Herramientas disponibles

| Herramienta | Scope | Descripción |
|---|---|---|
| `list_risks` | `risks:read` | Lista riesgos con búsqueda y filtros. |
| `get_risk` | `risks:read` | Detalle de un riesgo por UUID. |
| `create_risk` | `risks:write` | Crea un riesgo (único endpoint de escritura expuesto por MCP). |
| `list_controls` | `controls:read` | Lista controles con búsqueda y filtros. |
| `get_control` | `controls:read` | Detalle de un control. |
| `list_evidence` | `evidence:read` | Lista evidencias (solo metadatos, nunca el archivo). |
| `get_evidence` | `evidence:read` | Metadatos completos de una evidencia. |
| `list_findings` | `findings:read` | Lista hallazgos con búsqueda y filtros. |
| `list_remediation_actions` | `remediation:read` | Lista acciones de remediación. |
| `list_vendors` | `vendors:read` | Lista proveedores (TPRM) con búsqueda y filtros. |
| `get_vendor` | `vendors:read` | Detalle de un proveedor. |
| `get_dashboard_summary` | `dashboard:read` | KPIs del Dashboard GRC y Compliance Score global (reutiliza `/api/v1/dashboard/summary`, no recalcula nada). |
| `get_compliance_summary` | `compliance:read` | Estado de cumplimiento por control/categoría/framework (reutiliza `/api/v1/dashboard/compliance`). |
| `search_grc` | varios | Búsqueda unificada sobre riesgos/controles/evidencias/hallazgos/proveedores; una categoría sin scope se devuelve vacía con una nota, sin fallar la búsqueda completa. |

`create_risk` es deliberadamente la única herramienta de escritura: valida
todos los campos, respeta el scope `risks:write`, nunca acepta un
`organization_id` (se fija siempre por la credencial), genera un evento de
auditoría (`create_risk`) y devuelve el recurso creado. El score de riesgo y
su nivel los calcula siempre el backend.

Cada parámetro de cada herramienta tiene un tipo explícito (UUID como
`string`, enums como `Literal`, fechas como `string` `AAAA-MM-DD`, paginación
como `int`), generado automáticamente como JSON Schema por el SDK MCP a
partir de las anotaciones de tipo — visible en vivo vía `tools/list`. La
propia REST API **vuelve a validar todo de forma independiente** (doble capa
deliberada): un UUID mal formado o una página fuera de rango responden `422`
aunque el esquema MCP ya los describa como tales.

## Ejemplos de uso (flujos reales, no simulados)

Preguntas en lenguaje natural y la herramienta MCP que las resuelve, contra
la organización de demostración "Acme Security Labs":

- *"Muéstrame los riesgos críticos"* → `list_risks(level="critico")`.
- *"¿Cuál es el riesgo más crítico de fuga de datos?"* → `list_risks(search="fuga de datos")` seguido de `get_risk(risk_id=...)`.
- *"¿Cómo está el nivel de cumplimiento?"* → `get_compliance_summary()`.
- *"¿Qué proveedores críticos tienen revisiones próximas?"* → `list_vendors(criticality="critical", review_overdue=true)`.

Cada una de estas llamadas queda registrada en `AuditLog` como
`mcp_tool_call` (consultable vía `GET /api/v1/audit-logs?action=mcp_tool_call`)
y visible en los logs del contenedor `grcplatform-backend` como una petición
HTTP normal proveniente del contenedor `grcplatform-mcp`.

## Ejecución local (transporte stdio)

```bash
cd mcp
python -m venv .venv && .venv/Scripts/activate  # o source .venv/bin/activate
pip install -r requirements.txt
export GRC_MCP_TOKEN=grc_tu_secreto_real
export GRC_API_BASE_URL=http://localhost:8000
python server.py
```

Un cliente MCP (Claude Desktop, u otro) que lance este comando como
subproceso puede usar las herramientas inmediatamente.

## Ejecución en Docker (transporte streamable-http)

El servicio `mcp` de `docker-compose.yml` construye `mcp/Dockerfile` y expone
el puerto `8001`, dependiendo de que `backend` esté saludable. No recibe
`DATABASE_URL` ni ninguna credencial de PostgreSQL — solo `GRC_API_BASE_URL`,
`GRC_MCP_TOKEN`, `MCP_TRANSPORT` y `MCP_HTTP_PORT` (ver `.env.example`).

```bash
docker compose up -d mcp
curl -i -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"cliente","version":"1.0"}}}'
```

## Seguridad

- Nunca se registra el secreto de la credencial (`GRC_MCP_TOKEN`) en logs ni
  en `AuditLog` — solo su `integration_token_id` y su nombre.
- Doble capa de validación: el esquema de cada herramienta MCP y, de forma
  independiente, la propia REST API.
- Aislamiento multi-tenant idéntico al de un usuario humano (404, nunca 403,
  ante un recurso de otra organización).
- Rate limiting: **no implementado en esta fase.** No se ha añadido ninguna
  protección simulada; queda documentado como trabajo futuro (ver
  `docs/SECURITY.md`, sección "Pendiente"), previsiblemente a nivel de
  API key en `require_access()` una vez haya un caso de uso real que lo
  requiera (ninguna integración de producción activa todavía).

## Limitaciones conocidas

- Solo lectura salvo `create_risk`. Ampliar a otras entidades es
  intencionadamente un paso futuro, no de esta fase.
- `search_grc` es una búsqueda de texto simple (reutiliza el filtro `search`
  ya existente en cada listado), no full-text ni semántica.
- Sin streaming de resultados grandes: cada herramienta de listado respeta
  el mismo límite de `page_size` que la REST API (máximo 100).

## Ver también

- [API.md](API.md) — contrato completo de la REST API que consume este servidor.
- [ARCHITECTURE.md](ARCHITECTURE.md) — por qué esta arquitectura y no acceso directo a datos.
