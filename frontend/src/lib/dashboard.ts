import { api } from "./api";
import type {
  ComplianceDashboard,
  DashboardSummary,
  EvidenceDashboard,
  RemediationDashboard,
  RiskDashboard,
  VendorDashboard,
} from "../types";

export async function obtenerResumenDashboard(): Promise<DashboardSummary> {
  const response = await api.get<DashboardSummary>("/api/v1/dashboard/summary");
  return response.data;
}

export interface FiltrosRiesgosDashboard {
  status?: string;
  treatment?: string;
  vendor_id?: string;
}

export async function obtenerRiesgosDashboard(filtros: FiltrosRiesgosDashboard): Promise<RiskDashboard> {
  const response = await api.get<RiskDashboard>("/api/v1/dashboard/risks", { params: filtros });
  return response.data;
}

export interface FiltrosComplianceDashboard {
  framework_id?: string;
  category?: string;
}

export async function obtenerComplianceDashboard(filtros: FiltrosComplianceDashboard): Promise<ComplianceDashboard> {
  const response = await api.get<ComplianceDashboard>("/api/v1/dashboard/compliance", { params: filtros });
  return response.data;
}

export interface FiltrosEvidenciaDashboard {
  classification?: string;
  evidence_type?: string;
  vendor_id?: string;
}

export async function obtenerEvidenciaDashboard(filtros: FiltrosEvidenciaDashboard): Promise<EvidenceDashboard> {
  const response = await api.get<EvidenceDashboard>("/api/v1/dashboard/evidence", { params: filtros });
  return response.data;
}

export interface FiltrosRemediacionDashboard {
  finding_severity?: string;
  finding_status?: string;
  action_status?: string;
  action_priority?: string;
  vendor_id?: string;
}

export async function obtenerRemediacionDashboard(filtros: FiltrosRemediacionDashboard): Promise<RemediationDashboard> {
  const response = await api.get<RemediationDashboard>("/api/v1/dashboard/remediation", { params: filtros });
  return response.data;
}

export interface FiltrosProveedoresDashboard {
  criticality?: string;
  status?: string;
  due_diligence_status?: string;
}

export async function obtenerProveedoresDashboard(filtros: FiltrosProveedoresDashboard): Promise<VendorDashboard> {
  const response = await api.get<VendorDashboard>("/api/v1/dashboard/vendors", { params: filtros });
  return response.data;
}
