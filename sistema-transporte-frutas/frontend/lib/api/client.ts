import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { tokenStorage } from "@/lib/auth/tokenStorage";
import { useAuthStore } from "@/lib/auth/authStore";

const baseURL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const api = axios.create({
  baseURL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});
const refreshClient = axios.create({
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as
      (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    if (
      error.response?.status !== 401 ||
      !original ||
      original._retried ||
      original.url?.includes("/auth/")
    )
      return Promise.reject(error);
    original._retried = true;
    refreshing ??= refreshClient
      .post<{ access_token: string }>(
        "/api/auth/refresh",
        {},
        { withCredentials: true },
      )
      .then(({ data }) => {
        tokenStorage.setAccessToken(data.access_token);
        return data.access_token;
      })
      .catch(() => null)
      .finally(() => {
        refreshing = null;
      });
    const token = await refreshing;
    if (!token) {
      useAuthStore.getState().clearSession();
      if (typeof window !== "undefined") {
        await refreshClient
          .post("/api/auth/logout", {}, { withCredentials: true })
          .catch(() => undefined);
        window.dispatchEvent(new Event("transfrutas:unauthorized"));
      }
      return Promise.reject(error);
    }
    original.headers.Authorization = `Bearer ${token}`;
    return api(original);
  },
);
