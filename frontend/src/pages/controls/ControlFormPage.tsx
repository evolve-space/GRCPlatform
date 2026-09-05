import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import { actualizarControl, crearControl, obtenerControl } from "../../lib/controls";
import { ETIQUETAS_ESTADO_CONTROL, ETIQUETAS_FRECUENCIA } from "../../lib/labels";
import type { ControlFrequency, ControlInput, ControlStatus } from "../../types";

const VALORES_INICIALES: ControlInput = {
  control_id: "",
  name: "",
  description: "",
  objective: "",
  category: "",
  owner: "",
  status: "not_implemented",
  frequency: "annual",
};

export function ControlFormPage({ modo }: { modo: "crear" | "editar" }) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [datos, setDatos] = useState<ControlInput>(VALORES_INICIALES);
  const [cargando, setCargando] = useState(modo === "editar");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (modo === "editar" && id) {
      obtenerControl(id).then((control) => {
        setDatos({
          control_id: control.control_id,
          name: control.name,
          description: control.description,
          objective: control.objective,
          category: control.category,
          owner: control.owner,
          status: control.status,
          frequency: control.frequency,
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
        const control = await crearControl(datos);
        navigate(`/controles/${control.id}`);
      } else if (id) {
        await actualizarControl(id, datos);
        navigate(`/controles/${id}`);
      }
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEnviando(false);
    }
  }

  if (cargando) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        to={modo === "editar" && id ? `/controles/${id}` : "/controles"}
        className="text-sm text-slate-500 hover:underline"
      >
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">
        {modo === "crear" ? "Nuevo control" : "Editar control"}
      </h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Código</label>
            <input
              type="text"
              required
              value={datos.control_id}
              onChange={(evento) => setDatos({ ...datos, control_id: evento.target.value })}
              placeholder="p. ej. CTRL-001"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Nombre</label>
            <input
              type="text"
              required
              value={datos.name}
              onChange={(evento) => setDatos({ ...datos, name: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Objetivo</label>
          <textarea
            value={datos.objective ?? ""}
            onChange={(evento) => setDatos({ ...datos, objective: evento.target.value })}
            rows={2}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Descripción</label>
          <textarea
            value={datos.description ?? ""}
            onChange={(evento) => setDatos({ ...datos, description: evento.target.value })}
            rows={3}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
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
            <label className="block text-sm font-medium text-slate-700">Estado</label>
            <select
              value={datos.status}
              onChange={(evento) => setDatos({ ...datos, status: evento.target.value as ControlStatus })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ESTADO_CONTROL).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Frecuencia</label>
            <select
              value={datos.frequency}
              onChange={(evento) =>
                setDatos({ ...datos, frequency: evento.target.value as ControlFrequency })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_FRECUENCIA).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
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
