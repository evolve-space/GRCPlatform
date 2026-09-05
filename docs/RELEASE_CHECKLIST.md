# Checklist de release (previo a publicar en GitHub)

> Estado a fecha de esta fase. Marcado `[x]` = verificado de verdad en
> este entorno (ver el informe de la fase para el detalle de cada
> verificación); `[ ]` = pendiente, nunca marcado como hecho por defecto.

## Código

- [x] Tests backend: 365/365 passing.
- [x] Tests MCP: 15/15 passing.
- [x] Ruff (backend y `mcp/`): sin incidencias.
- [x] mypy (backend: 66 archivos, `mcp/`: 20 archivos): sin incidencias.
- [x] Frontend build (`tsc -b && vite build`): OK.
- [x] ESLint: sin incidencias.
- [x] `docker compose build`: las 4 imágenes de desarrollo construyen sin error.
- [x] `docker compose up -d`: los 4 servicios arrancan (`postgres`/`backend`/`mcp` healthy, `frontend` running).
- [x] `docker-compose.prod.yml`: build y arranque verificados en un proyecto Docker aislado.

## Seguridad

- [x] Sin secretos hardcodeados en código, documentación, scripts, YAML o JSON (auditoría completa realizada).
- [x] `.env`, `.env.prod` y `backend/.env` ignorados por git y no trackeados.
- [x] `.env.example` / `.env.prod.example` / `frontend/.env.example` / `backend/.env.example` presentes, solo con placeholders.
- [x] JWT: algoritmo fijado, expiración, sin secreto por defecto inseguro.
- [x] RBAC por rol verificado en tests de cada módulo.
- [x] Scopes de credenciales de integración verificados (mínimo privilegio, expiración, revocación).
- [x] Multi-tenancy verificado (404, nunca 403, ante datos de otra organización).
- [x] Rate limiting (login, API key por IP y por credencial) verificado con tests y en vivo.
- [x] Cabeceras de seguridad HTTP presentes y verificadas en un navegador real.
- [x] Hardening de subida de archivos (lista blanca, magic bytes, tamaño, path traversal).
- [x] Contenedores `backend`/`mcp` como usuario no-root, verificado.

## GitHub (preparado, no publicado)

- [x] `README.md` reescrito en tono profesional/portfolio, con badges, ciclo GRC, arquitectura, seguridad, roadmap.
- [x] `.gitignore` revisado y verificado con `git add -A --dry-run` (227 archivos, ninguno indebido).
- [x] Documentación técnica completa y enlazada desde el README (`docs/*.md`).
- [x] `.github/workflows/ci.yml` presente (no ejecutado aún en GitHub real).
- [x] Sin secretos en ningún archivo que `git add -A` incluiría.
- [x] `docs/GITHUB_PREVIEW.md`: nombre, descripción (3 opciones + recomendación), topics, estructura, vista previa.
- [ ] Crear el repositorio remoto en GitHub (decisión del autor, fuera del alcance de esta fase).
- [ ] Elegir licencia, si se decide publicar en abierto (ver sección Licencia del README).

## Demo

- [x] Guion de demo completo y verificable con los datos reales del seed (`docs/DEMO_SCRIPT.md`): login, panel, riesgo, control, evidencia, hallazgo, acción, proveedor, auditoría, MCP, demostración de seguridad (403/404).
- [x] Guion de presentación oral (`docs/PRESENTATION_SCRIPT.md`).
- [x] Preguntas de defensa con respuestas (`docs/DEFENSE_QA.md`, 26 preguntas).

## Producción

- [x] `docker-compose.prod.yml` independiente, con nombre de proyecto propio (`grcplatform-prod`) para no colisionar con desarrollo.
- [x] Nginx como único punto de entrada público (80/443), PostgreSQL/backend/MCP sin puertos publicados.
- [x] HTTPS funcional verificado con certificado de prueba (login, API, cabeceras de seguridad incluida HSTS).
- [x] Backup y restauración probados de extremo a extremo, con verificación de integridad SHA-256 de una evidencia.
- [x] `docs/DEPLOYMENT.md` completo (servidor, SSH, firewall, TLS, migraciones, actualización, rollback).

## Pendientes antes de publicar

### Obligatorios

- Decidir la visibilidad del repositorio (público/privado) antes de crear el remoto.
- Decidir la licencia (o confirmar explícitamente "sin licencia por ahora") antes de publicar en abierto.
- Revisar una última vez `git status`/`git diff` justo antes del primer `git add` real, por si ha cambiado algo desde esta auditoría.

### Opcionales (pueden esperar al despliegue público real)

- Validar HTTPS con un dominio público y Let's Encrypt real.
- Ejecutar el pipeline de CI/CD en GitHub Actions real y sustituir el badge de CI por el dinámico.
- Automatizar backups periódicos (cron/systemd timer).
- Autenticación multifactor (MFA).
- Motor de antivirus/antimalware real sobre Evidence Vault.
- Rate limiting por usuario JWT autenticado.
