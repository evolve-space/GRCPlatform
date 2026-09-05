import type { UserRole } from "../types";

const ROLES_ESCRITURA: UserRole[] = ["admin", "grc_manager", "analyst"];
const ROLES_ELIMINACION: UserRole[] = ["admin", "grc_manager"];

export function puedeEscribir(role: UserRole | undefined): boolean {
  return !!role && ROLES_ESCRITURA.includes(role);
}

export function puedeEliminar(role: UserRole | undefined): boolean {
  return !!role && ROLES_ELIMINACION.includes(role);
}
