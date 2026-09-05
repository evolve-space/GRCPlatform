import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DonutChart } from "../../components/charts/DonutChart";
import { HorizontalBarChart } from "../../components/charts/HorizontalBarChart";
import { obtenerComplianceDashboard } from "../../lib/dashboard";
import { listarFrameworks } from "../../lib/frameworks";
import { COLOR_TONO } from "../../lib/labels";
import type { ComplianceDashboard, Framework } from "../../types";

export function ComplianceSection() {
  const [datos, setDatos] = useState<ComplianceDashboard | null>(null);
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [frameworkId, setFrameworkId] = useState("");

  useEffect(() => {
    listarFrameworks().then(setFrameworks);
  }, []);

  useEffect(() => {
    obtenerComplianceDashboard({ framework_id: frameworkId || undefined }).then(setDatos);
  }, [frameworkId]);

  if (!datos) {
    return <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-400">Cargando…</div>;
  }

  const estadoDatos = [
    { label: "No implementado", value: datos.by_status.not_implemented, color: COLOR_TONO.rojo },
    { label: "Parcial", value: datos.by_status.partially_implemented, color: COLOR_TONO.ambar },
    { label: "Implementado", value: datos.by_status.implemented, color: COLOR_TONO.verde },
    { label: "No aplicable", value: datos.by_status.not_applicable, color: COLOR_TONO.gris },
  ];

  const categoriaDatos = Object.entries(datos.by_category)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([label, value]) => ({ label, value, color: COLOR_TONO.azul }));

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-700">Controles ({datos.total_controls})</h2>
        <select
          value={frameworkId}
          onChange={(e) => setFrameworkId(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1 text-xs"
        >
          <option value="">Todos los frameworks</option>
          {frameworks.map((fw) => (
            <option key={fw.id} value={fw.id}>
              {fw.short_name}
            </option>
          ))}
        </select>
      </div>
      {frameworkId && (
        <p className="mt-1 text-xs text-slate-400">
          El filtro de framework afecta solo a la distribución de controles de esta tarjeta; el Compliance Score
          global y el score por framework (abajo) no cambian con este filtro.
        </p>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por estado</p>
          <DonutChart datos={estadoDatos} altura={180} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por categoría (top 8)</p>
          <HorizontalBarChart datos={categoriaDatos} altura={180} />
        </div>
      </div>

      <Link to="/controles" className="mt-3 inline-block text-sm text-slate-600 hover:underline">
        Controles implementados sin evidencia vigente:{" "}
        <span className="font-semibold text-red-700">{datos.implemented_without_evidence}</span>
      </Link>

      {datos.frameworks.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <p className="mb-2 text-xs font-medium text-slate-500">Score por framework (Controles + Evidencias)</p>
          <ul className="space-y-1.5">
            {datos.frameworks.map((fw) => (
              <li key={fw.id} className="flex items-center justify-between text-sm">
                <Link to={`/marcos/${fw.id}`} className="text-slate-900 hover:underline">
                  {fw.short_name}
                </Link>
                <span className="font-medium text-slate-700">
                  {fw.score === null ? "Sin datos" : `${fw.score.toFixed(0)}/100`}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
