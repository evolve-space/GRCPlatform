import { Link } from "react-router-dom";
import { Badge } from "../Badge";
import type { AttentionItem } from "../../types";

const TONO_SEVERIDAD: Record<string, "rojo" | "naranja" | "ambar" | "gris"> = {
  critical: "rojo",
  high: "naranja",
  medium: "ambar",
  low: "gris",
};

const ETIQUETA_TIPO: Record<string, string> = {
  risk: "Riesgo",
  finding: "Hallazgo",
  action: "Acción",
  evidence: "Evidencia",
  vendor: "Proveedor",
};

export function AttentionList({ items }: { items: AttentionItem[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-700">Requiere atención</h2>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-slate-400">Sin elementos que requieran atención inmediata.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((item) => (
            <li key={`${item.kind}-${item.id}`}>
              <Link
                to={item.link}
                className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-slate-50"
              >
                <div className="min-w-0">
                  <p className="truncate text-slate-900">{item.label}</p>
                  <p className="text-xs text-slate-500">
                    {ETIQUETA_TIPO[item.kind] ?? item.kind} · {item.detail}
                  </p>
                </div>
                <Badge tono={TONO_SEVERIDAD[item.severity] ?? "gris"}>
                  {item.severity === "critical"
                    ? "Crítico"
                    : item.severity === "high"
                      ? "Alto"
                      : item.severity === "medium"
                        ? "Medio"
                        : "Bajo"}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
