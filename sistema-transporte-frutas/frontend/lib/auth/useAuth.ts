"use client";

import { useAuthStore } from "@/lib/auth/authStore";

export function useAuth() {
  const user = useAuthStore((state) => state.user);
  const hydrated = useAuthStore((state) => state.hydrated);
  const logout = useAuthStore((state) => state.clearSession);
  return { user, hydrated, isAuthenticated: Boolean(user), logout };
}
