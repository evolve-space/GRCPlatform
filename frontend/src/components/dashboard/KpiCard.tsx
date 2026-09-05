import { Link } from "react-router-dom";
import type { Tono } from "../../lib/labels";

const COLOR_VALOR: Record<Tono, string> = {
  verde: "text-emerald-700",
  ambar: "text-amber-700",
  naranja: "text-orange-700",
  rojo: "text-red-700",
  azul: "text-blue-700",
  morado: "text-purple-700",
  gris: "text-slate-900",
};

export function KpiCard({
  titulo,
  valor,
  enlace,
  tono = "gris",
}: {
  titulo: string;
  valor: number | null;
  enlace: string;
  tono?: Tono;
}) {
  const resaltar = valor !== null && valor > 0;
  return (
    <Link
      to={enlace}
      className="block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
    >
      <p className="text-sm font-medium text-slate-500">{titulo}</p>
      <p className={`mt-2 text-3xl font-semibold ${resaltar ? COLOR_VALOR[tono] : "text-slate-900"}`}>
        {valor ?? "…"}
      </p>
    </Link>
  );
}
