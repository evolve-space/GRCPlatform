# Arquitectura de GRCPlatform

## Dos caminos, una sola fuente de verdad

GRCPlatform tiene dos clientes de su lógica de negocio — el frontend web y el
servidor MCP — y ambos atraviesan **exactamente el mismo camino** hasta
PostgreSQL. Ninguno de los dos tiene un atajo propio:

```
┌─────────────┐        ┌──────────────┐
│   Frontend   │        │  Servidor MCP │
│  (React/TS)  │        │  (mcp/*.py)   │
└──────┬───────┘        └──────┬───────┘
       │ JWT                   │ API key (X-API-Key)
       │ (Authorization)       │
       ▼                       ▼
┌─────────────────────────────────────────┐
│         REST API — FastAPI               │
│  Actor / require_access                  │
│  (autenticación + RBAC/scopes)           │
├─────────────────────────────────────────┤
│         Multi-tenancy                    │
│  organization_id derivado del actor,      │
│  nunca del cliente                       │
├─────────────────────────────────────────┤
│         Lógica de negocio                 │
│  (risk scoring, Compliance Score,         │
│   estados derivados, validaciones)        │
├─────────────────────────────────────────┤
│         AuditLog                          │
│  (evento por cada operación sensible)     │
└──────────────────┬──────────────────────┘
                    ▼
              PostgreSQL
```

No hay una segunda copia de la lógica de negocio, ni una segunda ruta de
autorización, ni una conexión a base de datos que no pase por este camino.
Un cambio en el cálculo del Compliance Score, en una regla de RBAC o en el
aislamiento multi-tenant se aplica automáticamente a los dos clientes, porque
ambos llaman al mismo código.

## Por qué el servidor MCP no accede directamente a PostgreSQL

Esta es una decisión arquitectónica deliberada — no una limitación técnica —
y es obligatoria en todo el proyecto: **`mcp/` nunca importa `sqlalchemy` ni
los modelos del backend (`app.models`), y no recibe `DATABASE_URL`.**
Verificado automáticamente en `mcp/tests/test_no_direct_db_access.py`.

Razones:

1. **Una sola implementación de las reglas de negocio.** El Compliance
   Score, los niveles de riesgo, los estados derivados de vencimiento/
   revisión de proveedores, etc. viven en un único lugar (`app/core/...`).
   Si MCP consultara PostgreSQL directamente, tendría que reimplementar (y
   mantener sincronizada) toda esa lógica, o arriesgarse a mostrar datos
   inconsistentes con lo que ve un usuario humano en el mismo instante.

2. **Una sola implementación de la autorización.** RBAC por rol (humano) y
   por scope (integración) conviven en `require_access()`. Un acceso
   directo a la base de datos no tiene "RBAC": tendría que reimplementarse
   también ahí, duplicando la superficie de fallo de seguridad más
   sensible del sistema.

3. **Aislamiento multi-tenant no negociable.** Toda fila relevante tiene
   `organization_id`, pero la garantía real no es la columna — es que
   *cada consulta* la filtra correctamente. Eso ya está resuelto, probado y
   auditado en la capa REST; un segundo cliente con acceso a SQL crudo sería
   un segundo lugar donde ese filtro puede olvidarse.

4. **Auditoría centralizada y garantizada.** `mcp_tool_call` se registra
   dentro de `require_access()`, así que **toda** llamada autenticada por
   API key queda auditada por construcción, sin depender de que cada
   herramienta MCP recuerde llamar a `registrar_evento`. Un acceso directo a
   PostgreSQL no pasa por ahí: cualquier operación quedaría sin rastro.

5. **Superficie de ataque reducida.** El contenedor `grcplatform-mcp` no
   tiene ninguna credencial de PostgreSQL ni el driver instalado (verificado
   en Docker: `docker compose exec mcp env` no expone `DATABASE_URL`, y
   `docker compose exec mcp pip list` no incluye `sqlalchemy`/`psycopg`/
   `asyncpg`). Si el servidor MCP se viera comprometido, el atacante hereda
   como mucho los scopes de una credencial de integración — nunca acceso de
   lectura/escritura arbitrario a la base de datos completa.

6. **El servidor MCP es, por diseño, un cliente de integración más.**
   Tratarlo exactamente igual que cualquier futura integración externa
   (un SIEM, una herramienta de terceros) evita crear una categoría
   especial de "cliente privilegiado" solo para la IA.

La única desventaja aceptada es una latencia adicional (un salto HTTP más
respecto a hablar con PostgreSQL directamente), irrelevante para el patrón de
uso de MCP (consultas puntuales, no procesamiento masivo de datos).

## Componentes

| Componente | Responsabilidad | No hace |
|---|---|---|
| `frontend/` | UI en español, consume la REST API con JWT | No contiene lógica de negocio ni de autorización real (solo UX) |
| `backend/app/` | REST API, lógica de negocio, RBAC/scopes, multi-tenancy, AuditLog, acceso a PostgreSQL | No conoce el protocolo MCP |
| `mcp/` | Traduce herramientas MCP a peticiones HTTP autenticadas con API key | No accede a PostgreSQL, no reimplementa lógica de negocio, no reimplementa RBAC |
| `postgres` (contenedor) | Persistencia | Solo alcanzable por `backend`; ni `frontend` ni `mcp` tienen sus credenciales |

## Despliegue (Docker Compose)

```
postgres  ←──  backend  ←──  frontend
                 ▲
                 │ HTTP (X-API-Key)
                 │
                mcp
```

`mcp` depende de `backend` (`depends_on: backend, condition: service_healthy`)
y no tiene ninguna dependencia ni variable de entorno relacionada con
`postgres`. Cada servicio tiene su propio `Dockerfile` y su propio conjunto
de dependencias — el conflicto real de versiones detectado durante el
desarrollo entre el SDK MCP y las dependencias fijadas del backend (ver
`backend/tests/test_mcp_server.py`) es, de hecho, una confirmación práctica
de que ambos componentes están correctamente desacoplados: no comparten
entorno de ejecución ni en tests ni en producción.

## Ver también

- [API.md](API.md) — contrato de la REST API.
- [MCP.md](MCP.md) — el servidor MCP en detalle.
- [SECURITY.md](SECURITY.md) — modelo de seguridad completo.
