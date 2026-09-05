import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Pagination } from "../../components/Pagination";
import { useAuth } from "../../context/auth-context";
import { listarEvidencias } from "../../lib/evidence";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_ESTADO_EFECTIVO_EVIDENCIA,
  TONO_CLASIFICACION,
  TONO_ESTADO_EFECTIVO_EVIDENCIA,
} from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import type { DataClassification, Evidence } from "../../types";

const PAGE_SIZE = 20;

function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type FiltroCaducidad = "" | "vigentes" | "caducadas" | "proximas";

export function EvidenceListPage() {
  const { usuario } = useAuth();
  const [searchParams] = useSearchParams();
  const [evidencias, setEvidencias] = useState<Evidence[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [clasificacion, setClasificacion] = useState<DataClassification | "">("");
  const [caducidad, setCaducidad] = useState<FiltroCaducidad>(
    (searchParams.get("caducidad") as FiltroCaducidad) || "",
  );
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarEvidencias({
      search: search || undefined,
      classification: clasificacion || undefined,
      expired: caducidad === "caducadas" ? true : caducidad === "vigentes" ? false : undefined,
      expiring_within_days: caducidad === "proximas" ? 30 : undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setEvidencias(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [search, clasificacion, caducidad, page]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Evidencias</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/evidencias/nueva"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nueva evidencia
          </Link>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Buscar por nombre, descripción o archivo…"
          value={search}
          onChange={(evento) => {
            setPage(1);
            setSearch(evento.target.value);
          }}
          className="w-72 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
        />
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
        <select
          value={caducidad}
          onChange={(evento) => {
            setPage(1);
            setCaducidad(evento.target.value as FiltroCaducidad);
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todas</option>
          <option value="vigentes">Vigentes</option>
          <option value="caducadas">Caducadas</option>
          <option value="proximas">Próximas a caducar (30 días)</option>
        </select>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Clasificación</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Recopilación</th>
              <th className="px-4 py-3">Expiración</th>
              <th className="px-4 py-3">Tamaño</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : evidencias.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado evidencias con estos criterios.
                </td>
              </tr>
            ) : (
              evidencias.map((evidencia) => (
                <tr key={evidencia.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/evidencias/${evidencia.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {evidencia.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{evidencia.evidence_type}</td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_CLASIFICACION[evidencia.classification]}>
                      {ETIQUETAS_CLASIFICACION[evidencia.classification]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_ESTADO_EFECTIVO_EVIDENCIA[evidencia.effective_status]}>
                      {ETIQUETAS_ESTADO_EFECTIVO_EVIDENCIA[evidencia.effective_status]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {new Date(evidencia.collected_at).toLocaleDateString("es-ES")}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {evidencia.expires_at
                      ? new Date(evidencia.expires_at).toLocaleDateString("es-ES")
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatearTamano(evidencia.file_size)}</td>
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
