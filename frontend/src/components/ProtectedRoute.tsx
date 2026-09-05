import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/auth-context";

export function ProtectedRoute() {
  const { usuario, cargando } = useAuth();

  if (cargando) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Cargando…
      </div>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
