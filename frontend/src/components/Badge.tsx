import { CLASES_TONO, type Tono } from "../lib/labels";

interface BadgeProps {
  tono: Tono;
  children: React.ReactNode;
}

export function Badge({ tono, children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${CLASES_TONO[tono]}`}
    >
      {children}
    </span>
  );
}
