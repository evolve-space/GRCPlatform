import { useEffect, useState } from "react";
import { DonutChart } from "../../components/charts/DonutChart";
import { obtenerRiesgosDashboard } from "../../lib/dashboard";
import { COLOR_TONO, ETIQUETAS_ESTADO_RIESGO, ETIQUETAS_TRATAMIENTO, TONO_NIVEL_RIESGO } from "../../lib/labels";
import type { RiskDashboard, RiskStatus, RiskTreatment } from "../../types";

export function RiskSection({ vendorId }: { vendorId: string | null }) {
  const [datos, setDatos] = useState<RiskDashboard | null>(null);
  const [estado, setEstado] = useState<RiskStatus | "">("");
  const [tratamiento, setTratamiento] = useState<RiskTreatment | "">("");

  useEffect(() => {
    obtenerRiesgosDashboard({
      status: estado || undefined,
      treatment: tratamiento || undefined,
      vendor_id: vendorId || undefined,
    }).then(setDatos);
  }, [estado, tratamiento, vendorId]);

  if (!datos) {
    return <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-400">Cargando…</div>;
  }

  const nivelDatos = [
    { label: "Bajo", value: datos.by_level.bajo, color: COLOR_TONO[TONO_NIVEL_RIESGO.bajo] },
    { label: "Medio", value: datos.by_level.medio, color: COLOR_TONO[TONO_NIVEL_RIESGO.medio] },
    { label: "Alto", value: datos.by_level.alto, color: COLOR_TONO[TONO_NIVEL_RIESGO.alto] },
    { label: "Crítico", value: datos.by_level.critico, color: COLOR_TONO[TONO_NIVEL_RIESGO.critico] },
  ];

  const estadoDatos = Object.entries(datos.by_status).map(([clave, valor]) => ({
    label: ETIQUETAS_ESTADO_RIESGO[clave as RiskStatus] ?? clave,
    value: valor,
    color: COLOR_TONO.azul,
  }));

  const tratamientoDatos = Object.entries(datos.by_treatment).map(([clave, valor]) => ({
    label: ETIQUETAS_TRATAMIENTO[clave as RiskTreatment] ?? clave,
    value: valor,
    color: COLOR_TONO.morado,
  }));

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-700">Riesgos ({datos.total})</h2>
        <div className="flex gap-2">
          <select
            value={estado}
            onChange={(e) => setEstado(e.target.value as RiskStatus | "")}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs"
          >
            <option value="">Todo estado</option>
            {Object.entries(ETIQUETAS_ESTADO_RIESGO).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
          <select
            value={tratamiento}
            onChange={(e) => setTratamiento(e.target.value as RiskTreatment | "")}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs"
          >
            <option value="">Todo tratamiento</option>
            {Object.entries(ETIQUETAS_TRATAMIENTO).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por nivel</p>
          <DonutChart datos={nivelDatos} altura={180} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por estado</p>
          <DonutChart datos={estadoDatos} altura={180} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por tratamiento</p>
          <DonutChart datos={tratamientoDatos} altura={180} />
        </div>
      </div>

      <div className="mt-3 flex gap-4 text-sm">
        <span className="text-slate-600">
          Revisión vencida: <span className="font-semibold text-red-700">{datos.review_overdue}</span>
        </span>
        <span className="text-slate-600">
          Revisión próxima: <span className="font-semibold text-amber-700">{datos.review_due_soon}</span>
        </span>
      </div>
    </div>
  );
}
