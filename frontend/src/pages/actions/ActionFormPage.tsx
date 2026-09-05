import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import { listarHallazgos } from "../../lib/findings";
import { ETIQUETAS_CRITICIDAD, ETIQUETAS_ESTADO_ACCION } from "../../lib/labels";
import { actualizarAccion, crearAccion, obtenerAccion } from "../../lib/remediationActions";
import type { ActionStatus, AssetCriticality, Finding, RemediationActionInput } from "../../types";

function valoresIniciales(findingIdPrevio: string): RemediationActionInput {
  return {
    finding_id: findingIdPrevio,
    action_id: "",
    title: "",
    description: "",
    owner: "",
    priority: "medium",
    due_date: new Date().toISOString().slice(0, 10),
    status: "pending",
    completion_notes: "",
  };
}

export function ActionFormPage({ modo }: { modo: "crear" | "editar" }) {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [datos, setDatos] = useState<RemediationActionInput>(
    valoresIniciales(searchParams.get("finding_id") ?? ""),
  );
  const [hallazgos, setHallazgos] = useState<Finding[]>([]);
  const [cargando, setCargando] = useState(modo === "editar");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listarHallazgos({ page: 1, page_size: 100 }).then((r) => setHallazgos(r.items));
  }, []);

  useEffect(() => {
    if (modo === "editar" && id) {
      obtenerAccion(id).then((accion) => {
        setDatos({
          finding_id: accion.finding_id,
          action_id: accion.action_id,
          title: accion.title,
          description: accion.description,
          owner: accion.owner,
          priority: accion.priority,
          due_date: accion.due_date,
          status: accion.status,
          completion_notes: accion.completion_notes,
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
        const accion = await crearAccion(datos);
        navigate(`/acciones/${accion.id}`);
      } else if (id) {
        await actualizarAccion(id, datos);
        navigate(`/acciones/${id}`);
      }
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEnviando(false);
    }
  }

  if (cargando) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const requiereNotas = datos.status === "completed";

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        to={modo === "editar" && id ? `/acciones/${id}` : "/acciones"}
        className="text-sm text-slate-500 hover:underline"
      >
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">
        {modo === "crear" ? "Nueva acción de remediación" : "Editar acción de remediación"}
      </h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="block text-sm font-medium text-slate-700">Hallazgo</label>
          <select
            required
            disabled={modo === "editar"}
            value={datos.finding_id}
            onChange={(evento) => setDatos({ ...datos, finding_id: evento.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
          >
            <option value="">Selecciona un hallazgo…</option>
            {hallazgos.map((hallazgo) => (
              <option key={hallazgo.id} value={hallazgo.id}>
                {hallazgo.finding_id} — {hallazgo.title}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Código</label>
            <input
              type="text"
              required
              value={datos.action_id}
              onChange={(evento) => setDatos({ ...datos, action_id: evento.target.value })}
              placeholder="p. ej. ACT-001"
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
            <label className="block text-sm font-medium text-slate-700">Prioridad</label>
            <select
              value={datos.priority}
              onChange={(evento) => setDatos({ ...datos, priority: evento.target.value as AssetCriticality })}
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
              onChange={(evento) => setDatos({ ...datos, status: evento.target.value as ActionStatus })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ESTADO_ACCION).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
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
            Notas de finalización
            {requiereNotas ? (
              <span className="font-normal text-slate-400"> (opcional)</span>
            ) : (
              <span className="font-normal text-slate-400"> (se usan al completar la acción)</span>
            )}
          </label>
          <textarea
            value={datos.completion_notes ?? ""}
            onChange={(evento) => setDatos({ ...datos, completion_notes: evento.target.value })}
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
