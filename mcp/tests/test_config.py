"""Tests unitarios de `config.py`: lectura de variables de entorno, valores
por defecto y el error explícito cuando falta la credencial obligatoria."""

import pytest

from config import cargar_configuracion


def test_falta_grc_mcp_token_lanza_error_claro(monkeypatch):
    monkeypatch.delenv("GRC_MCP_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GRC_MCP_TOKEN"):
        cargar_configuracion()


def test_valores_por_defecto(monkeypatch):
    monkeypatch.setenv("GRC_MCP_TOKEN", "grc_secreto_de_prueba")
    monkeypatch.delenv("GRC_API_BASE_URL", raising=False)
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    monkeypatch.delenv("MCP_HTTP_PORT", raising=False)

    settings = cargar_configuracion()

    assert settings.api_base_url == "http://localhost:8000"
    assert settings.api_token == "grc_secreto_de_prueba"
    assert settings.transport == "stdio"
    assert settings.http_port == 8001


def test_variables_explicitas_se_respetan(monkeypatch):
    monkeypatch.setenv("GRC_MCP_TOKEN", "grc_otro_secreto")
    monkeypatch.setenv("GRC_API_BASE_URL", "http://backend:8000/")
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_HTTP_PORT", "9000")

    settings = cargar_configuracion()

    assert settings.api_base_url == "http://backend:8000"  # sin barra final
    assert settings.transport == "streamable-http"
    assert settings.http_port == 9000
