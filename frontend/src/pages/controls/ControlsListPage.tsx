import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Pagination } from "../../components/Pagination";
import { useAuth } from "../../context/auth-context";
import { listarControles } from "../../lib/controls";
import {
  ETIQUETAS_ESTADO_CONTROL,
  ETIQUETAS_FRECUENCIA,
  TONO_ESTADO_CONTROL,
} from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import type { Control, ControlFrequency, ControlStatus } from "../../types";

const PAGE_SIZE = 20;

export function ControlsListPage() {
  const { usuario } = useAuth();
  const [controles, setControles] = useState<Control[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState<ControlStatus | "">("");
  const [frecuencia, setFrecuencia] = useState<ControlFrequency | "">("");
  const [categoria, setCategoria] = useState("");
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarControles({
      search: search || undefined,
      status: estado || undefined,
      frequency: frecuencia || undefined,
      category: categoria || undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setControles(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [search, estado, frecuencia, categoria, page]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Controles</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/controles/nuevo"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nuevo control
          </Link>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Buscar por código, nombre o descripción…"
          value={search}
          onChange={(evento) => {
            setPage(1);
            setSearch(evento.target.value);
          }}
          className="w-72 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
        />
        <input
          type="text"
          placeholder="Categoría…"
          value={categoria}
          onChange={(evento) => {
            setPage(1);
            setCategoria(evento.target.value);
          }}
          className="w-48 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={estado}
          onChange={(evento) => {
            setPage(1);
            setEstado(evento.target.value as ControlStatus | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todo estado</option>
          {Object.entries(ETIQUETAS_ESTADO_CONTROL).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <select
          value={frecuencia}
          onChange={(evento) => {
            setPage(1);
            setFrecuencia(evento.target.value as ControlFrequency | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda frecuencia</option>
          {Object.entries(ETIQUETAS_FRECUENCIA).map(([valor, etiqueta]) => (
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
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Responsable</th>
              <th className="px-4 py-3">Frecuencia</th>
              <th className="px-4 py-3">Categoría</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : controles.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado controles con estos criterios.
                </td>
              </tr>
            ) : (
              controles.map((control) => (
                <tr key={control.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/controles/${control.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {control.control_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{control.name}</td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_ESTADO_CONTROL[control.status]}>
                      {ETIQUETAS_ESTADO_CONTROL[control.status]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{control.owner}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {ETIQUETAS_FRECUENCIA[control.frequency]}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{control.category}</td>
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
