import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import { actualizarActivo, crearActivo, obtenerActivo } from "../../lib/assets";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_ESTADO_ACTIVO,
  ETIQUETAS_TIPO_ACTIVO,
} from "../../lib/labels";
import type { AssetCriticality, AssetInput, AssetStatus, AssetType, DataClassification } from "../../types";

const VALORES_INICIALES: AssetInput = {
  name: "",
  description: "",
  asset_type: "system",
  owner: "",
  criticality: "medium",
  data_classification: "internal",
  status: "active",
};

export function AssetFormPage({ modo }: { modo: "crear" | "editar" }) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [datos, setDatos] = useState<AssetInput>(VALORES_INICIALES);
  const [cargando, setCargando] = useState(modo === "editar");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (modo === "editar" && id) {
      obtenerActivo(id).then((activo) => {
        setDatos({
          name: activo.name,
          description: activo.description,
          asset_type: activo.asset_type,
          owner: activo.owner,
          criticality: activo.criticality,
          data_classification: activo.data_classification,
          status: activo.status,
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
        const activo = await crearActivo(datos);
        navigate(`/activos/${activo.id}`);
      } else if (id) {
        await actualizarActivo(id, datos);
        navigate(`/activos/${id}`);
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
        to={modo === "editar" && id ? `/activos/${id}` : "/activos"}
        className="text-sm text-slate-500 hover:underline"
      >
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">
        {modo === "crear" ? "Nuevo activo" : "Editar activo"}
      </h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
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
            <label className="block text-sm font-medium text-slate-700">Tipo</label>
            <select
              value={datos.asset_type}
              onChange={(evento) =>
                setDatos({ ...datos, asset_type: evento.target.value as AssetType })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_TIPO_ACTIVO).map(([valor, etiqueta]) => (
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
            <label className="block text-sm font-medium text-slate-700">Criticidad</label>
            <select
              value={datos.criticality}
              onChange={(evento) =>
                setDatos({ ...datos, criticality: evento.target.value as AssetCriticality })
              }
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
            <label className="block text-sm font-medium text-slate-700">Clasificación de datos</label>
            <select
              value={datos.data_classification}
              onChange={(evento) =>
                setDatos({ ...datos, data_classification: evento.target.value as DataClassification })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_CLASIFICACION).map(([valor, etiqueta]) => (
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
              onChange={(evento) => setDatos({ ...datos, status: evento.target.value as AssetStatus })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ESTADO_ACTIVO).map(([valor, etiqueta]) => (
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
