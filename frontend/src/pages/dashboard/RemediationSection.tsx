import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DonutChart } from "../../components/charts/DonutChart";
import { obtenerRemediacionDashboard } from "../../lib/dashboard";
import {
  COLOR_TONO,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_ACCION,
  ETIQUETAS_ESTADO_HALLAZGO,
  TONO_CRITICIDAD,
  TONO_ESTADO_ACCION,
  TONO_ESTADO_HALLAZGO,
} from "../../lib/labels";
import type { ActionStatus, AssetCriticality, FindingStatus, RemediationDashboard } from "../../types";

export function RemediationSection({ vendorId }: { vendorId: string | null }) {
  const [datos, setDatos] = useState<RemediationDashboard | null>(null);

  useEffect(() => {
    obtenerRemediacionDashboard({ vendor_id: vendorId || undefined }).then(setDatos);
  }, [vendorId]);

  if (!datos) {
    return <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-400">Cargando…</div>;
  }

  const severidadDatos = Object.entries(datos.findings_by_severity).map(([clave, valor]) => ({
    label: ETIQUETAS_CRITICIDAD[clave as AssetCriticality] ?? clave,
    value: valor,
    color: COLOR_TONO[TONO_CRITICIDAD[clave as AssetCriticality] ?? "gris"],
  }));

  const estadoHallazgoDatos = Object.entries(datos.findings_by_status).map(([clave, valor]) => ({
    label: ETIQUETAS_ESTADO_HALLAZGO[clave as FindingStatus] ?? clave,
    value: valor,
    color: COLOR_TONO[TONO_ESTADO_HALLAZGO[clave as FindingStatus] ?? "gris"],
  }));

  const estadoAccionDatos = Object.entries(datos.actions_by_status).map(([clave, valor]) => ({
    label: ETIQUETAS_ESTADO_ACCION[clave as ActionStatus] ?? clave,
    value: valor,
    color: COLOR_TONO[TONO_ESTADO_ACCION[clave as ActionStatus] ?? "gris"],
  }));

  const tasa = datos.remediation_rate_pct;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="lg:col-span-2 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-700">
          Hallazgos ({datos.findings_total}) y Acciones ({datos.actions_total})
        </h2>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">Hallazgos por severidad</p>
            <DonutChart datos={severidadDatos} altura={170} />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">Hallazgos por estado</p>
            <DonutChart datos={estadoHallazgoDatos} altura={170} />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">Acciones por estado</p>
            <DonutChart datos={estadoAccionDatos} altura={170} />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <Link to="/hallazgos?overdue=true" className="text-slate-600 hover:underline">
            Hallazgos vencidos: <span className="font-semibold text-red-700">{datos.findings_overdue}</span>
          </Link>
          <Link to="/hallazgos?severity=critical" className="text-slate-600 hover:underline">
            Críticos abiertos: <span className="font-semibold text-red-700">{datos.findings_critical_open}</span>
          </Link>
          <Link to="/acciones?overdue=true" className="text-slate-600 hover:underline">
            Acciones vencidas: <span className="font-semibold text-red-700">{datos.actions_overdue}</span>
          </Link>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-700">Tasa de remediación</h2>
        <p className="mt-4 text-4xl font-bold text-slate-900">
          {tasa === null ? "Sin datos" : `${tasa.toFixed(0)}%`}
        </p>
        <p className="mt-1 text-xs text-slate-400">Acciones completadas / acciones totales</p>
      </div>
    </div>
  );
}
