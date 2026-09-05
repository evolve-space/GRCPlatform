import type {
  ActionStatus,
  AssetCriticality,
  AssetStatus,
  AssetType,
  ControlFrequency,
  ControlStatus,
  DataClassification,
  EvidenceEffectiveStatus,
  EvidenceStoredStatus,
  FindingSource,
  FindingStatus,
  FindingType,
  FrameworkStatus,
  RiskLevel,
  RiskStatus,
  RiskTreatment,
  UserRole,
  VendorDueDiligenceStatus,
  VendorStatus,
} from "../types";

export const ETIQUETAS_ROL: Record<UserRole, string> = {
  admin: "Administrador",
  grc_manager: "Gestor GRC",
  analyst: "Analista",
  viewer: "Visor",
};

export const ETIQUETAS_TIPO_ACTIVO: Record<AssetType, string> = {
  system: "Sistema",
  application: "Aplicación",
  server: "Servidor",
  endpoint: "Endpoint",
  database: "Base de datos",
  service: "Servicio",
  information: "Información",
  process: "Proceso",
  vendor: "Proveedor",
  other: "Otro",
};

export const ETIQUETAS_CRITICIDAD: Record<AssetCriticality, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  critical: "Crítica",
};

export const ETIQUETAS_CLASIFICACION: Record<DataClassification, string> = {
  public: "Pública",
  internal: "Interna",
  confidential: "Confidencial",
  restricted: "Restringida",
};

export const ETIQUETAS_ESTADO_ACTIVO: Record<AssetStatus, string> = {
  active: "Activo",
  inactive: "Inactivo",
  decommissioned: "Dado de baja",
};

export const ETIQUETAS_TRATAMIENTO: Record<RiskTreatment, string> = {
  mitigate: "Mitigar",
  avoid: "Evitar",
  transfer: "Transferir",
  accept: "Aceptar",
};

export const ETIQUETAS_ESTADO_RIESGO: Record<RiskStatus, string> = {
  identified: "Identificado",
  in_evaluation: "En evaluación",
  in_treatment: "En tratamiento",
  accepted: "Aceptado",
  closed: "Cerrado",
};

export const ETIQUETAS_NIVEL_RIESGO: Record<RiskLevel, string> = {
  bajo: "Bajo",
  medio: "Medio",
  alto: "Alto",
  critico: "Crítico",
};

export const ETIQUETAS_ESTADO_CONTROL: Record<ControlStatus, string> = {
  not_implemented: "No implementado",
  partially_implemented: "Parcialmente implementado",
  implemented: "Implementado",
  not_applicable: "No aplicable",
};

export const ETIQUETAS_FRECUENCIA: Record<ControlFrequency, string> = {
  continuous: "Continua",
  daily: "Diaria",
  weekly: "Semanal",
  monthly: "Mensual",
  quarterly: "Trimestral",
  semiannual: "Semestral",
  annual: "Anual",
  ad_hoc: "Ad hoc",
};

export const ETIQUETAS_ESTADO_FRAMEWORK: Record<FrameworkStatus, string> = {
  active: "Activo",
  inactive: "Inactivo",
};

// Género femenino ("evidencia"), a diferencia de ETIQUETAS_ESTADO_FRAMEWORK.
export const ETIQUETAS_ESTADO_EVIDENCIA: Record<EvidenceStoredStatus, string> = {
  active: "Activa",
  archived: "Archivada",
};

export const ETIQUETAS_ESTADO_EFECTIVO_EVIDENCIA: Record<EvidenceEffectiveStatus, string> = {
  active: "Activa",
  archived: "Archivada",
  expired: "Caducada",
};

export const ETIQUETAS_TIPO_HALLAZGO: Record<FindingType, string> = {
  audit_internal: "Auditoría interna",
  audit_external: "Auditoría externa",
  risk_assessment: "Evaluación de riesgos",
  incident: "Incidente",
  control_review: "Revisión de control",
  compliance: "Cumplimiento",
  vendor: "Proveedor",
  other: "Otro",
};

export const ETIQUETAS_ORIGEN_HALLAZGO: Record<FindingSource, string> = {
  audit: "Auditoría",
  risk_assessment: "Evaluación de riesgos",
  control: "Control",
  compliance: "Cumplimiento",
  incident: "Incidente",
  vendor: "Proveedor",
  manual: "Manual",
};

export const ETIQUETAS_ESTADO_HALLAZGO: Record<FindingStatus, string> = {
  open: "Abierto",
  under_review: "En análisis",
  remediation: "En remediación",
  pending_validation: "Pendiente de validación",
  closed: "Cerrado",
  accepted: "Aceptado",
};

export const ETIQUETAS_ESTADO_ACCION: Record<ActionStatus, string> = {
  pending: "Pendiente",
  in_progress: "En progreso",
  blocked: "Bloqueada",
  completed: "Completada",
  cancelled: "Cancelada",
};

export const ETIQUETAS_ESTADO_PROVEEDOR: Record<VendorStatus, string> = {
  prospect: "Prospecto",
  active: "Activo",
  suspended: "Suspendido",
  terminated: "Finalizado",
};

export const ETIQUETAS_DUE_DILIGENCE: Record<VendorDueDiligenceStatus, string> = {
  pending: "Pendiente",
  in_review: "En revisión",
  approved: "Aprobado",
  approved_with_conditions: "Aprobado con condiciones",
  rejected: "Rechazado",
  expired: "Caducado",
};

type Tono = "verde" | "ambar" | "naranja" | "rojo" | "azul" | "morado" | "gris";

export const TONO_NIVEL_RIESGO: Record<RiskLevel, Tono> = {
  bajo: "verde",
  medio: "ambar",
  alto: "naranja",
  critico: "rojo",
};

export const TONO_CRITICIDAD: Record<AssetCriticality, Tono> = {
  low: "verde",
  medium: "ambar",
  high: "naranja",
  critical: "rojo",
};

export const TONO_ESTADO_HALLAZGO: Record<FindingStatus, Tono> = {
  open: "rojo",
  under_review: "azul",
  remediation: "ambar",
  pending_validation: "ambar",
  closed: "verde",
  accepted: "morado",
};

export const TONO_ESTADO_ACCION: Record<ActionStatus, Tono> = {
  pending: "gris",
  in_progress: "azul",
  blocked: "rojo",
  completed: "verde",
  cancelled: "gris",
};

export const TONO_CLASIFICACION: Record<DataClassification, Tono> = {
  public: "gris",
  internal: "azul",
  confidential: "ambar",
  restricted: "rojo",
};

export const TONO_ESTADO_ACTIVO: Record<AssetStatus, Tono> = {
  active: "verde",
  inactive: "gris",
  decommissioned: "rojo",
};

export const TONO_ESTADO_RIESGO: Record<RiskStatus, Tono> = {
  identified: "gris",
  in_evaluation: "azul",
  in_treatment: "ambar",
  accepted: "morado",
  closed: "verde",
};

export const TONO_ESTADO_CONTROL: Record<ControlStatus, Tono> = {
  not_implemented: "rojo",
  partially_implemented: "ambar",
  implemented: "verde",
  not_applicable: "gris",
};

export const TONO_ESTADO_FRAMEWORK: Record<FrameworkStatus, Tono> = {
  active: "verde",
  inactive: "gris",
};

export const TONO_ESTADO_PROVEEDOR: Record<VendorStatus, Tono> = {
  prospect: "gris",
  active: "verde",
  suspended: "ambar",
  terminated: "rojo",
};

export const TONO_DUE_DILIGENCE: Record<VendorDueDiligenceStatus, Tono> = {
  pending: "gris",
  in_review: "azul",
  approved: "verde",
  approved_with_conditions: "ambar",
  rejected: "rojo",
  expired: "rojo",
};

export const TONO_ESTADO_EFECTIVO_EVIDENCIA: Record<EvidenceEffectiveStatus, Tono> = {
  active: "verde",
  archived: "gris",
  expired: "rojo",
};

// Equivalente en color hexadecimal de cada Tono, para usar como `fill` en
// gráficos (recharts no interpreta clases de Tailwind). Mismos tonos que
// CLASES_TONO, en la variante ~500 de la paleta de Tailwind.
export const COLOR_TONO: Record<Tono, string> = {
  verde: "#10b981",
  ambar: "#f59e0b",
  naranja: "#f97316",
  rojo: "#ef4444",
  azul: "#3b82f6",
  morado: "#a855f7",
  gris: "#94a3b8",
};

export const CLASES_TONO: Record<Tono, string> = {
  verde: "bg-emerald-100 text-emerald-800",
  ambar: "bg-amber-100 text-amber-800",
  naranja: "bg-orange-100 text-orange-800",
  rojo: "bg-red-100 text-red-800",
  azul: "bg-blue-100 text-blue-800",
  morado: "bg-purple-100 text-purple-800",
  gris: "bg-slate-100 text-slate-700",
};

export type { Tono };
