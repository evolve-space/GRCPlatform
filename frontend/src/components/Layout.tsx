import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/auth-context";
import { ETIQUETAS_ROL } from "../lib/labels";
import type { UserRole } from "../types";

const ENLACES = [
  { ruta: "/", etiqueta: "Panel" },
  { ruta: "/activos", etiqueta: "Activos" },
  { ruta: "/riesgos", etiqueta: "Riesgos" },
  { ruta: "/controles", etiqueta: "Controles" },
  { ruta: "/marcos", etiqueta: "Marcos de cumplimiento" },
  { ruta: "/evidencias", etiqueta: "Evidencias" },
  { ruta: "/hallazgos", etiqueta: "Hallazgos" },
  { ruta: "/acciones", etiqueta: "Acciones" },
  { ruta: "/proveedores", etiqueta: "Proveedores" },
];

// El Registro de auditoría solo es accesible en el backend para Admin y GRC
// Manager: se oculta el enlace para el resto de roles en lugar de mostrar un
// enlace que siempre devolvería 403.
const ROLES_AUDITORIA: UserRole[] = ["admin", "grc_manager"];

function claseEnlace(activo: boolean): string {
  return `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    activo ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
  }`;
}

export function Layout() {
  const { usuario, cerrarSesion } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-y-2 px-6 py-3">
          <div className="flex min-w-0 items-center gap-6">
            <span className="shrink-0 text-lg font-semibold text-slate-900">GRCPlatform</span>
            {/* overflow-x-auto: en pantallas estrechas hay más enlaces que
                anchura disponible; en vez de recortarlos (inaccesibles) o
                rediseñar el menú completo, se permite desplazamiento
                horizontal para llegar a todos. */}
            <nav className="flex gap-1 overflow-x-auto">
              {ENLACES.map((enlace) => (
                <NavLink
                  key={enlace.ruta}
                  to={enlace.ruta}
                  end={enlace.ruta === "/"}
                  className={({ isActive }) => `whitespace-nowrap ${claseEnlace(isActive)}`}
                >
                  {enlace.etiqueta}
                </NavLink>
              ))}
              {usuario && ROLES_AUDITORIA.includes(usuario.role) && (
                <NavLink
                  to="/auditoria"
                  className={({ isActive }) => `whitespace-nowrap ${claseEnlace(isActive)}`}
                >
                  Registro de auditoría
                </NavLink>
              )}
            </nav>
          </div>
          {usuario && (
            <div className="flex items-center gap-4">
              <div className="text-right text-sm">
                <p className="font-medium text-slate-900">{usuario.full_name}</p>
                <p className="text-slate-500">{ETIQUETAS_ROL[usuario.role]}</p>
              </div>
              <button
                onClick={cerrarSesion}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
