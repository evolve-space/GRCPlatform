# Borrador de presentación en GitHub

> Documento interno de preparación. **El repositorio NO se ha publicado
> todavía** — este archivo simula exactamente cómo se vería la página del
> repositorio en GitHub el día que se decida hacer el primer `push`, para
> poder revisarlo y ajustarlo sin haber tocado nada remoto. Ver
> `docs/RELEASE_CHECKLIST.md` para el checklist previo a publicar.

## Nombre del repositorio

```
GRCPlatform
```

## Descripción corta (para el campo "About" de GitHub)

Tres opciones — máximo ~160 caracteres, sin emoji, sin superlativos sin
respaldo ("the best", "enterprise-grade"):

1. **Técnica**:
   > API REST (FastAPI) + servidor MCP real + frontend React para gestión GRC multi-tenant: riesgos, controles, evidencias, hallazgos, proveedores y auditoría.

2. **Profesional / GRC**:
   > Plataforma GRC self-hosted: riesgos, controles, evidencias, hallazgos, remediación, proveedores, auditoría y Compliance Score, con API REST y MCP.

3. **Orientada a portfolio**:
   > Plataforma GRC self-hosted de portfolio: RBAC multi-tenant, API REST, integración MCP con Claude, Docker + Nginx, backups verificados.

**Recomendada: la opción 2** (profesional/GRC). Es la que mejor equilibra
qué hace el proyecto (funcionalmente) con quién lo entendería de un
vistazo — un reclutador técnico o un perfil de GRC entienden ambos la
frase completa sin necesitar contexto adicional. La opción 1 es más
precisa técnicamente pero menos legible para alguien no técnico; la
opción 3 es la más "vendida" pero dice menos sobre qué hace realmente la
plataforma.

## Topics recomendados

Solo los que aplican de verdad — nada añadido por relleno de palabras clave:

```
grc
governance-risk-compliance
risk-management
compliance
cybersecurity
fastapi
react
typescript
postgresql
docker
mcp
model-context-protocol
rbac
multi-tenant
```

Se han descartado deliberadamente topics genéricos que no aportan
señal real sobre este proyecto en concreto: `python`, `javascript`,
`web-app`, `saas` (demasiado amplios, no diferencian nada), y
`enterprise`/`production-ready` (no serían honestos dado el estado
"Release Candidate" — ver `docs/SECURITY.md`).

## Estructura del repositorio

```text
GRCPlatform/
├── backend/                 API REST (FastAPI + SQLAlchemy + Alembic)
│   ├── app/
│   │   ├── api/              Routers y dependencias (auth, RBAC, scopes)
│   │   ├── core/              Config, seguridad, rate limiting, Compliance Score
│   │   ├── db/                 Seed de datos de demostración
│   │   ├── models/             Modelos SQLAlchemy
│   │   └── schemas/            Esquemas Pydantic (request/response)
│   ├── alembic/              Migraciones de base de datos
│   ├── tests/                 365 tests (pytest)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 Aplicación web (React + TypeScript + Vite + Tailwind)
│   └── src/
│       ├── components/        Layout, gráficos, tarjetas del dashboard
│       ├── context/            Autenticación
│       ├── lib/                 Cliente API, tipos, etiquetas en español
│       └── pages/               Todas las pantallas de la aplicación
├── mcp/                      Servidor MCP real (SDK oficial `mcp`)
│   ├── tools/                 14 herramientas (una por recurso GRC)
│   ├── schemas/                Tipos que reflejan los enums de la API
│   └── tests/                   15 tests (unitarios + prueba arquitectónica)
├── nginx/                    Imagen de producción (build del frontend + reverse proxy)
├── scripts/                  backup.sh / restore.sh (probados de extremo a extremo)
├── docs/                     Documentación técnica y de producto
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── MCP.md
│   ├── SECURITY.md
│   ├── THREAT_MODEL.md
│   ├── PRIVACY.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
├── .github/workflows/        CI (tests, lint, mypy, build) — preparado, no ejecutado aún
├── docker-compose.yml         Desarrollo
├── docker-compose.prod.yml    Producción (Nginx + HTTPS, sin puertos internos publicados)
├── .env.example / .env.prod.example
├── .gitignore
└── README.md
```

## README preview

A continuación, el contenido exacto de `README.md` tal y como se vería en
la página principal del repositorio:

---

<!-- INICIO DEL CONTENIDO DE README.md -->

> El contenido completo y actualizado vive en [`README.md`](../README.md),
> en la raíz del repositorio — no se duplica aquí para evitar que ambos
> archivos queden desincronizados en cuanto uno de los dos cambie. Ábrelo
> directamente para ver la vista previa real; en GitHub aparecería
> renderizado exactamente igual, debajo del listado de archivos de esta
> misma estructura.

<!-- FIN DEL CONTENIDO DE README.md -->

---

## Cómo se vería la página del repositorio (resumen visual)

```
┌──────────────────────────────────────────────────────────────────┐
│  usuario / GRCPlatform                                    ⭐ Star │
│  Plataforma GRC self-hosted: riesgos, controles, evidencias,      │
│  hallazgos, remediación, proveedores, auditoría y Compliance      │
│  Score, con API REST y MCP.                                       │
│                                                                    │
│  🏷 grc · governance-risk-compliance · risk-management ·          │
│     compliance · cybersecurity · fastapi · react · typescript ·   │
│     postgresql · docker · mcp · model-context-protocol · rbac ·   │
│     multi-tenant                                                  │
│                                                                    │
│  [Python 3.12] [FastAPI 0.115] [React 18.3] [TypeScript 5.7]      │
│  [PostgreSQL 16] [Docker Compose] [backend tests: 365 passing]    │
│  [MCP tests: 15 passing] [CI: preparado | no ejecutado aún]       │
│                                                                    │
│  📁 backend  📁 frontend  📁 mcp  📁 nginx  📁 scripts  📁 docs   │
│  📁 .github  📄 docker-compose.yml  📄 README.md  ...             │
└──────────────────────────────────────────────────────────────────┘
```

## Notas para cuando se decida publicar

- El badge de CI está deliberadamente marcado como "preparado | no
  ejecutado aún" — en cuanto el primer workflow corra en GitHub Actions,
  sustituirlo por el badge dinámico real:
  `https://github.com/<usuario>/GRCPlatform/actions/workflows/ci.yml/badge.svg`.
- Revisar `docs/RELEASE_CHECKLIST.md` antes de crear el repositorio remoto.
- Confirmar la visibilidad deseada (público/privado) antes del primer push
  — este documento no asume ninguna de las dos.
