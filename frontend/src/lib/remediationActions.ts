import { api } from "./api";
import type { Page, RemediationAction, RemediationActionDetail, RemediationActionInput } from "../types";

export interface FiltrosAcciones {
  search?: string;
  status?: string;
  priority?: string;
  owner?: string;
  finding_id?: string;
  overdue?: boolean;
  page?: number;
  page_size?: number;
}

export async function listarAcciones(filtros: FiltrosAcciones): Promise<Page<RemediationAction>> {
  const response = await api.get<Page<RemediationAction>>("/api/v1/remediation-actions", { params: filtros });
  return response.data;
}

export async function obtenerAccion(id: string): Promise<RemediationActionDetail> {
  const response = await api.get<RemediationActionDetail>(`/api/v1/remediation-actions/${id}`);
  return response.data;
}

export async function crearAccion(datos: RemediationActionInput): Promise<RemediationAction> {
  const response = await api.post<RemediationAction>("/api/v1/remediation-actions", datos);
  return response.data;
}

export async function actualizarAccion(
  id: string,
  datos: Partial<RemediationActionInput>,
): Promise<RemediationAction> {
  const response = await api.patch<RemediationAction>(`/api/v1/remediation-actions/${id}`, datos);
  return response.data;
}

export async function eliminarAccion(id: string): Promise<void> {
  await api.delete(`/api/v1/remediation-actions/${id}`);
}

export async function vincularEvidenciaAccion(actionId: string, evidenceId: string): Promise<RemediationActionDetail> {
  const response = await api.post<RemediationActionDetail>(`/api/v1/remediation-actions/${actionId}/evidence`, {
    evidence_id: evidenceId,
  });
  return response.data;
}

export async function desvincularEvidenciaAccion(
  actionId: string,
  evidenceId: string,
): Promise<RemediationActionDetail> {
  const response = await api.delete<RemediationActionDetail>(
    `/api/v1/remediation-actions/${actionId}/evidence/${evidenceId}`,
  );
  return response.data;
}
