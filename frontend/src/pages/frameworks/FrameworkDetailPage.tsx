import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { obtenerMensajeError } from "../../lib/api";
import { listarFrameworks, listarRequisitos, obtenerFramework } from "../../lib/frameworks";
import { ETIQUETAS_ESTADO_FRAMEWORK, TONO_ESTADO_FRAMEWORK } from "../../lib/labels";
import { crearMapping, listarMappings } from "../../lib/mappings";
import type { Framework, FrameworkDetail, FrameworkMapping, Requirement } from "../../types";

function TarjetaResumen({ titulo, valor }: { titulo: string; valor: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium text-slate-500">{titulo}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{valor}</p>
    </div>
  );
}

export function FrameworkDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [framework, setFramework] = useState<FrameworkDetail | null>(null);
  const [requisitos, setRequisitos] = useState<Requirement[]>([]);
  const [otrosFrameworks, setOtrosFrameworks] = useState<Framework[]>([]);
  const [requisitosDestino, setRequisitosDestino] = useState<Requirement[]>([]);
  const [mappings, setMappings] = useState<FrameworkMapping[]>([]);
  const [frameworkDestinoId, setFrameworkDestinoId] = useState("");
  const [requisitoOrigenId, setRequisitoOrigenId] = useState("");
  const [requisitoDestinoId, setRequisitoDestinoId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function cargarTodo() {
    if (!id) return;
    const [detalle, listaRequisitos, frameworks] = await Promise.all([
      obtenerFramework(id),
      listarRequisitos(id, { page: 1, page_size: 200 }),
      listarFrameworks(),
    ]);
    setFramework(detalle);
    setRequisitos(listaRequisitos.items);
    setOtrosFrameworks(frameworks.filter((f) => f.id !== id));

    const idsRequisitos = new Set(listaRequisitos.items.map((r) => r.id));
    const todosLosMappings = await listarMappings();
    setMappings(
      todosLosMappings.filter(
        (m) => idsRequisitos.has(m.source_requirement.id) || idsRequisitos.has(m.target_requirement.id),
      ),
    );
  }

  useEffect(() => {
    cargarTodo().catch((err) => setError(obtenerMensajeError(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!frameworkDestinoId) {
      setRequisitosDestino([]);
      return;
    }
    listarRequisitos(frameworkDestinoId, { page: 1, page_size: 200 }).then((r) =>
      setRequisitosDestino(r.items),
    );
  }, [frameworkDestinoId]);

  async function manejarCrearMapping() {
    if (!requisitoOrigenId || !requisitoDestinoId) return;
    try {
      await crearMapping(requisitoOrigenId, requisitoDestinoId);
      setRequisitoOrigenId("");
      setRequisitoDestinoId("");
      setFrameworkDestinoId("");
      await cargarTodo();
    } catch (err) {
      setError(obtenerMensajeError(err));
    }
  }

  if (error) {
    return <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!framework) {
    return <p className="text-slate-400">Cargando…</p>;
  }

  const resumen = framework.compliance_summary;

  return (
    <div>
      <Link to="/marcos" className="text-sm text-slate-500 hover:underline">
        ← Volver a Marcos de cumplimiento
      </Link>
      <div className="mt-1 flex items-center gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">{framework.short_name}</h1>
        <Badge tono={TONO_ESTADO_FRAMEWORK[framework.status]}>
          {ETIQUETAS_ESTADO_FRAMEWORK[framework.status]}
        </Badge>
      </div>
      <p className="text-slate-500">
        {framework.name} · Versión {framework.version}
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <TarjetaResumen titulo="Implementados" valor={resumen.implemented} />
        <TarjetaResumen titulo="Parcialmente implementados" valor={resumen.partially_implemented} />
        <TarjetaResumen titulo="No implementados" valor={resumen.not_implemented} />
        <TarjetaResumen titulo="No aplicables" valor={resumen.not_applicable} />
      </div>
      <p className="mt-2 text-xs text-slate-400">
        {resumen.requirements_with_control} de {resumen.total_requirements} requisitos tienen al menos un
        control asociado.
      </p>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-3">
          <h2 className="text-sm font-semibold text-slate-700">Requisitos</h2>
        </div>
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Código</th>
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">Categoría</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {requisitos.map((req) => (
              <tr key={req.id}>
                <td className="px-4 py-2 font-medium text-slate-900">{req.code}</td>
                <td className="px-4 py-2 text-slate-600">{req.name}</td>
                <td className="px-4 py-2 text-slate-600">{req.category || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">Mappings con otros marcos</h2>
        <ul className="mt-3 space-y-2">
          {mappings.length === 0 && (
            <li className="text-sm text-slate-400">Sin mappings todavía.</li>
          )}
          {mappings.map((mapping) => (
            <li key={mapping.id} className="flex items-center gap-2 text-sm text-slate-700">
              <span className="font-medium">
                {mapping.source_requirement.framework_short_name} {mapping.source_requirement.code}
              </span>
              <span className="text-slate-400">↔</span>
              <span className="font-medium">
                {mapping.target_requirement.framework_short_name} {mapping.target_requirement.code}
              </span>
              {mapping.notes && <span className="text-slate-400">— {mapping.notes}</span>}
            </li>
          ))}
        </ul>

        <div className="mt-4 grid grid-cols-1 gap-2 border-t border-slate-100 pt-4 sm:grid-cols-4">
          <select
            value={requisitoOrigenId}
            onChange={(evento) => setRequisitoOrigenId(evento.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">Requisito de {framework.short_name}…</option>
            {requisitos.map((req) => (
              <option key={req.id} value={req.id}>
                {req.code} — {req.name}
              </option>
            ))}
          </select>
          <select
            value={frameworkDestinoId}
            onChange={(evento) => {
              setFrameworkDestinoId(evento.target.value);
              setRequisitoDestinoId("");
            }}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">Marco destino…</option>
            {otrosFrameworks.map((f) => (
              <option key={f.id} value={f.id}>
                {f.short_name}
              </option>
            ))}
          </select>
          <select
            value={requisitoDestinoId}
            onChange={(evento) => setRequisitoDestinoId(evento.target.value)}
            disabled={!frameworkDestinoId}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm disabled:opacity-50"
          >
            <option value="">Requisito destino…</option>
            {requisitosDestino.map((req) => (
              <option key={req.id} value={req.id}>
                {req.code} — {req.name}
              </option>
            ))}
          </select>
          <button
            onClick={manejarCrearMapping}
            disabled={!requisitoOrigenId || !requisitoDestinoId}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:opacity-40"
          >
            Crear mapping
          </button>
        </div>
      </div>
    </div>
  );
}
