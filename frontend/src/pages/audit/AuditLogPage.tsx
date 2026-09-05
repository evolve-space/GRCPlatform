import { Fragment, useEffect, useState } from "react";
import { Pagination } from "../../components/Pagination";
import { listarRegistrosAuditoria, obtenerMetaAuditoria } from "../../lib/auditLog";
import type { AuditLogEntry, AuditLogMeta } from "../../types";

const PAGE_SIZE = 20;

const ETIQUETAS_ENTIDAD: Record<string, string> = {
  vendor: "Proveedor",
  finding: "Hallazgo",
  remediation_action: "Acción de remediación",
  evidence: "Evidencia",
  risk: "Riesgo",
  integration_token: "Credencial de integración",
  // Los eventos "mcp_tool_call" usan el prefijo del scope como entity_type
  // (p. ej. "risks:read" -> "risks"), por lo que son plurales en inglés y
  // distintos de las claves ya usadas por los eventos creados por humanos.
  risks: "Riesgos",
  controls: "Controles",
  findings: "Hallazgos",
  remediation: "Acciones de remediación",
  vendors: "Proveedores",
  dashboard: "Dashboard",
  compliance: "Cumplimiento",
  audit: "Registro de auditoría",
};

function etiquetaEntidad(entityType: string): string {
  return ETIQUETAS_ENTIDAD[entityType] ?? entityType;
}

const ETIQUETAS_ACCION: Record<string, string> = {
  create_vendor: "Proveedor creado",
  update_vendor: "Proveedor modificado",
  change_vendor_status: "Cambio de estado del proveedor",
  delete_vendor: "Proveedor eliminado",
  link_vendor_risk: "Riesgo vinculado al proveedor",
  unlink_vendor_risk: "Riesgo desvinculado del proveedor",
  link_vendor_evidence: "Evidencia vinculada al proveedor",
  unlink_vendor_evidence: "Evidencia desvinculada del proveedor",
  link_vendor_finding: "Hallazgo vinculado al proveedor",
  unlink_vendor_finding: "Hallazgo desvinculado del proveedor",
  create_finding: "Hallazgo creado",
  update_finding: "Hallazgo modificado",
  close_finding: "Hallazgo cerrado",
  delete_finding: "Hallazgo eliminado",
  create_action: "Acción creada",
  update_action: "Acción modificada",
  complete_action: "Acción completada",
  delete_action: "Acción eliminada",
  upload_evidence: "Evidencia subida",
  update_evidence_metadata: "Metadatos de evidencia modificados",
  delete_evidence: "Evidencia eliminada",
  download_evidence: "Evidencia descargada",
  verify_integrity: "Integridad de evidencia verificada",
  create_risk: "Riesgo creado",
  integration_token_created: "Credencial de integración creada",
  integration_token_revoked: "Credencial de integración revocada",
  mcp_tool_call: "Llamada de una herramienta MCP",
};

// Traduce las acciones ya conocidas; si en el futuro se añade un evento nuevo
// que todavía no tenga traducción, se muestra igualmente en un formato legible
// (sin guiones bajos) en lugar de fallar o mostrar un identificador crudo.
function formatearAccion(action: string): string {
  return ETIQUETAS_ACCION[action] ?? action.replaceAll("_", " ");
}

export function AuditLogPage() {
  const [registros, setRegistros] = useState<AuditLogEntry[]>([]);
  const [meta, setMeta] = useState<AuditLogMeta>({ actions: [], entity_types: [] });
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [accion, setAccion] = useState("");
  const [entidad, setEntidad] = useState("");
  const [entityId, setEntityId] = useState("");
  const [actorId, setActorId] = useState<string | null>(null);
  const [actorEtiqueta, setActorEtiqueta] = useState<string | null>(null);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [expandido, setExpandido] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    obtenerMetaAuditoria().then(setMeta);
  }, []);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarRegistrosAuditoria({
      action: accion || undefined,
      entity_type: entidad || undefined,
      entity_id: entityId || undefined,
      user_id: actorId || undefined,
      date_from: fechaDesde || undefined,
      date_to: fechaHasta || undefined,
      page,
      page_size: PAGE_SIZE,
    }).then((resultado) => {
      if (!cancelado) {
        setRegistros(resultado.items);
        setTotal(resultado.total);
        setCargando(false);
      }
    });
    return () => {
      cancelado = true;
    };
  }, [accion, entidad, entityId, actorId, fechaDesde, fechaHasta, page]);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Registro de auditoría</h1>
      <p className="mt-1 text-sm text-slate-500">
        Historial de operaciones sensibles realizadas en la plataforma. Solo lectura.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <select
          value={accion}
          onChange={(evento) => {
            setPage(1);
            setAccion(evento.target.value);
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda acción</option>
          {meta.actions.map((valor) => (
            <option key={valor} value={valor}>
              {formatearAccion(valor)}
            </option>
          ))}
        </select>
        <select
          value={entidad}
          onChange={(evento) => {
            setPage(1);
            setEntidad(evento.target.value);
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Toda entidad</option>
          {meta.entity_types.map((valor) => (
            <option key={valor} value={valor}>
              {etiquetaEntidad(valor)}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="ID de entidad…"
          value={entityId}
          onChange={(evento) => {
            setPage(1);
            setEntityId(evento.target.value);
          }}
          className="w-56 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <label>Desde</label>
          <input
            type="date"
            value={fechaDesde}
            onChange={(evento) => {
              setPage(1);
              setFechaDesde(evento.target.value);
            }}
            className="rounded-md border border-slate-300 px-2 py-2 text-sm"
          />
          <label>Hasta</label>
          <input
            type="date"
            value={fechaHasta}
            onChange={(evento) => {
              setPage(1);
              setFechaHasta(evento.target.value);
            }}
            className="rounded-md border border-slate-300 px-2 py-2 text-sm"
          />
        </div>
        {actorId && (
          <button
            onClick={() => {
              setActorId(null);
              setActorEtiqueta(null);
              setPage(1);
            }}
            className="rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
          >
            Actor: {actorEtiqueta} ✕
          </button>
        )}
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Fecha / hora</th>
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Acción</th>
              <th className="px-4 py-3">Entidad</th>
              <th className="px-4 py-3">ID de entidad</th>
              <th className="px-4 py-3">Detalle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cargando ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  Cargando…
                </td>
              </tr>
            ) : registros.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  No se han encontrado eventos con estos criterios.
                </td>
              </tr>
            ) : (
              registros.map((registro) => (
                <Fragment key={registro.id}>
                  <tr className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                      {new Date(registro.created_at).toLocaleString("es-ES")}
                    </td>
                    <td className="px-4 py-3">
                      {registro.actor ? (
                        <button
                          onClick={() => {
                            setActorId(registro.user_id);
                            setActorEtiqueta(registro.actor?.full_name ?? registro.actor?.email ?? "");
                            setPage(1);
                          }}
                          className="text-slate-900 hover:underline"
                          title="Filtrar por este usuario"
                        >
                          {registro.actor.full_name}
                        </button>
                      ) : (
                        <span className="text-slate-400">Sistema</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{formatearAccion(registro.action)}</td>
                    <td className="px-4 py-3 text-slate-600">{etiquetaEntidad(registro.entity_type)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">
                      {registro.entity_id ? `${registro.entity_id.slice(0, 8)}…` : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {registro.details ? (
                        <button
                          onClick={() => setExpandido(expandido === registro.id ? null : registro.id)}
                          className="text-xs font-medium text-slate-500 hover:underline"
                        >
                          {expandido === registro.id ? "Ocultar" : "Ver detalle"}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-300">—</span>
                      )}
                    </td>
                  </tr>
                  {expandido === registro.id && registro.details && (
                    <tr>
                      <td colSpan={6} className="bg-slate-50 px-4 py-3">
                        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-3">
                          {Object.entries(registro.details).map(([clave, valor]) => (
                            <div key={clave}>
                              <dt className="font-medium text-slate-500">{clave}</dt>
                              <dd className="text-slate-700">{String(valor)}</dd>
                            </div>
                          ))}
                        </dl>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
    </div>
  );
}
