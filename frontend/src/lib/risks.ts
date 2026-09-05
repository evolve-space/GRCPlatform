import { api } from "./api";
import type { Page, Risk, RiskInput } from "../types";

export interface FiltrosRiesgos {
  search?: string;
  category?: string;
  status?: string;
  treatment?: string;
  asset_id?: string;
  level?: string;
  page?: number;
  page_size?: number;
}

export async function listarRiesgos(filtros: FiltrosRiesgos): Promise<Page<Risk>> {
  const response = await api.get<Page<Risk>>("/api/v1/risks", { params: filtros });
  return response.data;
}

export async function obtenerRiesgo(id: string): Promise<Risk> {
  const response = await api.get<Risk>(`/api/v1/risks/${id}`);
  return response.data;
}

export async function crearRiesgo(datos: RiskInput): Promise<Risk> {
  const response = await api.post<Risk>("/api/v1/risks", datos);
  return response.data;
}

export async function actualizarRiesgo(id: string, datos: Partial<RiskInput>): Promise<Risk> {
  const response = await api.patch<Risk>(`/api/v1/risks/${id}`, datos);
  return response.data;
}

export async function eliminarRiesgo(id: string): Promise<void> {
  await api.delete(`/api/v1/risks/${id}`);
}
