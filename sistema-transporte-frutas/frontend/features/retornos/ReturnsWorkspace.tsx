"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw, Search } from "lucide-react";
import Swal from "sweetalert2";
import { Load, Trip, useCatalog } from "@/features/transporte/data";
import { useResourceList } from "@/hooks/useResources";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";
import { useAuthStore } from "@/lib/auth/authStore";

type Client = { id: string; nombre: string; name?: string };
type ReturnRecord = { id: string; created_at?: string; data?: Record<string, unknown>; [key: string]: unknown };
type ClientBalance = {
  cliente_id: string;
  total_despachadas: number;
  total_retornadas: number;
  saldo_pendiente: number;
  periodo_id: string | null;
};
type BalanceCut = {
  id: string;
  cliente_id: string;
  numero_corte: number;
  cliente_nombre: string;
  total_despachadas: number;
  total_retornadas: number;
  saldo_pendiente: number;
  fecha: string;
  usuario_email: string;
};
const input = "mt-1 w-full rounded-lg border border-[#dce4df] bg-white px-3 py-2 text-sm";

export default function ReturnsWorkspace({ initialForm = false }: { initialForm?: boolean }) {
  const router = useRouter();
  const clients = useCatalog<Client>("clientes");
  const loads = useCatalog<Load>("cargas");
  const trips = useCatalog<Trip>("viajes");
  const history = useResourceList("retornos", { page: 1, page_size: 100 });
  const balances = useQuery({
    queryKey: ["retornos", "saldos-por-cliente"],
    queryFn: async () => (await api.get<ClientBalance[]>("/retornos/saldos-por-cliente")).data,
  });
  const cuts = useQuery({
    queryKey: ["retornos", "historial-cortes"],
    queryFn: async () =>
      (await api.get<BalanceCut[]>("/retornos/historial-cortes", { params: { limit: 100 } })).data,
  });
  const cache = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const [clientId, setClientId] = useState("");
  const [loadId, setLoadId] = useState("");
  const [tripId, setTripId] = useState("");
  const [box3, setBox3] = useState(0);
  const [box2, setBox2] = useState(0);
  const [loose, setLoose] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [cuttingClientId, setCuttingClientId] = useState("");

  const activePeriodId = balances.data?.find((balance) => balance.cliente_id === clientId)?.periodo_id ?? null;
  const clientLoads = (loads.data ?? []).filter(
    (load) =>
      load.cliente_id === clientId &&
      String(load.periodo_retorno_id ?? "") === String(activePeriodId ?? ""),
  );
  const selectedLoad = clientLoads.find((load) => load.id === loadId);
  const linkedTripIds = new Set([
    ...(selectedLoad?.viaje_id ? [selectedLoad.viaje_id] : []),
    ...(selectedLoad?.etapas ?? []).map((stage) => stage.viaje_id),
    ...(trips.data ?? []).filter((trip) => trip.cargas_ids.includes(loadId) || trip.etapas.some((stage) => stage.carga_id === loadId)).map((trip) => trip.id),
  ]);
  const linkedTrips = (trips.data ?? []).filter((trip) => linkedTripIds.has(trip.id));
  const dispatched = Number(selectedLoad?.jabas_despachadas ?? 0);
  const returned = box3 * 3 + box2 * 2 + loose;
  const difference = returned - dispatched;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    try {
      await api.post("/retornos", { data: {
        cliente_id: clientId,
        carga_id: loadId,
        viaje_id: tripId,
        paquetes_3: box3,
        paquetes_2: box2,
        sueltas: loose,
        observaciones: String(form.get("observaciones") ?? "").trim(),
      } });
      await Promise.all([cache.invalidateQueries({ queryKey: ["retornos"] }), cache.invalidateQueries({ queryKey: ["clientes"] })]);
      if (initialForm) router.push("/retornos");
      else { setClientId(""); setLoadId(""); setTripId(""); setBox3(0); setBox2(0); setLoose(0); (event.currentTarget as HTMLFormElement).reset(); }
    } catch (cause) { setError(getApiError(cause)); }
    finally { setBusy(false); }
  }

  async function resetClientBalance(client: Client) {
    const confirmation = await Swal.fire({
      title: "¿Reiniciar saldo?",
      text: `${client.nombre}: se guardará el saldo actual y comenzará un nuevo periodo.`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Reiniciar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#2563EB",
    });
    if (!confirmation.isConfirmed) return;

    setCuttingClientId(client.id);
    try {
      await api.post(`/retornos/clientes/${encodeURIComponent(client.id)}/reiniciar-saldo`);
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["retornos", "saldos-por-cliente"] }),
        cache.invalidateQueries({ queryKey: ["retornos", "historial-cortes"] }),
        cache.invalidateQueries({ queryKey: ["cargas", "transport-catalog"] }),
      ]);
      await Swal.fire({
        title: "Saldo reiniciado",
        text: "Nuevo periodo iniciado.",
        icon: "success",
        confirmButtonColor: "#2563EB",
        timer: 1800,
        showConfirmButton: false,
      });
    } catch (cause) {
      await Swal.fire({
        title: "No se pudo reiniciar",
        text: getApiError(cause),
        icon: "error",
        confirmButtonColor: "#2563EB",
      });
    } finally {
      setCuttingClientId("");
    }
  }

  const records = (history.data?.items ?? []) as unknown as ReturnRecord[];
  const filtered = records.filter((record) => {
    const data = record.data ?? record;
    const client = clients.data?.find((item) => item.id === String(data.cliente_id ?? ""));
    const load = loads.data?.find((item) => item.id === String(data.carga_id ?? ""));
    const trip = trips.data?.find((item) => item.id === String(data.viaje_id ?? ""));
    return [client?.nombre, load?.codigo, trip?.codigo, data.total_jabas_retornadas, data.observaciones, record.created_at]
      .some((value) => String(value ?? "").toLocaleLowerCase("es-PE").includes(search.trim().toLocaleLowerCase("es-PE")));
  });

  if (initialForm) return <main className="min-h-screen bg-[#f7f8fa] p-6 text-[#17211e]"><div className="mx-auto max-w-3xl"><Link href="/retornos" className="text-sm text-[#2563EB]">← Retornos</Link><h1 className="mt-4 text-2xl font-semibold">Registrar retorno</h1><p className="mt-1 text-sm text-gray-600">Selecciona cliente, carga y viaje; compara las jabas retornadas con las despachadas del periodo actual.</p>{returnForm({ clients: clients.data ?? [], loads: clientLoads, trips: linkedTrips, clientId, setClientId, loadId, setLoadId, tripId, setTripId, box3, setBox3, box2, setBox2, loose, setLoose, dispatched, returned, difference, busy, error, submit, balanceLoading: balances.isLoading, balanceError: balances.isError ? getApiError(balances.error) : "" })}</div></main>;

  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8"><div className="mx-auto max-w-6xl"><header className="mb-6 flex justify-between gap-4"><div><h1 className="text-2xl font-semibold">Retornos</h1><p className="mt-1 text-sm text-gray-600">Registra y revisa las jabas que regresan de las cargas.</p></div><Link href="/retornos/nuevo" className="shrink-0 rounded bg-[#2563EB] px-4 py-2 text-sm text-white">Registrar retorno</Link></header>
    {history.isLoading ? <TableSkeleton/> : history.isError ? <ErrorState message={getApiError(history.error)} onRetry={()=>void history.refetch()}/> : <section className="overflow-hidden rounded-xl border bg-white p-5"><div className="mb-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><h2 className="font-semibold">Historial de retornos</h2><p className="mt-1 text-xs text-gray-500">{filtered.length} registros</p></div><label className="relative block w-full sm:max-w-sm"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/><input type="search" value={search} onChange={(event)=>setSearch(event.target.value)} placeholder="Buscar cliente, carga o viaje…" className="h-10 w-full rounded-lg border border-gray-300 pl-9 pr-3 text-sm outline-none focus:border-[#2563EB]"/></label></div><div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead><tr>{["Fecha de registro","Cliente","Carga","Viaje","Jabas retornadas","Semáforo"].map((label)=><th key={label} className="border-b p-3">{label}</th>)}</tr></thead><tbody>{filtered.map((record)=>{const data=record.data??record;const client=clients.data?.find((item)=>item.id===String(data.cliente_id??""));const load=loads.data?.find((item)=>item.id===String(data.carga_id??""));const trip=trips.data?.find((item)=>item.id===String(data.viaje_id??""));const returnedCount=Number(data.total_jabas_retornadas??(Number(data.paquetes_3??0)*3+Number(data.paquetes_2??0)*2+Number(data.sueltas??0)));const dispatchedCount=Number(load?.jabas_despachadas??0);const additional=returnedCount-dispatchedCount;const signal=additional<0?{label:`Faltan ${Math.abs(additional)}`,className:"bg-red-100 text-red-800"}:additional===0?{label:"Igual",className:"bg-orange-100 text-orange-800"}:{label:`Adicional +${additional}`,className:"bg-emerald-100 text-emerald-800"};return <tr key={record.id} className="border-b"><td className="p-3">{record.created_at?new Date(record.created_at).toLocaleString("es-PE"):"—"}</td><td className="p-3">{client?.nombre??String(data.cliente_id??"—")}</td><td className="p-3">{load?.codigo??String(data.carga_id??"—")}</td><td className="p-3">{trip?.codigo??String(data.viaje_id??"—")}</td><td className="p-3">{returnedCount} / {dispatchedCount}</td><td className="p-3"><span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${signal.className}`}><span className="size-2 rounded-full bg-current"/>{signal.label}</span></td></tr>})}</tbody></table>{!filtered.length&&<p className="py-5 text-center text-sm text-gray-500">{search?"No se encontraron retornos con esa búsqueda.":"Todavía no hay retornos registrados."}</p>}</div></section>}<ClientReturnSummary clients={clients.data??[]} balances={balances} cuts={cuts} canReset={user?.role==="admin"} resetBusyId={cuttingClientId} onReset={resetClientBalance} onRetryBalances={()=>void balances.refetch()} onRetryCuts={()=>void cuts.refetch()}/></div></main>;
}

function ClientReturnSummary({
  clients,
  balances,
  cuts,
  canReset,
  resetBusyId,
  onReset,
  onRetryBalances,
  onRetryCuts,
}: {
  clients: Client[];
  balances: ReturnType<typeof useQuery<ClientBalance[]>>;
  cuts: ReturnType<typeof useQuery<BalanceCut[]>>;
  canReset: boolean;
  resetBusyId: string;
  onReset: (client: Client) => void;
  onRetryBalances: () => void;
  onRetryCuts: () => void;
}) {
  if (balances.isLoading) return <section className="mt-6"><TableSkeleton rows={2}/></section>;
  if (balances.isError) return <section className="mt-6"><ErrorState message={getApiError(balances.error)} onRetry={onRetryBalances}/></section>;
  const rows = balances.data ?? [];
  return (
    <>
      <section className="mt-6">
        <div className="mb-3">
          <h2 className="font-semibold">Saldo actual de jabas por cliente</h2>
          <p className="mt-1 text-xs text-gray-500">El saldo empieza desde el último corte registrado para cada cliente.</p>
        </div>
        {!rows.length ? (
          <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
            No hay cargas ni retornos registrados para mostrar.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {rows.map((row) => {
              const returned = row.total_retornadas;
              const difference = returned - row.total_despachadas;
              const status = difference < 0
                ? { text: `Faltan ${Math.abs(difference)} jabas`, color: "border-red-200 bg-red-50 text-red-800", dot: "bg-red-600" }
                : difference === 0
                  ? { text: "Cantidad completa", color: "border-orange-200 bg-orange-50 text-orange-800", dot: "bg-orange-500" }
                  : { text: `Adicional +${difference} jabas`, color: "border-emerald-200 bg-emerald-50 text-emerald-800", dot: "bg-emerald-600" };
              const client = clients.find((item) => item.id === row.cliente_id);
              return (
                <article key={row.cliente_id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <h3 className="font-semibold">{client?.nombre ?? row.cliente_id}</h3>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg bg-gray-50 p-3">
                      <p className="text-xs text-gray-500">Jabas despachadas</p>
                      <p className="mt-1 text-lg font-semibold">{row.total_despachadas}</p>
                    </div>
                    <div className="rounded-lg bg-gray-50 p-3">
                      <p className="text-xs text-gray-500">Jabas retornadas</p>
                      <p className="mt-1 text-lg font-semibold">{returned}</p>
                    </div>
                  </div>
                  <div className={`mt-3 flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold ${status.color}`}>
                    <span className={`size-2.5 rounded-full ${status.dot}`}/>{status.text}
                  </div>
                  {row.periodo_id && (
                    <p className="mt-2 text-[11px] text-gray-500">
                      Periodo iniciado luego del último reinicio; las cargas anteriores no se cuentan.
                    </p>
                  )}
                  {canReset && (
                    <button
                      type="button"
                      disabled={resetBusyId === row.cliente_id || (row.total_despachadas === 0 && returned === 0)}
                      onClick={() => onReset(client ?? { id: row.cliente_id, nombre: row.cliente_id })}
                      className="mt-4 inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <RotateCcw size={14}/>
                      {resetBusyId === row.cliente_id ? "Guardando corte…" : "Reiniciar saldo"}
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
      <section className="mt-7 overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="border-b border-gray-100 px-5 py-4">
          <h2 className="font-semibold">Historial de reinicios</h2>
          <p className="mt-1 text-xs text-gray-500">Cortes guardados para auditoría; los movimientos originales no se eliminan.</p>
        </div>
        {cuts.isLoading ? (
          <div className="p-5"><TableSkeleton rows={2}/></div>
        ) : cuts.isError ? (
          <div className="p-5"><ErrorState message={getApiError(cuts.error)} onRetry={onRetryCuts}/></div>
        ) : !cuts.data?.length ? (
          <p className="p-6 text-center text-sm text-gray-500">Todavía no se ha reiniciado ningún saldo.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>{["Corte", "Fecha", "Cliente", "Jabas despachadas", "Jabas retornadas", "Saldo anterior", "Registrado por"].map((label) => <th key={label} className="px-4 py-3">{label}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {cuts.data.map((cut) => (
                  <tr key={cut.id}>
                    <td className="px-4 py-3 font-medium">#{cut.numero_corte}</td>
                    <td className="whitespace-nowrap px-4 py-3">{new Date(cut.fecha).toLocaleString("es-PE")}</td>
                    <td className="px-4 py-3 font-medium">{cut.cliente_nombre}</td>
                    <td className="px-4 py-3">{cut.total_despachadas}</td>
                    <td className="px-4 py-3">{cut.total_retornadas}</td>
                    <td className="px-4 py-3">{cut.saldo_pendiente}</td>
                    <td className="px-4 py-3">{cut.usuario_email}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

type ReturnFormProps = {
  clients: Client[]; loads: Load[]; trips: Trip[]; clientId: string; setClientId: (value: string) => void;
  loadId: string; setLoadId: (value: string) => void; tripId: string; setTripId: (value: string) => void;
  box3: number; setBox3: (value: number) => void; box2: number; setBox2: (value: number) => void;
  loose: number; setLoose: (value: number) => void; dispatched: number; returned: number; difference: number;
  busy: boolean; error: string; submit: (event: React.FormEvent<HTMLFormElement>) => void;
  balanceLoading: boolean; balanceError: string;
};
function returnForm(props: ReturnFormProps) {
  const { clients, loads, trips, clientId, setClientId, loadId, setLoadId, tripId, setTripId, box3, setBox3, box2, setBox2, loose, setLoose, dispatched, returned, difference, busy, error, submit, balanceLoading, balanceError } = props;
  const comparison = !loadId ? "Selecciona una carga para comparar." : difference === 0 ? "Se retornó la misma cantidad que se despachó." : difference > 0 ? `Adicional +${difference}: se están trayendo jabas de más.` : `Adicional ${difference}: faltan ${Math.abs(difference)} jabas por retornar.`;
  return <form onSubmit={submit} className="mt-5 space-y-5 rounded-xl border bg-white p-5"><fieldset disabled={busy || balanceLoading || Boolean(balanceError)} className="grid gap-4 sm:grid-cols-2"><label className="text-sm">Cliente *<select required value={clientId} onChange={(event)=>{setClientId(event.target.value);setLoadId("");setTripId("");}} className={input}><option value="">Selecciona un cliente</option>{clients.map((client)=><option key={client.id} value={client.id}>{client.nombre}</option>)}</select></label><label className="text-sm">Carga *<select required value={loadId} disabled={!clientId} onChange={(event)=>{setLoadId(event.target.value);setTripId("");}} className={input}><option value="">{clientId?(balanceLoading?"Consultando periodo…":loads.length?"Selecciona una carga nueva":"No hay cargas nuevas en este periodo"):"Selecciona primero un cliente"}</option>{loads.map((load)=><option key={load.id} value={load.id}>{load.codigo} · {load.producto} · {load.jabas_despachadas} jabas</option>)}</select></label><label className="text-sm">Viaje *<select required value={tripId} disabled={!loadId} onChange={(event)=>setTripId(event.target.value)} className={input}><option value="">{loadId?"Selecciona el viaje vinculado":"Selecciona primero una carga"}</option>{trips.map((trip)=><option key={trip.id} value={trip.id}>{trip.codigo} · {trip.estado}</option>)}</select>{loadId&&!trips.length&&<span className="mt-1 block text-xs text-amber-700">Esta carga no tiene un viaje vinculado.</span>}</label><div className="rounded-lg bg-blue-50 p-3 text-sm"><span className="text-gray-600">Jabas despachadas</span><strong className="ml-2 text-blue-900">{dispatched}</strong></div></fieldset>{balanceLoading&&<p className="rounded bg-blue-50 p-3 text-sm text-blue-800">Cargando el periodo actual de jabas…</p>}{balanceError&&<p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{balanceError}</p>}<section className="rounded-lg border p-4"><h2 className="font-semibold">Jabas retornadas</h2><p className="mt-1 text-xs text-gray-500">Ingresa cuántos paquetes de cada tamaño llegaron.</p><div className="mt-4 grid gap-4 sm:grid-cols-3"><label className="text-sm">Paquetes de 3 jabas<input disabled={balanceLoading||Boolean(balanceError)} type="number" min="0" step="1" value={box3} onChange={(event)=>setBox3(Number(event.target.value))} className={input}/></label><label className="text-sm">Paquetes de 2 jabas<input disabled={balanceLoading||Boolean(balanceError)} type="number" min="0" step="1" value={box2} onChange={(event)=>setBox2(Number(event.target.value))} className={input}/></label><label className="text-sm">Jabas sueltas<input disabled={balanceLoading||Boolean(balanceError)} type="number" min="0" step="1" value={loose} onChange={(event)=>setLoose(Number(event.target.value))} className={input}/></label></div><div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-gray-50 p-3 text-sm"><span>Total retornadas: <strong>{returned}</strong></span><span>Adicional (retornadas − despachadas): <strong>{difference>0?`+${difference}`:difference}</strong></span><span className={difference>0?"font-semibold text-amber-700":difference<0?"font-semibold text-red-700":"font-semibold text-emerald-700"}>{comparison}</span></div></section><label className="block text-sm">Observaciones<textarea disabled={balanceLoading||Boolean(balanceError)} name="observaciones" rows={3} className={input} placeholder="Opcional"/></label>{error&&<p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="flex justify-end gap-2"><Link href="/retornos" className="rounded border px-4 py-2 text-sm">Cancelar</Link><button disabled={busy||balanceLoading||Boolean(balanceError)||!clients.length||!loads.length||!trips.length} className="rounded bg-[#2563EB] px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy?"Guardando…":"Guardar retorno"}</button></div></form>;
}
