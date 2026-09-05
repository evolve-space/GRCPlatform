"""Tablas intermedias para relaciones muchos-a-muchos entre Control/Evidence/
Finding/RemediationAction y Riesgo/Activo/Requisito/Evidencia. Se modelan como
tablas planas (sin columnas extra) porque no necesitan atributos propios."""

from sqlalchemy import Column, ForeignKey, Table, Uuid

from app.core.database import Base

control_risks = Table(
    "control_risks",
    Base.metadata,
    Column("control_id", Uuid, ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True),
    Column("risk_id", Uuid, ForeignKey("risks.id", ondelete="CASCADE"), primary_key=True),
)

control_assets = Table(
    "control_assets",
    Base.metadata,
    Column("control_id", Uuid, ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", Uuid, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)

control_requirements = Table(
    "control_requirements",
    Base.metadata,
    Column("control_id", Uuid, ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True),
    Column("requirement_id", Uuid, ForeignKey("requirements.id", ondelete="CASCADE"), primary_key=True),
)

evidence_controls = Table(
    "evidence_controls",
    Base.metadata,
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
    Column("control_id", Uuid, ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True),
)

evidence_risks = Table(
    "evidence_risks",
    Base.metadata,
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
    Column("risk_id", Uuid, ForeignKey("risks.id", ondelete="CASCADE"), primary_key=True),
)

evidence_assets = Table(
    "evidence_assets",
    Base.metadata,
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", Uuid, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)

evidence_requirements = Table(
    "evidence_requirements",
    Base.metadata,
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
    Column("requirement_id", Uuid, ForeignKey("requirements.id", ondelete="CASCADE"), primary_key=True),
)

finding_risks = Table(
    "finding_risks",
    Base.metadata,
    Column("finding_id", Uuid, ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
    Column("risk_id", Uuid, ForeignKey("risks.id", ondelete="CASCADE"), primary_key=True),
)

finding_controls = Table(
    "finding_controls",
    Base.metadata,
    Column("finding_id", Uuid, ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
    Column("control_id", Uuid, ForeignKey("controls.id", ondelete="CASCADE"), primary_key=True),
)

finding_assets = Table(
    "finding_assets",
    Base.metadata,
    Column("finding_id", Uuid, ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", Uuid, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)

finding_requirements = Table(
    "finding_requirements",
    Base.metadata,
    Column("finding_id", Uuid, ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
    Column("requirement_id", Uuid, ForeignKey("requirements.id", ondelete="CASCADE"), primary_key=True),
)

finding_evidence = Table(
    "finding_evidence",
    Base.metadata,
    Column("finding_id", Uuid, ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
)

remediation_action_evidences = Table(
    "remediation_action_evidences",
    Base.metadata,
    Column("action_id", Uuid, ForeignKey("remediation_actions.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
)

vendor_risks = Table(
    "vendor_risks",
    Base.metadata,
    Column("vendor_id", Uuid, ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True),
    Column("risk_id", Uuid, ForeignKey("risks.id", ondelete="CASCADE"), primary_key=True),
)

vendor_evidence = Table(
    "vendor_evidence",
    Base.metadata,
    Column("vendor_id", Uuid, ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
)

vendor_findings = Table(
    "vendor_findings",
    Base.metadata,
    Column("vendor_id", Uuid, ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True),
    Column("finding_id", Uuid, ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True),
)
