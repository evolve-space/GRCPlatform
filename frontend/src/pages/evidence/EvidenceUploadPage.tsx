import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import { subirEvidencia } from "../../lib/evidence";
import { ETIQUETAS_CLASIFICACION } from "../../lib/labels";
import type { DataClassification } from "../../types";

const TIPOS_EVIDENCIA_SUGERIDOS = [
  "Política",
  "Informe",
  "Checklist",
  "Captura de pantalla",
  "Registro",
  "Certificado",
  "Otro",
];

function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function EvidenceUploadPage() {
  const navigate = useNavigate();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [classification, setClassification] = useState<DataClassification>("internal");
  const [evidenceType, setEvidenceType] = useState("Política");
  const [collectedAt, setCollectedAt] = useState(new Date().toISOString().slice(0, 10));
  const [expiresAt, setExpiresAt] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function manejarSeleccionArchivo(evento: ChangeEvent<HTMLInputElement>) {
    const seleccionado = evento.target.files?.[0] ?? null;
    setArchivo(seleccionado);
    if (seleccionado && !name) {
      setName(seleccionado.name);
    }
  }

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    if (!archivo) {
      setError("Selecciona un archivo.");
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      const evidencia = await subirEvidencia({
        file: archivo,
        name,
        description: description || null,
        classification,
        evidence_type: evidenceType,
        collected_at: collectedAt,
        expires_at: expiresAt || null,
      });
      navigate(`/evidencias/${evidencia.id}`);
    } catch (err) {
      setError(obtenerMensajeError(err));
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link to="/evidencias" className="text-sm text-slate-500 hover:underline">
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">Subir evidencia</h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="block text-sm font-medium text-slate-700">Archivo</label>
          <input
            type="file"
            required
            onChange={manejarSeleccionArchivo}
            accept=".pdf,.docx,.xlsx,.csv,.txt,.png,.jpg,.jpeg"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium"
          />
          {archivo && (
            <p className="mt-2 text-xs text-slate-500">
              {archivo.name} · {formatearTamano(archivo.size)} · {archivo.type || "tipo desconocido"}
            </p>
          )}
          <p className="mt-1 text-xs text-slate-400">
            Formatos admitidos: PDF, DOCX, XLSX, CSV, TXT, PNG, JPG. Tamaño máximo: 20 MB.
          </p>
        </div>

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
            <label className="block text-sm font-medium text-slate-700">Tipo</label>
            <input
              type="text"
              required
              list="tipos-evidencia"
              value={evidenceType}
              onChange={(evento) => setEvidenceType(evento.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <datalist id="tipos-evidencia">
              {TIPOS_EVIDENCIA_SUGERIDOS.map((tipo) => (
                <option key={tipo} value={tipo} />
              ))}
            </datalist>
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

        {classification === "confidential" || classification === "restricted" ? (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Esta evidencia es {ETIQUETAS_CLASIFICACION[classification].toLowerCase()}: nunca se
            enviará a ningún servicio externo de IA ni de terceros.
          </p>
        ) : null}

        {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <button
          type="submit"
          disabled={enviando}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {enviando ? "Subiendo…" : "Subir evidencia"}
        </button>
      </form>
    </div>
  );
}
