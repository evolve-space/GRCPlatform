import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { obtenerMensajeError } from "../../lib/api";
import { listarActivos } from "../../lib/assets";
import { listarControles } from "../../lib/controls";
import { listarEvidencias } from "../../lib/evidence";
import {
  desvincularActivoHallazgo,
  desvincularControlHallazgo,
  desvincularEvidenciaHallazgo,
  desvincularRequisitoHallazgo,
  desvincularRiesgoHallazgo,
  eliminarHallazgo,
  obtenerHallazgo,
  vincularActivoHallazgo,
  vincularControlHallazgo,
  vincularEvidenciaHallazgo,
  vincularRequisitoHallazgo,
  vincularRiesgoHallazgo,
} from "../../lib/findings";
import { listarFrameworks, listarRequisitos } from "../../lib/frameworks";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_ACCION,
  ETIQUETAS_ESTADO_HALLAZGO,
  ETIQUETAS_NIVEL_RIESGO,
  ETIQUETAS_ORIGEN_HALLAZGO,
  ETIQUETAS_TIPO_HALLAZGO,
  TONO_CLASIFICACION,
  TONO_CRITICIDAD,
  TONO_ESTADO_ACCION,
  TONO_ESTADO_HALLAZGO,
  TONO_NIVEL_RIESGO,
} from "../../lib/labels";
import { puedeEliminar, puedeEscribir } from "../../lib/permisos";
import { listarRiesgos } from "../../lib/risks";
import type { Asset, Control, Evidence, FindingDetail, Requirement, Risk } from "../../types";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{etiqueta}</dt>
      <dd className="mt-1 text-slate-900">{children}</dd>
    </div>
  );
}

interface RequisitoConMarco extends Requirement {
  framework_short_name: string;
}

export function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { usuario } = useAuth();

  const [hallazgo, setHallazgo] = useState<FindingDetail | null>(null);
  const [riesgosDisponibles, setRiesgosDisponibles] = useState<Risk[]>([]);
  const [controlesDisponibles, setControlesDisponibles] = useState<Control[]>([]);
  const [activosDisponibles, setActivosDisponibles] = useState<Asset[]>([]);
  const [requisitosDisponibles, setRequisitosDisponibles] = useState<RequisitoConMarco[]>([]);
  const [evidenciasDisponibles, setEvidenciasDisponibles] = useState<Evidence[]>([]);

  const [riesgoSeleccionado, setRiesgoSeleccionado] = useState("");
  const [controlSeleccionado, setControlSeleccionado] = useState("");
  const [activoSeleccionado, setActivoSeleccionado] = useState("");
  const [requisitoSeleccionado, setRequisitoSeleccionado] = useState("");
  const [evidenciaSeleccionada, setEvidenciaSeleccionada] = useState("");

  const [eliminando, setEliminando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const puedeEditar = puedeEscribir(usuario?.role);

  async function recargar() {
    if (!id) return;
    const datos = await obtenerHallazgo(id);
    setHallazgo(datos);
  }

  useEffect(() => {
    recargar().catch((err) => setError(obtenerMensajeError(err)));
    listarRiesgos({ page: 1, page_size: 100 }).then((r) => setRiesgosDisponibles(r.items));
    listarControles({ page: 1, page_size: 100 }).then((r) => setControlesDisponibles(r.items));
    listarActivos({ page: 1, page_size: 100 }).then((r) => setActivosDisponibles(r.items));
    listarEvidencias({ page: 1, page_size: 100 }).then((r) => setEvidenciasDisponibles(r.items));
    listarFrameworks().then(async (frameworks) => {
      const listas = await Promise.all(
        frameworks.map((f) => listarRequisitos(f.id, { page: 1, page_size: 200 })),
      );
      const todos = frameworks.flatMap((framework, indice) =>
        listas[indice].items.map((req) => ({ ...req, framework_short_name: framework.short_name })),
      );
      setRequisitosDisponibles(todos);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function manejarEliminar() {
    if (!id || !window.confirm("¿Seguro que quieres eliminar este hallazgo? Se eliminarán también sus acciones.")) {
      return;
    }
    setEliminando(true);
    try {
      await eliminarHallazgo(id);
      navigate("/hallazgos");
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEliminando(false);
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!hallazgo) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const riesgosVinculadosIds = new Set(hallazgo.risks.map((r) => r.id));
  const controlesVinculadosIds = new Set(hallazgo.controls.map((c) => c.id));
  const activosVinculadosIds = new Set(hallazgo.assets.map((a) => a.id));
  const requisitosVinculadosIds = new Set(hallazgo.requirements.map((r) => r.id));
  const evidenciasVinculadasIds = new Set(hallazgo.evidence.map((e) => e.id));

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <Link to="/hallazgos" className="text-sm text-slate-500 hover:underline">
            ← Volver a Hallazgos
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">
            {hallazgo.finding_id} · {hallazgo.title}
          </h1>
        </div>
        <div className="flex gap-2">
          {puedeEditar && (
            <Link
              to={`/hallazgos/${hallazgo.id}/editar`}
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

      <dl className="mt-6 grid grid-cols-1 gap-6 rounded-lg border border-slate-200 bg-white p-6 sm:grid-cols-2 lg:grid-cols-3">
        <Campo etiqueta="Severidad">
          <Badge tono={TONO_CRITICIDAD[hallazgo.severity]}>{ETIQUETAS_CRITICIDAD[hallazgo.severity]}</Badge>
        </Campo>
        <Campo etiqueta="Estado">
          <div className="flex items-center gap-1.5">
            <Badge tono={TONO_ESTADO_HALLAZGO[hallazgo.status]}>
              {ETIQUETAS_ESTADO_HALLAZGO[hallazgo.status]}
            </Badge>
            {hallazgo.is_overdue && <Badge tono="rojo">Vencido</Badge>}
          </div>
        </Campo>
        <Campo etiqueta="Responsable">{hallazgo.owner}</Campo>
        <Campo etiqueta="Tipo">{ETIQUETAS_TIPO_HALLAZGO[hallazgo.finding_type]}</Campo>
        <Campo etiqueta="Origen">{ETIQUETAS_ORIGEN_HALLAZGO[hallazgo.source]}</Campo>
        <Campo etiqueta="Fecha de descubrimiento">
          {new Date(hallazgo.discovered_at).toLocaleDateString("es-ES")}
        </Campo>
        <Campo etiqueta="Fecha límite">{new Date(hallazgo.due_date).toLocaleDateString("es-ES")}</Campo>
        <Campo etiqueta="Fecha de cierre">
          {hallazgo.closed_at ? new Date(hallazgo.closed_at).toLocaleDateString("es-ES") : "Sin cerrar"}
        </Campo>
        <div className="sm:col-span-2 lg:col-span-3">
          <Campo etiqueta="Descripción">{hallazgo.description || "Sin descripción."}</Campo>
        </div>
        {hallazgo.resolution_summary && (
          <div className="sm:col-span-2 lg:col-span-3">
            <Campo etiqueta="Resumen de resolución">{hallazgo.resolution_summary}</Campo>
          </div>
        )}
      </dl>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Acciones de remediación</h2>
          {puedeEditar && (
            <Link
              to={`/acciones/nueva?finding_id=${hallazgo.id}`}
              className="text-sm font-medium text-slate-900 hover:underline"
            >
              + Nueva acción
            </Link>
          )}
        </div>
        <ul className="mt-3 space-y-2">
          {hallazgo.actions.length === 0 && (
            <li className="text-sm text-slate-400">Sin acciones de remediación todavía.</li>
          )}
          {hallazgo.actions.map((accion) => (
            <li key={accion.id} className="flex items-center justify-between gap-2 text-sm">
              <Link to={`/acciones/${accion.id}`} className="text-slate-900 hover:underline">
                {accion.action_id} — {accion.title}
              </Link>
              <div className="flex items-center gap-1.5">
                <span className="text-slate-500">{accion.owner}</span>
                <Badge tono={TONO_CRITICIDAD[accion.priority]}>{ETIQUETAS_CRITICIDAD[accion.priority]}</Badge>
                <Badge tono={TONO_ESTADO_ACCION[accion.status]}>{ETIQUETAS_ESTADO_ACCION[accion.status]}</Badge>
                {accion.is_overdue && <Badge tono="rojo">Vencida</Badge>}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Riesgos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {hallazgo.risks.length === 0 && <li className="text-sm text-slate-400">Sin riesgos relacionados.</li>}
            {hallazgo.risks.map((riesgo) => (
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
                        await desvincularRiesgoHallazgo(hallazgo.id, riesgo.id);
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
                  await vincularRiesgoHallazgo(hallazgo.id, riesgoSeleccionado);
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
          <h2 className="text-sm font-semibold text-slate-700">Controles relacionados</h2>
          <ul className="mt-3 space-y-2">
            {hallazgo.controls.length === 0 && (
              <li className="text-sm text-slate-400">Sin controles relacionados.</li>
            )}
            {hallazgo.controls.map((control) => (
              <li key={control.id} className="flex items-center justify-between text-sm">
                <Link to={`/controles/${control.id}`} className="text-slate-900 hover:underline">
                  {control.control_id} — {control.name}
                </Link>
                {puedeEditar && (
                  <button
                    onClick={async () => {
                      await desvincularControlHallazgo(hallazgo.id, control.id);
                      await recargar();
                    }}
                    className="text-xs text-red-600 hover:underline"
                  >
                    Quitar
                  </button>
                )}
              </li>
            ))}
          </ul>
          {puedeEditar && (
            <div className="mt-4 flex gap-2">
              <select
                value={controlSeleccionado}
                onChange={(evento) => setControlSeleccionado(evento.target.value)}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Vincular control…</option>
                {controlesDisponibles
                  .filter((c) => !controlesVinculadosIds.has(c.id))
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.control_id} — {c.name}
                    </option>
                  ))}
              </select>
              <button
                onClick={async () => {
                  if (!controlSeleccionado) return;
                  await vincularControlHallazgo(hallazgo.id, controlSeleccionado);
                  setControlSeleccionado("");
                  await recargar();
                }}
                disabled={!controlSeleccionado}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
              >
                Añadir
              </button>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Activos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {hallazgo.assets.length === 0 && <li className="text-sm text-slate-400">Sin activos relacionados.</li>}
            {hallazgo.assets.map((activo) => (
              <li key={activo.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/activos/${activo.id}`} className="text-slate-900 hover:underline">
                  {activo.name}
                </Link>
                <div className="flex items-center gap-2">
                  <Badge tono={TONO_CRITICIDAD[activo.criticality]}>{ETIQUETAS_CRITICIDAD[activo.criticality]}</Badge>
                  {puedeEditar && (
                    <button
                      onClick={async () => {
                        await desvincularActivoHallazgo(hallazgo.id, activo.id);
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
                value={activoSeleccionado}
                onChange={(evento) => setActivoSeleccionado(evento.target.value)}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Vincular activo…</option>
                {activosDisponibles
                  .filter((a) => !activosVinculadosIds.has(a.id))
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
              </select>
              <button
                onClick={async () => {
                  if (!activoSeleccionado) return;
                  await vincularActivoHallazgo(hallazgo.id, activoSeleccionado);
                  setActivoSeleccionado("");
                  await recargar();
                }}
                disabled={!activoSeleccionado}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
              >
                Añadir
              </button>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Requisitos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {hallazgo.requirements.length === 0 && (
              <li className="text-sm text-slate-400">Sin requisitos relacionados.</li>
            )}
            {hallazgo.requirements.map((req) => (
              <li key={req.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/marcos/${req.framework_id}`} className="text-slate-900 hover:underline">
                  {req.framework_short_name} — {req.code}
                </Link>
                {puedeEditar && (
                  <button
                    onClick={async () => {
                      await desvincularRequisitoHallazgo(hallazgo.id, req.id);
                      await recargar();
                    }}
                    className="text-xs text-red-600 hover:underline"
                  >
                    Quitar
                  </button>
                )}
              </li>
            ))}
          </ul>
          {puedeEditar && (
            <div className="mt-4 flex gap-2">
              <select
                value={requisitoSeleccionado}
                onChange={(evento) => setRequisitoSeleccionado(evento.target.value)}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Vincular requisito…</option>
                {requisitosDisponibles
                  .filter((r) => !requisitosVinculadosIds.has(r.id))
                  .map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.framework_short_name} — {r.code} ({r.name})
                    </option>
                  ))}
              </select>
              <button
                onClick={async () => {
                  if (!requisitoSeleccionado) return;
                  await vincularRequisitoHallazgo(hallazgo.id, requisitoSeleccionado);
                  setRequisitoSeleccionado("");
                  await recargar();
                }}
                disabled={!requisitoSeleccionado}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
              >
                Añadir
              </button>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-700">Evidencias relacionadas</h2>
          <ul className="mt-3 space-y-2">
            {hallazgo.evidence.length === 0 && (
              <li className="text-sm text-slate-400">Sin evidencias relacionadas.</li>
            )}
            {hallazgo.evidence.map((evidencia) => (
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
                        await desvincularEvidenciaHallazgo(hallazgo.id, evidencia.id);
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
                  await vincularEvidenciaHallazgo(hallazgo.id, evidenciaSeleccionada);
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
      </div>
    </div>
  );
}
