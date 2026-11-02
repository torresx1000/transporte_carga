"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Paperclip, Download } from "lucide-react";
import { useCatalog, Trip, Person, control } from "@/features/transporte/data";
import { useResourceList } from "@/hooks/useResources";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";

type Fueling = { id: string; created_at?: string; data?: Record<string, unknown>; [key: string]: unknown };
type FuelDocument = { id: string; nombre: string; tamano: number };
const input = `${control} mt-1`;
const localDate = () => { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`; };

export default function FuelingWorkspace({ initialForm = false }: { initialForm?: boolean }) {
  const router = useRouter();
  const trips = useCatalog<Trip>("viajes");
  const vehicles = useCatalog<Person>("vehiculos");
  const query = useResourceList("combustible", { page: 1, page_size: 100 });
  const cache = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedTripId, setSelectedTripId] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const trip = trips.data?.find((item) => item.id === String(form.get("viaje_id")));
    if (!trip?.vehiculo_id) { setError("Selecciona un viaje que tenga un vehículo asignado."); setBusy(false); return; }
    const liters = Number(form.get("liters"));
    const price = Number(form.get("price"));
    const data = {
      viaje_id: trip.id,
      vehiculo_id: trip.vehiculo_id,
      litros_milesimas: Math.round(liters * 1000),
      precio_centimos: Math.round(price * 100),
      odometro: Number(form.get("odometer") || 0),
      fecha_consumo: String(form.get("fecha_consumo")),
    };
    const files = form.getAll("archivo").filter((item): item is File => item instanceof File && item.size > 0);
    try {
      const record = (await api.post<Fueling>("/combustible", { data })).data;
      for (const file of files) {
        const upload = new FormData(); upload.append("archivo", file);
        await api.post(`/combustible/${record.id}/documentos`, upload, { headers: { "Content-Type": "multipart/form-data" } });
      }
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["combustible"] }),
        cache.invalidateQueries({ queryKey: ["reportes"] }),
      ]);
      if (initialForm) router.push("/combustible");
      else { formElement.reset(); setSelectedTripId(""); }
    } catch (cause) {
      setError(getApiError(cause));
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["combustible"] }),
        cache.invalidateQueries({ queryKey: ["reportes"] }),
      ]);
    } finally { setBusy(false); }
  }

  const rows = (query.data?.items ?? []) as unknown as Fueling[];
  const tripsList = trips.data ?? [];
  const vehiclesList = vehicles.data ?? [];
  const filtered = rows.filter((row) => {
    const data = row.data ?? row;
    const vehicleId = String(data.vehiculo_id ?? "");
    const vehicle = vehiclesList.find((item) => item.id === vehicleId);
    return [data.fecha_consumo, data.viaje_id, tripsList.find((trip)=>trip.id===data.viaje_id)?.codigo, data.vehiculo_id, vehicle?.placa, data.litros_milesimas, data.precio_centimos, data.odometro]
      .some((value) => String(value ?? "").toLocaleLowerCase("es-PE").includes(search.trim().toLocaleLowerCase("es-PE")));
  });

  if (initialForm) return <main className="min-h-screen bg-[#f7f8fa] p-6 text-[#17211e]"><div className="mx-auto max-w-3xl"><Link href="/combustible" className="text-sm text-[#2563EB]">← Combustible</Link><h1 className="mt-4 text-2xl font-semibold">Combustible · Nuevo registro</h1><p className="mt-1 text-sm text-gray-600">Asigna cada abastecimiento al viaje para sumar el costo al reporte del camión. El vehículo se toma del viaje.</p>{fuelForm(tripsList, vehiclesList, selectedTripId, setSelectedTripId, busy, error, submit)}</div></main>;

  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8"><div className="mx-auto max-w-6xl"><header className="mb-6 flex justify-between gap-4"><div><h1 className="text-2xl font-semibold">Combustible</h1><p className="mt-1 text-sm text-gray-600">Cada abastecimiento queda asociado al viaje y al vehículo asignado.</p></div><Link href="/combustible/nuevo" className="shrink-0 rounded bg-[#2563EB] px-4 py-2 text-sm text-white">Nuevo registro</Link></header>
    {query.isLoading ? <TableSkeleton/> : query.isError ? <ErrorState message={getApiError(query.error)} onRetry={()=>void query.refetch()}/> : <section className="overflow-hidden rounded-xl border bg-white p-5"><div className="mb-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><h2 className="font-semibold">Registros de consumo</h2><p className="mt-1 text-xs text-gray-500">{filtered.length} registros</p></div><label className="relative block w-full sm:max-w-sm"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/><input type="search" value={search} onChange={(event)=>setSearch(event.target.value)} placeholder="Buscar vehículo o fecha…" className="h-10 w-full rounded-lg border border-gray-300 pl-9 pr-3 text-sm outline-none focus:border-[#2563EB]"/></label></div><div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead><tr>{["Fecha de registro","Viaje","Vehículo","Fecha de consumo","Litros","Costo","Odómetro","Archivos"].map(label=><th key={label} className="border-b p-3">{label}</th>)}</tr></thead><tbody>{filtered.map((row)=>{const data=row.data??row;const vehicleId=String(data.vehiculo_id??"");const vehicle=vehiclesList.find((item)=>item.id===vehicleId);return <tr key={row.id} className="border-b"><td className="p-3">{row.created_at?new Date(row.created_at).toLocaleString("es-PE"):"—"}</td><td className="p-3">{tripsList.find((trip)=>trip.id===data.viaje_id)?.codigo||"—"}</td><td className="p-3">{vehicle?.placa||vehicleId||"—"}</td><td className="p-3">{formatDate(String(data.fecha_consumo??""))}</td><td className="p-3">{(Number(data.litros_milesimas??0)/1000).toLocaleString("es-PE",{maximumFractionDigits:3})} L</td><td className="p-3">S/ {(Number(data.precio_centimos??0)/100).toFixed(2)}</td><td className="p-3">{String(data.odometro??"—")} km</td><td className="p-3"><FuelingFiles id={row.id}/></td></tr>})}</tbody></table>{!filtered.length&&<p className="py-5 text-center text-sm text-gray-500">{search?"No se encontraron registros con esa búsqueda.":"Todavía no hay consumos registrados."}</p>}</div></section>}</div></main>;
}

function fuelForm(trips: Trip[], vehicles: Person[], selectedTripId: string, setSelectedTripId: (id: string) => void, busy: boolean, error: string, submit: (event: React.FormEvent<HTMLFormElement>) => void) {
  const selectedTrip = trips.find((trip) => trip.id === selectedTripId);
  const selectedVehicle = vehicles.find((vehicle) => vehicle.id === selectedTrip?.vehiculo_id);
  return <form onSubmit={submit} className="mt-5 grid gap-4 rounded-xl border bg-white p-5 sm:grid-cols-2"><label className="text-sm">Viaje *<select required name="viaje_id" value={selectedTripId} onChange={(event)=>setSelectedTripId(event.target.value)} className={input}><option value="">Selecciona el viaje del abastecimiento</option>{trips.filter((trip)=>trip.vehiculo_id).map((trip)=><option key={trip.id} value={trip.id}>{trip.codigo} · {trip.estado}</option>)}</select></label><label className="text-sm">Vehículo<input readOnly value={selectedVehicle?.placa||"Se completa desde el viaje"} className={`${input} bg-gray-50`}/></label><label className="text-sm">Fecha de registro<input readOnly value={new Date().toLocaleString("es-PE")} className={`${input} bg-gray-50`}/></label><label className="text-sm">Fecha de consumo *<input required type="date" name="fecha_consumo" defaultValue={localDate()} className={input}/></label><label className="text-sm">Cantidad (litros) *<input required type="number" min="0.001" step="0.001" name="liters" placeholder="0.000" className={input}/></label><label className="text-sm">Costo total (S/) *<input required type="number" min="0.01" step="0.01" name="price" placeholder="0.00" className={input}/></label><label className="text-sm">Odómetro (km)<input type="number" min="0" step="1" name="odometer" placeholder="Opcional" className={input}/></label><label className="text-sm sm:col-span-2">Comprobante o archivo (hasta 10 MB cada uno)<input type="file" multiple name="archivo" accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xlsx" className="mt-2 block w-full rounded-lg border p-2 text-sm"/><span className="mt-1 block text-xs text-gray-500">PDF, imágenes, DOC/DOCX o XLSX.</span></label>{error&&<p role="alert" className="sm:col-span-2 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={busy||!trips.some((trip)=>trip.vehiculo_id)} className="rounded bg-[#2563EB] px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50 sm:col-span-2">{busy?"Guardando…":"Guardar registro"}</button></form>;
}

function FuelingFiles({id}:{id:string}) {
  const [open, setOpen] = useState(false);
  const docs = useQuery({ queryKey: ["combustible", "documentos", id], queryFn: async () => (await api.get<FuelDocument[]>(`/combustible/${id}/documentos`)).data, enabled: open });
  async function download(doc: FuelDocument) { const response = await api.get(`/combustible/${id}/documentos/${doc.id}/archivo`, { responseType: "blob" }); const url = URL.createObjectURL(response.data); const link = document.createElement("a"); link.href = url; link.download = doc.nombre; link.click(); URL.revokeObjectURL(url); }
  return <div><button type="button" onClick={()=>setOpen(!open)} className="inline-flex items-center gap-1 text-xs text-[#2563EB] underline"><Paperclip size={13}/>{open?"Ocultar":"Ver archivos"}</button>{open&&(docs.isLoading?<p className="mt-1 text-xs text-gray-500">Cargando…</p>:docs.isError?<p className="mt-1 text-xs text-red-700">No se pudieron cargar los archivos.</p>:docs.data?.length?<ul className="mt-2 space-y-1">{docs.data.map((doc)=><li key={doc.id}><button type="button" onClick={()=>void download(doc)} className="inline-flex items-center gap-1 text-xs text-gray-600 hover:text-[#2563EB]"><Download size={12}/>{doc.nombre}</button></li>)}</ul>:<p className="mt-1 text-xs text-gray-500">Sin archivos</p>)}</div>;
}

function formatDate(value: string) { if (!value) return "—"; const match=value.match(/^(\d{4})-(\d{2})-(\d{2})$/); return match ? new Date(Number(match[1]),Number(match[2])-1,Number(match[3])).toLocaleDateString("es-PE") : new Date(value).toLocaleDateString("es-PE"); }
