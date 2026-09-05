import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import { actualizarEvidencia, obtenerEvidencia } from "../../lib/evidence";
import { ETIQUETAS_CLASIFICACION, ETIQUETAS_ESTADO_EVIDENCIA } from "../../lib/labels";
import type { DataClassification, EvidenceStoredStatus } from "../../types";

export function EvidenceEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [classification, setClassification] = useState<DataClassification>("internal");
  const [status, setStatus] = useState<EvidenceStoredStatus>("active");
  const [collectedAt, setCollectedAt] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  useEffect(() => {
    if (!id) return;
    obtenerEvidencia(id).then((evidencia) => {
      setName(evidencia.name);
      setDescription(evidencia.description ?? "");
      setClassification(evidencia.classification);
      setStatus(evidencia.status);
      setCollectedAt(evidencia.collected_at.slice(0, 10));
      setExpiresAt(evidencia.expires_at ? evidencia.expires_at.slice(0, 10) : "");
      setCargando(false);
    });
  }, [id]);

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    if (!id) return;
    setError(null);
    setEnviando(true);
    try {
      await actualizarEvidencia(id, {
        name,
        description: description || null,
        classification,
        status,
        collected_at: collectedAt,
        expires_at: expiresAt || null,
      });
      navigate(`/evidencias/${id}`);
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
      <Link to={`/evidencias/${id}`} className="text-sm text-slate-500 hover:underline">
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">Editar evidencia</h1>
      <p className="mt-1 text-sm text-slate-500">
        El archivo original no se puede reemplazar; solo pueden editarse sus metadatos.
      </p>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="block text-sm font-medium text-slate-700">Nombre</label>
          <input
            type="text"
            required
            value={name}
            onChange={(evento) => setName(evento.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Descripción</label>
          <textarea
            value={description}
            onChange={(evento) => setDescription(evento.target.value)}
            rows={2}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Clasificación</label>
            <select
              value={classification}
              onChange={(evento) => setClassification(evento.target.value as DataClassification)}
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
              value={status}
              onChange={(evento) => setStatus(evento.target.value as EvidenceStoredStatus)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ESTADO_EVIDENCIA).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Fecha de recopilación</label>
            <input
              type="date"
              required
              value={collectedAt}
              onChange={(evento) => setCollectedAt(evento.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Fecha de expiración <span className="font-normal text-slate-400">(opcional)</span>
            </label>
            <input
              type="date"
              value={expiresAt}
              onChange={(evento) => setExpiresAt(evento.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
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
