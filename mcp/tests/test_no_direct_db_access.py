"""Prueba arquitectónica obligatoria de la Fase 9: el servidor MCP NUNCA
accede directamente a PostgreSQL. Toda operación debe pasar por la REST API
de GRCPlatform (ver docs/MCP.md y docs/ARCHITECTURE.md).

No necesita base de datos, FastAPI ni el SDK MCP: analiza estáticamente el
código fuente del propio paquete `mcp/`."""

import ast
from pathlib import Path

_MCP_DIR = Path(__file__).resolve().parent.parent
_PROHIBIDOS = {"sqlalchemy", "psycopg", "psycopg2", "asyncpg", "app"}


def _modulos_python() -> list[Path]:
    return [
        ruta
        for ruta in _MCP_DIR.rglob("*.py")
        if "tests" not in ruta.relative_to(_MCP_DIR).parts and ".venv" not in ruta.parts
    ]


def test_ningun_modulo_importa_sqlalchemy_ni_modelos_del_backend():
    for ruta in _modulos_python():
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                raices = {alias.name.split(".")[0] for alias in nodo.names}
            elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
                raices = {nodo.module.split(".")[0]}
            else:
                continue
            interseccion = raices & _PROHIBIDOS
            assert not interseccion, f"{ruta} importa {interseccion}, prohibido en el paquete mcp/"


def test_requirements_no_incluye_drivers_de_base_de_datos():
    contenido = (_MCP_DIR / "requirements.txt").read_text(encoding="utf-8").lower()
    for paquete in ("sqlalchemy", "psycopg", "asyncpg"):
        assert paquete not in contenido


def test_ningun_modulo_lee_database_url():
    """Ningún módulo lee realmente la variable de entorno DATABASE_URL (los
    docstrings SÍ pueden mencionarla al explicar precisamente que no se usa,
    p. ej. en `server.py`; por eso se analiza el AST, no un `in` de texto)."""
    for ruta in _modulos_python():
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            argumentos = [a.value for a in nodo.args if isinstance(a, ast.Constant) and a.value == "DATABASE_URL"]
            if argumentos:
                raise AssertionError(f"{ruta} lee DATABASE_URL en tiempo de ejecución, prohibido en el paquete mcp/")


def test_config_solo_expone_credenciales_de_la_rest_api_no_de_postgres():
    from config import McpSettings

    campos = set(McpSettings.__dataclass_fields__.keys())
    assert campos == {"api_base_url", "api_token", "transport", "http_port"}
