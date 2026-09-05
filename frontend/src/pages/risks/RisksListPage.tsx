import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Pagination } from "../../components/Pagination";
import { useAuth } from "../../context/auth-context";
import { listarRiesgos } from "../../lib/risks";
import {
  ETIQUETAS_ESTADO_RIESGO,
  ETIQUETAS_NIVEL_RIESGO,
  ETIQUETAS_TRATAMIENTO,
  TONO_ESTADO_RIESGO,
  TONO_NIVEL_RIESGO,
} from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import type { Risk, RiskLevel, RiskStatus, RiskTreatment } from "../../types";

const PAGE_SIZE = 20;

export function RisksListPage() {
  const { usuario } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [riesgos, setRiesgos] = useState<Risk[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState<RiskStatus | "">("");
  const [tratamiento, setTratamiento] = useState<RiskTreatment | "">("");
  const [nivel, setNivel] = useState<RiskLevel | "">((searchParams.get("level") as RiskLevel) || "");
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarRiesgos({
      search: search || undefined,
      status: estado || undefined,
      treatment: tratamiento || undefined,
      level: nivel || undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setRiesgos(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [search, estado, tratamiento, nivel, page]);

  function cambiarNivel(valor: RiskLevel | "") {
    setPage(1);
    setNivel(valor);
    setSearchParams(valor ? { level: valor } : {});
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Riesgos</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/riesgos/nuevo"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nuevo riesgo
          </Link>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Buscar por título o descripción…"
          value={search}
          onChange={(evento) => {
            setPage(1);
            setSearch(evento.target.value);
          }}
          className="w-64 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
        />
        <select
          value={nivel}
          onChange={(evento) => cambiarNivel(evento.target.value as RiskLevel | "")}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todo nivel de riesgo</option>
          {Object.entries(ETIQUETAS_NIVEL_RIESGO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <select
          value={estado}
          onChange={(evento) => {
            setPage(1);
            setEstado(evento.target.value as RiskStatus | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
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
          onChange={(evento) => {
            setPage(1);
            setTratamiento(evento.target.value as RiskTreatment | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todo tratamiento</option>
          {Object.entries(ETIQUETAS_TRATAMIENTO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Título</th>
              <th className="px-4 py-3">Categoría</th>
              <th className="px-4 py-3">Nivel inherente</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Responsable</th>
              <th className="px-4 py-3">Revisión</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : riesgos.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado riesgos con estos criterios.
                </td>
              </tr>
            ) : (
              riesgos.map((riesgo) => (
                <tr key={riesgo.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/riesgos/${riesgo.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {riesgo.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{riesgo.category}</td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_NIVEL_RIESGO[riesgo.inherent_level]}>
                      {ETIQUETAS_NIVEL_RIESGO[riesgo.inherent_level]} ({riesgo.inherent_score})
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_ESTADO_RIESGO[riesgo.status]}>
                      {ETIQUETAS_ESTADO_RIESGO[riesgo.status]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{riesgo.owner}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {new Date(riesgo.review_date).toLocaleDateString("es-ES")}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
    </div>
  );
}
