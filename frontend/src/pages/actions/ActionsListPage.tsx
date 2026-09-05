import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Pagination } from "../../components/Pagination";
import { useAuth } from "../../context/auth-context";
import { ETIQUETAS_CRITICIDAD, ETIQUETAS_ESTADO_ACCION, TONO_CRITICIDAD, TONO_ESTADO_ACCION } from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import { listarAcciones } from "../../lib/remediationActions";
import type { ActionStatus, AssetCriticality, RemediationAction } from "../../types";

const PAGE_SIZE = 20;

export function ActionsListPage() {
  const { usuario } = useAuth();
  const [searchParams] = useSearchParams();
  const [acciones, setAcciones] = useState<RemediationAction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState<ActionStatus | "">("");
  const [prioridad, setPrioridad] = useState<AssetCriticality | "">("");
  const [soloVencidas, setSoloVencidas] = useState(searchParams.get("overdue") === "true");
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarAcciones({
      search: search || undefined,
      status: estado || undefined,
      priority: prioridad || undefined,
      overdue: soloVencidas ? true : undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setAcciones(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [search, estado, prioridad, soloVencidas, page]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Acciones de remediación</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/acciones/nueva"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nueva acción
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
          value={estado}
          onChange={(evento) => {
            setPage(1);
            setEstado(evento.target.value as ActionStatus | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todo estado</option>
          {Object.entries(ETIQUETAS_ESTADO_ACCION).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <select
          value={prioridad}
          onChange={(evento) => {
            setPage(1);
            setPrioridad(evento.target.value as AssetCriticality | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda prioridad</option>
          {Object.entries(ETIQUETAS_CRITICIDAD).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={soloVencidas}
            onChange={(evento) => {
              setPage(1);
              setSoloVencidas(evento.target.checked);
            }}
          />
          Solo vencidas
        </label>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Título</th>
              <th className="px-4 py-3">Prioridad</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Responsable</th>
              <th className="px-4 py-3">Fecha límite</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : acciones.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado acciones con estos criterios.
                </td>
              </tr>
            ) : (
              acciones.map((accion) => (
                <tr key={accion.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link to={`/acciones/${accion.id}`} className="font-medium text-slate-900 hover:underline">
                      {accion.action_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{accion.title}</td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_CRITICIDAD[accion.priority]}>{ETIQUETAS_CRITICIDAD[accion.priority]}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <Badge tono={TONO_ESTADO_ACCION[accion.status]}>{ETIQUETAS_ESTADO_ACCION[accion.status]}</Badge>
                      {accion.is_overdue && <Badge tono="rojo">Vencida</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{accion.owner}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {new Date(accion.due_date).toLocaleDateString("es-ES")}
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
