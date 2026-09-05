"""Registro de todas las herramientas MCP sobre una instancia de servidor."""

from typing import Any

from client import GRCApiClient

from . import (
    controls,
    dashboard,
    evidence,
    findings,
    remediation,
    risks,
    search,
    vendors,
)


def register_all_tools(mcp: Any, client: GRCApiClient) -> None:
    risks.register(mcp, client)
    controls.register(mcp, client)
    evidence.register(mcp, client)
    findings.register(mcp, client)
    remediation.register(mcp, client)
    vendors.register(mcp, client)
    dashboard.register(mcp, client)
    search.register(mcp, client)
