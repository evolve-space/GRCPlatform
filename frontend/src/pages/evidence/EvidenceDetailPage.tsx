import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { obtenerMensajeError } from "../../lib/api";
import { listarActivos } from "../../lib/assets";
import { listarControles } from "../../lib/controls";
import {
  desvincularActivoEvidencia,
  desvincularControlEvidencia,
  desvincularRequisitoEvidencia,
  desvincularRiesgoEvidencia,
  descargarEvidencia,
  eliminarEvidencia,
  obtenerEvidencia,
  verificarIntegridad,
  vincularActivoEvidencia,
  vincularControlEvidencia,
  vincularRequisitoEvidencia,
  vincularRiesgoEvidencia,
} from "../../lib/evidence";
import { listarFrameworks, listarRequisitos } from "../../lib/frameworks";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_EFECTIVO_EVIDENCIA,
  ETIQUETAS_NIVEL_RIESGO,
  TONO_CLASIFICACION,
  TONO_CRITICIDAD,
  TONO_ESTADO_EFECTIVO_EVIDENCIA,
  TONO_NIVEL_RIESGO,
} from "../../lib/labels";
import { puedeEliminar, puedeEscribir } from "../../lib/permisos";
import { listarRiesgos } from "../../lib/risks";
import type {
  Asset,
  Control,
  EvidenceDetail,
  IntegrityCheckResult,
  Requirement,
  Risk,
} from "../../types";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{etiqueta}</dt>
      <dd className="mt-1 text-slate-900">{children}</dd>
    </div>
  );
}

function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface RequisitoConMarco extends Requirement {
  framework_short_name: string;
}

export function EvidenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { usuario } = useAuth();

  const [evidencia, setEvidencia] = useState<EvidenceDetail | null>(null);
  const [controlesDisponibles, setControlesDisponibles] = useState<Control[]>([]);
  const [riesgosDisponibles, setRiesgosDisponibles] = useState<Risk[]>([]);
  const [activosDisponibles, setActivosDisponibles] = useState<Asset[]>([]);
  const [requisitosDisponibles, setRequisitosDisponibles] = useState<RequisitoConMarco[]>([]);

  const [controlSeleccionado, setControlSeleccionado] = useState("");
  const [riesgoSeleccionado, setRiesgoSeleccionado] = useState("");
  const [activoSeleccionado, setActivoSeleccionado] = useState("");
  const [requisitoSeleccionado, setRequisitoSeleccionado] = useState("");

  const [integridad, setIntegridad] = useState<IntegrityCheckResult | null>(null);
  const [verificando, setVerificando] = useState(false);
  const [eliminando, setEliminando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const puedeEditar = puedeEscribir(usuario?.role);

  async function recargar() {
    if (!id) return;
    const datos = await obtenerEvidencia(id);
    setEvidencia(datos);
  }

  useEffect(() => {
    recargar().catch((err) => setError(obtenerMensajeError(err)));
    listarControles({ page: 1, page_size: 100 }).then((r) => setControlesDisponibles(r.items));
    listarRiesgos({ page: 1, page_size: 100 }).then((r) => setRiesgosDisponibles(r.items));
    listarActivos({ page: 1, page_size: 100 }).then((r) => setActivosDisponibles(r.items));
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

  async function manejarDescarga() {
    if (!evidencia) return;
    try {
      await descargarEvidencia(evidencia.id, evidencia.original_filename);
    } catch (err) {
      setError(obtenerMensajeError(err));
    }
  }

  async function manejarVerificarIntegridad() {
    if (!id) return;
    setVerificando(true);
    try {
      const resultado = await verificarIntegridad(id);
      setIntegridad(resultado);
    } catch (err) {
      setError(obtenerMensajeError(err));
    } finally {
      setVerificando(false);
    }
  }

  async function manejarEliminar() {
    if (!id || !window.confirm("¿Seguro que quieres eliminar esta evidencia? Esta acción no se puede deshacer.")) {
      return;
    }
    setEliminando(true);
    try {
      await eliminarEvidencia(id);
      navigate("/evidencias");
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEliminando(false);
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!evidencia) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const controlesVinculadosIds = new Set(evidencia.controls.map((c) => c.id));
  const riesgosVinculadosIds = new Set(evidencia.risks.map((r) => r.id));
  const activosVinculadosIds = new Set(evidencia.assets.map((a) => a.id));
  const requisitosVinculadosIds = new Set(evidencia.requirements.map((r) => r.id));

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <Link to="/evidencias" className="text-sm text-slate-500 hover:underline">
            ← Volver a Evidencias
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">{evidencia.name}</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={manejarDescarga}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Descargar
          </button>
          {puedeEditar && (
            <Link
              to={`/evidencias/${evidencia.id}/editar`}
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
        <dl className="grid grid-cols-1 gap-6 rounded-lg border border-slate-200 bg-white p-6 sm:grid-cols-2 lg:col-span-2">
          <Campo etiqueta="Clasificación">
            <Badge tono={TONO_CLASIFICACION[evidencia.classification]}>
              {ETIQUETAS_CLASIFICACION[evidencia.classification]}
            </Badge>
          </Campo>
          <Campo etiqueta="Estado">
            <Badge tono={TONO_ESTADO_EFECTIVO_EVIDENCIA[evidencia.effective_status]}>
              {ETIQUETAS_ESTADO_EFECTIVO_EVIDENCIA[evidencia.effective_status]}
            </Badge>
          </Campo>
          <Campo etiqueta="Tipo">{evidencia.evidence_type}</Campo>
          <Campo etiqueta="Archivo original">{evidencia.original_filename}</Campo>
          <Campo etiqueta="Tipo MIME">{evidencia.mime_type}</Campo>
          <Campo etiqueta="Tamaño">{formatearTamano(evidencia.file_size)}</Campo>
          <Campo etiqueta="Fecha de recopilación">
            {new Date(evidencia.collected_at).toLocaleDateString("es-ES")}
          </Campo>
          <Campo etiqueta="Fecha de expiración">
            {evidencia.expires_at ? new Date(evidencia.expires_at).toLocaleDateString("es-ES") : "Sin expiración"}
          </Campo>
          <div className="sm:col-span-2">
            <Campo etiqueta="Descripción">{evidencia.description || "Sin descripción."}</Campo>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-slate-500">SHA-256</dt>
            <dd className="mt-1 break-all font-mono text-xs text-slate-700">{evidencia.sha256}</dd>
          </div>
        </dl>

        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <h2 className="text-sm font-semibold text-slate-700">Integridad del archivo</h2>
          <p className="mt-1 text-xs text-slate-500">
            Vuelve a calcular el SHA-256 del archivo almacenado y lo compara con el valor guardado.
          </p>
          <button
            onClick={manejarVerificarIntegridad}
            disabled={verificando}
            className="mt-3 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-60"
          >
            {verificando ? "Verificando…" : "Verificar integridad"}
          </button>

          {integridad && (
            <div className="mt-4">
              {integridad.status === "ok" && (
                <Badge tono="verde">Integridad correcta</Badge>
              )}
              {integridad.status === "mismatch" && (
                <Badge tono="rojo">Integridad comprometida</Badge>
              )}
              {integridad.status === "not_found" && (
                <Badge tono="rojo">Archivo no encontrado</Badge>
              )}
              {integridad.sha256_calculated && (
                <p className="mt-2 break-all font-mono text-xs text-slate-500">
                  Calculado: {integridad.sha256_calculated}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Controles relacionados</h2>
          <ul className="mt-3 space-y-2">
            {evidencia.controls.length === 0 && (
              <li className="text-sm text-slate-400">Sin controles relacionados.</li>
            )}
            {evidencia.controls.map((control) => (
              <li key={control.id} className="flex items-center justify-between text-sm">
                <Link to={`/controles/${control.id}`} className="text-slate-900 hover:underline">
                  {control.control_id} — {control.name}
                </Link>
                {puedeEditar && (
                  <button
                    onClick={async () => {
                      await desvincularControlEvidencia(evidencia.id, control.id);
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
                  await vincularControlEvidencia(evidencia.id, controlSeleccionado);
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
          <h2 className="text-sm font-semibold text-slate-700">Riesgos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {evidencia.risks.length === 0 && (
              <li className="text-sm text-slate-400">Sin riesgos relacionados.</li>
            )}
            {evidencia.risks.map((riesgo) => (
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
                        await desvincularRiesgoEvidencia(evidencia.id, riesgo.id);
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
                  await vincularRiesgoEvidencia(evidencia.id, riesgoSeleccionado);
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
          <h2 className="text-sm font-semibold text-slate-700">Activos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {evidencia.assets.length === 0 && (
              <li className="text-sm text-slate-400">Sin activos relacionados.</li>
            )}
            {evidencia.assets.map((activo) => (
              <li key={activo.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/activos/${activo.id}`} className="text-slate-900 hover:underline">
                  {activo.name}
                </Link>
                <div className="flex items-center gap-2">
                  <Badge tono={TONO_CRITICIDAD[activo.criticality]}>
                    {ETIQUETAS_CRITICIDAD[activo.criticality]}
                  </Badge>
                  {puedeEditar && (
                    <button
                      onClick={async () => {
                        await desvincularActivoEvidencia(evidencia.id, activo.id);
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
                  await vincularActivoEvidencia(evidencia.id, activoSeleccionado);
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
            {evidencia.requirements.length === 0 && (
              <li className="text-sm text-slate-400">Sin requisitos relacionados.</li>
            )}
            {evidencia.requirements.map((req) => (
              <li key={req.id} className="flex items-center justify-between gap-2 text-sm">
                <Link to={`/marcos/${req.framework_id}`} className="text-slate-900 hover:underline">
                  {req.framework_short_name} — {req.code}
                </Link>
                {puedeEditar && (
                  <button
                    onClick={async () => {
                      await desvincularRequisitoEvidencia(evidencia.id, req.id);
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
                  await vincularRequisitoEvidencia(evidencia.id, requisitoSeleccionado);
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
      </div>
    </div>
  );
}
