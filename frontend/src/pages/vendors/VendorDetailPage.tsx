import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { obtenerMensajeError } from "../../lib/api";
import { listarEvidencias } from "../../lib/evidence";
import { listarHallazgos } from "../../lib/findings";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_DUE_DILIGENCE,
  ETIQUETAS_ESTADO_ACCION,
  ETIQUETAS_ESTADO_HALLAZGO,
  ETIQUETAS_ESTADO_PROVEEDOR,
  ETIQUETAS_NIVEL_RIESGO,
  TONO_CLASIFICACION,
  TONO_CRITICIDAD,
  TONO_DUE_DILIGENCE,
  TONO_ESTADO_ACCION,
  TONO_ESTADO_HALLAZGO,
  TONO_ESTADO_PROVEEDOR,
  TONO_NIVEL_RIESGO,
} from "../../lib/labels";
import { puedeEliminar, puedeEscribir } from "../../lib/permisos";
import { listarRiesgos } from "../../lib/risks";
import {
  desvincularEvidenciaProveedor,
  desvincularHallazgoProveedor,
  desvincularRiesgoProveedor,
  eliminarProveedor,
  obtenerProveedor,
  vincularEvidenciaProveedor,
  vincularHallazgoProveedor,
  vincularRiesgoProveedor,
} from "../../lib/vendors";
import type { Evidence, Finding, Risk, VendorDetail } from "../../types";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{etiqueta}</dt>
      <dd className="mt-1 text-slate-900">{children}</dd>
    </div>
  );
}

export function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { usuario } = useAuth();

  const [proveedor, setProveedor] = useState<VendorDetail | null>(null);
  const [riesgosDisponibles, setRiesgosDisponibles] = useState<Risk[]>([]);
  const [evidenciasDisponibles, setEvidenciasDisponibles] = useState<Evidence[]>([]);
  const [hallazgosDisponibles, setHallazgosDisponibles] = useState<Finding[]>([]);

  const [riesgoSeleccionado, setRiesgoSeleccionado] = useState("");
  const [evidenciaSeleccionada, setEvidenciaSeleccionada] = useState("");
  const [hallazgoSeleccionado, setHallazgoSeleccionado] = useState("");

  const [eliminando, setEliminando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const puedeEditar = puedeEscribir(usuario?.role);

  async function recargar() {
    if (!id) return;
    const datos = await obtenerProveedor(id);
    setProveedor(datos);
  }

  useEffect(() => {
    recargar().catch((err) => setError(obtenerMensajeError(err)));
    listarRiesgos({ page: 1, page_size: 100 }).then((r) => setRiesgosDisponibles(r.items));
    listarEvidencias({ page: 1, page_size: 100 }).then((r) => setEvidenciasDisponibles(r.items));
    listarHallazgos({ page: 1, page_size: 100 }).then((r) => setHallazgosDisponibles(r.items));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function manejarEliminar() {
    if (!id || !window.confirm("¿Seguro que quieres eliminar este proveedor?")) return;
    setEliminando(true);
    try {
      await eliminarProveedor(id);
      navigate("/proveedores");
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEliminando(false);
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!proveedor) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const riesgosVinculadosIds = new Set(proveedor.risks.map((r) => r.id));
  const evidenciasVinculadasIds = new Set(proveedor.evidence.map((e) => e.id));
  const hallazgosVinculadosIds = new Set(proveedor.findings.map((f) => f.id));

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <Link to="/proveedores" className="text-sm text-slate-500 hover:underline">
            ← Volver a Proveedores
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">
            {proveedor.vendor_id} · {proveedor.name}
          </h1>
          {proveedor.legal_name && <p className="mt-1 text-sm text-slate-500">{proveedor.legal_name}</p>}
        </div>
        <div className="flex gap-2">
          {puedeEditar && (
            <Link
              to={`/proveedores/${proveedor.id}/editar`}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Editar
            </Link>
          )}
          {puedeEliminar(usuario?.role) && (
            <button
              onClick={manejarEliminar}
              disabled={eliminando}
              className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
            >
              {eliminando ? "Eliminando…" : "Eliminar"}
            </button>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Información general</h2>
          <dl className="mt-3 space-y-3">
            <Campo etiqueta="Categoría">{proveedor.category}</Campo>
            <Campo etiqueta="Responsable">{proveedor.owner}</Campo>
            <Campo etiqueta="Criticidad">
              <Badge tono={TONO_CRITICIDAD[proveedor.criticality]}>{ETIQUETAS_CRITICIDAD[proveedor.criticality]}</Badge>
            </Campo>
            <Campo etiqueta="Estado">
              <Badge tono={TONO_ESTADO_PROVEEDOR[proveedor.status]}>
                {ETIQUETAS_ESTADO_PROVEEDOR[proveedor.status]}
              </Badge>
            </Campo>
            <Campo etiqueta="Clasificación de datos">
              <Badge tono={TONO_CLASIFICACION[proveedor.data_classification]}>
                {ETIQUETAS_CLASIFICACION[proveedor.data_classification]}
              </Badge>
            </Campo>
            {proveedor.description && <Campo etiqueta="Descripción">{proveedor.description}</Campo>}
          </dl>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Contrato</h2>
          <dl className="mt-3 space-y-3">
            <Campo etiqueta="Inicio de la relación">
              {new Date(proveedor.relationship_start_date).toLocaleDateString("es-ES")}
            </Campo>
            <Campo etiqueta="Fin de contrato">
              <div className="flex items-center gap-1.5">
                {proveedor.contract_end_date
                  ? new Date(proveedor.contract_end_date).toLocaleDateString("es-ES")
                  : "Sin definir"}
                {proveedor.is_contract_expired && <Badge tono="rojo">Vencido</Badge>}
                {proveedor.is_contract_expiring_soon && <Badge tono="ambar">Próximo a vencer</Badge>}
              </div>
            </Campo>
          </dl>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Seguridad</h2>
          <dl className="mt-3 space-y-3">
            <Campo etiqueta="Última revisión">
              {proveedor.last_security_review_date
                ? new Date(proveedor.last_security_review_date).toLocaleDateString("es-ES")
                : "Sin realizar"}
            </Campo>
            <Campo etiqueta="Próxima revisión">
              <div className="flex items-center gap-1.5">
                {proveedor.next_security_review_date
                  ? new Date(proveedor.next_security_review_date).toLocaleDateString("es-ES")
                  : "Sin definir"}
                {proveedor.is_review_overdue && <Badge tono="rojo">Vencida</Badge>}
                {proveedor.is_review_due_soon && <Badge tono="ambar">Próxima</Badge>}
              </div>
            </Campo>
            <Campo etiqueta="Due diligence">
              <Badge tono={TONO_DUE_DILIGENCE[proveedor.due_diligence_status]}>
                {ETIQUETAS_DUE_DILIGENCE[proveedor.due_diligence_status]}
              </Badge>
            </Campo>
          </dl>
        </div>
      </div>

      {proveedor.actions.length > 0 && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Acciones de remediación</h2>
          <p className="mt-1 text-xs text-slate-400">Derivadas de los hallazgos relacionados con este proveedor.</p>
          <ul className="mt-3 space-y-2">
            {proveedor.actions.map((accion) => (
              <li key={accion.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/acciones/${accion.id}`} className="text-slate-900 hover:underline">
                  {accion.action_id} — {accion.title}
                </Link>
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500">{accion.owner}</span>
                  <Badge tono={TONO_ESTADO_ACCION[accion.status]}>{ETIQUETAS_ESTADO_ACCION[accion.status]}</Badge>
                  {accion.is_overdue && <Badge tono="rojo">Vencida</Badge>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Riesgos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {proveedor.risks.length === 0 && <li className="text-sm text-slate-400">Sin riesgos relacionados.</li>}
            {proveedor.risks.map((riesgo) => (
              <li key={riesgo.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/riesgos/${riesgo.id}`} className="text-slate-900 hover:underline">
                  {riesgo.title}
                </Link>
                <div className="flex items-center gap-2">
                  <Badge tono={TONO_NIVEL_RIESGO[riesgo.inherent_level]}>
                    {ETIQUETAS_NIVEL_RIESGO[riesgo.inherent_level]}
                  </Badge>
                  {puedeEditar && (
                    <button
                      onClick={async () => {
                        await desvincularRiesgoProveedor(proveedor.id, riesgo.id);
                        await recargar();
                      }}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Quitar
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {puedeEditar && (
            <div className="mt-4 flex gap-2">
              <select
                value={riesgoSeleccionado}
                onChange={(evento) => setRiesgoSeleccionado(evento.target.value)}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Vincular riesgo…</option>
                {riesgosDisponibles
                  .filter((r) => !riesgosVinculadosIds.has(r.id))
                  .map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.title}
                    </option>
                  ))}
              </select>
              <button
                onClick={async () => {
                  if (!riesgoSeleccionado) return;
                  await vincularRiesgoProveedor(proveedor.id, riesgoSeleccionado);
                  setRiesgoSeleccionado("");
                  await recargar();
                }}
                disabled={!riesgoSeleccionado}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
              >
                Añadir
              </button>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Evidencias relacionadas</h2>
          <ul className="mt-3 space-y-2">
            {proveedor.evidence.length === 0 && (
              <li className="text-sm text-slate-400">Sin evidencias relacionadas.</li>
            )}
            {proveedor.evidence.map((evidencia) => (
              <li key={evidencia.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/evidencias/${evidencia.id}`} className="text-slate-900 hover:underline">
                  {evidencia.name}
                </Link>
                <div className="flex items-center gap-2">
                  <Badge tono={TONO_CLASIFICACION[evidencia.classification]}>
                    {ETIQUETAS_CLASIFICACION[evidencia.classification]}
                  </Badge>
                  {puedeEditar && (
                    <button
                      onClick={async () => {
                        await desvincularEvidenciaProveedor(proveedor.id, evidencia.id);
                        await recargar();
                      }}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Quitar
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {puedeEditar && (
            <div className="mt-4 flex gap-2">
              <select
                value={evidenciaSeleccionada}
                onChange={(evento) => setEvidenciaSeleccionada(evento.target.value)}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Vincular evidencia…</option>
                {evidenciasDisponibles
                  .filter((e) => !evidenciasVinculadasIds.has(e.id))
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name}
                    </option>
                  ))}
              </select>
              <button
                onClick={async () => {
                  if (!evidenciaSeleccionada) return;
                  await vincularEvidenciaProveedor(proveedor.id, evidenciaSeleccionada);
                  setEvidenciaSeleccionada("");
                  await recargar();
                }}
                disabled={!evidenciaSeleccionada}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
              >
                Añadir
              </button>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-700">Hallazgos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {proveedor.findings.length === 0 && (
              <li className="text-sm text-slate-400">Sin hallazgos relacionados.</li>
            )}
            {proveedor.findings.map((hallazgo) => (
              <li key={hallazgo.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/hallazgos/${hallazgo.id}`} className="text-slate-900 hover:underline">
                  {hallazgo.finding_id} — {hallazgo.title}
                </Link>
                <div className="flex items-center gap-2">
                  <Badge tono={TONO_CRITICIDAD[hallazgo.severity]}>{ETIQUETAS_CRITICIDAD[hallazgo.severity]}</Badge>
                  <Badge tono={TONO_ESTADO_HALLAZGO[hallazgo.status]}>
                    {ETIQUETAS_ESTADO_HALLAZGO[hallazgo.status]}
                  </Badge>
                  {puedeEditar && (
                    <button
                      onClick={async () => {
                        await desvincularHallazgoProveedor(proveedor.id, hallazgo.id);
                        await recargar();
                      }}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Quitar
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {puedeEditar && (
            <div className="mt-4 flex gap-2">
              <select
                value={hallazgoSeleccionado}
                onChange={(evento) => setHallazgoSeleccionado(evento.target.value)}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Vincular hallazgo…</option>
                {hallazgosDisponibles
                  .filter((f) => !hallazgosVinculadosIds.has(f.id))
                  .map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.finding_id} — {f.title}
                    </option>
                  ))}
              </select>
              <button
                onClick={async () => {
                  if (!hallazgoSeleccionado) return;
                  await vincularHallazgoProveedor(proveedor.id, hallazgoSeleccionado);
                  setHallazgoSeleccionado("");
                  await recargar();
                }}
                disabled={!hallazgoSeleccionado}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
              >
                Añadir
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
