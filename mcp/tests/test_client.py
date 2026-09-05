"""Tests unitarios de `client.py`: construcción de peticiones (limpieza de
parámetros `None`, cabecera `X-API-Key`), parseo de respuestas correctas y
manejo de los distintos formatos de error de la REST API — sin red real, con
`httpx.MockTransport`."""

import httpx
import pytest

from client import GRCApiClient, GRCApiError
from config import McpSettings


def _settings() -> McpSettings:
    return McpSettings(api_base_url="http://api.test", api_token="grc_test_token", transport="stdio", http_port=8001)


@pytest.mark.asyncio
async def test_envia_cabecera_x_api_key():
    capturada = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        capturada["headers"] = request.headers
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 20})

    client = GRCApiClient(_settings(), transport=httpx.MockTransport(_handler))
    await client.list_risks()
    await client.aclose()

    assert capturada["headers"]["x-api-key"] == "grc_test_token"


@pytest.mark.asyncio
async def test_parametros_none_no_se_envian_en_la_query():
    capturada = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        capturada["url"] = str(request.url)
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 20})

    client = GRCApiClient(_settings(), transport=httpx.MockTransport(_handler))
    await client.list_risks(search=None, level="critico", page=1, page_size=20)
    await client.aclose()

    assert "search" not in capturada["url"]
    assert "level=critico" in capturada["url"]


@pytest.mark.asyncio
async def test_respuesta_correcta_se_devuelve_como_dict():
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "abc", "title": "Riesgo de prueba"})

    client = GRCApiClient(_settings(), transport=httpx.MockTransport(_handler))
    resultado = await client.get_risk("abc")
    await client.aclose()

    assert resultado == {"id": "abc", "title": "Riesgo de prueba"}


@pytest.mark.asyncio
async def test_error_con_formato_normalizado_code_message():
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": {"code": "NOT_FOUND", "message": "Riesgo no encontrado."}})

    client = GRCApiClient(_settings(), transport=httpx.MockTransport(_handler))
    with pytest.raises(GRCApiError) as exc_info:
        await client.get_risk("no-existe")
    await client.aclose()

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "NOT_FOUND"
    assert exc_info.value.message == "Riesgo no encontrado."


@pytest.mark.asyncio
async def test_error_con_formato_nativo_de_validacion_pydantic():
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": [{"loc": ["query", "page_size"], "msg": "Input should be less than or equal to 100"}]},
        )

    client = GRCApiClient(_settings(), transport=httpx.MockTransport(_handler))
    with pytest.raises(GRCApiError) as exc_info:
        await client.list_risks(page_size=99999)
    await client.aclose()

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "VALIDATION_ERROR"
    assert "100" in exc_info.value.message


@pytest.mark.asyncio
async def test_error_con_detail_string_simple():
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "Error interno inesperado."})

    client = GRCApiClient(_settings(), transport=httpx.MockTransport(_handler))
    with pytest.raises(GRCApiError) as exc_info:
        await client.get_risk("x")
    await client.aclose()

    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "Error interno inesperado."


@pytest.mark.asyncio
async def test_error_sin_cuerpo_json_no_hace_crashear_el_cliente():
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    client = GRCApiClient(_settings(), transport=httpx.MockTransport(_handler))
    with pytest.raises(GRCApiError) as exc_info:
        await client.get_risk("x")
    await client.aclose()

    assert exc_info.value.status_code == 502
