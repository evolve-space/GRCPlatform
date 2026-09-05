from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import (
    assets,
    audit_logs,
    auth,
    controls,
    dashboard,
    evidence,
    findings,
    frameworks,
    integration_tokens,
    mappings,
    organizations,
    remediation_actions,
    requirements,
    risks,
    users,
    vendors,
)
from app.core.config import settings
from app.core.database import engine
from app.core.errors import registrar_manejadores_de_error
from app.core.security_headers import registrar_cabeceras_de_seguridad

app = FastAPI(
    title="GRCPlatform API",
    description="API REST de GRCPlatform — Plataforma de Gestión de Riesgos y Cumplimiento (GRC).",
    version="0.1.0",
)

registrar_manejadores_de_error(app)
registrar_cabeceras_de_seguridad(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuarios"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["Organizaciones"])
app.include_router(assets.router, prefix="/api/v1/assets", tags=["Activos"])
app.include_router(risks.router, prefix="/api/v1/risks", tags=["Riesgos"])
app.include_router(controls.router, prefix="/api/v1/controls", tags=["Controles"])
app.include_router(frameworks.router, prefix="/api/v1/frameworks", tags=["Marcos de cumplimiento"])
app.include_router(requirements.router, prefix="/api/v1/requirements", tags=["Requisitos"])
app.include_router(mappings.router, prefix="/api/v1/mappings", tags=["Mappings"])
app.include_router(evidence.router, prefix="/api/v1/evidence", tags=["Evidencias"])
app.include_router(findings.router, prefix="/api/v1/findings", tags=["Hallazgos"])
app.include_router(
    remediation_actions.router, prefix="/api/v1/remediation-actions", tags=["Acciones de remediación"]
)
app.include_router(vendors.router, prefix="/api/v1/vendors", tags=["Proveedores"])
app.include_router(audit_logs.router, prefix="/api/v1/audit-logs", tags=["Registro de auditoría"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(
    integration_tokens.router, prefix="/api/v1/integration-tokens", tags=["Credenciales de integración"]
)


@app.get("/")
def read_root() -> dict:
    return {
        "servicio": settings.APP_NAME,
        "estado": "en funcionamiento",
        "entorno": settings.ENVIRONMENT,
    }


@app.get("/health")
def health_check() -> dict:
    """Comprueba el estado del servicio y la conectividad con la base de datos."""
    db_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "estado": "ok" if db_status == "ok" else "degradado",
        "base_de_datos": db_status,
    }
