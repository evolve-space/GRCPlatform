import { api } from "./api";
import type { FrameworkMapping } from "../types";

export async function listarMappings(requirementId?: string): Promise<FrameworkMapping[]> {
  const response = await api.get<FrameworkMapping[]>("/api/v1/mappings", {
    params: requirementId ? { requirement_id: requirementId } : undefined,
  });
  return response.data;
}

export async function crearMapping(
  sourceRequirementId: string,
  targetRequirementId: string,
  notes?: string,
): Promise<FrameworkMapping> {
  const response = await api.post<FrameworkMapping>("/api/v1/mappings", {
    source_requirement_id: sourceRequirementId,
    target_requirement_id: targetRequirementId,
    notes: notes || null,
  });
  return response.data;
}

export async function eliminarMapping(id: string): Promise<void> {
  await api.delete(`/api/v1/mappings/${id}`);
}
