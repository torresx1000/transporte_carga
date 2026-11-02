import { create } from "zustand";
import { tokenStorage } from "@/lib/auth/tokenStorage";

export type SessionUser = { id: string; email: string; role: string; name?: string };
type AuthState = {
  user: SessionUser | null;
  hydrated: boolean;
  setSession: (token: string, user: SessionUser) => void;
  clearSession: () => void;
  hydrate: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  hydrated: false,
  setSession: (token, user) => { tokenStorage.setAccessToken(token); tokenStorage.setUser(user); set({ user, hydrated: true }); },
  clearSession: () => { tokenStorage.clear(); set({ user: null, hydrated: true }); },
  hydrate: () => set({ user: tokenStorage.getUser<SessionUser>(), hydrated: true }),
}));
