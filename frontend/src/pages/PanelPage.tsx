import { useEffect, useState } from "react";
import { AttentionList } from "../components/dashboard/AttentionList";
import { ComplianceScoreCard } from "../components/dashboard/ComplianceScoreCard";
import { KpiCard } from "../components/dashboard/KpiCard";
import { useAuth } from "../context/auth-context";
import { obtenerResumenDashboard } from "../lib/dashboard";
import { listarProveedores } from "../lib/vendors";
import { ComplianceSection } from "./dashboard/ComplianceSection";
import { EvidenceSection } from "./dashboard/EvidenceSection";
import { RemediationSection } from "./dashboard/RemediationSection";
import { RiskSection } from "./dashboard/RiskSection";
import { VendorSection } from "./dashboard/VendorSection";
import type { DashboardSummary, Vendor } from "../types";

export function PanelPage() {
  const { usuario } = useAuth();
  const [resumen, setResumen] = useState<DashboardSummary | null>(null);
  const [proveedores, setProveedores] = useState<Vendor[]>([]);
  const [vendorId, setVendorId] = useState<string | null>(null);

  useEffect(() => {
    obtenerResumenDashboard().then(setResumen);
    listarProveedores({ page: 1, page_size: 100 }).then((r) => setProveedores(r.items));
  }, []);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Panel GRC — Hola, {usuario?.full_name.split(" ")[0]}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {resumen ? `Datos actualizados: ${new Date(resumen.generated_at).toLocaleString("es-ES")}` : "Cargando…"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-500">Filtrar por proveedor</label>
          <select
            value={vendorId ?? ""}
            onChange={(e) => setVendorId(e.target.value || null)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Todos</option>
            {proveedores.map((v) => (
              <option key={v.id} value={v.id}>
                {v.vendor_id} — {v.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {vendorId && (
        <p className="mt-1 text-xs text-slate-400">
          El filtro de proveedor afecta a las secciones de Riesgos, Evidencias y Hallazgos/Acciones. No afecta a
          Cumplimiento ni a la lista general de Proveedores.
        </p>
      )}

      {!resumen ? (
        <p className="mt-8 text-slate-400">Cargando panel…</p>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <KpiCard
              titulo="Riesgos críticos"
              valor={resumen.kpis.risks_critical}
              enlace="/riesgos?level=critico"
              tono="rojo"
            />
            <KpiCard titulo="Riesgos altos" valor={resumen.kpis.risks_high} enlace="/riesgos?level=alto" tono="naranja" />
            <KpiCard titulo="Hallazgos abiertos" valor={resumen.kpis.findings_open} enlace="/hallazgos" tono="azul" />
            <KpiCard
              titulo="Acciones vencidas"
              valor={resumen.kpis.actions_overdue}
              enlace="/acciones?overdue=true"
              tono="rojo"
            />
            <KpiCard
              titulo="Evidencias próx. a caducar"
              valor={resumen.kpis.evidence_expiring_soon}
              enlace="/evidencias?caducidad=proximas"
              tono="ambar"
            />
            <KpiCard
              titulo="Proveedores críticos"
              valor={resumen.kpis.vendors_critical}
              enlace="/proveedores?criticality=critical"
              tono="rojo"
            />
            <KpiCard
              titulo="Hallazgos críticos abiertos"
              valor={resumen.kpis.findings_critical_open}
              enlace="/hallazgos?severity=critical"
              tono="rojo"
            />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <AttentionList items={resumen.attention} />
            </div>
            <ComplianceScoreCard score={resumen.compliance_score} />
          </div>

          <div className="mt-6 space-y-4">
            <RiskSection vendorId={vendorId} />
            <ComplianceSection />
            <EvidenceSection vendorId={vendorId} />
            <RemediationSection vendorId={vendorId} />
            <VendorSection />
          </div>
        </>
      )}
    </div>
  );
}
