import { api } from "./api";
import type { AuditLogEntry, AuditLogMeta, Page } from "../types";

export interface FiltrosAuditoria {
  action?: string;
  entity_type?: string;
  entity_id?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export async function listarRegistrosAuditoria(filtros: FiltrosAuditoria): Promise<Page<AuditLogEntry>> {
  const response = await api.get<Page<AuditLogEntry>>("/api/v1/audit-logs", { params: filtros });
  return response.data;
}

export async function obtenerMetaAuditoria(): Promise<AuditLogMeta> {
  const response = await api.get<AuditLogMeta>("/api/v1/audit-logs/meta");
  return response.data;
}
