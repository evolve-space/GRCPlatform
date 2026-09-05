"""Abstracción de almacenamiento de archivos de evidencias.

``LocalStorageService`` es la única implementación por ahora (almacenamiento
en disco local, fuera del árbol servido por el frontend). El resto de la
aplicación solo depende de esta interfaz (guardar/leer/eliminar/generar
storage_key), de modo que sustituirla por S3/MinIO en el futuro no debería
requerir cambios en la lógica de negocio de Evidence.
"""

import uuid
from pathlib import Path

from app.core.config import settings


class StorageError(Exception):
    """Error de almacenamiento (p. ej. una storage_key que intenta escapar del directorio base)."""


class LocalStorageService:
    def __init__(self, base_path: str | None = None) -> None:
        self._base_path = Path(base_path or settings.EVIDENCE_STORAGE_PATH).resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)

    def generar_storage_key(self, organization_id: uuid.UUID, extension: str) -> str:
        """Genera una clave de almacenamiento segura. Nunca se deriva del nombre del usuario."""
        return f"{organization_id}/{uuid.uuid4().hex}{extension}"

    def _resolver_ruta(self, storage_key: str) -> Path:
        """Resuelve storage_key a una ruta absoluta, garantizando que no escapa de la base.

        Defensa en profundidad: aunque storage_key siempre se genera en el
        servidor (nunca a partir de una ruta recibida del cliente), esta
        comprobación impide cualquier path traversal si en el futuro se
        introdujera un error en quien llama a este servicio.
        """
        candidata = (self._base_path / storage_key).resolve()
        try:
            candidata.relative_to(self._base_path)
        except ValueError:
            raise StorageError("Ruta de almacenamiento inválida.") from None
        return candidata

    def guardar(self, storage_key: str, contenido: bytes) -> None:
        ruta = self._resolver_ruta(storage_key)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)

    def leer(self, storage_key: str) -> bytes:
        ruta = self._resolver_ruta(storage_key)
        if not ruta.is_file():
            raise FileNotFoundError(storage_key)
        return ruta.read_bytes()

    def eliminar(self, storage_key: str) -> None:
        try:
            ruta = self._resolver_ruta(storage_key)
        except StorageError:
            return
        ruta.unlink(missing_ok=True)

    def existe(self, storage_key: str) -> bool:
        try:
            ruta = self._resolver_ruta(storage_key)
        except StorageError:
            return False
        return ruta.is_file()


storage_service = LocalStorageService()
