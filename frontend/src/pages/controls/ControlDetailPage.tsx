import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { obtenerMensajeError } from "../../lib/api";
import { listarActivos } from "../../lib/assets";
import {
  desvincularActivo,
  desvincularRiesgo,
  eliminarControl,
  obtenerControl,
  vincularActivo,
  vincularRiesgo,
} from "../../lib/controls";
import {
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_CONTROL,
  ETIQUETAS_FRECUENCIA,
  ETIQUETAS_NIVEL_RIESGO,
  TONO_CRITICIDAD,
  TONO_ESTADO_CONTROL,
  TONO_NIVEL_RIESGO,
} from "../../lib/labels";
import { puedeEliminar, puedeEscribir } from "../../lib/permisos";
import { listarRiesgos } from "../../lib/risks";
import type { Asset, ControlDetail, Risk } from "../../types";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{etiqueta}</dt>
      <dd className="mt-1 text-slate-900">{children}</dd>
    </div>
  );
}

export function ControlDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const [control, setControl] = useState<ControlDetail | null>(null);
  const [activosDisponibles, setActivosDisponibles] = useState<Asset[]>([]);
  const [riesgosDisponibles, setRiesgosDisponibles] = useState<Risk[]>([]);
  const [activoSeleccionado, setActivoSeleccionado] = useState("");
  const [riesgoSeleccionado, setRiesgoSeleccionado] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [eliminando, setEliminando] = useState(false);

  const puedeEditar = puedeEscribir(usuario?.role);

  async function recargar() {
    if (!id) return;
    const datos = await obtenerControl(id);
    setControl(datos);
  }

  useEffect(() => {
    recargar().catch((err) => setError(obtenerMensajeError(err)));
    listarActivos({ page: 1, page_size: 100 }).then((r) => setActivosDisponibles(r.items));
    listarRiesgos({ page: 1, page_size: 100 }).then((r) => setRiesgosDisponibles(r.items));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function manejarEliminar() {
    if (!id || !window.confirm("¿Seguro que quieres eliminar este control?")) return;
    setEliminando(true);
    try {
      await eliminarControl(id);
      navigate("/controles");
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEliminando(false);
    }
  }

  async function agregarActivo() {
    if (!id || !activoSeleccionado) return;
    try {
      await vincularActivo(id, activoSeleccionado);
      setActivoSeleccionado("");
      await recargar();
    } catch (err) {
      setError(obtenerMensajeError(err));
    }
  }

  async function quitarActivo(assetId: string) {
    if (!id) return;
    try {
      await desvincularActivo(id, assetId);
      await recargar();
    } catch (err) {
      setError(obtenerMensajeError(err));
    }
  }

  async function agregarRiesgo() {
    if (!id || !riesgoSeleccionado) return;
    try {
      await vincularRiesgo(id, riesgoSeleccionado);
      setRiesgoSeleccionado("");
      await recargar();
    } catch (err) {
      setError(obtenerMensajeError(err));
    }
  }

  async function quitarRiesgo(riskId: string) {
    if (!id) return;
    try {
      await desvincularRiesgo(id, riskId);
      await recargar();
    } catch (err) {
      setError(obtenerMensajeError(err));
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!control) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const activosVinculadosIds = new Set(control.assets.map((a) => a.id));
  const riesgosVinculadosIds = new Set(control.risks.map((r) => r.id));

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <Link to="/controles" className="text-sm text-slate-500 hover:underline">
            ← Volver a Controles
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">
            {control.control_id} · {control.name}
          </h1>
        </div>
        <div className="flex gap-2">
          {puedeEditar && (
            <Link
              to={`/controles/${control.id}/editar`}
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
        <Campo etiqueta="Estado">
          <Badge tono={TONO_ESTADO_CONTROL[control.status]}>
            {ETIQUETAS_ESTADO_CONTROL[control.status]}
          </Badge>
        </Campo>
        <Campo etiqueta="Frecuencia">{ETIQUETAS_FRECUENCIA[control.frequency]}</Campo>
        <Campo etiqueta="Responsable">{control.owner}</Campo>
        <Campo etiqueta="Categoría">{control.category}</Campo>
        <div className="sm:col-span-2">
          <Campo etiqueta="Objetivo">{control.objective || "Sin objetivo definido."}</Campo>
        </div>
        <div className="sm:col-span-2">
          <Campo etiqueta="Descripción">{control.description || "Sin descripción."}</Campo>
        </div>
      </dl>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Riesgos relacionados</h2>
          <ul className="mt-3 space-y-2">
            {control.risks.length === 0 && (
              <li className="text-sm text-slate-400">Sin riesgos relacionados.</li>
            )}
            {control.risks.map((riesgo) => (
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
                      onClick={() => quitarRiesgo(riesgo.id)}
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
                  .filter((riesgo) => !riesgosVinculadosIds.has(riesgo.id))
                  .map((riesgo) => (
                    <option key={riesgo.id} value={riesgo.id}>
                      {riesgo.title}
                    </option>
                  ))}
              </select>
              <button
                onClick={agregarRiesgo}
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
            {control.assets.length === 0 && (
              <li className="text-sm text-slate-400">Sin activos relacionados.</li>
            )}
            {control.assets.map((activo) => (
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
                      onClick={() => quitarActivo(activo.id)}
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
                  .filter((activo) => !activosVinculadosIds.has(activo.id))
                  .map((activo) => (
                    <option key={activo.id} value={activo.id}>
                      {activo.name}
                    </option>
                  ))}
              </select>
              <button
                onClick={agregarActivo}
                disabled={!activoSeleccionado}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
              >
                Añadir
              </button>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-700">Marcos de cumplimiento relacionados</h2>
          <ul className="mt-3 space-y-2">
            {control.requirements.length === 0 && (
              <li className="text-sm text-slate-400">Sin requisitos relacionados.</li>
            )}
            {control.requirements.map((req) => (
              <li key={req.id} className="text-sm">
                <Link to={`/marcos/${req.framework_id}`} className="text-slate-900 hover:underline">
                  {req.framework_short_name} — {req.code}
                </Link>
                <p className="text-slate-500">{req.name}</p>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-400">
            Para vincular requisitos, hazlo desde el detalle del marco de cumplimiento.
          </p>
        </div>
      </div>
    </div>
  );
}
