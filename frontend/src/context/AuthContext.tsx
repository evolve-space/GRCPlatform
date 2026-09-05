import { useCallback, useEffect, useState } from "react";
import { api, clearToken, getToken, setToken } from "../lib/api";
import type { CurrentUser } from "../types";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<CurrentUser | null>(null);
  const [cargando, setCargando] = useState(true);

  const cargarUsuarioActual = useCallback(async () => {
    if (!getToken()) {
      setUsuario(null);
      setCargando(false);
      return;
    }
    try {
      const response = await api.get<CurrentUser>("/api/v1/auth/me");
      setUsuario(response.data);
    } catch {
      clearToken();
      setUsuario(null);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    cargarUsuarioActual();

    const alExpirarSesion = () => setUsuario(null);
    window.addEventListener("grcplatform:sesion-expirada", alExpirarSesion);
    return () => window.removeEventListener("grcplatform:sesion-expirada", alExpirarSesion);
  }, [cargarUsuarioActual]);

  const iniciarSesion = useCallback(
    async (email: string, password: string) => {
      const cuerpo = new URLSearchParams();
      cuerpo.set("username", email);
      cuerpo.set("password", password);

      const response = await api.post<{ access_token: string }>("/api/v1/auth/login", cuerpo, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      setToken(response.data.access_token);
      await cargarUsuarioActual();
    },
    [cargarUsuarioActual],
  );

  const cerrarSesion = useCallback(() => {
    clearToken();
    setUsuario(null);
  }, []);

  return (
    <AuthContext.Provider value={{ usuario, cargando, iniciarSesion, cerrarSesion }}>
      {children}
    </AuthContext.Provider>
  );
}
