# Modelo de amenazas

> Documento vivo, escrito para defender el proyecto, no como ejercicio
> académico. Metodología: Activos → Amenazas/superficie de ataque →
> Controles implementados → Riesgo residual. Todo lo marcado como
> "implementado" está verificado con tests automatizados y/o una prueba
> manual real documentada en `docs/SECURITY.md` o en el informe de la
> Fase 10 — nada se declara "mitigado" solo porque "debería funcionar".

## Activos a proteger

1. Datos de riesgos, controles, evidencias, hallazgos, proveedores y
   Compliance Score de cada organización cliente (multi-tenant).
2. Credenciales: contraseñas de usuarios, claves de integración (API keys),
   `SECRET_KEY` de firma JWT.
3. Archivos de Evidence Vault (pueden contener información sensible/
   confidencial de la organización cliente).
4. El propio Registro de auditoría (integridad de la traza de quién hizo qué).
5. Disponibilidad del servicio (para el uso normal de la plataforma).

## 1. Autenticación

| Amenaza | Superficie | Control implementado | Riesgo residual |
|---|---|---|---|
| Fuerza bruta contra `/auth/login` | Formulario de login | Rate limiting por IP: 10 intentos/60s (`app/core/rate_limit.py`), verificado en tests y en vivo contra Docker (10x 401 → 11º intento 429) | Un atacante distribuido (muchas IPs) no está cubierto — mitigación completa requeriría un WAF/CDN delante, fuera del alcance de este proyecto |
| Credenciales robadas (contraseña filtrada) | Login | bcrypt (coste por defecto), contraseña nunca en logs/respuestas, mínimo 8 caracteres | Sin MFA — aceptado, documentado como mejora futura |
| JWT robado (XSS, dispositivo comprometido) | `localStorage` del frontend | Expiración corta (60 min por defecto), `SECRET_KEY` obligatorio sin valor por defecto inseguro, algoritmo fijado explícitamente (`algorithms=[...]`, sin aceptar `alg=none`) | `localStorage` es accesible por JS — un XSS real robaría el token; mitigado en parte por CSP y por no tener `dangerouslySetInnerHTML` en el frontend (verificado, cero usos) |
| Fuerza bruta / spray contra API keys de integración | Cabecera `X-API-Key` | Rate limiting por IP (30/60s) antes incluso de mirar la base de datos, más rate limiting por credencial válida (120/60s) — verificado en tests y en vivo | Igual que el login: atacante multi-IP no cubierto |

## 2. Autorización (IDOR / escalada de privilegios / de scope)

| Amenaza | Superficie | Control implementado | Riesgo residual |
|---|---|---|---|
| Usuario de rol bajo accede a una acción restringida (p. ej. Viewer crea un riesgo) | Cualquier endpoint de escritura | `require_roles(...)` / `require_access(roles=..., scope=...)` en cada endpoint — nunca decidido solo en el frontend | Ninguno conocido; cubierto por tests de RBAC en cada módulo |
| Una credencial de integración usa un scope que no tiene | Cualquier endpoint dual-auth (MCP) | Comprobación de scope explícita en `require_access`, `403` con el scope que falta | Ninguno conocido |
| Una credencial de integración intenta ampliar sus propios scopes | Gestión de API keys | No existe ningún endpoint de "actualizar" una credencial — solo crear (con scopes fijados por un Admin humano) y revocar | Ninguno: la superficie de ataque no existe |
| IDOR: adivinar/enumerar un UUID de otra organización | Cualquier endpoint `GET/PATCH/DELETE /{id}` | El backend nunca confía en `organization_id` del cliente; toda consulta filtra por la organización del actor autenticado; un recurso ajeno responde `404` (nunca `403`, para no confirmar su existencia) | Ninguno conocido; verificado exhaustivamente en tests (`test_*.py` de cada módulo) y en vivo vía MCP (Fase 9) |

## 3. Multi-tenancy

| Amenaza | Superficie | Control implementado | Riesgo residual |
|---|---|---|---|
| Fuga de datos entre organizaciones por un filtro olvidado | Cualquier query de listado/agregación | Todas las queries filtran explícitamente por `organization_id`; el Dashboard/Compliance Score se probó explícitamente con datasets de dos organizaciones | El riesgo real es "un desarrollador futuro olvida el filtro en un endpoint nuevo" — mitigado por convención de código consistente, no por un mecanismo automático (p. ej. no hay row-level security de PostgreSQL) |
| Manipulación de UUID para acceder a datos ajenos | Path/query params | Ver IDOR arriba: siempre `404` | Ninguno conocido |

## 4. API (inyección, mass assignment, abuso de endpoints)

| Amenaza | Superficie | Control implementado | Riesgo residual |
|---|---|---|---|
| SQL injection | Cualquier query | 100% SQLAlchemy ORM; único SQL literal es `SELECT 1` sin interpolación (`/health`); verificado por búsqueda exhaustiva en el código | Ninguno conocido |
| Mass assignment (el cliente fija campos que no debería) | Creación/edición de cualquier entidad | Los esquemas Pydantic de entrada (`*Create`/`*Update`) son listas blancas explícitas de campos — nunca se hace `Model(**request.json())`; campos derivados (`inherent_score`, `is_review_overdue`, `closed_at`, etc.) se calculan siempre en el backend | Ninguno conocido |
| Abuso de un endpoint por volumen (scraping, DoS de aplicación) | Cualquier endpoint autenticado por API key | Rate limiting por credencial (120 peticiones/60s) | Sin rate limiting general para JWT humano (se confía en el uso normal de la UI); un usuario humano malicioso con credenciales válidas podría hacer scraping — riesgo aceptado, bajo impacto (ya tiene acceso legítimo a esos datos) |
| Filtración de información en errores | Cualquier endpoint | Formato de error normalizado, sin trazas/SQL/rutas; errores 500 se registran en el servidor, nunca se devuelven al cliente (verificado con un error real inducido en la Fase 10: DB sin migrar → 500 genérico, traza solo en logs) | Ninguno conocido |

## 5. Evidence Vault (archivos)

| Amenaza | Superficie | Control implementado | Riesgo residual |
|---|---|---|---|
| Subida de malware/ejecutable | `POST /evidence` | Lista blanca de extensiones, comprobación de magic bytes, lista negra de firmas peligrosas (`MZ`, ELF, `#!`, `<script`, `<?php`) | **Sin motor antivirus/antimalware real** — declarado explícitamente, ver `docs/SECURITY.md` |
| Path traversal en el nombre de archivo | Subida/descarga | Nombre físico generado siempre por el servidor (`{organization_id}/{uuid4}.{ext}`); `sanear_nombre_original` descarta cualquier componente de ruta; `_resolver_ruta` rechaza cualquier resultado fuera del directorio base | Ninguno conocido |
| Acceso no autorizado a un archivo de otra organización | Descarga | Mismo patrón multi-tenant que el resto de la API; `404` si no pertenece a la organización del actor | Ninguno conocido |
| Manipulación silenciosa de un archivo ya almacenado | Almacenamiento en disco | SHA-256 calculado al subir y comparado bajo demanda (`/integrity`) | Ninguno automático: la comprobación es bajo demanda, no continua/programada — mejora futura razonable |
| DoS por archivos enormes | Subida | Límite de tamaño configurable (`MAX_EVIDENCE_FILE_SIZE_MB`, 20 MB por defecto), rechazo de archivos vacíos | Sin límite de número total de archivos/cuota de organización — mejora futura |

## 6. MCP

| Amenaza | Superficie | Control implementado | Riesgo residual |
|---|---|---|---|
| Abuso de herramientas MCP para saltarse la autorización | Cualquier herramienta MCP | El servidor MCP nunca accede a PostgreSQL: cada herramienta pasa por la misma REST API, el mismo `require_access`, los mismos scopes — verificado en vivo (scope insuficiente → 403 a través del propio servidor MCP desplegado) | Ninguno conocido |
| Acceso cross-tenant a través de una herramienta MCP | `get_risk`, `get_vendor`, etc. con un UUID ajeno | Mismo aislamiento que la API REST — `404`, verificado en tests (`test_mcp_server.py`) y en vivo | Ninguno conocido |
| Abuso de la herramienta de escritura (`create_risk`) | `create_risk` | Requiere scope `risks:write`; el `organization_id` se fija siempre por la credencial, nunca es un parámetro de la herramienta; genera un evento de auditoría (`create_risk`) igual que si lo creara un humano | Ninguno conocido |
| Exposición de información sensible en la respuesta de una herramienta | Cualquier herramienta | Nunca se expone el secreto de la propia credencial; `list_evidence`/`get_evidence` nunca devuelven el contenido binario del archivo, solo metadatos | Ninguno conocido |
| "Prompt/tool abuse": un modelo de lenguaje mal instruido invoca `create_risk` repetidamente o con datos basura | `create_risk` | Rate limiting por credencial (120/60s); validación de tipos/enum en el esquema de la herramienta y, de forma independiente, en la REST API | El contenido semántico de un riesgo creado por un LLM no se valida por "sensatez" (p. ej. un `title` sin sentido) — es responsabilidad de quien opera el cliente MCP, documentado en `docs/MCP.md` |
| Servidor MCP comprometido | Contenedor `grcplatform-mcp` | No tiene ninguna credencial de PostgreSQL ni el driver instalado (verificado: `docker exec mcp env`, `pip list`); solo hereda los scopes de la credencial que usa | Un compromiso del contenedor MCP filtraría como mucho el `GRC_MCP_TOKEN` configurado — impacto acotado a los scopes de esa credencial, revocable en segundos |

## 7. Infraestructura

| Amenaza | Superficie | Control implementado | Riesgo residual |
|---|---|---|---|
| PostgreSQL expuesto públicamente | Puerto 5432 | En desarrollo se publica en `5433` del host (conveniencia local); en producción (`docker-compose.prod.yml`) **no se publica ningún puerto** — solo alcanzable dentro de la red interna de Docker, verificado (`docker compose ps` sin `PORTS` para postgres/backend/mcp en producción) | Ninguno en producción; en desarrollo, riesgo aceptado (entorno local, no público) |
| Contenedor comprometido con privilegios de root | Cualquier contenedor | `backend` y `mcp` corren como usuario no-root (`appuser`), verificado en Docker real (`whoami` dentro del contenedor); `frontend` (solo el servidor de desarrollo Vite) corre como root, excepción documentada — no existe en producción, sustituido por `nginx` sirviendo estáticos | El `frontend` de desarrollo como root es un riesgo aceptado y acotado a la máquina de desarrollo local |
| Secretos commiteados a Git | Repositorio | Búsqueda exhaustiva realizada (Fase 10); `.env`/`.env.prod` excluidos por `.gitignore`; solo `.env*.example` con placeholders | Depende de la disciplina futura del equipo — mitigado con revisión antes de cada commit (`git status`/`git diff` antes de `git add`) |
| Dependencias con vulnerabilidades conocidas | `pip`/`npm` | `pip-audit`/`npm audit` ejecutados; `pyjwt` y `python-multipart` actualizados tras detectarse vulnerabilidades conocidas; `starlette`/`pytest` deliberadamente sin actualizar (romperían la compatibilidad con FastAPI, mismo conflicto documentado en la Fase 9) | Dependencias no actualizadas por compatibilidad quedan con el hallazgo documentado, no oculto |
| Ausencia de HTTPS | Tráfico en tránsito | `docker-compose.prod.yml` + Nginx con terminación TLS, verificado end-to-end con un certificado de prueba (login, consulta autenticada y cabeceras de seguridad funcionando sobre HTTPS real) | **No verificado con un dominio público y un certificado real de Let's Encrypt** (sin acceso a un dominio en este entorno) — ver categorización en el informe final |
| Pérdida de datos (fallo de disco, error humano) | PostgreSQL + almacenamiento de evidencias | `scripts/backup.sh`/`scripts/restore.sh`, probados de extremo a extremo (backup real → restauración en un stack aislado → verificación de datos e integridad SHA-256 de una evidencia) | Sin automatización de backups periódicos (cron) todavía — documentado como recomendación en `docs/DEPLOYMENT.md` |

## Resumen de riesgo residual aceptado (explícito, no oculto)

- Sin MFA para usuarios humanos.
- `localStorage` para el JWT (XSS residual si se introdujera uno en el futuro).
- Sin antivirus/antimalware real sobre Evidence Vault.
- Rate limiting por IP, no por usuario autenticado con JWT (bajo impacto: ya tiene acceso legítimo).
- Sin automatización de backups periódicos (procedimiento manual documentado y probado).
- HTTPS preparado y verificado funcionalmente, pero no contra un dominio/certificado público reales.

Ninguno de estos se presenta como "resuelto" en `docs/SECURITY.md` — están listados ahí también, bajo "Recomendado / futuro".
