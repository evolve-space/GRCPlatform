import uuid
from datetime import datetime

from pydantic import BaseModel


class ComplianceScoreBreakdown(BaseModel):
    """Desglose del Compliance Score. Cada `_pct` es `None` ("Sin datos") si la
    dimensión no tiene datos aplicables. Ver `app/core/compliance_score.py`
    para la fórmula completa."""

    controls_pct: float | None
    evidence_pct: float | None
    findings_pct: float | None
    remediation_pct: float | None
    score: float | None
    level: str | None


class AttentionItem(BaseModel):
    """Un elemento de la lista "Requiere atención" del dashboard."""

    kind: str  # "risk" | "finding" | "action" | "evidence" | "vendor"
    id: uuid.UUID
    label: str
    detail: str
    severity: str
    link: str


class KpiCounts(BaseModel):
    risks_critical: int
    risks_high: int
    findings_open: int
    findings_critical_open: int
    actions_overdue: int
    evidence_expiring_soon: int
    vendors_critical: int


class DashboardSummary(BaseModel):
    generated_at: datetime
    kpis: KpiCounts
    compliance_score: ComplianceScoreBreakdown
    attention: list[AttentionItem]


class RiskLevelCounts(BaseModel):
    bajo: int
    medio: int
    alto: int
    critico: int


class RiskDashboard(BaseModel):
    total: int
    by_level: RiskLevelCounts
    by_status: dict[str, int]
    by_treatment: dict[str, int]
    review_overdue: int
    review_due_soon: int


class ControlsByStatus(BaseModel):
    not_implemented: int
    partially_implemented: int
    implemented: int
    not_applicable: int


class FrameworkScore(BaseModel):
    id: uuid.UUID
    short_name: str
    name: str
    controls_pct: float | None
    evidence_pct: float | None
    score: float | None
    level: str | None


class ComplianceDashboard(BaseModel):
    total_controls: int
    by_status: ControlsByStatus
    by_category: dict[str, int]
    implemented_without_evidence: int
    compliance_score: ComplianceScoreBreakdown
    frameworks: list[FrameworkScore]


class EvidenceAttentionItem(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    classification: str
    expires_at: str | None


class EvidenceDashboard(BaseModel):
    total: int
    active: int
    archived: int
    expiring_soon: int
    expired: int
    by_classification: dict[str, int]
    by_type: dict[str, int]
    needs_attention: list[EvidenceAttentionItem]


class RemediationDashboard(BaseModel):
    findings_total: int
    findings_by_severity: dict[str, int]
    findings_by_status: dict[str, int]
    findings_overdue: int
    findings_critical_open: int
    actions_total: int
    actions_by_status: dict[str, int]
    actions_by_priority: dict[str, int]
    actions_overdue: int
    remediation_rate_pct: float | None


class VendorDashboard(BaseModel):
    total: int
    active: int
    critical: int
    suspended: int
    due_diligence_pending: int
    review_overdue: int
    review_due_soon: int
    by_criticality: dict[str, int]
    by_due_diligence: dict[str, int]
