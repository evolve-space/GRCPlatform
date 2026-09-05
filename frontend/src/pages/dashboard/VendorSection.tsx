import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DonutChart } from "../../components/charts/DonutChart";
import { obtenerProveedoresDashboard } from "../../lib/dashboard";
import { COLOR_TONO, ETIQUETAS_CRITICIDAD, ETIQUETAS_DUE_DILIGENCE, TONO_CRITICIDAD, TONO_DUE_DILIGENCE } from "../../lib/labels";
import type { AssetCriticality, VendorDashboard, VendorDueDiligenceStatus } from "../../types";

export function VendorSection() {
  const [datos, setDatos] = useState<VendorDashboard | null>(null);

  useEffect(() => {
    obtenerProveedoresDashboard({}).then(setDatos);
  }, []);

  if (!datos) {
    return <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-400">Cargando…</div>;
  }

  const criticidadDatos = Object.entries(datos.by_criticality).map(([clave, valor]) => ({
    label: ETIQUETAS_CRITICIDAD[clave as AssetCriticality] ?? clave,
    value: valor,
    color: COLOR_TONO[TONO_CRITICIDAD[clave as AssetCriticality] ?? "gris"],
  }));

  const dueDiligenceDatos = Object.entries(datos.by_due_diligence).map(([clave, valor]) => ({
    label: ETIQUETAS_DUE_DILIGENCE[clave as VendorDueDiligenceStatus] ?? clave,
    value: valor,
    color: COLOR_TONO[TONO_DUE_DILIGENCE[clave as VendorDueDiligenceStatus] ?? "gris"],
  }));

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-700">Proveedores ({datos.total})</h2>

      <div className="mt-3 flex flex-wrap gap-4 text-sm">
        <span className="text-slate-600">
          Activos: <span className="font-semibold text-emerald-700">{datos.active}</span>
        </span>
        <Link to="/proveedores?criticality=critical" className="text-slate-600 hover:underline">
          Críticos: <span className="font-semibold text-red-700">{datos.critical}</span>
        </Link>
        <span className="text-slate-600">
          Suspendidos: <span className="font-semibold text-amber-700">{datos.suspended}</span>
        </span>
        <span className="text-slate-600">
          Due diligence pendiente: <span className="font-semibold text-slate-700">{datos.due_diligence_pending}</span>
        </span>
        <Link to="/proveedores?review_overdue=true" className="text-slate-600 hover:underline">
          Revisión vencida: <span className="font-semibold text-red-700">{datos.review_overdue}</span>
        </Link>
        <Link to="/proveedores?review_due_soon=true" className="text-slate-600 hover:underline">
          Revisión próxima: <span className="font-semibold text-amber-700">{datos.review_due_soon}</span>
        </Link>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por criticidad</p>
          <DonutChart datos={criticidadDatos} altura={180} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Estado de due diligence</p>
          <DonutChart datos={dueDiligenceDatos} altura={180} />
        </div>
      </div>
    </div>
  );
}
