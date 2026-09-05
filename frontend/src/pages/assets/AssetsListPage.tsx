import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Pagination } from "../../components/Pagination";
import { useAuth } from "../../context/auth-context";
import { listarActivos } from "../../lib/assets";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_ACTIVO,
  ETIQUETAS_TIPO_ACTIVO,
  TONO_CRITICIDAD,
} from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import type { Asset, AssetCriticality, AssetType, DataClassification } from "../../types";

const PAGE_SIZE = 20;

export function AssetsListPage() {
  const { usuario } = useAuth();
  const [activos, setActivos] = useState<Asset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [tipo, setTipo] = useState<AssetType | "">("");
  const [criticidad, setCriticidad] = useState<AssetCriticality | "">("");
  const [clasificacion, setClasificacion] = useState<DataClassification | "">("");
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarActivos({
      search: search || undefined,
      asset_type: tipo || undefined,
      criticality: criticidad || undefined,
      data_classification: clasificacion || undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setActivos(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [search, tipo, criticidad, clasificacion, page]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Activos</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/activos/nuevo"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nuevo activo
          </Link>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Buscar por nombre o descripción…"
          value={search}
          onChange={(evento) => {
            setPage(1);
            setSearch(evento.target.value);
          }}
          className="w-64 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
        />
        <select
          value={tipo}
          onChange={(evento) => {
            setPage(1);
            setTipo(evento.target.value as AssetType | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todos los tipos</option>
          {Object.entries(ETIQUETAS_TIPO_ACTIVO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <select
          value={criticidad}
          onChange={(evento) => {
            setPage(1);
            setCriticidad(evento.target.value as AssetCriticality | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda criticidad</option>
          {Object.entries(ETIQUETAS_CRITICIDAD).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <select
          value={clasificacion}
          onChange={(evento) => {
            setPage(1);
            setClasificacion(evento.target.value as DataClassification | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda clasificación</option>
          {Object.entries(ETIQUETAS_CLASIFICACION).map(([valor, etiqueta]) => (
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
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Criticidad</th>
              <th className="px-4 py-3">Clasificación</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Responsable</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : activos.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado activos con estos criterios.
                </td>
              </tr>
            ) : (
              activos.map((activo) => (
                <tr key={activo.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/activos/${activo.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {activo.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{ETIQUETAS_TIPO_ACTIVO[activo.asset_type]}</td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_CRITICIDAD[activo.criticality]}>
                      {ETIQUETAS_CRITICIDAD[activo.criticality]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {ETIQUETAS_CLASIFICACION[activo.data_classification]}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{ETIQUETAS_ESTADO_ACTIVO[activo.status]}</td>
                  <td className="px-4 py-3 text-slate-600">{activo.owner}</td>
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
