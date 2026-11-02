const ACCESS_KEY = "transfrutas.access";
const USER_KEY = "transfrutas.user";

export const tokenStorage = {
  getAccessToken(): string | null {
    return typeof window === "undefined" ? null : window.localStorage.getItem(ACCESS_KEY);
  },
  setAccessToken(token: string) {
    if (typeof window !== "undefined") window.localStorage.setItem(ACCESS_KEY, token);
  },
  getUser<T>(): T | null {
    if (typeof window === "undefined") return null;
    try { const value = window.localStorage.getItem(USER_KEY); return value ? JSON.parse(value) as T : null; }
    catch { return null; }
  },
  setUser(user: unknown) {
    if (typeof window !== "undefined") window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    if (typeof window !== "undefined") { window.localStorage.removeItem(ACCESS_KEY); window.localStorage.removeItem(USER_KEY); }
  },
};
