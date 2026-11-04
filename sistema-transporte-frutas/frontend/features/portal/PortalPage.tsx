"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";
import { useAuthStore } from "@/lib/auth/authStore";

type PortalModule = "me" | "cargas" | "viajes" | "documentos" | "pagos";
const titles: Record<PortalModule, string> = { me: "Resumen", cargas: "Mis cargas", viajes: "Mis viajes", documentos: "Documentos", pagos: "Pagos" };
const nav = [{ href: "/cliente", title: "Resumen" }, { href: "/cliente/cargas", title: "Cargas" }, { href: "/cliente/viajes", title: "Viajes" }, { href: "/cliente/documentos", title: "Documentos" }, { href: "/cliente/pagos", title: "Pagos" }, { href: "/cliente/perfil", title: "Mi perfil" }];

export default function PortalPage({ module }: { module: PortalModule }) {
  const router = useRouter();
  const clearSession = useAuthStore((state) => state.clearSession);
  const query = useQuery({ queryKey: ["portal", module], queryFn: async () => { const { data } = await api.get(module === "me" ? "/portal/me" : `/portal/${module}`); return data as Record<string, unknown> | Record<string, unknown>[]; }, refetchOnWindowFocus: true });
  const records = Array.isArray(query.data) ? query.data : query.data ? [query.data] : [];
  const fields = records.length ? Object.keys(records[0]).filter((key) => key !== "data" && key !== "perfil") : [];
  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10"><div className="mx-auto max-w-[1200px]"><div className="mb-7 flex flex-wrap items-start justify-between gap-4"><div><p className="mb-2 text-xs text-[#87918c]">Portal del cliente / <span className="text-[#47534d]">{titles[module]}</span></p><h1 className="text-[28px] font-semibold tracking-[-.8px]">{titles[module]}</h1><p className="mt-1 text-sm text-[#7a8580]">Consulta la información de tus operaciones.</p></div><button onClick={async () => { await fetch("/api/auth/logout", { method: "POST" }); clearSession(); router.replace("/login"); }} className="rounded-lg border border-[#e1e6e2] bg-white px-3 py-2 text-xs font-medium text-[#59655f]">Cerrar sesión</button></div><nav className="mb-6 flex flex-wrap gap-2">{nav.map((item) => <Link key={item.href} href={item.href} className={`rounded-lg border px-3 py-2 text-xs ${item.title === titles[module] ? "border-[#2563EB] bg-[#eaf5ee] font-medium text-[#2563EB]" : "border-[#e5eae6] bg-white text-[#59655f]"}`}>{item.title}</Link>)}</nav>
    {query.isLoading ? <TableSkeleton /> : query.isError ? <ErrorState message={getApiError(query.error)} onRetry={() => void query.refetch()} /> : records.length === 0 ? <EmptyState title="Aún no tienes información" description="Cuando se registren operaciones asociadas a tu cuenta, aparecerán aquí." /> : module === "me" ? <div className="grid gap-4 sm:grid-cols-2"><InfoCard label="Correo de acceso" value={String(records[0].email ?? "—")} /><InfoCard label="Cliente vinculado" value={String(records[0].cliente_nombre ?? records[0].cliente_id ?? "—")} /><InfoCard label="Operaciones" value="Consulta tus cargas, viajes, pagos y documentos desde el menú." /></div> : <section className="overflow-hidden rounded-xl border border-[#e8ece9] bg-white"><div className="border-b border-[#edf0ee] px-5 py-4"><h2 className="text-sm font-semibold">{titles[module]}</h2><p className="mt-1 text-xs text-[#89938e]">{records.length} registros</p></div><div className="overflow-x-auto"><table className="w-full min-w-[600px] text-left"><thead className="bg-[#fafbfa] text-[10px] uppercase tracking-wide text-[#909a95]"><tr>{fields.map((key) => <th key={key} className="px-4 py-3">{key.replaceAll("_", " ")}</th>)}</tr></thead><tbody className="divide-y divide-[#f0f2f1]">{records.map((record, index) => <tr key={String(record.id ?? index)}>{fields.map((key) => <td key={key} className="max-w-[280px] truncate px-4 py-3 text-xs text-[#59655f]">{formatValue(record[key])}</td>)}</tr>)}</tbody></table></div></section>}
    <p className="mt-4 text-[11px] text-[#9ba49f]">Información consultada desde tu cuenta autenticada.</p></div></main>;
}
function formatValue(value: unknown) { if (value == null || value === "") return "—"; if (typeof value === "object") return JSON.stringify(value); return String(value); }
function InfoCard({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-[#e8ece9] bg-white p-5"><p className="text-xs text-[#89938e]">{label}</p><p className="mt-2 break-words text-sm font-medium text-[#46524b]">{value}</p></div>; }
