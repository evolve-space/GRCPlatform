import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface BarraHorizontal {
  label: string;
  value: number;
  color: string;
}

export function HorizontalBarChart({
  datos,
  altura,
}: {
  datos: BarraHorizontal[];
  altura?: number;
}) {
  if (datos.length === 0 || datos.every((d) => d.value === 0)) {
    return <div className="flex items-center justify-center py-10 text-sm text-slate-400">Sin datos</div>;
  }

  const alturaCalculada = altura ?? Math.max(120, datos.length * 40);

  return (
    <ResponsiveContainer width="100%" height={alturaCalculada}>
      <BarChart data={datos} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} stroke="#94a3b8" />
        <YAxis type="category" dataKey="label" width={140} tick={{ fontSize: 12 }} stroke="#94a3b8" />
        <Tooltip formatter={(value) => [String(value), "Cantidad"]} cursor={{ fill: "#f1f5f9" }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={18}>
          {datos.map((barra) => (
            <Cell key={barra.label} fill={barra.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
