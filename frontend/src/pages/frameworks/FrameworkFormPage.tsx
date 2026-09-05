import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import { crearFramework } from "../../lib/frameworks";
import type { FrameworkInput } from "../../types";

const VALORES_INICIALES: FrameworkInput = {
  name: "",
  short_name: "",
  description: "",
  version: "",
  status: "active",
};

export function FrameworkFormPage() {
  const navigate = useNavigate();
  const [datos, setDatos] = useState<FrameworkInput>(VALORES_INICIALES);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const framework = await crearFramework(datos);
      navigate(`/marcos/${framework.id}`);
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Link to="/marcos" className="text-sm text-slate-500 hover:underline">
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">Nuevo marco de cumplimiento</h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="block text-sm font-medium text-slate-700">Nombre corto</label>
          <input
            type="text"
            required
            placeholder="p. ej. ISO 27001"
            value={datos.short_name}
            onChange={(evento) => setDatos({ ...datos, short_name: evento.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Nombre completo</label>
          <input
            type="text"
            required
            placeholder="p. ej. ISO/IEC 27001:2022"
            value={datos.name}
            onChange={(evento) => setDatos({ ...datos, name: evento.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Versión</label>
          <input
            type="text"
            required
            value={datos.version}
            onChange={(evento) => setDatos({ ...datos, version: evento.target.value })}
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
