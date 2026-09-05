# GRCPlatform

> Nombre técnico/provisional del proyecto. La marca comercial definitiva aún no está decidida.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](backend/requirements.txt)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=white)](frontend/package.json)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](frontend/package.json)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](docker-compose.yml)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Backend tests](https://img.shields.io/badge/backend%20tests-365%20passing-brightgreen)](backend/tests)
[![MCP tests](https://img.shields.io/badge/MCP%20tests-15%20passing-brightgreen)](mcp/tests)
[![CI](https://img.shields.io/badge/CI-preparado%20%7C%20no%20ejecutado%20a%C3%BAn-lightgrey)](.github/workflows/ci.yml)

**Plataforma GRC (Gobierno, Riesgo y Cumplimiento) self-hosted**, con API
REST, RBAC multi-tenant, y una integración MCP real para consultar y operar
la plataforma desde Claude u otro cliente MCP — sin que la IA acceda nunca
directamente a la base de datos.

> **Estado: `v1.0` — Release Candidate.** Aplicación funcional completa,
> endurecida y con configuración de producción preparada y verificada en un
> entorno controlado. Ver [Seguridad](#seguridad-1) para qué está verificado
> y qué queda pendiente de validar sobre infraestructura pública real.

## Qué problema resuelve

Gestionar el riesgo y el cumplimiento de una organización implica coordinar
piezas que casi siempre viven separadas: un inventario de activos en una
hoja de cálculo, los riesgos en otra, las evidencias de auditoría en una
carpeta compartida, los hallazgos de la última revisión en un documento de
Word, y las acciones correctivas en el correo. Nada está conectado, nadie
tiene una vista real del estado de cumplimiento, y demostrarlo ante una
auditoría es un ejercicio manual y propenso a errores.

GRCPlatform es un **laboratorio/plataforma GRC self-hosted** que modela
esa realidad como un grafo de entidades relacionadas —activos, riesgos,
controles, marcos de cumplimiento, evidencias, hallazgos, acciones de
remediación y proveedores— con un **registro de auditoría inmutable** y un
**Compliance Score** calculado en tiempo real a partir de datos reales, no
de una cifra fijada a mano. Es un proyecto de portfolio profesional que
demuestra diseño de producto GRC y arquitectura de software de forma
conjunta: no solo qué debe hacer una plataforma de este tipo, sino cómo
construirla con garantías reales de seguridad y aislamiento multi-tenant.

## Ciclo GRC

```
   Activo
     │
     ▼
   Riesgo ──────► Control ──────► Evidencia
     │               │                │
     │               ▼                │
     │           Requisito             │
     │        (marco de cumplimiento)   │
     ▼                                 │
  Proveedor                            │
     │                                 │
     ▼                                 ▼
  Hallazgo ◄─────────────────────────────
     │
     ▼
  Acción de remediación
     │
     ▼
  Auditoría ──────► Compliance Score
```

Cada flecha es una relación real en el modelo de datos (no solo un
concepto): un riesgo se mitiga con controles, un control se demuestra con
evidencias, un control sin evidencia vigente o no implementado puede
originar un hallazgo, un hallazgo se cierra con una acción de remediación
asignada a un responsable y una fecha límite, un proveedor hereda su
propio riesgo mediante la misma entidad `Risk`, y cada paso queda escrito
en el registro de auditoría, que alimenta el Compliance Score global.

## Funcionalidades

### Gestión GRC

- **Activos** — inventario con criticidad y clasificación de datos.
- **Riesgos** — riesgo inherente y residual (likelihood × impact),
  tratamiento, vinculación a activos y controles.
- **Controles** y **Marcos de cumplimiento** (ISO 27001, NIST CSF de
  ejemplo) — requisitos, mapeo cruzado entre marcos.
- **Evidencias** — subida de archivos con validación, hash SHA-256,
  clasificación, caducidad.
- **Hallazgos** y **Acciones de remediación** — severidad, responsable,
  fecha límite, cierre controlado por el backend.
- **Proveedores (TPRM)** — criticidad, due diligence, contrato, riesgo
  compartido con la entidad `Risk` (sin motor de scoring duplicado).
- **Registro de auditoría** — inmutable, sin endpoints de escritura,
  distingue actor humano de actor de integración.
- **Dashboard GRC + Compliance Score** — todo calculado en tiempo real
  sobre PostgreSQL, nunca cifras fijas.

### Seguridad

Autenticación JWT + bcrypt, RBAC por rol, aislamiento multi-tenant
verificado (un recurso ajeno responde `404`, nunca `403`), API keys de
integración con scopes de mínimo privilegio y expiración/revocación, rate
limiting (login y API keys), validación de entrada en dos capas,
protección de archivos subidos (lista blanca, magic bytes, SHA-256),
cabeceras de seguridad HTTP, configuración de producción validada al
arrancar, contenedores no-root, y separación de servicios (frontend,
backend, MCP, base de datos). Detalle completo en
[docs/SECURITY.md](docs/SECURITY.md).

### API

REST API completa bajo `/api/v1`, documentada automáticamente con OpenAPI
(Swagger UI en `/docs`), con dos esquemas de autenticación (JWT para el
frontend, API key para integraciones) y autorización por rol/scope en
cada endpoint protegido.

### MCP (Model Context Protocol)

Un servidor MCP real (SDK oficial `mcp`) permite que Claude u otro cliente
MCP consulte y opere sobre GRCPlatform en lenguaje natural — 14
herramientas, mayoritariamente de lectura. La regla que gobierna todo el
diseño:

```
Claude → MCP Server → HTTP → REST API → Autorización/RBAC → PostgreSQL
```

**El servidor MCP nunca accede directamente a PostgreSQL.** Ver
[docs/MCP.md](docs/MCP.md) y [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Producción

Docker Compose + Nginx (reverse proxy y terminación HTTPS) + health
checks + backups con verificación de integridad + CI/CD preparado. Ver
[Producción](#producción-1) más abajo.

## Arquitectura

**En una frase, para alguien de GRC**: hay un único camino hacia los
datos, y todo el mundo lo comparte — la web y la integración con Claude
pasan exactamente por las mismas comprobaciones de seguridad, así que no
hay un "atajo" que las salte.

**Vista técnica**:

```
Navegador
   │
   ▼
 Nginx (HTTPS, producción)
   │
   ▼
 Frontend (React) ──────► REST API (FastAPI)
                                │
                                ▼
                          SQLAlchemy (ORM)
                                │
                                ▼
                           PostgreSQL

Claude / cliente MCP
   │
   ▼
 Servidor MCP (Python)
   │  HTTP + API key
   ▼
 REST API (FastAPI) ────► (mismo camino que arriba)
```

Frontend y servidor MCP son dos clientes distintos de la **misma** REST
API — ninguno tiene un acceso propio a PostgreSQL, ninguno reimplementa
autorización o lógica de negocio. Detalle y razonamiento completo en
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Seguridad

**Release Candidate v1.0**: preparado y verificado para producción en un
entorno controlado (Docker local, certificado de prueba), con
determinados controles operacionales pendientes de validación sobre
infraestructura pública real. No se presenta como "100% seguro" ni como
"production-ready sin limitaciones" — ver la categorización exacta
(verificado / no verificado / pendiente) en
[docs/SECURITY.md](docs/SECURITY.md).

**Limitaciones conocidas**, sin rodeos:

- Sin autenticación multifactor (MFA).
- Sin motor de antivirus/antimalware real sobre archivos subidos.
- Rate limiting por IP/credencial, no todavía por usuario JWT autenticado.
- Sin automatización periódica de backups (el procedimiento manual está
  documentado y probado de extremo a extremo).
- HTTPS verificado funcionalmente con un certificado de prueba; pendiente
  de validar con un dominio público y Let's Encrypt real.
- El pipeline de CI/CD está escrito y cada paso verificado manualmente,
  pero no se ha ejecutado todavía en GitHub Actions real.

## Compliance Score

Índice interno **0–100**, cuatro dimensiones ponderadas:

| Dimensión | Peso |
|---|---|
| Controles | 40% |
| Evidencias | 20% |
| Hallazgos | 20% |
| Remediación | 20% |

Con renormalización automática cuando una dimensión no tiene datos
aplicables, y **"Sin datos"** como resultado honesto cuando no hay una
base razonable para calcular un número — nunca un `0` engañoso. Cálculo
completo y ejemplos en [docs/API.md](docs/API.md) y en el propio código
(`backend/app/core/compliance_score.py`, con tests sobre datasets
conocidos).

**No es una certificación.** El Compliance Score es un indicador interno
de cobertura/madurez GRC — nunca se presenta como una certificación ISO
27001 ni como una declaración legal de cumplimiento.

## Datos de demostración

La aplicación incluye datos completamente **ficticios** de una
organización de ejemplo, **Acme Security Labs** (riesgos, controles,
evidencias, hallazgos, proveedores). Los usuarios de demostración (uno por
rol) se crean con el script de seed — las credenciales exactas no se
publican en este README; consulta [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
tras clonar el repositorio.

## Ejecución local

```bash
cp .env.example .env
docker compose up -d --build
```

Servicios:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API REST | http://localhost:8000 |
| Documentación interactiva (Swagger) | http://localhost:8000/docs |
| Comprobación de salud | http://localhost:8000/health |
| Servidor MCP (streamable-http) | http://localhost:8001/mcp |
| PostgreSQL | `localhost:5433` (no expuesto en producción) |

Comprobar el estado de los 4 servicios:

```bash
docker compose ps       # los 4 deben quedar "healthy" (frontend: "running")
```

Migraciones y datos de demostración (ver
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) para el detalle):

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.db.seed
```

## Producción

Configuración independiente de desarrollo: `docker-compose.prod.yml` +
`nginx/`.

```
Internet
   │
  443 (HTTPS)
   │
   ▼
 Nginx ──────► Frontend (estático) / API (proxy inverso)
```

- **PostgreSQL no está expuesto públicamente.**
- **El backend no está expuesto públicamente** — solo alcanzable desde Nginx.
- **El servidor MCP no está expuesto directamente en producción** por
  defecto — es un servicio interno, igual que el backend.
- Nginx es el único punto de entrada público, con redirección automática
  de HTTP a HTTPS.

Guía completa (servidor, SSH, firewall, TLS, migraciones, actualización,
rollback) en [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Backups

```bash
COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup.sh /ruta/segura/backups/$(date +%Y%m%d)
COMPOSE_FILE=docker-compose.prod.yml ./scripts/restore.sh /ruta/al/backup
```

Cubren PostgreSQL **y** el almacenamiento de evidencias — no solo la base
de datos. Se realizó una recuperación completa de extremo a extremo en un
entorno Docker aislado (backup real → restauración → verificación de
datos e **integridad SHA-256** de una evidencia restaurada) — ver
[docs/SECURITY.md](docs/SECURITY.md) para el detalle de la prueba.

## Documentación

| Documento | Contenido |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Por qué el frontend y el servidor MCP comparten el mismo camino hacia PostgreSQL |
| [docs/API.md](docs/API.md) | Autenticación, paginación, errores, credenciales de integración, scopes |
| [docs/MCP.md](docs/MCP.md) | Servidor MCP: arquitectura, transporte, herramientas, seguridad |
| [docs/SECURITY.md](docs/SECURITY.md) | Modelo de seguridad completo, con categorización verificado/pendiente |
| [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) | Activos, amenazas, controles, riesgo residual |
| [docs/PRIVACY.md](docs/PRIVACY.md) | Qué datos almacena la plataforma y cómo los trata (incluido MCP) |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Despliegue completo en un servidor real, desde cero |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Convenciones de código y flujo de trabajo local |

## Tests y calidad

```
Backend:  365/365 tests passed  ·  Ruff: sin incidencias  ·  mypy: sin incidencias (66 archivos)
MCP:       15/15  tests passed  ·  Ruff: sin incidencias  ·  mypy: sin incidencias (20 archivos)
Frontend: build (tsc + Vite) OK ·  ESLint: sin incidencias
```

```bash
cd backend && pytest && ruff check . && mypy app
cd ../mcp && pytest && ruff check . && mypy .
cd ../frontend && npm run lint && npm run build
```

Los tests de integración/seguridad del servidor MCP contra la REST API
real (multi-tenancy, scopes, tokens revocados, auditoría) viven en
`backend/tests/test_mcp_server.py` — ejercitan el código real de `mcp/`
contra la app FastAPI real y una base de datos PostgreSQL de pruebas real,
sin mockear la lógica de negocio.

## Roadmap

No implementado en esta fase — posibles evoluciones futuras:

- Autenticación multifactor (MFA).
- Motor de antivirus/antimalware real para Evidence Vault.
- Rate limiting por usuario JWT autenticado.
- Automatización periódica de backups (cron/systemd timer).
- HTTPS público verificado con Let's Encrypt y un dominio real.
- Despliegue cloud (más allá de un único servidor Docker).
- Soporte para más marcos de cumplimiento predefinidos.
- SSO / OIDC.
- Métricas y observabilidad avanzadas.

## Idioma

Todo el contenido visible del frontend (menús, botones, formularios,
mensajes, estados, etc.) está en **español de España**. Los nombres
internos del código (modelos, tablas, endpoints, variables) permanecen en
inglés cuando es una convención técnica razonable.

## Licencia

Proyecto de portfolio profesional (GRC/ciberseguridad). Todavía no tiene
asignada una licencia — decisión deliberada, no un olvido: elegir una
licencia implica una decisión legal/de negocio que corresponde al autor
del proyecto. Si se decide publicar el código abiertamente, añadir aquí la
licencia elegida en un archivo `LICENSE`.
