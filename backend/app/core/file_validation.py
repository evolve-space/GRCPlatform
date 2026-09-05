"""Validación de archivos subidos como evidencia.

Objetivo: una primera barrera de seguridad razonable para una plataforma GRC,
no un antivirus. Se aplica una lista blanca de tipos permitidos, una
comprobación de "magic bytes" para los formatos binarios, y una lista negra
de firmas de archivos ejecutables/script aplicada a cualquier subida,
independientemente del tipo declarado por el cliente.
"""

from pathlib import PurePosixPath

# extensión -> tipos MIME válidos para esa extensión.
TIPOS_PERMITIDOS: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    ".csv": ("text/csv", "application/vnd.ms-excel", "text/plain"),
    ".txt": ("text/plain",),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
}

# mime -> posibles firmas iniciales ("magic bytes") de ese formato.
_FIRMAS_POR_MIME: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    # DOCX/XLSX son contenedores ZIP (Office Open XML).
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (b"PK\x03\x04",),
}

# Firmas de archivos ejecutables/script, prohibidas sin importar el tipo declarado.
_FIRMAS_PELIGROSAS: tuple[bytes, ...] = (
    b"MZ",  # ejecutables Windows (.exe, .dll)
    b"\x7fELF",  # ejecutables Linux
    b"#!",  # scripts con shebang (.sh, etc.)
    b"<script",
    b"<SCRIPT",
    b"<?php",
)


class ArchivoInvalido(Exception):
    """Se lanza cuando un archivo subido no supera las validaciones de seguridad."""


def sanear_nombre_original(filename: str) -> str:
    """Devuelve solo el nombre de archivo, sin componentes de ruta ni bytes nulos.

    Nunca se usa para construir una ruta física: es puramente un metadato para
    mostrar en pantalla y como nombre de descarga.
    """
    nombre = PurePosixPath(filename.replace("\\", "/")).name
    nombre = nombre.replace("\x00", "").strip()
    if not nombre or nombre in {".", ".."}:
        raise ArchivoInvalido("El nombre del archivo no es válido.")
    return nombre[:255]


def determinar_tipo_seguro(
    nombre_saneado: str, contenido: bytes, tamano_maximo_bytes: int
) -> tuple[str, str]:
    """Valida el contenido de un archivo y determina su tipo MIME real.

    Nunca confía únicamente en el ``Content-Type`` declarado por el cliente.
    Devuelve ``(mime_type, extension)`` o lanza ``ArchivoInvalido``.
    """
    if len(contenido) == 0:
        raise ArchivoInvalido("El archivo está vacío.")
    if len(contenido) > tamano_maximo_bytes:
        limite_mb = tamano_maximo_bytes // (1024 * 1024)
        raise ArchivoInvalido(f"El archivo supera el tamaño máximo permitido ({limite_mb} MB).")

    inicio = contenido[:32]
    if any(inicio.startswith(firma) for firma in _FIRMAS_PELIGROSAS):
        raise ArchivoInvalido("El contenido del archivo no está permitido por motivos de seguridad.")

    extension = PurePosixPath(nombre_saneado).suffix.lower()
    if extension not in TIPOS_PERMITIDOS:
        etiqueta = extension or "(sin extensión)"
        raise ArchivoInvalido(f"Extensión de archivo no permitida: {etiqueta}.")

    tipos_validos = TIPOS_PERMITIDOS[extension]

    firmas_binarias = [
        firmas for mime in tipos_validos if (firmas := _FIRMAS_POR_MIME.get(mime)) is not None
    ]
    if firmas_binarias:
        firmas_esperadas = firmas_binarias[0]
        if not any(contenido.startswith(firma) for firma in firmas_esperadas):
            raise ArchivoInvalido(
                "El contenido del archivo no coincide con su extensión (posible manipulación)."
            )
        mime_type = next(mime for mime in tipos_validos if mime in _FIRMAS_POR_MIME)
    else:
        # .csv/.txt: no existe una firma binaria fiable; se exige que decodifique como texto.
        try:
            contenido.decode("utf-8")
        except UnicodeDecodeError:
            raise ArchivoInvalido(
                "El archivo de texto no tiene una codificación válida (se esperaba UTF-8)."
            ) from None
        mime_type = tipos_validos[0]

    return mime_type, extension
