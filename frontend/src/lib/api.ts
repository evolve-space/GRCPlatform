import axios from "axios";

const TOKEN_STORAGE_KEY = "grcplatform_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      window.dispatchEvent(new Event("grcplatform:sesion-expirada"));
    }
    return Promise.reject(error);
  },
);

export function obtenerMensajeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detalle = error.response?.data?.detail;
    if (typeof detalle === "string") {
      return detalle;
    }
    // Formato normalizado de la Fase 9: {"detail": {"code": "...", "message": "..."}}
    if (detalle && typeof detalle === "object" && typeof detalle.message === "string") {
      return detalle.message;
    }
    if (Array.isArray(detalle)) {
      return detalle.map((item) => item.msg ?? String(item)).join(" ");
    }
  }
  return "Ha ocurrido un error inesperado. Inténtalo de nuevo.";
}
