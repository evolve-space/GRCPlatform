import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { obtenerMensajeError } from "../../lib/api";
import { obtenerActivo } from "../../lib/assets";
import {
  ETIQUETAS_ESTADO_RIESGO,
  ETIQUETAS_NIVEL_RIESGO,
  ETIQUETAS_TRATAMIENTO,
  TONO_ESTADO_RIESGO,
  TONO_NIVEL_RIESGO,
} from "../../lib/labels";
import { puedeEliminar, puedeEscribir } from "../../lib/permisos";
import { eliminarRiesgo, obtenerRiesgo } from "../../lib/risks";
import type { Risk } from "../../types";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{etiqueta}</dt>
      <dd className="mt-1 text-slate-900">{children}</dd>
    </div>
  );
}

export function RiskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const [riesgo, setRiesgo] = useState<Risk | null>(null);
  const [nombreActivo, setNombreActivo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [eliminando, setEliminando] = useState(false);

  useEffect(() => {
    if (!id) return;
    obtenerRiesgo(id)
      .then((datos) => {
        setRiesgo(datos);
        if (datos.asset_id) {
          obtenerActivo(datos.asset_id).then((activo) => setNombreActivo(activo.name));
        }
      })
      .catch((err) => setError(obtenerMensajeError(err)));
  }, [id]);

  async function manejarEliminar() {
    if (!id || !window.confirm("¿Seguro que quieres eliminar este riesgo?")) return;
    setEliminando(true);
    try {
      await eliminarRiesgo(id);
      navigate("/riesgos");
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEliminando(false);
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!riesgo) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <Link to="/riesgos" className="text-sm text-slate-500 hover:underline">
            ← Volver a Riesgos
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">{riesgo.title}</h1>
        </div>
        <div className="flex gap-2">
          {puedeEscribir(usuario?.role) && (
            <Link
              to={`/riesgos/${riesgo.id}/editar`}
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
        <div className="rounded-lg border border-slate-200 bg-white p-6 lg:col-span-2">
          <dl className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Campo etiqueta="Activo relacionado">
              {nombreActivo ?? (riesgo.asset_id ? "Cargando…" : "Sin activo relacionado")}
            </Campo>
            <Campo etiqueta="Categoría">{riesgo.category}</Campo>
            <Campo etiqueta="Amenaza">{riesgo.threat}</Campo>
            <Campo etiqueta="Vulnerabilidad">{riesgo.vulnerability}</Campo>
            <Campo etiqueta="Tratamiento">{ETIQUETAS_TRATAMIENTO[riesgo.treatment]}</Campo>
            <Campo etiqueta="Responsable">{riesgo.owner}</Campo>
            <Campo etiqueta="Estado">
              <Badge tono={TONO_ESTADO_RIESGO[riesgo.status]}>
                {ETIQUETAS_ESTADO_RIESGO[riesgo.status]}
              </Badge>
            </Campo>
            <Campo etiqueta="Fecha de revisión">
              {new Date(riesgo.review_date).toLocaleDateString("es-ES")}
            </Campo>
            <div className="sm:col-span-2">
              <Campo etiqueta="Descripción">{riesgo.description || "Sin descripción."}</Campo>
            </div>
            <div className="sm:col-span-2">
              <Campo etiqueta="Comentarios">{riesgo.comments || "Sin comentarios."}</Campo>
            </div>
          </dl>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <h2 className="text-sm font-medium text-slate-500">Riesgo inherente</h2>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{riesgo.inherent_score}</p>
            <p className="mt-1 text-sm text-slate-500">
              Probabilidad {riesgo.likelihood} × Impacto {riesgo.impact}
            </p>
            <div className="mt-3">
              <Badge tono={TONO_NIVEL_RIESGO[riesgo.inherent_level]}>
                {ETIQUETAS_NIVEL_RIESGO[riesgo.inherent_level]}
              </Badge>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <h2 className="text-sm font-medium text-slate-500">Riesgo residual</h2>
            {riesgo.residual_score !== null && riesgo.residual_level ? (
              <>
                <p className="mt-2 text-3xl font-semibold text-slate-900">{riesgo.residual_score}</p>
                <p className="mt-1 text-sm text-slate-500">
                  Probabilidad {riesgo.residual_likelihood} × Impacto {riesgo.residual_impact}
                </p>
                <div className="mt-3">
                  <Badge tono={TONO_NIVEL_RIESGO[riesgo.residual_level]}>
                    {ETIQUETAS_NIVEL_RIESGO[riesgo.residual_level]}
                  </Badge>
                </div>
              </>
            ) : (
              <p className="mt-2 text-sm text-slate-400">Aún no evaluado.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
