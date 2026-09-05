# Seguridad

> Documento vivo. Esta versión cubre el proyecto completo hasta la Fase 10
> (release candidate / v1.0): base de datos, autenticación, Evidencias,
> Hallazgos/Acciones de remediación, Proveedores, Registro de auditoría, el
> Dashboard GRC / Compliance Score, la API REST avanzada + servidor MCP, y
> el hardening de seguridad, producción, CI/CD y backups de la Fase 10.

## Autenticación

- Las contraseñas nunca se almacenan en texto plano: se hashean con **bcrypt**
  (`app/core/security.py`). La API nunca devuelve `hashed_password` ni ningún
  campo de contraseña en sus respuestas.
- El login (`POST /api/v1/auth/login`) usa el flujo estándar OAuth2 Password
  Flow y devuelve un **JSON Web Token (JWT)** firmado con `HS256`.
- El JWT incluye una expiración (`exp`), configurable mediante la variable de
  entorno `ACCESS_TOKEN_EXPIRE_MINUTES` (60 minutos por defecto). Un token
  expirado o manipulado es rechazado con `401 Unauthorized`.
- La clave de firma (`SECRET_KEY`) se lee obligatoriamente de una variable de
  entorno. No existe ningún valor por defecto en el código: si falta, la
  aplicación no arranca. Cada entorno (Docker, desarrollo local, tests, y en
  el futuro producción) debe tener su propio valor, generado con:

  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

## Autorización basada en roles (RBAC)

Roles soportados: `admin`, `grc_manager`, `analyst`, `viewer`.

La autorización se implementa **siempre en el backend**, mediante la
dependencia `require_roles(...)` de FastAPI (`app/api/deps.py`). El frontend
podrá ocultar botones por comodidad de UX, pero eso no es un control de
seguridad: cualquier intento de saltarse la restricción llamando directamente
a la API es rechazado con `403 Forbidden`.

En esta fase, la gestión de usuarios (crear, listar, consultar) está
restringida al rol `admin`. Los roles `grc_manager`, `analyst` y `viewer` se
usarán para autorizar los módulos funcionales (riesgos, controles, etc.) en
las fases siguientes, según lo definido en la especificación principal.

## Aislamiento entre organizaciones (multiempresa)

- Todo dato relevante está asociado a una organización mediante
  `organization_id`.
- El backend **nunca** confía en un `organization_id` recibido del cliente
  (ni por parámetro, ni por cuerpo de la petición). La organización del
  usuario se obtiene siempre a partir del JWT validado y del registro del
  usuario en base de datos (`get_current_user` → `current_user.organization_id`).
- Todas las consultas que devuelven o modifican datos filtran explícitamente
  por `organization_id == current_user.organization_id`.
- Cuando un usuario intenta acceder a un recurso de otra organización por su
  id, la API responde `404 Not Found` (no `403`), para no confirmar ni negar
  la existencia de datos de otras organizaciones.
- Esto está cubierto por tests automatizados (`tests/test_users.py`) que
  verifican que un administrador de una organización no puede listar,
  consultar ni crear usuarios en otra.

## Variables de entorno y secretos

- Ningún secreto (contraseñas, `SECRET_KEY`) está hardcodeado en el código.
- Los archivos `.env` (raíz y `backend/.env`) están excluidos de git
  mediante `.gitignore`. Solo se versionan los `.env.example` con valores de
  ejemplo/placeholder.

## Evidencias: almacenamiento y validación de archivos

Implementado en `app/core/storage.py` (almacenamiento) y
`app/core/file_validation.py` (validación), usados por
`app/api/routes/evidence.py`.

- **Dónde se almacenan**: en disco, bajo el directorio configurado por
  `EVIDENCE_STORAGE_PATH` (por defecto `storage/evidence`, relativo al
  directorio de trabajo del backend). Ese directorio nunca se sirve como
  contenido estático ni a través de Nginx: la única forma de obtener un
  archivo es `GET /api/v1/evidence/{id}/download`, autenticado y con
  comprobación de organización.
- **Nombre físico**: nunca el nombre proporcionado por el usuario. Se genera
  como `{organization_id}/{uuid4}.{extensión}` (`LocalStorageService.generar_storage_key`).
  El nombre original solo se conserva como metadato (`original_filename`,
  saneado) para mostrarlo en pantalla y como nombre de descarga.
- **Protección contra path traversal**: `sanear_nombre_original` descarta
  cualquier componente de ruta del nombre subido (usa solo el "basename").
  Además, `LocalStorageService._resolver_ruta` resuelve toda `storage_key`
  contra el directorio base y rechaza cualquier resultado que quede fuera de
  él (`StorageError`) — una defensa en profundidad, ya que `storage_key`
  siempre se genera en el servidor y nunca se acepta desde el cliente.
- **Lista blanca de tipos permitidos**: PDF, DOCX, XLSX, CSV, TXT, PNG,
  JPG/JPEG (`TIPOS_PERMITIDOS` en `file_validation.py`). Cualquier otra
  extensión se rechaza con `422`, incluidos ejecutables (`.exe`, `.bat`,
  `.cmd`, `.ps1`, `.sh`) y contenido HTML/script.
- **No se confía en el `Content-Type` declarado por el cliente**: para los
  tipos binarios (PDF, PNG, JPEG, DOCX, XLSX) se comprueban los primeros
  bytes del archivo ("magic bytes") y deben coincidir con la extensión
  declarada; si no coinciden, se rechaza como posible manipulación.
- **Lista negra de firmas peligrosas**, aplicada a *cualquier* subida
  independientemente del tipo declarado: cabeceras de ejecutables Windows
  (`MZ`), ELF, shebang de script (`#!`), `<script`, `<?php`.
- **Límite de tamaño** configurable (`MAX_EVIDENCE_FILE_SIZE_MB`, 20 MB por
  defecto). Los archivos vacíos (0 bytes) se rechazan.
- **SHA-256**: se calcula sobre los bytes efectivamente recibidos y
  almacenados (nunca sobre lo que el cliente *diga* que ha enviado), y se
  guarda en PostgreSQL en el momento de la subida. No se sobrescribe nunca
  de forma silenciosa. `GET /api/v1/evidence/{id}/integrity` vuelve a leer el
  archivo del disco, recalcula el hash y compara, devolviendo `ok`,
  `mismatch` (el archivo cambió respecto al hash guardado) o `not_found`
  (el archivo ya no está en el almacenamiento).
- **No hay integración de antivirus/antimalware real en esta fase.** Las
  comprobaciones anteriores son una primera barrera razonable (lista blanca +
  magic bytes + lista negra de firmas), no un reemplazo de un escáner real.
  El diseño (una única función `determinar_tipo_seguro`, una única clase de
  almacenamiento) deja preparado el punto de extensión para añadirlo más
  adelante sin reescribir la lógica de Evidence.
- **Clasificación y datos sensibles**: la clasificación de una evidencia
  (`public/internal/confidential/restricted`, el mismo enum que Activos)
  determina cómo debe tratarse el documento. Las evidencias `confidential` y
  `restricted` **nunca se envían a ningún servicio externo**: esta fase no
  incluye ninguna integración de IA externa ni de terceros sobre el
  contenido de las evidencias, y no está prevista salvo con IA local/on-premise
  en una fase futura (ver especificación principal, sección de IA y privacidad).
- **Eliminación**: al eliminar una evidencia se borran primero las relaciones
  y el registro en PostgreSQL (en la misma transacción que el registro de
  auditoría) y, si esa transacción tiene éxito, se borra el archivo físico.
  Si el archivo ya no existe en disco por cualquier motivo, la eliminación no
  falla (se trata como ya completada).

## Hallazgos y Acciones de remediación: cierre/finalización controlados por el backend

Implementado en `app/api/routes/findings.py` y
`app/api/routes/remediation_actions.py`.

- **`closed_at` y `completed_at` nunca aceptan un valor del cliente.** Los
  esquemas `FindingUpdate` y `RemediationActionUpdate` excluyen deliberadamente
  esos campos: aunque el cliente los incluya en el cuerpo de la petición, se
  ignoran. El backend los fija comparando el estado antes/después de la
  actualización y usando la hora del servidor en el momento del cambio, y los
  limpia (`None`) automáticamente si el hallazgo se reabre o la acción vuelve
  a un estado no finalizado.
- **Cierre de un hallazgo**: `status=closed` exige `resolution_summary` no
  vacío; si falta, se rechaza con `422` antes de tocar la base de datos.
- **Regla de integridad Hallazgo→Acción**: no se puede crear una acción de
  remediación sobre un hallazgo cuyo `status` sea `closed` — hay que reabrirlo
  primero (`status` a cualquier valor distinto de `closed`). Esto evita que se
  añadan pasos de trabajo a algo que ya se declaró resuelto y auditado.
- **Relaciones M2M validadas por organización en ambos extremos**: hallazgo↔
  riesgo/control/activo/requisito/evidencia y acción↔evidencia siguen el mismo
  patrón que Controles/Evidencias — si el otro extremo de la relación
  pertenece a otra organización, la API responde `404` (nunca `403`, para no
  confirmar la existencia del recurso ajeno).
- **Eliminación de un hallazgo elimina en cascada sus acciones** (FK
  `ondelete="CASCADE"`), pero esa cascada ocurre a nivel de base de datos y no
  genera un evento de auditoría individual por cada acción eliminada; el
  evento `delete_finding` sí queda registrado.

## Proveedores (TPRM): multi-tenancy y derivación segura de vencimientos

Implementado en `app/api/routes/vendors.py`.

- Mismo patrón de aislamiento que el resto de módulos: `organization_id` se
  obtiene siempre de `current_user`, nunca del cliente; toda relación
  (`Vendor↔Risk`, `Vendor↔Evidence`, `Vendor↔Finding`) valida que el otro
  extremo pertenezca a la misma organización antes de vincularlo (`404` si no).
- `is_review_overdue`, `is_review_due_soon`, `is_contract_expired` e
  `is_contract_expiring_soon` son **siempre calculados en el backend** a
  partir de las fechas almacenadas y la fecha del servidor; no existen como
  columnas persistidas ni se aceptan del cliente, por lo que no pueden
  manipularse para ocultar una revisión o un contrato vencidos.
- Las acciones de remediación mostradas en el detalle de un proveedor se
  derivan en el momento de la consulta a partir de los hallazgos vinculados
  (no es una relación ni una tabla propia), por lo que no hay un segundo lugar
  donde ese dato pueda quedar desincronizado o manipulado de forma independiente.

## Registro de auditoría

- Modelo `AuditLog` (`app/models/audit_log.py`) y punto único de escritura
  `registrar_evento` (`app/core/audit.py`): usuario, organización, acción,
  tipo y id de entidad, IP, metadata en JSON.
- Se registran las operaciones sensibles sobre evidencias (subida,
  modificación de metadatos, descarga, eliminación, verificación de
  integridad), sobre hallazgos y acciones de remediación (creación, edición,
  cambio de estado, cierre/finalización, eliminación) y, desde la Fase 7,
  sobre proveedores: creación, edición, cambio de estado, eliminación y cada
  vinculación/desvinculación de riesgo/evidencia/hallazgo
  (`create_vendor`, `update_vendor`, `change_vendor_status`, `delete_vendor`,
  `link_vendor_risk`, `unlink_vendor_risk`, `link_vendor_evidence`,
  `unlink_vendor_evidence`, `link_vendor_finding`, `unlink_vendor_finding`).
- **Nunca se registra** el contenido de un archivo, una contraseña, un token
  ni ningún otro secreto — solo metadatos seguros (nombre de archivo,
  tamaño, clasificación, resultado de la verificación, ids de entidad).
- **Consulta**: `GET /api/v1/audit-logs` (`app/api/routes/audit_logs.py`),
  con filtros por acción, tipo de entidad, id de entidad, actor y rango de
  fechas, paginado y ordenado siempre por fecha descendente (no configurable
  por el cliente). Filtra siempre por `organization_id` del usuario
  autenticado — igual que el resto de recursos, un usuario nunca puede ver
  eventos de otra organización. `GET /api/v1/audit-logs/meta` expone
  únicamente los valores de `action`/`entity_type` ya usados (sin datos
  sensibles), para poblar los filtros del frontend.
- **RBAC de mínimo privilegio**: solo **Admin** y **GRC Manager** pueden leer
  el registro (`403` para Analyst y Viewer). El registro de auditoría es una
  herramienta de supervisión/cumplimiento, no una funcionalidad operativa que
  un Analyst necesite en su trabajo diario; Viewer no tiene ningún acceso.
  Decisión documentada aquí porque se aparta ligeramente de la matriz
  "lectura para todos los roles" usada en el resto de módulos GRC.
- **Inmutable por diseño**: no existe ningún endpoint `POST`/`PATCH`/`DELETE`
  sobre `/api/v1/audit-logs` — ni en el router ni en ningún otro lugar de la
  API. La única forma de crear una entrada es `registrar_evento`, llamado
  desde el propio backend en la misma transacción que la operación que audita.
- **Corrección de un bug de generación heredado de las Fases 5-6**: en varios
  `create_*` (`create_finding`, `create_action`, `upload_evidence` y ahora
  `create_vendor`), `registrar_evento` leía `entidad.id` **antes** de que
  SQLAlchemy asignara ese id (el `default=uuid.uuid4` de la columna solo se
  aplica en el `flush()`), por lo que esos eventos se guardaban con
  `entity_id = NULL`. Se añadió un `db.flush()` justo después de `db.add(...)`
  y antes de `registrar_evento(...)` en los cuatro puntos afectados, de forma
  que el filtro `entity_id` del nuevo endpoint de consulta (y cualquier caso
  de uso futuro que dependa de él) funcione correctamente también para
  eventos de creación. Los registros antiguos ya persistidos con
  `entity_id = NULL` no se han reescrito (no se altera el histórico).

## Dashboard / Compliance Score

Implementado en `app/api/routes/dashboard.py` y `app/core/compliance_score.py`.

- **Multi-tenancy**: todas las consultas de agregación filtran siempre por
  `Model.organization_id == current_user.organization_id`; ningún endpoint
  acepta `organization_id` del cliente. El filtro `vendor_id` (usado en
  `/risks`, `/evidence`, `/remediation`) reutiliza el mismo helper
  `_obtener_vendor_o_404` que el resto de la API: un `vendor_id` de otra
  organización responde `404`, nunca se filtra "silenciosamente" a vacío.
  Probado explícitamente con datasets de dos organizaciones
  (`tests/test_dashboard.py`), incluyendo el caso de una organización sin
  ningún dato (todos los KPIs en 0, Compliance Score "Sin datos", nunca un
  error 500).
- **RBAC**: los 6 endpoints son de solo lectura y accesibles para los 4
  roles (Admin, GRC Manager, Analyst, Viewer) — a diferencia del Registro de
  auditoría, el dashboard no expone eventos individuales sensibles, solo
  agregados/conteos, por lo que no hay razón de mínimo privilegio para
  restringirlo. El dashboard nunca permite modificar datos: solo enlaza
  hacia los módulos ya existentes, donde se aplica la autorización habitual.
- **Validación de filtros**: todos los filtros de enum (`status`,
  `treatment`, `criticality`, etc.) usan los mismos tipos `Enum`/`StrEnum` ya
  definidos en los modelos — un valor inválido responde `422` antes de
  tocar la base de datos, igual que en el resto de la API. Los `vendor_id`/
  `framework_id` son `uuid.UUID` tipados por FastAPI (`422` si no es un UUID
  válido).
- **Sin SQL concatenado**: todas las consultas usan el ORM de SQLAlchemy
  (`db.query(...).filter(...)`); ningún filtro se interpola como texto en
  una sentencia SQL.
- **Rendimiento como propiedad de seguridad**: cada endpoint ejecuta un
  número fijo de consultas (no una por fila), lo que además de evitar N+1
  evita que un endpoint de solo-lectura se convierta en un vector de
  denegación de servicio a medida que crecen los datos de una organización.
- **Sin secretos**: los endpoints de dashboard solo devuelven conteos,
  porcentajes y resúmenes (título/severidad/fecha) de entidades ya
  accesibles individualmente por el usuario con su rol; no exponen ningún
  campo nuevo que no estuviera ya disponible en los endpoints de cada módulo.
- **Compliance Score robusto ante casos límite**: cubierto explícitamente
  por tests (`tests/test_compliance_score.py`, `tests/test_dashboard.py`)
  para que ninguna combinación de datos (sin controles, sin evidencias, sin
  hallazgos, sin acciones, framework sin requisitos, requisito sin
  controles) produzca `NaN`, `Infinity` ni un error 500 — siempre `None`
  ("Sin datos") o un número en el rango 0-100.

## Credenciales de integración (API keys) y servidor MCP

Implementado en `app/models/integration_token.py`, `app/api/deps.py`
(`Actor`, `require_access`) y `app/api/routes/integration_tokens.py`. Ver
[docs/API.md](API.md) y [docs/MCP.md](MCP.md) para el detalle funcional.

- **El secreto nunca se almacena ni se puede recuperar.** Solo su hash
  SHA-256 (`token_hash`) se persiste; el texto plano se devuelve una única
  vez, en la respuesta de creación. Deliberadamente **no** se usa bcrypt: el
  secreto ya tiene alta entropía (generado por el servidor,
  `secrets.token_urlsafe(32)`), por lo que no necesita un hash lento para
  resistir fuerza bruta offline, y SHA-256 permite una búsqueda indexada por
  igualdad en cada petición sin recalcular un hash costoso — a diferencia de
  una contraseña humana, donde sí se usa bcrypt.
- **Scopes de mínimo privilegio**, lista cerrada (`VALID_SCOPES`): una
  credencial nunca puede concederse a sí misma un permiso no soportado.
- **Doble mecanismo de autenticación en los mismos endpoints**: `Actor` y
  `require_access(*, roles, scope)` permiten que un endpoint acepte JWT
  humano (verificado por rol) o API key (verificada por scope) sin duplicar
  rutas ni lógica de negocio. Aplicado quirúrgicamente solo a los ~13
  endpoints que necesita el servidor MCP, no a los ~150 de la API.
- **Auditoría centralizada y garantizada**: `require_access()` registra un
  evento `mcp_tool_call` por cada petición autenticada con API key, con
  `integration_token_id` (nunca `user_id`) — no depende de que cada endpoint
  recuerde auditar. `AuditLogRead` distingue explícitamente actor humano
  (`actor`) de actor de integración (`integration_actor`).
- **Aislamiento multi-tenant idéntico al de un usuario humano**: un intento
  de acceder a un recurso de otra organización con una API key válida
  responde `404`, nunca `403` — no se confirma su existencia. Probado con
  datasets de dos organizaciones (`tests/test_integration_auth.py`,
  `tests/test_mcp_server.py`) y verificado en vivo contra el contenedor
  Docker real (ver informe de la Fase 9).
- **El servidor MCP nunca accede directamente a PostgreSQL** (regla
  arquitectónica obligatoria, no solo una preferencia — ver
  [docs/ARCHITECTURE.md](ARCHITECTURE.md)). El paquete `mcp/` no importa
  `sqlalchemy` ni modelos del backend, no recibe `DATABASE_URL`, y su
  contenedor Docker no tiene el driver de PostgreSQL instalado ni ninguna
  credencial de base de datos — verificado automáticamente
  (`mcp/tests/test_no_direct_db_access.py`) y manualmente
  (`docker compose exec mcp env`, `docker compose exec mcp pip list`).
- **Formato de error normalizado** (`{"detail": {"code", "message"}}`) para
  toda respuesta basada en `HTTPException`, sin filtrar trazas de pila, SQL
  ni secretos — ver [docs/API.md](API.md).

## Fase 10 — Hardening, producción y CI/CD

### Configuración segura por entorno

`app/core/config.py` valida la configuración al arrancar
(`_validar_seguridad_en_produccion`): si `ENVIRONMENT=production`, rechaza el
arranque si `DATABASE_URL` sigue siendo el valor de desarrollo por defecto,
si `SECRET_KEY` tiene menos de 32 caracteres, o si `CORS_ORIGINS` incluye
`*`. Falla rápido y explícito en vez de arrancar "seguro a medias".
Verificado: el backend arranca normalmente en desarrollo y se probó
end-to-end con `ENVIRONMENT=production` real en `docker-compose.prod.yml`.

### Cabeceras de seguridad HTTP

`app/core/security_headers.py`, aplicadas a toda respuesta:
`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, `Content-Security-Policy` (estricta para la API,
con una excepción justificada y necesaria en `/docs`/`/redoc` para que
Swagger UI pueda ejecutar su script de arranque), y `Strict-Transport-
Security` solo cuando `ENVIRONMENT=production`. Verificado en un navegador
real (Swagger UI probado tras introducir la CSP — sin la excepción en
`/docs`, la interfaz queda en blanco; con ella, funciona) y en producción
real vía HTTPS (`docker-compose.prod.yml`, cabecera HSTS confirmada en la
respuesta).

### Rate limiting

`app/core/rate_limit.py`: limitador en memoria de ventana fija, pensado
para un despliegue de una sola instancia (ver `docker-compose.yml`, un
único contenedor `backend`) — evita depender de Redis para una necesidad
que este proyecto no tiene todavía.

- Login: 10 intentos/60s por IP.
- API key inválida/desconocida: 30 intentos/60s por IP (protege contra
  fuerza bruta/spray de claves).
- API key válida: 120 peticiones/60s por credencial (acota el abuso de una
  clave filtrada, sin bloquear el uso legítimo de una integración real).

Todos verificados con tests dedicados (`tests/test_rate_limit.py`) y en
vivo contra el contenedor Docker real (10 intentos de login → 401,
11º → 429, con el formato de error normalizado `RATE_LIMITED`).

### Dependencias

`pip-audit`/`npm audit` ejecutados. `pyjwt` (2.10.1 → 2.13.0) y
`python-multipart` (0.0.20 → 0.0.31) actualizados tras detectarse
vulnerabilidades conocidas — 359+ tests re-verificados tras la
actualización. `starlette` y `pytest` deliberadamente **no** actualizados:
una versión más reciente de `starlette` rompe la compatibilidad fijada con
FastAPI 0.115.6 (mismo conflicto de dependencias documentado en la Fase 9
entre el SDK MCP y el backend) — se prioriza estabilidad verificada sobre
parchear una dependencia de test/transitiva sin impacto de seguridad directo
confirmado.

### Docker hardening

- `backend` y `mcp` corren como usuario no-root (`appuser`, uid 1000),
  verificado en contenedores reales (`whoami` → `appuser`).
- `frontend` (servidor de desarrollo Vite) se probó como no-root y se
  revirtió: el volumen anónimo `node_modules` de `docker-compose.yml` se
  recrea con propietario root en cada arranque, rompiendo Vite
  (`EACCES`, comprobado). Excepción documentada y acotada al entorno de
  desarrollo local — no existe en producción (sustituido por `nginx`
  sirviendo estáticos, sin bind mounts).
- `.dockerignore` en `backend/`, `frontend/`, `mcp/` y en la raíz del
  repositorio (evita enviar `.venv`/`node_modules`/tests al contexto de
  build).
- PostgreSQL, backend y MCP **no publican ningún puerto** en
  `docker-compose.prod.yml` — solo `nginx` (80/443). Verificado
  (`docker compose ps` sin columna `PORTS` para esos tres servicios).

### Producción, Nginx y HTTPS

`docker-compose.prod.yml` (proyecto Docker Compose independiente y con
nombre propio, `grcplatform-prod`, para no poder colisionar nunca con los
contenedores de desarrollo — ver la incidencia real documentada en el
informe de la Fase 10) + `nginx/` (imagen que compila el frontend y sirve
tanto los estáticos como el proxy inverso hacia el backend). Verificado
end-to-end con un certificado autofirmado de prueba: build de las 3
imágenes, arranque de los 4 servicios, migraciones, seed, login vía HTTPS,
consulta autenticada vía HTTPS, cabeceras de seguridad (incluida HSTS)
presentes en la respuesta real. **No verificado** contra un dominio público
y un certificado real de Let's Encrypt (sin acceso a un dominio en este
entorno) — procedimiento documentado en `docs/DEPLOYMENT.md`.

### Backups y recuperación

`scripts/backup.sh` / `scripts/restore.sh` (PostgreSQL vía `pg_dump
--no-owner --no-privileges` + almacenamiento de evidencias vía `tar`).
**Probado de extremo a extremo de verdad**: backup real del stack de
desarrollo (con datos de "Acme Security Labs" y una evidencia real) →
restauración completa en un stack Docker aislado y vacío → verificación de
que la organización/usuarios restaurados coinciden → verificación de que
el hash SHA-256 de la evidencia restaurada coincide exactamente con el
almacenado (`GET /evidence/{id}/integrity` → `"status": "ok"`). Dos fallos
reales se encontraron y corrigieron durante esta prueba (documentados en
los propios scripts): `DROP DATABASE` falla si el backend mantiene
conexiones abiertas (el script ahora para el backend antes de restaurar la
BD y lo reinicia después), y `pg_dump` sin `--no-owner` falla al restaurar
en un entorno con un rol de PostgreSQL distinto al de origen.

### CI/CD

`.github/workflows/ci.yml`: tests + ruff + mypy del backend (con un
PostgreSQL de servicio efímero), tests + ruff + mypy de `mcp/` (entorno
propio, sin el conflicto de dependencias con el backend), lint + build del
frontend, y un job final que construye todas las imágenes Docker
(desarrollo y producción). Cada comando se verificó manualmente de forma
individual con el código real de esta fase antes de escribir el workflow;
no se ha ejecutado aún en un GitHub Actions real (sin acceso a un
repositorio remoto en este entorno).

## Categorización explícita de controles

No se declara "seguro" nada que no se haya probado. Leyenda:
**[V]** implementado y verificado · **[NV]** implementado pero no
verificado en un entorno real · **[P]** pendiente · **[NA]** no aplica.

| Control | Estado |
|---|---|
| JWT (algoritmo fijado, expiración, sin secreto por defecto) | [V] |
| bcrypt para contraseñas humanas | [V] |
| RBAC por rol | [V] |
| Multi-tenancy (`organization_id` derivado del servidor, 404 no 403) | [V] |
| IDOR probado explícitamente | [V] |
| Scopes de API key (mínimo privilegio) | [V] |
| API keys: hash, expiración, revocación, secreto mostrado una vez | [V] |
| Rate limiting (login, API key por IP y por credencial) | [V] |
| CORS restringido por variable de entorno, sin `*` en producción | [V] |
| Cabeceras de seguridad HTTP | [V] |
| Errores sin traza/SQL/secretos | [V] |
| Sin secretos en logs ni en Git | [V] |
| Hardening de subida de archivos (extensión, magic bytes, tamaño) | [V] |
| Antivirus/antimalware real sobre archivos subidos | [P] |
| Path traversal en Evidence Vault | [V] |
| SSRF | [NA] — no existe ninguna funcionalidad donde una entrada de usuario se convierta en una petición HTTP saliente (ver `docs/THREAT_MODEL.md`) |
| MCP aislado de PostgreSQL | [V] |
| PostgreSQL no público en producción | [V] |
| Contenedores backend/MCP como no-root | [V] |
| Contenedor frontend (dev) como no-root | [P] — revertido por incompatibilidad real con el volumen anónimo de `node_modules`; no aplica en producción |
| HTTPS/Nginx (funcional, certificado de prueba) | [V] funcionalmente · [NV] con dominio y certificado reales de Let's Encrypt |
| Backups | [V] |
| Restauración | [V] |
| CI/CD (comandos verificados individualmente) | [NV] — no ejecutado en GitHub Actions real |
| MFA | [P] |
| Rate limiting por usuario JWT (no solo por IP) | [P] |
| Automatización periódica de backups (cron) | [P] |

## Pendiente (fases posteriores)

- Autenticación multifactor (MFA) para usuarios humanos.
- Integración real de antivirus/antimalware para archivos subidos.
- Rate limiting también para usuarios JWT autenticados (no solo login/API key).
- Automatización periódica de backups (cron/systemd timer) — el
  procedimiento manual ya está documentado y probado.
- Verificación de HTTPS contra un dominio público y un certificado real.
- Ejecución real del pipeline de CI/CD en GitHub Actions.
- Ampliar el servidor MCP más allá de lectura + `create_risk` (más
  herramientas de escritura), si un caso de uso real lo justifica.
