import { api } from "./api";
import type {
  Evidence,
  EvidenceDetail,
  EvidenceUpdateInput,
  EvidenceUploadInput,
  IntegrityCheckResult,
  Page,
} from "../types";

export interface FiltrosEvidencias {
  search?: string;
  classification?: string;
  status?: string;
  evidence_type?: string;
  expired?: boolean;
  expiring_within_days?: number;
  page?: number;
  page_size?: number;
}

export async function listarEvidencias(filtros: FiltrosEvidencias): Promise<Page<Evidence>> {
  const response = await api.get<Page<Evidence>>("/api/v1/evidence", { params: filtros });
  return response.data;
}

export async function obtenerEvidencia(id: string): Promise<EvidenceDetail> {
  const response = await api.get<EvidenceDetail>(`/api/v1/evidence/${id}`);
  return response.data;
}

export async function subirEvidencia(datos: EvidenceUploadInput): Promise<Evidence> {
  const formData = new FormData();
  formData.append("file", datos.file);
  formData.append("name", datos.name);
  if (datos.description) formData.append("description", datos.description);
  formData.append("classification", datos.classification);
  formData.append("evidence_type", datos.evidence_type);
  formData.append("collected_at", datos.collected_at);
  if (datos.expires_at) formData.append("expires_at", datos.expires_at);

  const response = await api.post<Evidence>("/api/v1/evidence", formData);
  return response.data;
}

export async function actualizarEvidencia(id: string, datos: EvidenceUpdateInput): Promise<Evidence> {
  const response = await api.patch<Evidence>(`/api/v1/evidence/${id}`, datos);
  return response.data;
}

export async function eliminarEvidencia(id: string): Promise<void> {
  await api.delete(`/api/v1/evidence/${id}`);
}

export async function verificarIntegridad(id: string): Promise<IntegrityCheckResult> {
  const response = await api.get<IntegrityCheckResult>(`/api/v1/evidence/${id}/integrity`);
  return response.data;
}

export async function descargarEvidencia(id: string, nombreSugerido: string): Promise<void> {
  const response = await api.get(`/api/v1/evidence/${id}/download`, { responseType: "blob" });
  const url = window.URL.createObjectURL(response.data as Blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreSugerido;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  window.URL.revokeObjectURL(url);
}

export async function vincularControlEvidencia(evidenceId: string, controlId: string): Promise<EvidenceDetail> {
  const response = await api.post<EvidenceDetail>(`/api/v1/evidence/${evidenceId}/controls`, {
    control_id: controlId,
  });
  return response.data;
}

export async function desvincularControlEvidencia(
  evidenceId: string,
  controlId: string,
): Promise<EvidenceDetail> {
  const response = await api.delete<EvidenceDetail>(`/api/v1/evidence/${evidenceId}/controls/${controlId}`);
  return response.data;
}

export async function vincularRiesgoEvidencia(evidenceId: string, riskId: string): Promise<EvidenceDetail> {
  const response = await api.post<EvidenceDetail>(`/api/v1/evidence/${evidenceId}/risks`, {
    risk_id: riskId,
  });
  return response.data;
}

export async function desvincularRiesgoEvidencia(evidenceId: string, riskId: string): Promise<EvidenceDetail> {
  const response = await api.delete<EvidenceDetail>(`/api/v1/evidence/${evidenceId}/risks/${riskId}`);
  return response.data;
}

export async function vincularActivoEvidencia(evidenceId: string, assetId: string): Promise<EvidenceDetail> {
  const response = await api.post<EvidenceDetail>(`/api/v1/evidence/${evidenceId}/assets`, {
    asset_id: assetId,
  });
  return response.data;
}

export async function desvincularActivoEvidencia(
  evidenceId: string,
  assetId: string,
): Promise<EvidenceDetail> {
  const response = await api.delete<EvidenceDetail>(`/api/v1/evidence/${evidenceId}/assets/${assetId}`);
  return response.data;
}

export async function vincularRequisitoEvidencia(
  evidenceId: string,
  requirementId: string,
): Promise<EvidenceDetail> {
  const response = await api.post<EvidenceDetail>(`/api/v1/evidence/${evidenceId}/requirements`, {
    requirement_id: requirementId,
  });
  return response.data;
}

export async function desvincularRequisitoEvidencia(
  evidenceId: string,
  requirementId: string,
): Promise<EvidenceDetail> {
  const response = await api.delete<EvidenceDetail>(
    `/api/v1/evidence/${evidenceId}/requirements/${requirementId}`,
  );
  return response.data;
}
