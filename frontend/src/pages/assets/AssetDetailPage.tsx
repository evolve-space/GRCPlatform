import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { eliminarActivo, obtenerActivo } from "../../lib/assets";
import { obtenerMensajeError } from "../../lib/api";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_ACTIVO,
  ETIQUETAS_TIPO_ACTIVO,
  TONO_CRITICIDAD,
} from "../../lib/labels";
import { puedeEliminar, puedeEscribir } from "../../lib/permisos";
import type { Asset } from "../../types";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{etiqueta}</dt>
      <dd className="mt-1 text-slate-900">{children}</dd>
    </div>
  );
}

export function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const [activo, setActivo] = useState<Asset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [eliminando, setEliminando] = useState(false);

  useEffect(() => {
    if (!id) return;
    obtenerActivo(id)
      .then(setActivo)
      .catch((err) => setError(obtenerMensajeError(err)));
  }, [id]);

  async function manejarEliminar() {
    if (!id || !window.confirm("¿Seguro que quieres eliminar este activo?")) return;
    setEliminando(true);
    try {
      await eliminarActivo(id);
      navigate("/activos");
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEliminando(false);
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!activo) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <Link to="/activos" className="text-sm text-slate-500 hover:underline">
            ← Volver a Activos
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">{activo.name}</h1>
        </div>
        <div className="flex gap-2">
          {puedeEscribir(usuario?.role) && (
            <Link
              to={`/activos/${activo.id}/editar`}
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
        <Campo etiqueta="Tipo">{ETIQUETAS_TIPO_ACTIVO[activo.asset_type]}</Campo>
        <Campo etiqueta="Criticidad">
          <Badge tono={TONO_CRITICIDAD[activo.criticality]}>
            {ETIQUETAS_CRITICIDAD[activo.criticality]}
          </Badge>
        </Campo>
        <Campo etiqueta="Clasificación de datos">
          {ETIQUETAS_CLASIFICACION[activo.data_classification]}
        </Campo>
        <Campo etiqueta="Estado">{ETIQUETAS_ESTADO_ACTIVO[activo.status]}</Campo>
        <Campo etiqueta="Responsable">{activo.owner}</Campo>
        <Campo etiqueta="Última actualización">
          {new Date(activo.updated_at).toLocaleString("es-ES")}
        </Campo>
        <div className="sm:col-span-2">
          <Campo etiqueta="Descripción">{activo.description || "Sin descripción."}</Campo>
        </div>
      </dl>
    </div>
  );
}
