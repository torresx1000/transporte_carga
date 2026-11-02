"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth/authStore";

export default function PendingAccessPage() {
  const router = useRouter();
  const clearSession = useAuthStore((state) => state.clearSession);
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    clearSession();
    router.replace("/login");
  }
  return <main className="flex min-h-screen items-center justify-center bg-[#f3f5f9] px-5 py-10 text-[#172b4d]">
    <section className="w-full max-w-lg rounded-2xl border border-[#e1e7f0] bg-white p-8 text-center shadow-sm">
      <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-amber-50 text-xl text-amber-700">!</div>
      <h1 className="mt-5 text-xl font-semibold">Acceso pendiente</h1>
      <p className="mt-2 text-sm leading-6 text-[#647b9d]">Tu cuenta de chofer aún no tiene acceso operativo. Un administrador debe vincularla con tu ficha de conductor antes de habilitar tus viajes y cargas asignadas.</p>
      <button onClick={() => void logout()} className="mt-6 inline-flex rounded-lg border border-[#dce3ed] px-4 py-2 text-sm font-medium text-[#536a8d]">Cerrar sesión</button>
    </section>
  </main>;
}
