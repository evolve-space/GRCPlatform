#!/usr/bin/env bash
# Restauración de GRCPlatform desde un backup creado con scripts/backup.sh.
#
# ADVERTENCIA: sobrescribe la base de datos y el almacenamiento de
# evidencias del stack indicado. Pensado para restaurar en un entorno
# nuevo/de prueba, o en una recuperación de desastre real — no lo ejecutes
# contra producción sin estar seguro de que es lo que quieres.
#
# Uso:
#   ./scripts/restore.sh <directorio_de_backup>

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ORIGEN="${1:?Uso: ./scripts/restore.sh <directorio_de_backup>}"

if [ ! -f "$ORIGEN/postgres.sql" ] || [ ! -f "$ORIGEN/evidence.tar.gz" ]; then
  echo "No se encuentran postgres.sql y evidence.tar.gz en $ORIGEN" >&2
  exit 1
fi

# "-a" (incluye contenedores parados): un intento de restauración previo
# pudo dejar el backend parado a mitad de proceso (comprobado) — hay que
# poder encontrarlo igualmente para poder arrancarlo de nuevo.
POSTGRES_CID=$(docker compose -f "$COMPOSE_FILE" ps -aq postgres)
BACKEND_CID=$(docker compose -f "$COMPOSE_FILE" ps -aq backend)
if [ -z "$POSTGRES_CID" ] || [ -z "$BACKEND_CID" ]; then
  echo "No se encuentran los contenedores de postgres/backend (¿está arrancado el stack?)." >&2
  exit 1
fi

# El backend mantiene un pool de conexiones abierto a la base de datos —
# hay que pararlo antes de poder recrearla (DROP DATABASE falla si alguien
# la tiene abierta). Se reinicia al final, no se deja parado.
echo "==> Deteniendo backend para poder restaurar la base de datos"
docker compose -f "$COMPOSE_FILE" stop backend

echo "==> Restaurando PostgreSQL desde $ORIGEN/postgres.sql"
docker exec "$POSTGRES_CID" sh -c \
  'psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";" && psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$POSTGRES_DB\";"'
docker exec -i "$POSTGRES_CID" sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' < "$ORIGEN/postgres.sql"

echo "==> Reiniciando backend"
docker compose -f "$COMPOSE_FILE" start backend

# El backend tiene que estar corriendo para poder usar "docker exec" contra
# él — restaurar los archivos de evidencias no necesita que esté parado
# (a diferencia de la base de datos, no mantiene los archivos abiertos).
echo "==> Restaurando almacenamiento de evidencias desde $ORIGEN/evidence.tar.gz"
docker exec "$BACKEND_CID" sh -c 'rm -rf /app/storage/evidence/*'
docker exec -i "$BACKEND_CID" tar -xzf - -C /app/storage < "$ORIGEN/evidence.tar.gz"

echo "==> Restauración completa. Verifica con:"
echo "    curl http://localhost:8000/health"
echo "    (o el dominio real en producción)"
