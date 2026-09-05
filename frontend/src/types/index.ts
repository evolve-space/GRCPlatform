export type UserRole = "admin" | "grc_manager" | "analyst" | "viewer";

export interface CurrentUser {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type AssetType =
  | "system"
  | "application"
  | "server"
  | "endpoint"
  | "database"
  | "service"
  | "information"
  | "process"
  | "vendor"
  | "other";

export type AssetCriticality = "low" | "medium" | "high" | "critical";
export type DataClassification = "public" | "internal" | "confidential" | "restricted";
export type AssetStatus = "active" | "inactive" | "decommissioned";

export interface Asset {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  asset_type: AssetType;
  owner: string;
  criticality: AssetCriticality;
  data_classification: DataClassification;
  status: AssetStatus;
  created_at: string;
  updated_at: string;
}

export interface AssetInput {
  name: string;
  description: string | null;
  asset_type: AssetType;
  owner: string;
  criticality: AssetCriticality;
  data_classification: DataClassification;
  status: AssetStatus;
}

export type RiskTreatment = "mitigate" | "avoid" | "transfer" | "accept";
export type RiskStatus = "identified" | "in_evaluation" | "in_treatment" | "accepted" | "closed";
export type RiskLevel = "bajo" | "medio" | "alto" | "critico";

export interface Risk {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  asset_id: string | null;
  category: string;
  threat: string;
  vulnerability: string;
  likelihood: number;
  impact: number;
  inherent_score: number;
  inherent_level: RiskLevel;
  treatment: RiskTreatment;
  owner: string;
  review_date: string;
  status: RiskStatus;
  residual_likelihood: number | null;
  residual_impact: number | null;
  residual_score: number | null;
  residual_level: RiskLevel | null;
  comments: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskInput {
  title: string;
  description: string | null;
  asset_id: string | null;
  category: string;
  threat: string;
  vulnerability: string;
  likelihood: number;
  impact: number;
  treatment: RiskTreatment;
  owner: string;
  review_date: string;
  status: RiskStatus;
  residual_likelihood: number | null;
  residual_impact: number | null;
  comments: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type ControlStatus =
  | "not_implemented"
  | "partially_implemented"
  | "implemented"
  | "not_applicable";

export type ControlFrequency =
  | "continuous"
  | "daily"
  | "weekly"
  | "monthly"
  | "quarterly"
  | "semiannual"
  | "annual"
  | "ad_hoc";

export interface Control {
  id: string;
  organization_id: string;
  control_id: string;
  name: string;
  description: string | null;
  objective: string | null;
  category: string;
  owner: string;
  status: ControlStatus;
  frequency: ControlFrequency;
  created_at: string;
  updated_at: string;
}

export interface ControlInput {
  control_id: string;
  name: string;
  description: string | null;
  objective: string | null;
  category: string;
  owner: string;
  status: ControlStatus;
  frequency: ControlFrequency;
}

export interface RiskSummary {
  id: string;
  title: string;
  inherent_level: RiskLevel;
}

export interface AssetSummary {
  id: string;
  name: string;
  criticality: AssetCriticality;
}

export interface RequirementSummary {
  id: string;
  code: string;
  name: string;
  framework_id: string;
  framework_short_name: string;
}

export interface ControlDetail extends Control {
  risks: RiskSummary[];
  assets: AssetSummary[];
  requirements: RequirementSummary[];
}

export type FrameworkStatus = "active" | "inactive";

export interface Framework {
  id: string;
  organization_id: string;
  name: string;
  short_name: string;
  description: string | null;
  version: string;
  status: FrameworkStatus;
  created_at: string;
  updated_at: string;
}

export interface FrameworkInput {
  name: string;
  short_name: string;
  description: string | null;
  version: string;
  status: FrameworkStatus;
}

export interface ComplianceSummary {
  implemented: number;
  partially_implemented: number;
  not_implemented: number;
  not_applicable: number;
  total_requirements: number;
  requirements_with_control: number;
}

export interface FrameworkDetail extends Framework {
  compliance_summary: ComplianceSummary;
}

export interface Requirement {
  id: string;
  organization_id: string;
  framework_id: string;
  parent_requirement_id: string | null;
  code: string;
  name: string;
  description: string | null;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface RequirementInput {
  parent_requirement_id: string | null;
  code: string;
  name: string;
  description: string | null;
  category: string | null;
}

export interface RequirementBrief {
  id: string;
  code: string;
  name: string;
  framework_id: string;
  framework_short_name: string;
}

export interface FrameworkMapping {
  id: string;
  organization_id: string;
  source_requirement: RequirementBrief;
  target_requirement: RequirementBrief;
  notes: string | null;
  created_at: string;
}

export type EvidenceStoredStatus = "active" | "archived";
export type EvidenceEffectiveStatus = "active" | "archived" | "expired";

export interface Evidence {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  original_filename: string;
  mime_type: string;
  file_size: number;
  sha256: string;
  classification: DataClassification;
  status: EvidenceStoredStatus;
  evidence_type: string;
  collected_at: string;
  expires_at: string | null;
  uploaded_by_id: string | null;
  created_at: string;
  updated_at: string;
  is_expired: boolean;
  effective_status: EvidenceEffectiveStatus;
}

export interface ControlSummary {
  id: string;
  control_id: string;
  name: string;
}

export interface EvidenceDetail extends Evidence {
  controls: ControlSummary[];
  risks: RiskSummary[];
  assets: AssetSummary[];
  requirements: RequirementSummary[];
}

export interface EvidenceUploadInput {
  file: File;
  name: string;
  description: string | null;
  classification: DataClassification;
  evidence_type: string;
  collected_at: string;
  expires_at: string | null;
}

export interface EvidenceUpdateInput {
  name?: string;
  description?: string | null;
  classification?: DataClassification;
  evidence_type?: string;
  status?: EvidenceStoredStatus;
  collected_at?: string;
  expires_at?: string | null;
}

export interface IntegrityCheckResult {
  status: "ok" | "mismatch" | "not_found";
  sha256_stored: string;
  sha256_calculated: string | null;
}

export interface EvidenceSummary {
  id: string;
  name: string;
  classification: DataClassification;
}

export type FindingType =
  | "audit_internal"
  | "audit_external"
  | "risk_assessment"
  | "incident"
  | "control_review"
  | "compliance"
  | "vendor"
  | "other";

export type FindingSource =
  | "audit"
  | "risk_assessment"
  | "control"
  | "compliance"
  | "incident"
  | "vendor"
  | "manual";

export type FindingStatus = "open" | "under_review" | "remediation" | "pending_validation" | "closed" | "accepted";

export interface Finding {
  id: string;
  organization_id: string;
  finding_id: string;
  title: string;
  description: string | null;
  finding_type: FindingType;
  severity: AssetCriticality;
  status: FindingStatus;
  source: FindingSource;
  owner: string;
  discovered_at: string;
  due_date: string;
  closed_at: string | null;
  resolution_summary: string | null;
  created_by_id: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
}

export interface FindingInput {
  finding_id: string;
  title: string;
  description: string | null;
  finding_type: FindingType;
  severity: AssetCriticality;
  source: FindingSource;
  owner: string;
  discovered_at: string;
  due_date: string;
  status: FindingStatus;
  resolution_summary: string | null;
}

export interface ActionSummary {
  id: string;
  action_id: string;
  title: string;
  owner: string;
  priority: AssetCriticality;
  status: ActionStatus;
  due_date: string;
  is_overdue: boolean;
}

export interface FindingDetail extends Finding {
  risks: RiskSummary[];
  controls: ControlSummary[];
  assets: AssetSummary[];
  requirements: RequirementSummary[];
  evidence: EvidenceSummary[];
  actions: ActionSummary[];
}

export type ActionStatus = "pending" | "in_progress" | "blocked" | "completed" | "cancelled";

export interface RemediationAction {
  id: string;
  organization_id: string;
  finding_id: string;
  action_id: string;
  title: string;
  description: string | null;
  owner: string;
  status: ActionStatus;
  priority: AssetCriticality;
  due_date: string;
  completed_at: string | null;
  completion_notes: string | null;
  created_by_id: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
}

export interface RemediationActionInput {
  finding_id: string;
  action_id: string;
  title: string;
  description: string | null;
  owner: string;
  priority: AssetCriticality;
  due_date: string;
  status: ActionStatus;
  completion_notes: string | null;
}

export interface RemediationActionDetail extends RemediationAction {
  evidence: EvidenceSummary[];
}

export interface FindingSummary {
  id: string;
  finding_id: string;
  title: string;
  severity: AssetCriticality;
  status: FindingStatus;
}

export type VendorStatus = "prospect" | "active" | "suspended" | "terminated";

export type VendorDueDiligenceStatus =
  | "pending"
  | "in_review"
  | "approved"
  | "approved_with_conditions"
  | "rejected"
  | "expired";

export interface Vendor {
  id: string;
  organization_id: string;
  vendor_id: string;
  name: string;
  legal_name: string | null;
  description: string | null;
  category: string;
  owner: string;
  criticality: AssetCriticality;
  data_classification: DataClassification;
  status: VendorStatus;
  due_diligence_status: VendorDueDiligenceStatus;
  relationship_start_date: string;
  contract_end_date: string | null;
  last_security_review_date: string | null;
  next_security_review_date: string | null;
  created_by_id: string | null;
  created_at: string;
  updated_at: string;
  is_review_overdue: boolean;
  is_review_due_soon: boolean;
  is_contract_expired: boolean;
  is_contract_expiring_soon: boolean;
}

export interface VendorInput {
  vendor_id: string;
  name: string;
  legal_name: string | null;
  description: string | null;
  category: string;
  owner: string;
  criticality: AssetCriticality;
  data_classification: DataClassification;
  status: VendorStatus;
  due_diligence_status: VendorDueDiligenceStatus;
  relationship_start_date: string;
  contract_end_date: string | null;
  last_security_review_date: string | null;
  next_security_review_date: string | null;
}

export interface VendorDetail extends Vendor {
  risks: RiskSummary[];
  evidence: EvidenceSummary[];
  findings: FindingSummary[];
  actions: ActionSummary[];
}

export interface ActorSummary {
  id: string;
  email: string;
  full_name: string;
}

export interface AuditLogEntry {
  id: string;
  organization_id: string;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
  actor: ActorSummary | null;
}

export interface AuditLogMeta {
  actions: string[];
  entity_types: string[];
}

export interface ComplianceScoreBreakdown {
  controls_pct: number | null;
  evidence_pct: number | null;
  findings_pct: number | null;
  remediation_pct: number | null;
  score: number | null;
  level: "excelente" | "bueno" | "mejorable" | "critico" | null;
}

export interface AttentionItem {
  kind: "risk" | "finding" | "action" | "evidence" | "vendor";
  id: string;
  label: string;
  detail: string;
  severity: string;
  link: string;
}

export interface KpiCounts {
  risks_critical: number;
  risks_high: number;
  findings_open: number;
  findings_critical_open: number;
  actions_overdue: number;
  evidence_expiring_soon: number;
  vendors_critical: number;
}

export interface DashboardSummary {
  generated_at: string;
  kpis: KpiCounts;
  compliance_score: ComplianceScoreBreakdown;
  attention: AttentionItem[];
}

export interface RiskLevelCounts {
  bajo: number;
  medio: number;
  alto: number;
  critico: number;
}

export interface RiskDashboard {
  total: number;
  by_level: RiskLevelCounts;
  by_status: Record<string, number>;
  by_treatment: Record<string, number>;
  review_overdue: number;
  review_due_soon: number;
}

export interface ControlsByStatus {
  not_implemented: number;
  partially_implemented: number;
  implemented: number;
  not_applicable: number;
}

export interface FrameworkScore {
  id: string;
  short_name: string;
  name: string;
  controls_pct: number | null;
  evidence_pct: number | null;
  score: number | null;
  level: string | null;
}

export interface ComplianceDashboard {
  total_controls: number;
  by_status: ControlsByStatus;
  by_category: Record<string, number>;
  implemented_without_evidence: number;
  compliance_score: ComplianceScoreBreakdown;
  frameworks: FrameworkScore[];
}

export interface EvidenceAttentionItem {
  id: string;
  name: string;
  status: "expired" | "expiring_soon";
  classification: DataClassification;
  expires_at: string | null;
}

export interface EvidenceDashboard {
  total: number;
  active: number;
  archived: number;
  expiring_soon: number;
  expired: number;
  by_classification: Record<string, number>;
  by_type: Record<string, number>;
  needs_attention: EvidenceAttentionItem[];
}

export interface RemediationDashboard {
  findings_total: number;
  findings_by_severity: Record<string, number>;
  findings_by_status: Record<string, number>;
  findings_overdue: number;
  findings_critical_open: number;
  actions_total: number;
  actions_by_status: Record<string, number>;
  actions_by_priority: Record<string, number>;
  actions_overdue: number;
  remediation_rate_pct: number | null;
}

export interface VendorDashboard {
  total: number;
  active: number;
  critical: number;
  suspended: number;
  due_diligence_pending: number;
  review_overdue: number;
  review_due_soon: number;
  by_criticality: Record<string, number>;
  by_due_diligence: Record<string, number>;
}
