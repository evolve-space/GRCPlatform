import { api } from "./api";
import type { Requirement, RequirementInput } from "../types";

export async function obtenerRequisito(id: string): Promise<Requirement> {
  const response = await api.get<Requirement>(`/api/v1/requirements/${id}`);
  return response.data;
}

export async function actualizarRequisito(
  id: string,
  datos: Partial<RequirementInput>,
): Promise<Requirement> {
  const response = await api.patch<Requirement>(`/api/v1/requirements/${id}`, datos);
  return response.data;
}
