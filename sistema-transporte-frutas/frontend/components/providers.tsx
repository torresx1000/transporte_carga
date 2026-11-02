"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { makeQueryClient } from "@/lib/query/queryClient";
import { useAuthStore } from "@/lib/auth/authStore";

function AuthBootstrap() {
  const router = useRouter();
  const hydrate = useAuthStore((state) => state.hydrate);
  useEffect(() => {
    hydrate();
    const onUnauthorized = () => router.replace("/login");
    window.addEventListener("transfrutas:unauthorized", onUnauthorized);
    return () => window.removeEventListener("transfrutas:unauthorized", onUnauthorized);
  }, [hydrate, router]);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);
  return <QueryClientProvider client={queryClient}><AuthBootstrap />{children}<Toaster position="top-right" richColors /></QueryClientProvider>;
}
