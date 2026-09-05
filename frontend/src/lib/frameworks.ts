import { api } from "./api";
import type { Framework, FrameworkDetail, FrameworkInput, Page, Requirement, RequirementInput } from "../types";

export async function listarFrameworks(): Promise<Framework[]> {
  const response = await api.get<Framework[]>("/api/v1/frameworks");
  return response.data;
}

export async function obtenerFramework(id: string): Promise<FrameworkDetail> {
  const response = await api.get<FrameworkDetail>(`/api/v1/frameworks/${id}`);
  return response.data;
}

export async function crearFramework(datos: FrameworkInput): Promise<Framework> {
  const response = await api.post<Framework>("/api/v1/frameworks", datos);
  return response.data;
}

export async function eliminarFramework(id: string): Promise<void> {
  await api.delete(`/api/v1/frameworks/${id}`);
}

export interface FiltrosRequisitos {
  search?: string;
  category?: string;
  parent_requirement_id?: string;
  page?: number;
  page_size?: number;
}

export async function listarRequisitos(
  frameworkId: string,
  filtros: FiltrosRequisitos,
): Promise<Page<Requirement>> {
  const response = await api.get<Page<Requirement>>(`/api/v1/frameworks/${frameworkId}/requirements`, {
    params: filtros,
  });
  return response.data;
}

export async function crearRequisito(
  frameworkId: string,
  datos: RequirementInput,
): Promise<Requirement> {
  const response = await api.post<Requirement>(
    `/api/v1/frameworks/${frameworkId}/requirements`,
    datos,
  );
  return response.data;
}
