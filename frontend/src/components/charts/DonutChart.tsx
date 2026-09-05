import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export interface SegmentoDonut {
  label: string;
  value: number;
  color: string;
}

export function DonutChart({ datos, altura = 220 }: { datos: SegmentoDonut[]; altura?: number }) {
  const conValor = datos.filter((d) => d.value > 0);

  if (conValor.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-slate-400" style={{ height: altura }}>
        Sin datos
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={altura}>
      <PieChart>
        <Pie
          data={conValor}
          dataKey="value"
          nameKey="label"
          innerRadius="55%"
          outerRadius="80%"
          paddingAngle={2}
        >
          {conValor.map((segmento) => (
            <Cell key={segmento.label} fill={segmento.color} stroke="white" strokeWidth={2} />
          ))}
        </Pie>
        <Tooltip formatter={(value) => [String(value), "Cantidad"]} />
        <Legend verticalAlign="bottom" height={36} iconType="circle" iconSize={8} />
      </PieChart>
    </ResponsiveContainer>
  );
}
