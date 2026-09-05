FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fase 10 (hardening): no ejecutar el proceso de la aplicación como root.
# storage/evidence se crea aquí explícitamente (está en .dockerignore, así
# que no llega con el COPY anterior) para que exista con el propietario
# correcto ANTES de que Docker monte encima el volumen nombrado de
# producción — un volumen nombrado vacío hereda el contenido/permisos del
# directorio de la imagen en su primer uso; sin este paso, el volumen se
# crea con propietario root y `appuser` no puede escribir evidencias
# (comprobado: PermissionError real al montar `evidence_storage` en
# docker-compose.prod.yml antes de este fix).
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/storage/evidence \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
