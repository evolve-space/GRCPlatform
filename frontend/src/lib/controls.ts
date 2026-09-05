import { api } from "./api";
import type { Control, ControlDetail, ControlInput, Page } from "../types";

export interface FiltrosControles {
  search?: string;
  category?: string;
  owner?: string;
  status?: string;
  frequency?: string;
  page?: number;
  page_size?: number;
}

export async function listarControles(filtros: FiltrosControles): Promise<Page<Control>> {
  const response = await api.get<Page<Control>>("/api/v1/controls", { params: filtros });
  return response.data;
}

export async function obtenerControl(id: string): Promise<ControlDetail> {
  const response = await api.get<ControlDetail>(`/api/v1/controls/${id}`);
  return response.data;
}

export async function crearControl(datos: ControlInput): Promise<Control> {
  const response = await api.post<Control>("/api/v1/controls", datos);
  return response.data;
}

export async function actualizarControl(id: string, datos: Partial<ControlInput>): Promise<Control> {
  const response = await api.patch<Control>(`/api/v1/controls/${id}`, datos);
  return response.data;
}

export async function eliminarControl(id: string): Promise<void> {
  await api.delete(`/api/v1/controls/${id}`);
}

export async function vincularRiesgo(controlId: string, riskId: string): Promise<ControlDetail> {
  const response = await api.post<ControlDetail>(`/api/v1/controls/${controlId}/risks`, { risk_id: riskId });
  return response.data;
}

export async function desvincularRiesgo(controlId: string, riskId: string): Promise<ControlDetail> {
  const response = await api.delete<ControlDetail>(`/api/v1/controls/${controlId}/risks/${riskId}`);
  return response.data;
}

export async function vincularActivo(controlId: string, assetId: string): Promise<ControlDetail> {
  const response = await api.post<ControlDetail>(`/api/v1/controls/${controlId}/assets`, {
    asset_id: assetId,
  });
  return response.data;
}

export async function desvincularActivo(controlId: string, assetId: string): Promise<ControlDetail> {
  const response = await api.delete<ControlDetail>(`/api/v1/controls/${controlId}/assets/${assetId}`);
  return response.data;
}

export async function vincularRequisito(
  controlId: string,
  requirementId: string,
): Promise<ControlDetail> {
  const response = await api.post<ControlDetail>(`/api/v1/controls/${controlId}/requirements`, {
    requirement_id: requirementId,
  });
  return response.data;
}

export async function desvincularRequisito(
  controlId: string,
  requirementId: string,
): Promise<ControlDetail> {
  const response = await api.delete<ControlDetail>(
    `/api/v1/controls/${controlId}/requirements/${requirementId}`,
  );
  return response.data;
}
