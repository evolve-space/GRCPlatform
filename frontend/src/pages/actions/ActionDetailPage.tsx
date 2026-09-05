import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { obtenerMensajeError } from "../../lib/api";
import { listarEvidencias } from "../../lib/evidence";
import { obtenerHallazgo } from "../../lib/findings";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_ACCION,
  TONO_CLASIFICACION,
  TONO_CRITICIDAD,
  TONO_ESTADO_ACCION,
} from "../../lib/labels";
import { puedeEliminar, puedeEscribir } from "../../lib/permisos";
import {
  desvincularEvidenciaAccion,
  eliminarAccion,
  obtenerAccion,
  vincularEvidenciaAccion,
} from "../../lib/remediationActions";
import type { Evidence, Finding, RemediationActionDetail } from "../../types";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{etiqueta}</dt>
      <dd className="mt-1 text-slate-900">{children}</dd>
    </div>
  );
}

export function ActionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { usuario } = useAuth();

  const [accion, setAccion] = useState<RemediationActionDetail | null>(null);
  const [hallazgo, setHallazgo] = useState<Finding | null>(null);
  const [evidenciasDisponibles, setEvidenciasDisponibles] = useState<Evidence[]>([]);
  const [evidenciaSeleccionada, setEvidenciaSeleccionada] = useState("");
  const [eliminando, setEliminando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const puedeEditar = puedeEscribir(usuario?.role);

  async function recargar() {
    if (!id) return;
    const datos = await obtenerAccion(id);
    setAccion(datos);
    const hallazgoAsociado = await obtenerHallazgo(datos.finding_id);
    setHallazgo(hallazgoAsociado);
  }

  useEffect(() => {
    recargar().catch((err) => setError(obtenerMensajeError(err)));
    listarEvidencias({ page: 1, page_size: 100 }).then((r) => setEvidenciasDisponibles(r.items));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function manejarEliminar() {
    if (!id || !window.confirm("¿Seguro que quieres eliminar esta acción?")) return;
    setEliminando(true);
    try {
      await eliminarAccion(id);
      navigate(hallazgo ? `/hallazgos/${hallazgo.id}` : "/acciones");
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEliminando(false);
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!accion) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const evidenciasVinculadasIds = new Set(accion.evidence.map((e) => e.id));

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <Link to="/acciones" className="text-sm text-slate-500 hover:underline">
            ← Volver a Acciones
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">
            {accion.action_id} · {accion.title}
          </h1>
          {hallazgo && (
            <p className="mt-1 text-sm text-slate-500">
              Hallazgo:{" "}
              <Link to={`/hallazgos/${hallazgo.id}`} className="text-slate-900 hover:underline">
                {hallazgo.finding_id} — {hallazgo.title}
              </Link>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          {puedeEditar && (
            <Link
              to={`/acciones/${accion.id}/editar`}
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

      <dl className="mt-6 grid grid-cols-1 gap-6 rounded-lg border border-slate-200 bg-white p-6 sm:grid-cols-2">
        <Campo etiqueta="Prioridad">
          <Badge tono={TONO_CRITICIDAD[accion.priority]}>{ETIQUETAS_CRITICIDAD[accion.priority]}</Badge>
        </Campo>
        <Campo etiqueta="Estado">
          <div className="flex items-center gap-1.5">
            <Badge tono={TONO_ESTADO_ACCION[accion.status]}>{ETIQUETAS_ESTADO_ACCION[accion.status]}</Badge>
            {accion.is_overdue && <Badge tono="rojo">Vencida</Badge>}
          </div>
        </Campo>
        <Campo etiqueta="Responsable">{accion.owner}</Campo>
        <Campo etiqueta="Fecha límite">{new Date(accion.due_date).toLocaleDateString("es-ES")}</Campo>
        <Campo etiqueta="Fecha de finalización">
          {accion.completed_at ? new Date(accion.completed_at).toLocaleDateString("es-ES") : "Sin finalizar"}
        </Campo>
        <div className="sm:col-span-2">
          <Campo etiqueta="Descripción">{accion.description || "Sin descripción."}</Campo>
        </div>
        {accion.completion_notes && (
          <div className="sm:col-span-2">
            <Campo etiqueta="Notas de finalización">{accion.completion_notes}</Campo>
          </div>
        )}
      </dl>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">Evidencias de cierre</h2>
        <ul className="mt-3 space-y-2">
          {accion.evidence.length === 0 && (
            <li className="text-sm text-slate-400">Sin evidencias de cierre todavía.</li>
          )}
          {accion.evidence.map((evidencia) => (
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
                      await desvincularEvidenciaAccion(accion.id, evidencia.id);
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
              <option value="">Vincular evidencia de cierre…</option>
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
                await vincularEvidenciaAccion(accion.id, evidenciaSeleccionada);
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
  );
}
