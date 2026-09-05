import { api } from "./api";
import type { Asset, AssetInput, Page } from "../types";

export interface FiltrosActivos {
  search?: string;
  asset_type?: string;
  criticality?: string;
  data_classification?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export async function listarActivos(filtros: FiltrosActivos): Promise<Page<Asset>> {
  const response = await api.get<Page<Asset>>("/api/v1/assets", { params: filtros });
  return response.data;
}

export async function obtenerActivo(id: string): Promise<Asset> {
  const response = await api.get<Asset>(`/api/v1/assets/${id}`);
  return response.data;
}

export async function crearActivo(datos: AssetInput): Promise<Asset> {
  const response = await api.post<Asset>("/api/v1/assets", datos);
  return response.data;
}

export async function actualizarActivo(id: string, datos: Partial<AssetInput>): Promise<Asset> {
  const response = await api.patch<Asset>(`/api/v1/assets/${id}`, datos);
  return response.data;
}

export async function eliminarActivo(id: string): Promise<void> {
  await api.delete(`/api/v1/assets/${id}`);
}
