"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Suspense } from "react";
import { useAuthStore } from "@/lib/auth/authStore";

const schema = z.object({ email: z.string().email("Ingresa un correo válido"), password: z.string().min(1, "Ingresa tu contraseña") });
type Values = z.infer<typeof schema>;

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const setSession = useAuthStore((state) => state.setSession);
  const [serverError, setServerError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) });
  async function submit(values: Values) {
    setServerError("");
    const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { setServerError(data.detail ?? "No se pudo iniciar sesión."); return; }
    setSession(data.access_token, data.user);
    const next = params.get("next");
    const safeNext = next?.startsWith("/") && !next.startsWith("//") ? next : data.user.role === "cliente" ? "/cliente" : "/";
    router.replace(safeNext);
  }
  return <main className="flex min-h-screen items-center justify-center bg-[#f3f5f9] px-4 py-10 text-[#172b4d]"><section className="w-full max-w-[420px] rounded-2xl border border-[#e1e7f0] bg-white p-7 shadow-sm"><div className="mb-7 flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-xl bg-[#2864ed] text-lg font-semibold text-white">T</span><div><h1 className="text-lg font-semibold">TransFrutas</h1><p className="text-xs text-[#7e91ad]">Acceso al sistema de gestión</p></div></div><h2 className="text-xl font-semibold">Iniciar sesión</h2><p className="mt-1 text-sm text-[#7e91ad]">Ingresa tus credenciales para continuar.</p><form onSubmit={handleSubmit(submit)} className="mt-6 space-y-4"><label className="block text-sm font-medium">Correo electrónico<input {...register("email")} type="email" autoComplete="email" className="mt-1.5 h-11 w-full rounded-lg border border-[#dce3ed] px-3 text-sm outline-none focus:border-[#2864ed]" placeholder="correo@empresa.com" />{errors.email && <span className="mt-1 block text-xs text-red-600">{errors.email.message}</span>}</label><label className="block text-sm font-medium">Contraseña<input {...register("password")} type="password" autoComplete="current-password" className="mt-1.5 h-11 w-full rounded-lg border border-[#dce3ed] px-3 text-sm outline-none focus:border-[#2864ed]" />{errors.password && <span className="mt-1 block text-xs text-red-600">{errors.password.message}</span>}</label>{serverError && <p role="alert" className="text-sm text-red-600">{serverError}</p>}<button disabled={isSubmitting} className="h-11 w-full rounded-lg bg-[#2864ed] text-sm font-medium text-white disabled:opacity-60">{isSubmitting ? "Validando…" : "Ingresar"}</button></form><p className="mt-5 text-xs text-[#7e91ad]">Si necesitas acceso al sistema, comunícate con el administrador.</p></section></main>;
}

export default function LoginPage() {
  return <Suspense fallback={<main className="flex min-h-screen items-center justify-center bg-[#f3f5f9] text-sm text-[#7e91ad]">Cargando acceso…</main>}><LoginForm /></Suspense>;
}
