"use client";

import Link from "next/link";
import DeleteRecordButton from "@/components/ui/DeleteRecordButton";
import { useState } from "react";
import { Building2, Check, ChevronDown, Download, Ellipsis, Eye, MapPin, Pencil, Plus, Search, Users, X } from "lucide-react";
import type { Client, ClientKind, ClientStatus } from "@/types/client";
import { useCliente, useClientesList, useUpdateCliente } from "@/hooks/useClientes";
import { getApiError } from "@/lib/api/errors";
import { useAuthStore } from "@/lib/auth/authStore";
import { canReactivateInactiveClient } from "@/features/clientes/clientAccess";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";

const PAGE_SIZE = 10;

export default function ClientsPage() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("Todos los estados");
  const [kind, setKind] = useState("Todos los tipos");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<Client | null>(null);
  const [notice, setNotice] = useState("");
  const role = useAuthStore((state) => state.user?.role);

  const statusFilter = status === "Todos los estados" ? undefined : status === "Activo" ? "activo" : "inactivo";
  const kindFilter = kind === "Todos los tipos" ? undefined : kind as ClientKind;
  const clientsQuery = useClientesList({ page, page_size: PAGE_SIZE, q: query.trim() || undefined, estado: statusFilter, tipo: kindFilter });
  const totalQuery = useClientesList({ page: 1, page_size: 1 });
  const activeQuery = useClientesList({ page: 1, page_size: 1, estado: "activo" });
  const companyQuery = useClientesList({ page: 1, page_size: 1, tipo: "Empresa" });
  const detailQuery = useCliente(selectedId ?? "", Boolean(selectedId));
  const updateClient = useUpdateCliente();
  const rows = clientsQuery.data?.items ?? [];
  const total = clientsQuery.data?.total ?? 0;
  const pages = clientsQuery.data?.pages ?? 1;

  function resetPageAnd(setter: (value: string) => void, value: string) {
    setPage(1);
    setter(value);
  }

  async function toggleStatus(client: Client) {
    try {
      await updateClient.mutateAsync({ id: client.id, payload: { estado: client.estado === "activo" ? "inactivo" : "activo" } });
      setNotice(`${client.nombre} ahora está ${client.estado === "activo" ? "inactivo" : "activo"}.`);
    } catch {
      setNotice("No se pudo actualizar el estado del cliente.");
    } finally {
      setConfirm(null);
      window.setTimeout(() => setNotice(""), 3200);
    }
  }

  function exportPage() {
    const columns: Array<[keyof Client, string]> = [["id", "ID"], ["nombre", "Cliente"], ["documento", "Documento"], ["telefono", "Teléfono"], ["ubicacion", "Ubicación"], ["tipo", "Tipo"], ["estado", "Estado"]];
    const csv = [columns.map(([, title]) => title).join(","), ...rows.map((client) => columns.map(([key]) => `"${String(client[key] ?? "").replaceAll('"', '""')}"`).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `clientes-pagina-${page}.csv`; link.click(); URL.revokeObjectURL(url);
  }

  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10"><div className="mx-auto max-w-[1440px]">
    <div className="mb-7 flex items-start justify-between gap-4"><div><div className="mb-2 flex items-center gap-2 text-xs text-[#87918c]"><span>Administración</span><span>/</span><span className="text-[#47534d]">Clientes</span></div><h1 className="text-[28px] font-semibold tracking-[-0.8px]">Clientes</h1><p className="mt-1 text-sm text-[#7a8580]">Gestiona tus clientes, contactos y actividad comercial.</p></div><Link href="/clientes/nuevo" className="inline-flex h-10 shrink-0 items-center gap-2 rounded-lg bg-[#2563EB] px-4 text-sm font-medium text-white shadow-sm hover:bg-[#1D4ED8]"><Plus size={17}/><span className="hidden sm:inline">Nuevo cliente</span><span className="sm:hidden">Nuevo</span></Link></div>

    <section className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3"><SummaryCard label="Total clientes" value={totalQuery.data?.total} icon={<Users size={18}/>} tone="green"/><SummaryCard label="Clientes activos" value={activeQuery.data?.total} icon={<Check size={18}/>} tone="blue"/><SummaryCard label="Empresas" value={companyQuery.data?.total} icon={<Building2 size={18}/>} tone="violet"/></section>

    <section className="overflow-hidden rounded-xl border border-[#e8ece9] bg-white shadow-[0_1px_2px_rgba(20,40,30,.03)]"><div className="flex flex-col justify-between gap-4 border-b border-[#edf0ee] px-5 py-4 sm:flex-row sm:items-center sm:px-6"><div><h2 className="text-[15px] font-semibold">Directorio de clientes</h2><p className="mt-0.5 text-xs text-[#89938e]">Consulta y administra la información de tu cartera.</p></div><button onClick={exportPage} disabled={rows.length === 0} className="inline-flex items-center gap-2 self-start rounded-lg border border-[#e6eae7] px-3 py-2 text-xs font-medium text-[#59655f] disabled:opacity-50"><Download size={15}/>Exportar página</button></div>
      <div className="flex flex-col gap-3 border-b border-[#edf0ee] px-5 py-4 sm:flex-row sm:px-6"><label className="relative min-w-0 flex-1"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9aa39f]"/><input value={query} onChange={(event)=>resetPageAnd(setQuery,event.target.value)} placeholder="Buscar por nombre, documento, teléfono..." className="h-10 w-full rounded-lg border border-[#e7ebe8] pl-9 pr-3 text-sm outline-none focus:border-[#2563EB]"/></label><label className="relative"><select value={kind} onChange={(event)=>resetPageAnd(setKind,event.target.value)} className="h-10 w-full appearance-none rounded-lg border border-[#e7ebe8] bg-white px-3 pr-9 text-xs sm:w-[165px]"><option>Todos los tipos</option><option>Empresa</option><option>Persona natural</option></select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#929c97]"/></label><label className="relative"><select value={status} onChange={(event)=>resetPageAnd(setStatus,event.target.value)} className="h-10 w-full appearance-none rounded-lg border border-[#e7ebe8] bg-white px-3 pr-9 text-xs sm:w-[165px]"><option>Todos los estados</option><option>Activo</option><option>Inactivo</option></select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#929c97]"/></label></div>
      {clientsQuery.isLoading ? <TableSkeleton rows={5} columns={6}/> : clientsQuery.isError ? <ErrorState message={getApiError(clientsQuery.error)} onRetry={()=>void clientsQuery.refetch()}/> : rows.length === 0 ? <EmptyState title="No hay clientes" description="No encontramos coincidencias con la búsqueda y filtros seleccionados." action={<Link href="/clientes/nuevo" className="rounded-lg bg-[#2563EB] px-3 py-2 text-xs font-medium text-white">Crear cliente</Link>}/> : <>
        <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left"><thead className="bg-[#fafbfa] text-[10px] font-semibold uppercase tracking-[.08em] text-[#909a95]"><tr><th className="px-6 py-3">Cliente</th><th className="px-4 py-3">Documento</th><th className="px-4 py-3">Teléfono</th><th className="px-4 py-3">Ubicación</th><th className="px-4 py-3">Tipo</th><th className="px-4 py-3">Estado</th><th className="px-5 py-3 text-right">Acciones</th></tr></thead><tbody className="divide-y divide-[#f0f2f1]">{rows.map((client)=><tr key={client.id} className="group hover:bg-[#fbfcfb]"><td className="px-6 py-3.5"><button onClick={()=>setSelectedId(client.id)} className="flex items-center gap-3 text-left"><Avatar name={client.nombre}/><span><span className="block max-w-[245px] truncate text-[13px] font-medium">{client.nombre}</span><span className="mt-0.5 block max-w-[245px] truncate text-[10px] text-[#9aa39f]">{client.id}</span></span></button></td><td className="px-4 py-3.5"><span className="block text-[12px]">{client.documento ?? "—"}</span><span className="mt-0.5 block text-[10px] text-[#a0a9a4]">{client.tipo_documento ?? "—"}</span></td><td className="px-4 py-3.5 text-[12px]">{client.telefono ?? "—"}</td><td className="px-4 py-3.5 text-[12px]"><MapPin size={13} className="mr-1 inline text-[#9ba59f]"/>{client.ubicacion ?? client.departamento ?? "—"}</td><td className="px-4 py-3.5 text-[12px]">{client.tipo ?? "—"}</td><td className="px-4 py-3.5"><StatusBadge status={client.estado}/></td><td className="px-5 py-3.5"><div className="flex justify-end gap-1">{canReactivateInactiveClient(role,client.estado)&&<button title="Reactivar cliente" onClick={()=>void toggleStatus(client)} className="rounded-md px-2 py-1 text-[11px] font-medium text-[#2563EB] hover:bg-[#eaf5ee]">Reactivar</button>}<button title="Ver detalle" onClick={()=>setSelectedId(client.id)} className="rounded-md p-2 text-[#7c8781]"><Eye size={16}/></button><DeleteRecordButton resource={"clientes"} id={client.id}/><Link title="Editar" href={`/clientes/nuevo?editar=${client.id}`} className="rounded-md p-2 text-[#7c8781]"><Pencil size={15}/></Link><button title={client.estado === "activo" ? "Desactivar" : "Activar"} onClick={()=>setConfirm(client)} className="rounded-md p-2 text-[#7c8781]"><Ellipsis size={17}/></button></div></td></tr>)}</tbody></table></div>
        <div className="flex flex-col items-center justify-between gap-3 border-t border-[#edf0ee] px-5 py-3.5 text-xs text-[#89938e] sm:flex-row sm:px-6"><span>Mostrando {rows.length} de {total} clientes · página {clientsQuery.data?.page ?? page} de {pages}</span><div className="flex gap-2"><button disabled={page<=1} onClick={()=>setPage((current)=>Math.max(1,current-1))} className="rounded-md border px-3 py-1.5 disabled:opacity-40">Anterior</button><button disabled={page>=pages} onClick={()=>setPage((current)=>Math.min(pages,current+1))} className="rounded-md border px-3 py-1.5 disabled:opacity-40">Siguiente</button></div></div>
      </>}
      <div className="border-t border-[#edf0ee] px-5 py-3 text-[11px] text-[#9ba49f]">Los resultados, filtros y páginas se consultan en el servidor.</div>
    </section>
    {confirm&&<div className="fixed inset-0 z-40 flex items-center justify-center bg-[#17211e]/35 p-4"><section className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl"><h2 className="text-base font-semibold">{confirm.estado === "activo" ? "¿Desactivar cliente?" : "¿Activar cliente?"}</h2><p className="mt-2 text-sm text-[#78837d]">{confirm.nombre}</p><div className="mt-6 flex justify-end gap-2"><button onClick={()=>setConfirm(null)} className="rounded-lg border px-3.5 py-2 text-sm">Cancelar</button><button disabled={updateClient.isPending} onClick={()=>void toggleStatus(confirm)} className="rounded-lg bg-[#2563EB] px-3.5 py-2 text-sm text-white">Confirmar</button></div></section></div>}
    {selectedId&&<ClientDetail id={selectedId} client={detailQuery.data} loading={detailQuery.isLoading} error={detailQuery.isError?getApiError(detailQuery.error):undefined} onRetry={()=>void detailQuery.refetch()} onClose={()=>setSelectedId(null)}/>}
    {notice&&<div role="status" className="fixed bottom-5 right-5 z-50 rounded-lg bg-[#1d3429] px-4 py-3 text-sm text-white shadow-lg">{notice}</div>}
  </div></main>;
}

function SummaryCard({label,value,icon,tone}:{label:string;value?:number;icon:React.ReactNode;tone:string}){const colors:Record<string,string>={green:"bg-[#eaf5ee] text-[#36845d]",blue:"bg-[#edf3fb] text-[#5577ae]",violet:"bg-[#f2effa] text-[#8170ae]"};return <div className="rounded-xl border border-[#e8ece9] bg-white p-4 sm:p-5"><div className="flex items-start justify-between"><p className="text-xs font-medium text-[#7c8781]">{label}</p><span className={`flex size-8 items-center justify-center rounded-lg ${colors[tone]}`}>{icon}</span></div><p className="mt-3 text-[25px] font-semibold leading-none">{value===undefined?"—":String(value).padStart(2,"0")}</p></div>}
function Avatar({name,large=false}:{name:string;large?:boolean}){const initials=name.split(/\s+/).slice(0,2).map((part)=>part[0]).join("");return <span className={`flex shrink-0 items-center justify-center rounded-full bg-[#e5f1e9] font-semibold text-[#43825c] ${large?"size-12 text-sm":"size-9 text-[11px]"}`}>{initials}</span>}
function StatusBadge({status}:{status:ClientStatus}){const active=status==="activo";return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-medium ${active?"bg-[#eaf5ee] text-[#37825b]":"bg-[#f0f1f1] text-[#7d8782]"}`}><span className={`size-1.5 rounded-full ${active?"bg-[#48a56e]":"bg-[#aab1ad]"}`}/>{active?"Activo":"Inactivo"}</span>}

function ClientDetail({ id, client, loading, error, onRetry, onClose }: { id: string; client?: Client; loading: boolean; error?: string; onRetry: () => void; onClose: () => void }) {
  const joinedAt = client?.created_at ? new Intl.DateTimeFormat("es-PE", { dateStyle: "medium" }).format(new Date(client.created_at)) : null;
  return <div className="fixed inset-0 z-30 flex justify-end bg-[#17211e]/35" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="flex h-full w-full max-w-[540px] flex-col overflow-y-auto bg-white shadow-2xl">
    <header className="flex items-center justify-between border-b border-[#edf0ee] px-6 py-4"><div><p className="text-[10px] font-medium uppercase tracking-[.1em] text-[#939d98]">Perfil del cliente</p><p className="mt-0.5 max-w-[360px] truncate text-xs text-[#68736d]">{id}</p></div><button onClick={onClose} className="rounded-lg p-2 text-[#7c8781]"><X size={19}/></button></header>
    {loading ? <TableSkeleton rows={5}/> : error ? <ErrorState message={error} onRetry={onRetry}/> : client ? <>
      <div className="border-b border-[#edf0ee] px-6 py-6"><div className="flex items-start gap-4"><Avatar name={client.nombre} large/><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{client.nombre}</h2><StatusBadge status={client.estado}/></div><p className="mt-1 text-xs text-[#8a958f]">{client.tipo ?? "Tipo no especificado"}{joinedAt ? ` · Cliente desde ${joinedAt}` : ""}</p></div><Link href={`/clientes/nuevo?editar=${client.id}`} className="rounded-lg border p-2 text-[#68736d]"><Pencil size={16}/></Link></div></div>
      <div className="flex-1 px-6 py-5"><h3 className="text-sm font-semibold">Información de contacto</h3><div className="mt-4 grid gap-4 sm:grid-cols-2"><InfoItem label="Documento" value={[client.tipo_documento, client.documento].filter(Boolean).join(" ") || "—"}/><InfoItem label="Contacto principal" value={client.contacto ?? "—"}/><InfoItem label="Teléfono" value={client.telefono ?? "—"}/><InfoItem label="Correo electrónico" value={client.correo ?? "—"}/><InfoItem label="Ubicación" value={client.ubicacion ?? client.departamento ?? "—"}/><InfoItem label="Dirección" value={client.direccion ?? "—"}/><InfoItem label="Nombre comercial" value={client.nombre_comercial ?? "—"}/><InfoItem label="Notas" value={client.notas ?? "—"}/></div><p className="mt-8 rounded-lg bg-[#f7f9f8] p-3 text-xs text-[#89938e]">El historial de cargas, viajes y pagos aún no está disponible en la API.</p></div>
      <footer className="sticky bottom-0 flex justify-end gap-2 border-t border-[#edf0ee] bg-white px-6 py-4"><button onClick={onClose} className="rounded-lg border px-4 py-2 text-xs">Cerrar</button><Link href={`/clientes/nuevo?editar=${client.id}`} className="rounded-lg bg-[#2563EB] px-4 py-2 text-xs font-medium text-white">Editar cliente</Link></footer>
    </> : null}
  </aside></div>;
}
function InfoItem({label,value}:{label:string;value:string}){return <div><p className="text-[10px] text-[#9aa39f]">{label}</p><p className="mt-1 break-words text-xs font-medium text-[#49564f]">{value}</p></div>}
