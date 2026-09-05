# Guía de desarrollo

Para instalación y arranque ver el [README](../README.md). Este documento
cubre convenciones y flujos del día a día que no encajan ahí.

## Convenciones de código

- **Idioma**: todo texto visible en el frontend, en español de España
  (menús, botones, mensajes, estados, errores). Nombres internos de código
  (modelos, columnas, endpoints, variables) pueden quedar en inglés cuando
  sea una convención técnica razonable (p. ej. `Risk`, `organization_id`).
- **Backend**: Python 3.12, tipado explícito en toda función pública,
  Pydantic v2 para todo esquema de entrada/salida. `ruff` (`backend/pyproject.toml`
  implícito vía defaults) y `mypy` (`backend/mypy.ini`) deben quedar limpios
  antes de dar por terminado un cambio.
- **Multi-tenancy**: `organization_id` se deriva SIEMPRE del actor
  autenticado (JWT o API key), nunca se acepta del cliente. Un recurso de
  otra organización responde `404`, nunca `403`.
- **Campos derivados** (scores, estados calculados, timestamps de
  cierre): siempre calculados en el backend, nunca aceptados como entrada.
- **Auditoría**: cualquier operación de escritura sensible nueva debe
  llamar a `registrar_evento` (`app/core/audit.py`) en la misma transacción
  — con `db.flush()` antes si necesitas el `id` recién creado (gotcha
  recurrente: el `default=uuid.uuid4` de una columna no se aplica hasta el
  flush).
- **Errores**: lanza `HTTPException(status_code=..., detail="mensaje en español")`
  con normalidad — el formato `{code, message}` lo añade automáticamente
  `app/core/errors.py`, no lo construyas a mano.

## Flujo de trabajo habitual

```bash
# Backend
cd backend
.venv/Scripts/activate  # o source .venv/bin/activate
pytest                  # toda la suite
pytest tests/test_risks.py -v   # un módulo concreto
ruff check .
ruff check . --fix      # autofix de imports/estilo
mypy app

# Frontend
cd frontend
npm run dev
npm run lint
npm run build

# MCP
cd mcp
pytest
ruff check .
mypy .
```

Ejecuta la suite completa (no solo el módulo que tocaste) antes de dar un
cambio por terminado — varios módulos comparten helpers (`app/api/deps.py`,
`app/core/audit.py`) y una regresión cruzada es fácil de introducir sin
darse cuenta.

## Añadir una migración de Alembic

```bash
cd backend
alembic revision --autogenerate -m "Descripción en español de lo que cambia"
```

Revisa SIEMPRE el archivo generado antes de aplicarlo: Alembic no detecta
bien los cambios de tipos de enum nativos de PostgreSQL. Si reutilizas un
enum ya existente en otro modelo, cambia `sa.Enum(...)` por
`postgresql.ENUM(..., create_type=False)` en la migración generada — si no,
falla al intentar crear un tipo que ya existe.

```bash
alembic upgrade head    # aplicar
alembic downgrade -1    # revertir la última
```

## Datos de demostración

```bash
python -m app.db.seed
```

Crea la organización "Acme Security Labs" con datos ficticios completos
(usuarios, activos, riesgos, controles, marcos, evidencias, hallazgos,
acciones, proveedores). Es idempotente — puedes ejecutarlo varias veces
sin duplicar datos (comprueba existencia por campos únicos antes de crear).

Usuarios de demostración (misma contraseña para los cuatro, solo válida en
local/demo — **nunca reutilizar en un despliegue real**, ver
`docs/DEPLOYMENT.md`):

| Rol | Email | Contraseña |
|---|---|---|
| Admin | `admin@acme-labs.demo` | `Demo1234!` |
| GRC Manager | `grc.manager@acme-labs.demo` | `Demo1234!` |
| Analyst | `analista@acme-labs.demo` | `Demo1234!` |
| Viewer | `visor@acme-labs.demo` | `Demo1234!` |
**No ejecutar en un despliegue real** (ver `docs/DEPLOYMENT.md`).

## Estructura de tests (backend)

- `tests/conftest.py`: fixtures compartidos (`db_session`, `client`,
  organizaciones/usuarios de prueba A/B para multi-tenancy, helpers como
  `_crear_integration_token`). Cada test corre en una transacción que se
  revierte al final — no necesitas limpiar datos manualmente.
- Un archivo de test por módulo/router (`test_risks.py`, `test_vendors.py`,
  etc.), más archivos transversales (`test_integration_auth.py`,
  `test_mcp_server.py`, `test_rate_limit.py`).
- Los tests de multi-tenancy siempre crean datos en **dos** organizaciones
  (`organizacion_a`/`organizacion_b`) y comprueban aislamiento en ambos
  sentidos, no solo que "A no ve B".

## Por qué `mcp/` tiene su propio venv, separado del backend

El SDK MCP real (`mcp==2.1.1`) tiene dependencias transitivas
(Starlette/Pydantic) incompatibles con las versiones fijadas del backend
— comprobado empíricamente (`ResolutionImpossible` de pip al intentar
instalar ambos juntos). Por eso `mcp/` tiene su propio
`requirements.txt`/`requirements-dev.txt` y su propio `.venv`, y por eso
`backend/tests/test_mcp_server.py` sustituye la capa de registro del SDK
por un stand-in mínimo en vez de instalar el SDK real en el venv del
backend (ver el docstring de ese archivo para el detalle completo). Nunca
intentes instalar `mcp` (el paquete PyPI) en el venv del backend.

## Antes de proponer un cambio

1. `pytest` (backend y, si tocaste `mcp/`, también `mcp/`) — toda la suite.
2. `ruff check .` y `mypy` en cada paquete tocado.
3. Si tocaste el frontend: `npm run lint` y `npm run build`.
4. Si el cambio afecta contenedores: `docker compose up -d --build` y
   comprobar que los 4 healthchecks quedan en `healthy`.
5. Si el cambio es visible en el frontend: comprobarlo en un navegador real,
   no solo confiar en que compila — confirmar que el texto sigue en español.
