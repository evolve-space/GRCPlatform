import type { ComplianceScoreBreakdown } from "../../types";

const ETIQUETAS_NIVEL: Record<string, string> = {
  excelente: "Excelente",
  bueno: "Bueno",
  mejorable: "Mejorable",
  critico: "Crítico",
};

const COLOR_NIVEL: Record<string, string> = {
  excelente: "text-emerald-600",
  bueno: "text-blue-600",
  mejorable: "text-amber-600",
  critico: "text-red-600",
};

const ANILLO_NIVEL: Record<string, string> = {
  excelente: "#10b981",
  bueno: "#3b82f6",
  mejorable: "#f59e0b",
  critico: "#ef4444",
};

function FilaDesglose({ etiqueta, valor }: { etiqueta: string; valor: number | null }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500">{etiqueta}</span>
      <span className="font-medium text-slate-900">{valor === null ? "Sin datos" : `${valor.toFixed(0)}%`}</span>
    </div>
  );
}

export function ComplianceScoreCard({ score }: { score: ComplianceScoreBreakdown }) {
  const nivel = score.level;
  const porcentaje = score.score ?? 0;
  const color = nivel ? ANILLO_NIVEL[nivel] : "#cbd5e1";

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">Compliance Score</h2>
        {nivel && (
          <span className={`text-xs font-semibold uppercase tracking-wide ${COLOR_NIVEL[nivel]}`}>
            {ETIQUETAS_NIVEL[nivel]}
          </span>
        )}
      </div>

      <div className="mt-4 flex items-center gap-5">
        <div
          className="relative flex h-24 w-24 shrink-0 items-center justify-center rounded-full"
          style={{
            background: score.score === null
              ? "#e2e8f0"
              : `conic-gradient(${color} ${porcentaje * 3.6}deg, #e2e8f0 0deg)`,
          }}
        >
          <div className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-white">
            <span className="text-xl font-bold text-slate-900">{score.score === null ? "—" : score.score.toFixed(0)}</span>
          </div>
        </div>
        <div className="flex-1 space-y-1.5">
          <FilaDesglose etiqueta="Controles (40%)" valor={score.controls_pct} />
          <FilaDesglose etiqueta="Evidencias (20%)" valor={score.evidence_pct} />
          <FilaDesglose etiqueta="Hallazgos (20%)" valor={score.findings_pct} />
          <FilaDesglose etiqueta="Remediación (20%)" valor={score.remediation_pct} />
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-400">
        Índice interno de cobertura/madurez GRC, no una certificación ni una declaración legal de cumplimiento.
      </p>
    </div>
  );
}
