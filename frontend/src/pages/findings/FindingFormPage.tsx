import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import { actualizarHallazgo, crearHallazgo, obtenerHallazgo } from "../../lib/findings";
import {
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_HALLAZGO,
  ETIQUETAS_ORIGEN_HALLAZGO,
  ETIQUETAS_TIPO_HALLAZGO,
} from "../../lib/labels";
import type { AssetCriticality, FindingInput, FindingSource, FindingStatus, FindingType } from "../../types";

const VALORES_INICIALES: FindingInput = {
  finding_id: "",
  title: "",
  description: "",
  finding_type: "control_review",
  severity: "medium",
  source: "manual",
  owner: "",
  discovered_at: new Date().toISOString().slice(0, 10),
  due_date: new Date().toISOString().slice(0, 10),
  status: "open",
  resolution_summary: "",
};

export function FindingFormPage({ modo }: { modo: "crear" | "editar" }) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [datos, setDatos] = useState<FindingInput>(VALORES_INICIALES);
  const [cargando, setCargando] = useState(modo === "editar");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (modo === "editar" && id) {
      obtenerHallazgo(id).then((hallazgo) => {
        setDatos({
          finding_id: hallazgo.finding_id,
          title: hallazgo.title,
          description: hallazgo.description,
          finding_type: hallazgo.finding_type,
          severity: hallazgo.severity,
          source: hallazgo.source,
          owner: hallazgo.owner,
          discovered_at: hallazgo.discovered_at,
          due_date: hallazgo.due_date,
          status: hallazgo.status,
          resolution_summary: hallazgo.resolution_summary,
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
        const hallazgo = await crearHallazgo(datos);
        navigate(`/hallazgos/${hallazgo.id}`);
      } else if (id) {
        await actualizarHallazgo(id, datos);
        navigate(`/hallazgos/${id}`);
      }
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEnviando(false);
    }
  }

  if (cargando) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const requiereResolucion = datos.status === "closed";

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        to={modo === "editar" && id ? `/hallazgos/${id}` : "/hallazgos"}
        className="text-sm text-slate-500 hover:underline"
      >
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">
        {modo === "crear" ? "Nuevo hallazgo" : "Editar hallazgo"}
      </h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Código</label>
            <input
              type="text"
              required
              value={datos.finding_id}
              onChange={(evento) => setDatos({ ...datos, finding_id: evento.target.value })}
              placeholder="p. ej. FND-001"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
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
            <label className="block text-sm font-medium text-slate-700">Tipo</label>
            <select
              value={datos.finding_type}
              onChange={(evento) => setDatos({ ...datos, finding_type: evento.target.value as FindingType })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_TIPO_HALLAZGO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Origen</label>
            <select
              value={datos.source}
              onChange={(evento) => setDatos({ ...datos, source: evento.target.value as FindingSource })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ORIGEN_HALLAZGO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Severidad</label>
            <select
              value={datos.severity}
              onChange={(evento) => setDatos({ ...datos, severity: evento.target.value as AssetCriticality })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_CRITICIDAD).map(([valor, etiqueta]) => (
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
              onChange={(evento) => setDatos({ ...datos, status: evento.target.value as FindingStatus })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ESTADO_HALLAZGO).map(([valor, etiqueta]) => (
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
            <label className="block text-sm font-medium text-slate-700">Fecha de descubrimiento</label>
            <input
              type="date"
              required
              value={datos.discovered_at}
              onChange={(evento) => setDatos({ ...datos, discovered_at: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Fecha límite</label>
            <input
              type="date"
              required
              value={datos.due_date}
              onChange={(evento) => setDatos({ ...datos, due_date: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">
            Resumen de resolución
            {requiereResolucion ? (
              <span className="font-normal text-red-600"> (obligatorio para cerrar)</span>
            ) : (
              <span className="font-normal text-slate-400"> (opcional)</span>
            )}
          </label>
          <textarea
            value={datos.resolution_summary ?? ""}
            onChange={(evento) => setDatos({ ...datos, resolution_summary: evento.target.value })}
            rows={2}
            required={requiereResolucion}
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
