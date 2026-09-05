import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Pagination } from "../../components/Pagination";
import { useAuth } from "../../context/auth-context";
import { listarHallazgos } from "../../lib/findings";
import {
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_HALLAZGO,
  ETIQUETAS_ORIGEN_HALLAZGO,
  ETIQUETAS_TIPO_HALLAZGO,
  TONO_CRITICIDAD,
  TONO_ESTADO_HALLAZGO,
} from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import type { AssetCriticality, Finding, FindingStatus } from "../../types";

const PAGE_SIZE = 20;

export function FindingsListPage() {
  const { usuario } = useAuth();
  const [searchParams] = useSearchParams();
  const [hallazgos, setHallazgos] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [severidad, setSeveridad] = useState<AssetCriticality | "">(
    (searchParams.get("severity") as AssetCriticality) || "",
  );
  const [estado, setEstado] = useState<FindingStatus | "">("");
  const [soloVencidos, setSoloVencidos] = useState(searchParams.get("overdue") === "true");
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarHallazgos({
      search: search || undefined,
      severity: severidad || undefined,
      status: estado || undefined,
      overdue: soloVencidos ? true : undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setHallazgos(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [search, severidad, estado, soloVencidos, page]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Hallazgos</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/hallazgos/nuevo"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nuevo hallazgo
          </Link>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Buscar por código, título o descripción…"
          value={search}
          onChange={(evento) => {
            setPage(1);
            setSearch(evento.target.value);
          }}
          className="w-72 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
        />
        <select
          value={severidad}
          onChange={(evento) => {
            setPage(1);
            setSeveridad(evento.target.value as AssetCriticality | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda severidad</option>
          {Object.entries(ETIQUETAS_CRITICIDAD).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <select
          value={estado}
          onChange={(evento) => {
            setPage(1);
            setEstado(evento.target.value as FindingStatus | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todo estado</option>
          {Object.entries(ETIQUETAS_ESTADO_HALLAZGO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={soloVencidos}
            onChange={(evento) => {
              setPage(1);
              setSoloVencidos(evento.target.checked);
            }}
          />
          Solo vencidos
        </label>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Título</th>
              <th className="px-4 py-3">Severidad</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Origen</th>
              <th className="px-4 py-3">Responsable</th>
              <th className="px-4 py-3">Fecha límite</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : hallazgos.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado hallazgos con estos criterios.
                </td>
              </tr>
            ) : (
              hallazgos.map((hallazgo) => (
                <tr key={hallazgo.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/hallazgos/${hallazgo.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {hallazgo.finding_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{hallazgo.title}</td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_CRITICIDAD[hallazgo.severity]}>
                      {ETIQUETAS_CRITICIDAD[hallazgo.severity]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <Badge tono={TONO_ESTADO_HALLAZGO[hallazgo.status]}>
                        {ETIQUETAS_ESTADO_HALLAZGO[hallazgo.status]}
                      </Badge>
                      {hallazgo.is_overdue && <Badge tono="rojo">Vencido</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{ETIQUETAS_TIPO_HALLAZGO[hallazgo.finding_type]}</td>
                  <td className="px-4 py-3 text-slate-600">{ETIQUETAS_ORIGEN_HALLAZGO[hallazgo.source]}</td>
                  <td className="px-4 py-3 text-slate-600">{hallazgo.owner}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {new Date(hallazgo.due_date).toLocaleDateString("es-ES")}
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
