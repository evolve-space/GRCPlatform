import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { obtenerMensajeError } from "../../lib/api";
import {
  ETIQUETAS_CLASIFICACION,
  ETIQUETAS_CRITICIDAD,
  ETIQUETAS_DUE_DILIGENCE,
  ETIQUETAS_ESTADO_PROVEEDOR,
} from "../../lib/labels";
import { actualizarProveedor, crearProveedor, obtenerProveedor } from "../../lib/vendors";
import type {
  AssetCriticality,
  DataClassification,
  VendorDueDiligenceStatus,
  VendorInput,
  VendorStatus,
} from "../../types";

const VALORES_INICIALES: VendorInput = {
  vendor_id: "",
  name: "",
  legal_name: "",
  description: "",
  category: "",
  owner: "",
  criticality: "medium",
  data_classification: "internal",
  status: "prospect",
  due_diligence_status: "pending",
  relationship_start_date: new Date().toISOString().slice(0, 10),
  contract_end_date: "",
  last_security_review_date: "",
  next_security_review_date: "",
};

export function VendorFormPage({ modo }: { modo: "crear" | "editar" }) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [datos, setDatos] = useState<VendorInput>(VALORES_INICIALES);
  const [cargando, setCargando] = useState(modo === "editar");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (modo === "editar" && id) {
      obtenerProveedor(id).then((proveedor) => {
        setDatos({
          vendor_id: proveedor.vendor_id,
          name: proveedor.name,
          legal_name: proveedor.legal_name,
          description: proveedor.description,
          category: proveedor.category,
          owner: proveedor.owner,
          criticality: proveedor.criticality,
          data_classification: proveedor.data_classification,
          status: proveedor.status,
          due_diligence_status: proveedor.due_diligence_status,
          relationship_start_date: proveedor.relationship_start_date,
          contract_end_date: proveedor.contract_end_date,
          last_security_review_date: proveedor.last_security_review_date,
          next_security_review_date: proveedor.next_security_review_date,
        });
        setCargando(false);
      });
    }
  }, [modo, id]);

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    const payload: VendorInput = {
      ...datos,
      legal_name: datos.legal_name || null,
      description: datos.description || null,
      contract_end_date: datos.contract_end_date || null,
      last_security_review_date: datos.last_security_review_date || null,
      next_security_review_date: datos.next_security_review_date || null,
    };
    try {
      if (modo === "crear") {
        const proveedor = await crearProveedor(payload);
        navigate(`/proveedores/${proveedor.id}`);
      } else if (id) {
        await actualizarProveedor(id, payload);
        navigate(`/proveedores/${id}`);
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
        to={modo === "editar" && id ? `/proveedores/${id}` : "/proveedores"}
        className="text-sm text-slate-500 hover:underline"
      >
        ← Cancelar
      </Link>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">
        {modo === "crear" ? "Nuevo proveedor" : "Editar proveedor"}
      </h1>

      <form onSubmit={manejarEnvio} className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Código</label>
            <input
              type="text"
              required
              value={datos.vendor_id}
              onChange={(evento) => setDatos({ ...datos, vendor_id: evento.target.value })}
              placeholder="p. ej. VEN-001"
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

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Razón social (opcional)</label>
            <input
              type="text"
              value={datos.legal_name ?? ""}
              onChange={(evento) => setDatos({ ...datos, legal_name: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Categoría / servicio</label>
            <input
              type="text"
              required
              value={datos.category}
              onChange={(evento) => setDatos({ ...datos, category: evento.target.value })}
              placeholder="p. ej. Infraestructura cloud"
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
            <label className="block text-sm font-medium text-slate-700">Responsable interno</label>
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
              onChange={(evento) => setDatos({ ...datos, criticality: evento.target.value as AssetCriticality })}
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
              onChange={(evento) => setDatos({ ...datos, status: evento.target.value as VendorStatus })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_ESTADO_PROVEEDOR).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Due diligence</label>
            <select
              value={datos.due_diligence_status}
              onChange={(evento) =>
                setDatos({ ...datos, due_diligence_status: evento.target.value as VendorDueDiligenceStatus })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(ETIQUETAS_DUE_DILIGENCE).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Inicio de la relación</label>
            <input
              type="date"
              required
              value={datos.relationship_start_date}
              onChange={(evento) => setDatos({ ...datos, relationship_start_date: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Fin de contrato (opcional)</label>
            <input
              type="date"
              value={datos.contract_end_date ?? ""}
              onChange={(evento) => setDatos({ ...datos, contract_end_date: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Última revisión de seguridad</label>
            <input
              type="date"
              value={datos.last_security_review_date ?? ""}
              onChange={(evento) => setDatos({ ...datos, last_security_review_date: evento.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Próxima revisión de seguridad</label>
            <input
              type="date"
              value={datos.next_security_review_date ?? ""}
              onChange={(evento) => setDatos({ ...datos, next_security_review_date: evento.target.value })}
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
