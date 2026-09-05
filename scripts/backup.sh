#!/usr/bin/env bash
# Backup de GRCPlatform: PostgreSQL + almacenamiento de evidencias.
#
# Un backup completo NECESITA ambas partes — la base de datos referencia
# evidencias por su storage_key, pero el contenido físico de los archivos
# vive en el volumen de almacenamiento, no en PostgreSQL. Restaurar solo
# una de las dos deja el sistema inconsistente (registros sin archivo, o
# archivos huérfanos sin metadatos). Ver docs/DEPLOYMENT.md.
#
# Uso:
#   ./scripts/backup.sh [directorio_destino]
#
# Por defecto usa ./backups/<timestamp>/. Pensado para producción
# (docker-compose.prod.yml, contenedores sin sufijo de proyecto fijo — se
# detectan por nombre de servicio con `docker compose ps -q`), pero funciona
# igual contra el stack de desarrollo.

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DESTINO="${1:-backups/$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$DESTINO"

echo "==> Backup de PostgreSQL"
POSTGRES_CID=$(docker compose -f "$COMPOSE_FILE" ps -q postgres)
if [ -z "$POSTGRES_CID" ]; then
  echo "No se encuentra el contenedor de postgres (¿está arrancado el stack?)." >&2
  exit 1
fi
# --no-owner --no-privileges: el dump no debe fijar el rol de PostgreSQL de
# origen en los objetos (ALTER TABLE ... OWNER TO ...) — si se restaura en
# un entorno con un usuario distinto (habitual al restaurar en un servidor
# nuevo o en una prueba de recuperación), esas sentencias fallarían con
# "role ... does not exist" para cada tabla/tipo (comprobado). Sin
# propietario/privilegios explícitos, todo pasa a pertenecer a quien
# ejecuta la restauración, que es exactamente lo que se quiere.
docker exec "$POSTGRES_CID" sh -c 'pg_dump --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$DESTINO/postgres.sql"
echo "    -> $DESTINO/postgres.sql ($(du -h "$DESTINO/postgres.sql" | cut -f1))"

echo "==> Backup del almacenamiento de evidencias"
BACKEND_CID=$(docker compose -f "$COMPOSE_FILE" ps -q backend)
if [ -z "$BACKEND_CID" ]; then
  echo "No se encuentra el contenedor de backend." >&2
  exit 1
fi
docker exec "$BACKEND_CID" tar -czf - -C /app/storage evidence > "$DESTINO/evidence.tar.gz"
echo "    -> $DESTINO/evidence.tar.gz ($(du -h "$DESTINO/evidence.tar.gz" | cut -f1))"

echo "==> Backup completo en: $DESTINO"
echo "    Recuerda: cifra y copia este directorio fuera del servidor (ver docs/DEPLOYMENT.md)."
