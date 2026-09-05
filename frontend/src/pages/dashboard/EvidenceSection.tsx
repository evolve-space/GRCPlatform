import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { DonutChart } from "../../components/charts/DonutChart";
import { HorizontalBarChart } from "../../components/charts/HorizontalBarChart";
import { obtenerEvidenciaDashboard } from "../../lib/dashboard";
import { COLOR_TONO, ETIQUETAS_CLASIFICACION, TONO_CLASIFICACION } from "../../lib/labels";
import type { DataClassification, EvidenceDashboard } from "../../types";

export function EvidenceSection({ vendorId }: { vendorId: string | null }) {
  const [datos, setDatos] = useState<EvidenceDashboard | null>(null);

  useEffect(() => {
    obtenerEvidenciaDashboard({ vendor_id: vendorId || undefined }).then(setDatos);
  }, [vendorId]);

  if (!datos) {
    return <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-400">Cargando…</div>;
  }

  const clasificacionDatos = Object.entries(datos.by_classification).map(([clave, valor]) => ({
    label: ETIQUETAS_CLASIFICACION[clave as DataClassification] ?? clave,
    value: valor,
    color: COLOR_TONO[TONO_CLASIFICACION[clave as DataClassification] ?? "gris"],
  }));

  const tipoDatos = Object.entries(datos.by_type)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([label, value]) => ({ label, value, color: COLOR_TONO.azul }));

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-700">Evidencias ({datos.total})</h2>

      <div className="mt-3 flex flex-wrap gap-4 text-sm">
        <span className="text-slate-600">
          Activas: <span className="font-semibold text-emerald-700">{datos.active}</span>
        </span>
        <span className="text-slate-600">
          Archivadas: <span className="font-semibold text-slate-700">{datos.archived}</span>
        </span>
        <Link to="/evidencias?caducidad=proximas" className="text-slate-600 hover:underline">
          Próximas a caducar: <span className="font-semibold text-amber-700">{datos.expiring_soon}</span>
        </Link>
        <Link to="/evidencias?caducidad=caducadas" className="text-slate-600 hover:underline">
          Caducadas: <span className="font-semibold text-red-700">{datos.expired}</span>
        </Link>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por clasificación</p>
          <DonutChart datos={clasificacionDatos} altura={180} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-slate-500">Por tipo (top 8)</p>
          <HorizontalBarChart datos={tipoDatos} altura={180} />
        </div>
      </div>

      {datos.needs_attention.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <p className="mb-2 text-xs font-medium text-slate-500">Requieren atención</p>
          <ul className="space-y-1.5">
            {datos.needs_attention.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/evidencias/${item.id}`}
                  className="flex items-center justify-between gap-2 text-sm hover:underline"
                >
                  <span className="truncate text-slate-900">{item.name}</span>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-slate-400">{item.expires_at}</span>
                    <Badge tono={item.status === "expired" ? "rojo" : "ambar"}>
                      {item.status === "expired" ? "Caducada" : "Próxima"}
                    </Badge>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
