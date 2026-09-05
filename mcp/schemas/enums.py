"""Alias de tipos `Literal` que reflejan EXACTAMENTE los enums de la REST API
de GRCPlatform (backend/app/models/*.py). Tipar los parámetros de las
herramientas MCP con estos `Literal` (en vez de `str`) da una primera capa
real de validación en el propio esquema de la herramienta — el cliente MCP
(Claude) ve las opciones válidas de antemano — mientras que la REST API
sigue siendo la autoridad final que vuelve a validar en el servidor."""

from typing import Literal

RiskLevel = Literal["bajo", "medio", "alto", "critico"]
RiskStatus = Literal["identified", "in_evaluation", "in_treatment", "accepted", "closed"]
RiskTreatment = Literal["mitigate", "avoid", "transfer", "accept"]

ControlStatus = Literal["not_implemented", "partially_implemented", "implemented", "not_applicable"]

DataClassification = Literal["public", "internal", "confidential", "restricted"]
EvidenceStatus = Literal["active", "archived"]

Criticality = Literal["low", "medium", "high", "critical"]  # severidad/prioridad/criticidad (mismo enum)

FindingType = Literal[
    "audit_internal", "audit_external", "risk_assessment", "incident", "control_review", "compliance", "vendor", "other"
]
FindingStatus = Literal["open", "under_review", "remediation", "pending_validation", "closed", "accepted"]

ActionStatus = Literal["pending", "in_progress", "blocked", "completed", "cancelled"]

VendorStatus = Literal["prospect", "active", "suspended", "terminated"]
VendorDueDiligenceStatus = Literal[
    "pending", "in_review", "approved", "approved_with_conditions", "rejected", "expired"
]
