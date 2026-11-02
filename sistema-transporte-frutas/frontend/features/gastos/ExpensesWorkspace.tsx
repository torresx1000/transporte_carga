"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Banknote, ReceiptText, Route, Search, Wallet } from "lucide-react";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { useCatalog, Trip, control } from "@/features/transporte/data";
import { useResourceList } from "@/hooks/useResources";
import { ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";

type Expense = { id: string; viaje_id?: string; monto_centimos?: number; motivo?: string; detalle?: string; created_at?: string; data?: Record<string, unknown> };

export default function ExpensesWorkspace({ initialForm = false }: { initialForm?: boolean }) {
  const router = useRouter();
  const trips = useCatalog<Trip>("viajes");
  const expenses = useResourceList("gastos", { page: 1, page_size: 100 });
  const cache = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setSaving(true); setError("");
    const form = new FormData(event.currentTarget);
    const amount = Number(form.get("amount"));
    const trip = trips.data?.find((item) => item.id === String(form.get("viaje_id")));
    const data = {
      viaje_id: String(form.get("viaje_id")),
      vehiculo_id: trip?.vehiculo_id || null,
      monto_centimos: Math.round(amount * 100),
      motivo: String(form.get("motivo")).trim(),
      categoria: String(form.get("motivo")).trim(),
      detalle: String(form.get("detalle")).trim(),
      descripcion: String(form.get("detalle")).trim(),
    };
    const files = form.getAll("archivo").filter((item): item is File => item instanceof File && item.size > 0);
    try {
      const created = (await api.post<Expense>("/gastos", { data })).data;
      for (const file of files) {
        const upload = new FormData(); upload.append("archivo", file);
        await api.post(`/gastos/${created.id}/documentos`, upload, { headers: { "Content-Type": "multipart/form-data" } });
      }
      await Promise.all([cache.invalidateQueries({ queryKey: ["gastos"] }), cache.invalidateQueries({ queryKey: ["viajes"] }), cache.invalidateQueries({ queryKey: ["reportes"] })]);
      if (!initialForm) (event.currentTarget as HTMLFormElement).reset();
      else router.push("/gastos");
    } catch (cause) {
      setError(getApiError(cause));
      await cache.invalidateQueries({ queryKey: ["gastos"] });
    } finally { setSaving(false); }
  }

  const rows = (expenses.data?.items ?? []) as unknown as Expense[];
  const filteredRows = rows.filter((row) => {
    const d: Record<string, unknown> = row.data ?? row as unknown as Record<string, unknown>;
    const tripId = String(d.viaje_id ?? row.viaje_id ?? "");
    const tripCode = trips.data?.find((trip) => trip.id === tripId)?.codigo ?? "";
    return [row.created_at, tripId, tripCode, d.motivo, d.categoria, d.detalle, d.descripcion, d.monto_centimos]
      .some((value) => String(value ?? "").toLocaleLowerCase("es-PE").includes(search.trim().toLocaleLowerCase("es-PE")));
  });
  if (initialForm) return <main className="min-h-screen bg-[#f7f8fa] p-6 text-[#17211e]"><div className="mx-auto max-w-3xl"><Link href="/gastos" className="text-sm text-[#2563EB]">← Gastos</Link><h1 className="mt-4 text-2xl font-semibold">Gastos · Nuevo</h1><p className="mt-1 text-sm text-gray-600">Registra un importe asociado a un viaje. La fecha y hora se asignan automáticamente.</p>{formContent(trips.data ?? [], saving, error, submit, typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("viaje_id") ?? "" : "")}</div></main>;

  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10"><div className="mx-auto max-w-[1440px]"><div className="mb-7 flex items-start justify-between gap-4"><div><div className="mb-2 flex items-center gap-2 text-xs text-[#87918c]"><span>Administración</span><span>/</span><span>Finanzas</span><span>/</span><span className="text-[#47534d]">Gastos</span></div><h1 className="text-[28px] font-semibold tracking-[-.8px]">Gastos</h1><p className="mt-1 text-sm text-[#7a8580]">Registra y consulta los costos asociados a cada viaje.</p></div><Link href="/gastos/nuevo" className="inline-flex h-10 shrink-0 items-center gap-2 rounded-lg bg-[#2563EB] px-4 text-sm font-medium text-white shadow-sm transition hover:bg-[#1D4ED8]"><span className="text-base">+</span><span className="hidden sm:inline">Nuevo gasto</span><span className="sm:hidden">Nuevo</span></Link></div><section className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4"><div className="rounded-xl border border-[#e8ece9] bg-white p-4"><div className="flex items-center justify-between text-[#2f3a36]"><span className="text-xs font-medium text-[#7a8580]">Total gastos</span><span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#EAF5EE] text-[#236A4A]"><Wallet size={16}/></span></div><p className="mt-4 text-2xl font-semibold">{rows.length.toString().padStart(2,"0")}</p><p className="mt-1 text-[11px] text-[#89938e]">Registros</p></div><div className="rounded-xl border border-[#e8ece9] bg-white p-4"><div className="flex items-center justify-between text-[#2f3a36]"><span className="text-xs font-medium text-[#7a8580]">Importe</span><span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#E0F2FE] text-[#1D4ED8]"><Banknote size={16}/></span></div><p className="mt-4 text-2xl font-semibold">S/ {rows.reduce((sum, row) => sum + Number((row.data ?? row).monto_centimos ?? row.monto_centimos ?? 0) / 100, 0).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p><p className="mt-1 text-[11px] text-[#89938e]">Acumulado</p></div><div className="rounded-xl border border-[#e8ece9] bg-white p-4"><div className="flex items-center justify-between text-[#2f3a36]"><span className="text-xs font-medium text-[#7a8580]">Viajes</span><span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#F3E8FF] text-[#7C3AED]"><Route size={16}/></span></div><p className="mt-4 text-2xl font-semibold">{new Set(rows.map((row) => String((row.data ?? row).viaje_id ?? row.viaje_id ?? "")).filter(Boolean)).size.toString().padStart(2,"0")}</p><p className="mt-1 text-[11px] text-[#89938e]">Vinculados</p></div><div className="rounded-xl border border-[#e8ece9] bg-white p-4"><div className="flex items-center justify-between text-[#2f3a36]"><span className="text-xs font-medium text-[#7a8580]">Por revisar</span><span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#FEF3C7] text-[#B45309]"><ReceiptText size={16}/></span></div><p className="mt-4 text-2xl font-semibold">{rows.filter((row) => !String((row.data ?? row).motivo ?? row.motivo ?? "").trim()).length.toString().padStart(2,"0")}</p><p className="mt-1 text-[11px] text-[#89938e]">Sin motivo</p></div></section>
    {expenses.isLoading ? <TableSkeleton/> : expenses.isError ? <ErrorState message={getApiError(expenses.error)} onRetry={()=>void expenses.refetch()}/> : <section className="overflow-hidden rounded-xl border border-[#e8ece9] bg-white shadow-[0_1px_2px_rgba(20,40,30,.03)]"><div className="mb-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><h2 className="text-[15px] font-semibold text-[#28332e]">Gastos registrados</h2><p className="mt-0.5 text-xs text-[#89938e]">{filteredRows.length} registros encontrados</p></div><label className="relative block w-full sm:max-w-sm"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/><input type="search" value={search} onChange={(event)=>setSearch(event.target.value)} placeholder="Buscar por viaje, motivo, detalle o importe…" className="h-10 w-full rounded-lg border border-[#e7ebe8] pl-9 pr-3 text-sm outline-none placeholder:text-[#a4ada8] focus:border-[#2563EB] focus:ring-2 focus:ring-[#DBEAFE]"/></label></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left"><thead className="bg-[#fafbfa] text-left text-[10px] font-semibold uppercase tracking-[.08em] text-[#909a95]"><tr>{["Fecha de registro","Viaje","Motivo","Detalle","Importe"].map(x=><th key={x} className="border-b border-[#edf0ee] px-4 py-3">{x}</th>)}</tr></thead><tbody>{filteredRows.map((row: Expense)=>{const d:Record<string,unknown>=row.data??row as unknown as Record<string,unknown>;const tripId=String(d.viaje_id??row.viaje_id??"");const tripCode=trips.data?.find((trip)=>trip.id===tripId)?.codigo;return <tr key={row.id} className="group border-b border-[#f0f2f1] transition hover:bg-[#fbfcfb]"><td className="px-4 py-3.5 text-[12px] text-[#56625c]">{row.created_at?new Date(row.created_at).toLocaleString("es-PE"):"—"}</td><td className="px-4 py-3.5 text-[12px] text-[#56625c]">{tripCode||tripId||"—"}</td><td className="px-4 py-3.5 text-[12px] text-[#56625c]">{String(d.motivo??d.categoria??"—")}</td><td className="px-4 py-3.5 text-[12px] text-[#56625c]">{String(d.detalle??d.descripcion??"—")}</td><td className="px-4 py-3.5 text-[12px] text-[#56625c]">S/ {((Number(d.monto_centimos??row.monto_centimos??0))/100).toFixed(2)}</td></tr>})}</tbody></table>{!filteredRows.length&&<p className="p-8 text-center text-sm text-[#89938e]">{search?"No se encontraron gastos con esa búsqueda.":"Todavía no hay gastos registrados."}</p>}</div></section>}</div></main>;
}

function formContent(trips: Trip[], saving: boolean, error: string, submit: (event: React.FormEvent<HTMLFormElement>) => void, selectedTrip = "") {
  return <form onSubmit={submit} className="mt-5 grid gap-4 rounded-xl border bg-white p-5 sm:grid-cols-2"><label className="text-sm">Viaje *<select required name="viaje_id" defaultValue={selectedTrip} className={control}><option value="">Selecciona un viaje</option>{trips.filter((trip)=>trip.vehiculo_id).map(trip=><option key={trip.id} value={trip.id}>{trip.codigo} · {trip.estado}</option>)}</select></label><label className="text-sm">Importe (S/) *<input required name="amount" type="number" min="0.01" step="0.01" className={control} placeholder="0.00"/></label><label className="text-sm">Motivo *<input required name="motivo" maxLength={80} className={control} placeholder="Combustible, peajes, alimentación…"/></label><label className="text-sm">Fecha de registro<input readOnly value={new Date().toLocaleString("es-PE")} className={`${control} bg-gray-50`}/></label><label className="text-sm sm:col-span-2">Detalle *<textarea required name="detalle" rows={3} maxLength={2000} className={`${control} h-auto py-2`} placeholder="Describe el gasto"/></label><label className="text-sm sm:col-span-2">Adjuntar archivo (PDF o imagen, hasta 10 MB cada uno)<input name="archivo" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xlsx" className="mt-2 block w-full rounded-lg border p-2 text-sm"/></label>{error&&<p role="alert" className="sm:col-span-2 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={saving||!trips.some((trip)=>trip.vehiculo_id)} className="rounded bg-[#2563EB] px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50 sm:col-span-2">{saving?"Guardando…":"Guardar gasto"}</button></form>;
}
