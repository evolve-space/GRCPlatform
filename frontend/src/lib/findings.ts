import { api } from "./api";
import type { Finding, FindingDetail, FindingInput, Page } from "../types";

export interface FiltrosHallazgos {
  search?: string;
  severity?: string;
  status?: string;
  finding_type?: string;
  source?: string;
  owner?: string;
  overdue?: boolean;
  risk_id?: string;
  control_id?: string;
  page?: number;
  page_size?: number;
}

export async function listarHallazgos(filtros: FiltrosHallazgos): Promise<Page<Finding>> {
  const response = await api.get<Page<Finding>>("/api/v1/findings", { params: filtros });
  return response.data;
}

export async function obtenerHallazgo(id: string): Promise<FindingDetail> {
  const response = await api.get<FindingDetail>(`/api/v1/findings/${id}`);
  return response.data;
}

export async function crearHallazgo(datos: FindingInput): Promise<Finding> {
  const response = await api.post<Finding>("/api/v1/findings", datos);
  return response.data;
}

export async function actualizarHallazgo(id: string, datos: Partial<FindingInput>): Promise<Finding> {
  const response = await api.patch<Finding>(`/api/v1/findings/${id}`, datos);
  return response.data;
}

export async function eliminarHallazgo(id: string): Promise<void> {
  await api.delete(`/api/v1/findings/${id}`);
}

async function vincular(finding_id: string, ruta: string, cuerpo: Record<string, string>): Promise<FindingDetail> {
  const response = await api.post<FindingDetail>(`/api/v1/findings/${finding_id}/${ruta}`, cuerpo);
  return response.data;
}

async function desvincular(finding_id: string, ruta: string, entidad_id: string): Promise<FindingDetail> {
  const response = await api.delete<FindingDetail>(`/api/v1/findings/${finding_id}/${ruta}/${entidad_id}`);
  return response.data;
}

export const vincularRiesgoHallazgo = (findingId: string, riskId: string) =>
  vincular(findingId, "risks", { risk_id: riskId });
export const desvincularRiesgoHallazgo = (findingId: string, riskId: string) =>
  desvincular(findingId, "risks", riskId);

export const vincularControlHallazgo = (findingId: string, controlId: string) =>
  vincular(findingId, "controls", { control_id: controlId });
export const desvincularControlHallazgo = (findingId: string, controlId: string) =>
  desvincular(findingId, "controls", controlId);

export const vincularActivoHallazgo = (findingId: string, assetId: string) =>
  vincular(findingId, "assets", { asset_id: assetId });
export const desvincularActivoHallazgo = (findingId: string, assetId: string) =>
  desvincular(findingId, "assets", assetId);

export const vincularRequisitoHallazgo = (findingId: string, requirementId: string) =>
  vincular(findingId, "requirements", { requirement_id: requirementId });
export const desvincularRequisitoHallazgo = (findingId: string, requirementId: string) =>
  desvincular(findingId, "requirements", requirementId);

export const vincularEvidenciaHallazgo = (findingId: string, evidenceId: string) =>
  vincular(findingId, "evidence", { evidence_id: evidenceId });
export const desvincularEvidenciaHallazgo = (findingId: string, evidenceId: string) =>
  desvincular(findingId, "evidence", evidenceId);
