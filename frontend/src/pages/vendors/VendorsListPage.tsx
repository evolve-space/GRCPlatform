import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Pagination } from "../../components/Pagination";
import { useAuth } from "../../context/auth-context";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_DUE_DILIGENCE,
  ETIQUETAS_ESTADO_PROVEEDOR,
  TONO_CRITICIDAD,
  TONO_DUE_DILIGENCE,
  TONO_ESTADO_PROVEEDOR,
} from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import { listarProveedores } from "../../lib/vendors";
import type { AssetCriticality, DataClassification, Vendor, VendorDueDiligenceStatus, VendorStatus } from "../../types";

const PAGE_SIZE = 20;

export function VendorsListPage() {
  const { usuario } = useAuth();
  const [searchParams] = useSearchParams();
  const [proveedores, setProveedores] = useState<Vendor[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState<VendorStatus | "">("");
  const [criticidad, setCriticidad] = useState<AssetCriticality | "">(
    (searchParams.get("criticality") as AssetCriticality) || "",
  );
  const [clasificacion, setClasificacion] = useState<DataClassification | "">("");
  const [dueDiligence, setDueDiligence] = useState<VendorDueDiligenceStatus | "">("");
  const [revisionVencida, setRevisionVencida] = useState(searchParams.get("review_overdue") === "true");
  const [revisionProxima, setRevisionProxima] = useState(searchParams.get("review_due_soon") === "true");
  const [contratoVencido, setContratoVencido] = useState(false);
  const [contratoProximo, setContratoProximo] = useState(false);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarProveedores({
      search: search || undefined,
      status: estado || undefined,
      criticality: criticidad || undefined,
      data_classification: clasificacion || undefined,
      due_diligence_status: dueDiligence || undefined,
      review_overdue: revisionVencida ? true : undefined,
      review_due_soon: revisionProxima ? true : undefined,
      contract_expired: contratoVencido ? true : undefined,
      contract_expiring_soon: contratoProximo ? true : undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setProveedores(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [search, estado, criticidad, clasificacion, dueDiligence, revisionVencida, revisionProxima, contratoVencido, contratoProximo, page]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Proveedores</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/proveedores/nuevo"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nuevo proveedor
          </Link>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Buscar por código, nombre o razón social…"
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
            setEstado(evento.target.value as VendorStatus | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todo estado</option>
          {Object.entries(ETIQUETAS_ESTADO_PROVEEDOR).map(([valor, etiqueta]) => (
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
        <select
          value={dueDiligence}
          onChange={(evento) => {
            setPage(1);
            setDueDiligence(evento.target.value as VendorDueDiligenceStatus | "");
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda due diligence</option>
          {Object.entries(ETIQUETAS_DUE_DILIGENCE).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={revisionVencida}
            onChange={(evento) => {
              setPage(1);
              setRevisionVencida(evento.target.checked);
            }}
          />
          Revisión vencida
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={revisionProxima}
            onChange={(evento) => {
              setPage(1);
              setRevisionProxima(evento.target.checked);
            }}
          />
          Revisión próxima
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={contratoVencido}
            onChange={(evento) => {
              setPage(1);
              setContratoVencido(evento.target.checked);
            }}
          />
          Contrato vencido
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={contratoProximo}
            onChange={(evento) => {
              setPage(1);
              setContratoProximo(evento.target.checked);
            }}
          />
          Contrato próximo a finalizar
        </label>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Categoría</th>
              <th className="px-4 py-3">Criticidad</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Due diligence</th>
              <th className="px-4 py-3">Responsable</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : proveedores.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado proveedores con estos criterios.
                </td>
              </tr>
            ) : (
              proveedores.map((proveedor) => (
                <tr key={proveedor.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/proveedores/${proveedor.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {proveedor.vendor_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{proveedor.name}</td>
                  <td className="px-4 py-3 text-slate-600">{proveedor.category}</td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_CRITICIDAD[proveedor.criticality]}>
                      {ETIQUETAS_CRITICIDAD[proveedor.criticality]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge tono={TONO_ESTADO_PROVEEDOR[proveedor.status]}>
                        {ETIQUETAS_ESTADO_PROVEEDOR[proveedor.status]}
                      </Badge>
                      {proveedor.is_review_overdue && <Badge tono="rojo">Revisión vencida</Badge>}
                      {proveedor.is_contract_expired && <Badge tono="rojo">Contrato vencido</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tono={TONO_DUE_DILIGENCE[proveedor.due_diligence_status]}>
                      {ETIQUETAS_DUE_DILIGENCE[proveedor.due_diligence_status]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{proveedor.owner}</td>
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
