import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { useAuth } from "../../context/auth-context";
import { listarFrameworks } from "../../lib/frameworks";
import { ETIQUETAS_ESTADO_FRAMEWORK, TONO_ESTADO_FRAMEWORK } from "../../lib/labels";
import { puedeEscribir } from "../../lib/permisos";
import type { Framework } from "../../types";

export function FrameworksListPage() {
  const { usuario } = useAuth();
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    listarFrameworks().then((datos) => {
      setFrameworks(datos);
      setCargando(false);
    });
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Marcos de cumplimiento</h1>
        {puedeEscribir(usuario?.role) && (
          <Link
            to="/marcos/nuevo"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Nuevo marco
          </Link>
        )}
      </div>

      {cargando ? (
        <p className="mt-6 text-slate-400">Cargando…</p>
      ) : frameworks.length === 0 ? (
        <p className="mt-6 text-slate-400">Aún no hay marcos de cumplimiento configurados.</p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {frameworks.map((framework) => (
            <Link
              key={framework.id}
              to={`/marcos/${framework.id}`}
              className="block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">{framework.short_name}</h2>
                <Badge tono={TONO_ESTADO_FRAMEWORK[framework.status]}>
                  {ETIQUETAS_ESTADO_FRAMEWORK[framework.status]}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-slate-500">{framework.name}</p>
              <p className="mt-2 text-xs text-slate-400">Versión {framework.version}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
