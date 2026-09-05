# Despliegue en producción

Guía completa desde un PC local hasta la aplicación pública, sirviendo de
referencia real (no solo teórica) — todo lo descrito aquí, salvo la
emisión de un certificado Let's Encrypt contra un dominio público, se
verificó de extremo a extremo durante la Fase 10 usando un certificado de
prueba. Ver la categorización exacta de qué está verificado en
[docs/SECURITY.md](SECURITY.md).

```
PC local → Git → GitHub → Servidor Linux (SSH + RSA) → Docker →
Nginx → HTTPS → Aplicación pública
```

## 1. Requisitos del servidor

- Linux (Ubuntu 22.04/24.04 LTS recomendado; cualquier distribución con
  Docker soportado sirve).
- 2 vCPU / 4 GB RAM como mínimo razonable para este stack (Postgres +
  backend + MCP + Nginx).
- Docker Engine 24+ y el plugin Docker Compose (`docker compose version`).
- Un dominio propio apuntando a la IP del servidor (registro DNS `A`).
- Puerto 22 (SSH), 80 y 443 accesibles desde Internet.

## 2. Acceso al servidor: SSH + par de claves RSA

No uses contraseña para SSH. Desde tu PC local:

```bash
ssh-keygen -t rsa -b 4096 -C "tu-email@ejemplo.com" -f ~/.ssh/grcplatform_deploy
```

Copia la clave pública al servidor (con acceso inicial por contraseña o
por la consola del proveedor):

```bash
ssh-copy-id -i ~/.ssh/grcplatform_deploy.pub usuario@tu-servidor
```

En el servidor, desactiva el login por contraseña una vez confirmado que
el acceso por clave funciona (`/etc/ssh/sshd_config`:
`PasswordAuthentication no`, luego `sudo systemctl restart sshd`). **Nunca
subas la clave privada (`grcplatform_deploy`, sin `.pub`) a ningún sitio.**

## 3. Firewall

Con `ufw` (o el equivalente de tu proveedor):

```bash
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP -> redirige a HTTPS
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable
```

**No abras el puerto 5432** (PostgreSQL) ni ningún otro puerto interno:
`docker-compose.prod.yml` ya no los publica al host, así que ni siquiera
hace falta bloquearlos explícitamente — pero si en algún momento se
depurara temporalmente publicando uno, ciérralo de nuevo al terminar.

Si una integración externa necesitara alcanzar el servidor MCP
directamente (fuera del propio backend), expón su puerto de forma
explícita y documentada, nunca por comodidad — y considera restringirlo
por IP de origen en el firewall.

## 4. Instalar Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
# cierra sesión y vuelve a entrar para que el grupo surta efecto
docker compose version
```

## 5. Obtener el código

```bash
git clone https://github.com/tu-usuario/GRCPlatform.git
cd GRCPlatform
```

## 6. Configurar variables de entorno

```bash
cp .env.prod.example .env.prod
```

Edita `.env.prod` y sustituye **todos** los valores:

- `DOMAIN`: tu dominio real (p. ej. `grcplatform.tuempresa.com`).
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`: credenciales
  reales, nunca las de desarrollo.
- `SECRET_KEY`: genera un valor propio de al menos 32 caracteres —
  `ENVIRONMENT=production` rechaza el arranque si no lo cumple:

  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- `GRC_MCP_TOKEN`: se genera DESPUÉS del primer arranque (paso 9) — déjalo
  con el placeholder por ahora si es la primera vez.

`.env.prod` nunca se commitea (ya excluido en `.gitignore`).

## 7. Certificados TLS (Let's Encrypt)

Antes del primer arranque necesitas un certificado válido en
`nginx/certs/fullchain.pem` y `nginx/certs/privkey.pem` (montados de solo
lectura en el contenedor `nginx`). La forma más simple con Certbot en modo
standalone (parando temporalmente cualquier cosa en el puerto 80):

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d tu-dominio-real.example.com
sudo mkdir -p nginx/certs
sudo cp /etc/letsencrypt/live/tu-dominio-real.example.com/fullchain.pem nginx/certs/
sudo cp /etc/letsencrypt/live/tu-dominio-real.example.com/privkey.pem nginx/certs/
sudo chown "$USER":"$USER" nginx/certs/*.pem
```

**Renovación**: los certificados de Let's Encrypt caducan a los 90 días.
Programa una tarea (`cron`/`systemd timer`) que ejecute `certbot renew` y
vuelva a copiar los archivos a `nginx/certs/`, seguido de
`docker compose -f docker-compose.prod.yml restart nginx`. `nginx/certs/`
está excluido de git (`.gitignore`) — **nunca subir un certificado privado
al repositorio**.

## 8. Arrancar el stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

Los 4 servicios (`postgres`, `backend`, `mcp`, `nginx`) deben quedar en
estado `healthy` (postgres/backend/mcp) o `running` (nginx). Comprueba:

```bash
curl -I https://tu-dominio-real.example.com/health
```

## 9. Migraciones y datos iniciales

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

**No ejecutes `python -m app.db.seed` en un despliegue real** — ese script
crea la organización y los usuarios de demostración (con contraseña
pública `Demo1234!`), pensados solo para desarrollo/demo. En producción,
crea el primer usuario Admin real directamente en la base de datos o
mediante un script propio equivalente (fuera del alcance de esta fase).

Con un usuario Admin real ya creado, genera la credencial de integración
para el servidor MCP:

```bash
curl -X POST https://tu-dominio-real.example.com/api/v1/integration-tokens \
  -H "Authorization: Bearer $JWT_ADMIN" -H "Content-Type: application/json" \
  -d '{"name": "Servidor MCP", "scopes": ["risks:read","controls:read","evidence:read","findings:read","remediation:read","vendors:read","dashboard:read","compliance:read"]}'
```

Copia el campo `token` de la respuesta (solo se muestra una vez) a
`GRC_MCP_TOKEN` en `.env.prod`, y reinicia el servicio `mcp`:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d mcp
```

## 10. Backups

Ver [scripts/backup.sh](../scripts/backup.sh) y
[scripts/restore.sh](../scripts/restore.sh) — probados de extremo a
extremo (backup real → restauración en un stack aislado → verificación de
integridad SHA-256 de una evidencia, ver `docs/SECURITY.md`).

```bash
COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup.sh /ruta/segura/backups/$(date +%Y%m%d)
```

- **Frecuencia recomendada**: diaria (cron), más una copia manual antes de
  cualquier actualización o migración.
- **Dónde almacenar**: fuera del propio servidor (otro host, almacenamiento
  objeto tipo S3, etc.) — un backup que vive solo en el disco que puede
  fallar no es un backup real.
- **Cifrado recomendado**: cifra el directorio de backup antes de
  transferirlo fuera del servidor (p. ej. `gpg --symmetric` o cifrado del
  propio bucket de almacenamiento en destino).
- **Retención**: al menos 7 backups diarios + 4 semanales, ajustable según
  el volumen de cambios real.
- **Restauración**: `COMPOSE_FILE=docker-compose.prod.yml ./scripts/restore.sh /ruta/al/backup`
  — sobrescribe la base de datos y el almacenamiento de evidencias del
  stack indicado; verifica siempre en un entorno de prueba antes de
  restaurar sobre producción si tienes dudas.
- **Riesgo si no se hace**: pérdida total e irrecuperable de todos los
  datos GRC y evidencias ante un fallo de disco, un error humano, o un
  incidente de seguridad destructivo.

Ejemplo de cron diario a las 3:00:

```
0 3 * * * cd /ruta/al/repo && COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup.sh /ruta/segura/backups/$(date +\%Y\%m\%d) >> /var/log/grcplatform-backup.log 2>&1
```

## 11. Actualización

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod build
COMPOSE_FILE=docker-compose.prod.yml ./scripts/backup.sh /ruta/segura/backups/pre-update-$(date +%Y%m%d_%H%M%S)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Siempre backup antes de actualizar, especialmente si la actualización
incluye una migración de base de datos.

## 12. Rollback básico

Si una actualización falla:

```bash
git checkout <commit-o-tag-anterior>
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Si además la migración de base de datos de la versión nueva ya se aplicó
y es incompatible con el código anterior, restaura el backup pre-
actualización (paso 10) en vez de solo volver el código atrás — un
rollback de código sin revertir también el esquema puede dejar la
aplicación en un estado inconsistente.

## 13. Verificación post-despliegue

```bash
curl -I https://tu-dominio-real.example.com/health
curl -I https://tu-dominio-real.example.com/            # frontend
curl -I https://tu-dominio-real.example.com/api/v1/auth/login  # backend vía proxy
docker compose -f docker-compose.prod.yml --env-file .env.prod ps  # todo "healthy"
```

Comprueba también en el navegador: login, un par de páginas del panel, y
que las cabeceras de seguridad (`X-Frame-Options`, `Strict-Transport-
Security`, etc.) están presentes (herramientas de desarrollador del
navegador → pestaña Network → cabeceras de respuesta).
