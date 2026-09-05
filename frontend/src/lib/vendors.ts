import { api } from "./api";
import type { Page, Vendor, VendorDetail, VendorInput } from "../types";

export interface FiltrosProveedores {
  search?: string;
  status?: string;
  criticality?: string;
  data_classification?: string;
  due_diligence_status?: string;
  review_overdue?: boolean;
  review_due_soon?: boolean;
  contract_expired?: boolean;
  contract_expiring_soon?: boolean;
  page?: number;
  page_size?: number;
}

export async function listarProveedores(filtros: FiltrosProveedores): Promise<Page<Vendor>> {
  const response = await api.get<Page<Vendor>>("/api/v1/vendors", { params: filtros });
  return response.data;
}

export async function obtenerProveedor(id: string): Promise<VendorDetail> {
  const response = await api.get<VendorDetail>(`/api/v1/vendors/${id}`);
  return response.data;
}

export async function crearProveedor(datos: VendorInput): Promise<Vendor> {
  const response = await api.post<Vendor>("/api/v1/vendors", datos);
  return response.data;
}

export async function actualizarProveedor(id: string, datos: Partial<VendorInput>): Promise<Vendor> {
  const response = await api.patch<Vendor>(`/api/v1/vendors/${id}`, datos);
  return response.data;
}

export async function eliminarProveedor(id: string): Promise<void> {
  await api.delete(`/api/v1/vendors/${id}`);
}

async function vincular(vendorId: string, ruta: string, cuerpo: Record<string, string>): Promise<VendorDetail> {
  const response = await api.post<VendorDetail>(`/api/v1/vendors/${vendorId}/${ruta}`, cuerpo);
  return response.data;
}

async function desvincular(vendorId: string, ruta: string, entidadId: string): Promise<VendorDetail> {
  const response = await api.delete<VendorDetail>(`/api/v1/vendors/${vendorId}/${ruta}/${entidadId}`);
  return response.data;
}

export const vincularRiesgoProveedor = (vendorId: string, riskId: string) =>
  vincular(vendorId, "risks", { risk_id: riskId });
export const desvincularRiesgoProveedor = (vendorId: string, riskId: string) =>
  desvincular(vendorId, "risks", riskId);

export const vincularEvidenciaProveedor = (vendorId: string, evidenceId: string) =>
  vincular(vendorId, "evidence", { evidence_id: evidenceId });
export const desvincularEvidenciaProveedor = (vendorId: string, evidenceId: string) =>
  desvincular(vendorId, "evidence", evidenceId);

export const vincularHallazgoProveedor = (vendorId: string, findingId: string) =>
  vincular(vendorId, "findings", { finding_id: findingId });
export const desvincularHallazgoProveedor = (vendorId: string, findingId: string) =>
  desvincular(vendorId, "findings", findingId);
