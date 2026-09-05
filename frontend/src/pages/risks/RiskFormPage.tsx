import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { obtenerMensajeError } from "../../lib/api";
import { listarActivos } from "../../lib/assets";
import {
  ETIQUETAS_ESTADO_RIESGO,
  ETIQUETAS_NIVEL_RIESGO,
  ETIQUETAS_TRATAMIENTO,
  TONO_NIVEL_RIESGO,
} from "../../lib/labels";
import { actualizarRiesgo, crearRiesgo, obtenerRiesgo } from "../../lib/risks";
import type { Asset, RiskInput, RiskLevel, RiskStatus, RiskTreatment } from "../../types";

const VALORES_INICIALES: RiskInput = {
  title: "",
  description: "",
  asset_id: null,
  category: "",
  threat: "",
  vulnerability: "",
  likelihood: 3,
  impact: 3,
  treatment: "mitigate",
  owner: "",
  review_date: new Date().toISOString().slice(0, 10),
  status: "identified",
  residual_likelihood: null,
  residual_impact: null,
  comments: "",
};

/** Vista previa local del nivel de riesgo, solo orientativa: el backend siempre
 * recalcula el score de forma autoritativa al guardar. */
function nivelDeRiesgoPreview(score: number): RiskLevel {
  if (score <= 4) return "bajo";
  if (score <= 9) return "medio";
  if (score <= 16) return "alto";
  return "critico";
}

export function RiskFormPage({ modo }: { modo: "crear" | "editar" }) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [datos, setDatos] = useState<RiskInput>(VALORES_INICIALES);
  const [activos, setActivos] = useState<Asset[]>([]);
  const [cargando, setCargando] = useState(modo === "editar");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarActivos({ page: 1, page_size: 100 }).then((resultado) => setActivos(resultado.items));
  }, []);

  useEffect(() => {
    if (modo === "editar" && id) {
      obtenerRiesgo(id).then((riesgo) => {
        setDatos({
          title: riesgo.title,
          description: riesgo.description,
          asset_id: riesgo.asset_id,
          category: riesgo.category,
          threat: riesgo.threat,
          vulnerability: riesgo.vulnerability,
          likelihood: riesgo.likelihood,
          impact: riesgo.impact,
          treatment: riesgo.treatment,
          owner: riesgo.owner,
          review_date: riesgo.review_date,
          status: riesgo.status,
          residual_likelihood: riesgo.residual_likelihood,
          residual_impact: riesgo.residual_impact,
          comments: riesgo.comments,
        });
        setCargando(false);
      });
    }
  }, [modo, id]);

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      if (modo === "crear") {
        const riesgo = await crearRiesgo(datos);
        navigate(`/riesgos/${riesgo.id}`);
      } else if (id) {
        await actualizarRiesgo(id, datos);
        navigate(`/riesgos/${id}`);
      }
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEnviando(false);
    }
  }

  if (cargando) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const scoreInherente = datos.likelihood * datos.impact;
  const nivelInherente = nivelDeRiesgoPreview(scoreInherente);
  const tieneResidual = datos.residual_likelihood !== null && datos.residual_impact !== null;
  const scoreResidual = tieneResidual
    ? (datos.residual_likelihood as number) * (datos.residual_impact as number)
    : null;

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        to={modo === "editar" && id ? `/riesgos/${id}` : "/riesgos"}
        className="text-sm text-slate-500 hover:underline"
      >
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">
        {modo === "crear" ? "Nuevo riesgo" : "Editar riesgo"}
      </h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="block text-sm font-medium text-slate-700">Título</label>
          <input
            type="text"
            required
            value={datos.title}
            onChange={(evento) => setDatos({ ...datos, title: evento.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Descripción</label>
          <textarea
            value={datos.description ?? ""}
            onChange={(evento) => setDatos({ ...datos, description: evento.target.value })}
            rows={2}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Activo relacionado</label>
            <select
              value={datos.asset_id ?? ""}
              onChange={(evento) =>
                setDatos({ ...datos, asset_id: evento.target.value || null })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Sin activo relacionado</option>
              {activos.map((activo) => (
                <option key={activo.id} value={activo.id}>
                  {activo.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Categoría</label>
            <input
              type="text"
              required
              value={datos.category}
              onChange={(evento) => setDatos({ ...datos, category: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Amenaza</label>
            <input
              type="text"
              required
              value={datos.threat}
              onChange={(evento) => setDatos({ ...datos, threat: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Vulnerabilidad</label>
            <input
              type="text"
              required
              value={datos.vulnerability}
              onChange={(evento) => setDatos({ ...datos, vulnerability: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-700">Riesgo inherente</p>
          <div className="mt-2 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500">Probabilidad (1-5)</label>
              <input
                type="number"
                min={1}
                max={5}
                required
                value={datos.likelihood}
                onChange={(evento) =>
                  setDatos({ ...datos, likelihood: Number(evento.target.value) })
                }
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500">Impacto (1-5)</label>
              <input
                type="number"
                min={1}
                max={5}
                required
                value={datos.impact}
                onChange={(evento) => setDatos({ ...datos, impact: Number(evento.target.value) })}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2 text-sm text-slate-600">
            <span>
              Score: <strong>{scoreInherente}</strong>
            </span>
            <Badge tono={TONO_NIVEL_RIESGO[nivelInherente]}>{ETIQUETAS_NIVEL_RIESGO[nivelInherente]}</Badge>
          </div>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-700">
            Riesgo residual <span className="font-normal text-slate-400">(opcional)</span>
          </p>
          <div className="mt-2 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500">Probabilidad residual</label>
              <input
                type="number"
                min={1}
                max={5}
                value={datos.residual_likelihood ?? ""}
                onChange={(evento) =>
                  setDatos({
                    ...datos,
                    residual_likelihood: evento.target.value ? Number(evento.target.value) : null,
                  })
                }
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500">Impacto residual</label>
              <input
                type="number"
                min={1}
                max={5}
                value={datos.residual_impact ?? ""}
                onChange={(evento) =>
                  setDatos({
                    ...datos,
                    residual_impact: evento.target.value ? Number(evento.target.value) : null,
                  })
                }
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          {tieneResidual && scoreResidual !== null && (
            <div className="mt-3 flex items-center gap-2 text-sm text-slate-600">
              <span>
                Score: <strong>{scoreResidual}</strong>
              </span>
              <Badge tono={TONO_NIVEL_RIESGO[nivelDeRiesgoPreview(scoreResidual)]}>
                {ETIQUETAS_NIVEL_RIESGO[nivelDeRiesgoPreview(scoreResidual)]}
              </Badge>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Tratamiento</label>
            <select
              value={datos.treatment}
              onChange={(evento) =>
                setDatos({ ...datos, treatment: evento.target.value as RiskTreatment })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_TRATAMIENTO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Estado</label>
            <select
              value={datos.status}
              onChange={(evento) => setDatos({ ...datos, status: evento.target.value as RiskStatus })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ESTADO_RIESGO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Responsable</label>
            <input
              type="text"
              required
              value={datos.owner}
              onChange={(evento) => setDatos({ ...datos, owner: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Fecha de revisión</label>
            <input
              type="date"
              required
              value={datos.review_date}
              onChange={(evento) => setDatos({ ...datos, review_date: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Comentarios</label>
          <textarea
            value={datos.comments ?? ""}
            onChange={(evento) => setDatos({ ...datos, comments: evento.target.value })}
            rows={2}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <button
          type="submit"
          disabled={enviando}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {enviando ? "Guardando…" : "Guardar"}
        </button>
      </form>
    </div>
  );
}
