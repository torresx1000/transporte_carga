"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { createResourceService, type ResourceRecord } from "@/services/resource.service";

type City = { id_ciudad: number; nombre: string };
type Stop = { ciudad_id: number; orden: number; tiempo_espera: number };
const control = "mt-1 w-full rounded-lg border border-[#dce4df] bg-white px-3 py-2 text-sm";

export default function RouteEditor({ initial, loading, message, onSave, onCancel }: { initial?: ResourceRecord; loading: boolean; message: string; onSave: (values: ResourceRecord) => void; onCancel: () => void }) {
  const [values, setValues] = useState<ResourceRecord>(() => ({ codigo: "", nombre: "", origen_id: "", destino_id: "", estado: "activa", distancia_km: "", duracion_minutos: "60", peajes_minor: "0", tarifa_referencial_minor: "0", moneda: "PEN", notas: "", ...initial }));
  const [stops, setStops] = useState<Stop[]>(() => initial?.paradas ? JSON.parse(initial.paradas) : []);
  const [newCity, setNewCity] = useState("");
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const queryClient = useQueryClient();
  const cities = useQuery({ queryKey: ["ciudades"], queryFn: async () => (await api.get<City[]>("/ciudades")).data });
  const change = (key: string, value: string) => setValues(current => ({ ...current, [key]: value }));
  const cityName = (id: string | number) => cities.data?.find(city => city.id_ciudad === Number(id))?.nombre || "Selecciona ciudad";
  const cityOptions = (intermediate = false) => (cities.data ?? []).filter(city => !intermediate || ![Number(values.origen_id), Number(values.destino_id)].includes(city.id_ciudad)).map(city => <option key={city.id_ciudad} value={city.id_ciudad}>{city.nombre}</option>);

  async function addCity() {
    if (!newCity.trim() || adding) return;
    setAdding(true); setError("");
    try { await api.post("/ciudades", { nombre: newCity.trim() }); await queryClient.invalidateQueries({ queryKey: ["ciudades"] }); setNewCity(""); }
    catch (cause) { setError(getApiError(cause)); }
    finally { setAdding(false); }
  }
  function move(index: number, direction: number) {
    setStops(current => { const copy = [...current]; [copy[index], copy[index + direction]] = [copy[index + direction], copy[index]]; return copy.map((stop, i) => ({ ...stop, orden: i + 1 })); });
  }
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (values.origen_id === values.destino_id) { setError("El origen y el destino deben ser diferentes."); return; }
    if (stops.some(stop => [Number(values.origen_id), Number(values.destino_id)].includes(stop.ciudad_id))) { setError("Las paradas deben ser ciudades intermedias, distintas del origen y destino."); return; }
    onSave({ ...Object.fromEntries(Object.entries(values).filter(([key]) => ["codigo", "nombre", "origen_id", "destino_id", "estado", "distancia_km", "duracion_minutos", "peajes_minor", "tarifa_referencial_minor", "moneda", "notas"].includes(key))), paradas: JSON.stringify(stops.map((stop, i) => ({ ...stop, orden: i + 1 }))) });
  }
  function text(key: string, label: string, type = "text", required = true) { return <label className="text-sm" key={key}>{label}<input required={required} type={type} min={type === "number" ? key === "distancia_km" ? "0.01" : "0" : undefined} step={key === "distancia_km" ? "0.01" : "1"} className={control} value={values[key] ?? ""} onChange={event => change(key, event.target.value)} /></label>; }

  return <main className="min-h-screen bg-[#f7f8fa] p-6"><div className="mx-auto max-w-4xl"><button onClick={onCancel} className="mb-4 text-sm text-[#2563EB]">← Volver a rutas</button><h1 className="text-2xl font-semibold">{initial ? "Editar ruta" : "Nueva ruta"}</h1><p className="mt-2 text-sm text-[#68736d]">Origen y destino definen los extremos. Añade únicamente las ciudades intermedias como paradas.</p><form onSubmit={submit} className="mt-6 space-y-6 rounded-xl bg-white p-6"><fieldset disabled={loading || adding} className="grid gap-4 sm:grid-cols-2"><legend className="mb-4 font-semibold">Datos de la ruta</legend>
  {text("codigo", "Código")}{!initial && <button type="button" className="self-end rounded border px-3 py-2 text-sm" onClick={async () => { try { change("codigo", await createResourceService("rutas").suggestCode()); } catch (cause) { setError(getApiError(cause)); } }}>Sugerir código</button>}
  {text("nombre", "Nombre de la ruta")}
  {[ ["origen_id", "Ciudad de origen"], ["destino_id", "Ciudad de destino"] ].map(([key, label]) => <label key={key} className="text-sm">{label}<select required disabled={!cities.isSuccess} className={control} value={values[key]} onChange={event => change(key, event.target.value)}><option value="">Selecciona una ciudad</option>{cityOptions()}</select></label>)}
  {text("distancia_km", "Distancia (km)", "number")}
  <label className="text-sm">Duración estimada<div className="flex gap-2"><label className="flex-1">Horas<input aria-label="Horas de recorrido" required type="number" min="0" max="16666" className={control} value={Math.floor(Number(values.duracion_minutos) / 60)} onChange={event => change("duracion_minutos", String(Number(event.target.value) * 60 + Number(values.duracion_minutos) % 60))}/></label><label className="flex-1">Minutos<input aria-label="Minutos de recorrido" required type="number" min="0" max="59" className={control} value={Number(values.duracion_minutos) % 60} onChange={event => change("duracion_minutos", String(Math.floor(Number(values.duracion_minutos) / 60) * 60 + Number(event.target.value)))}/></label></div></label>
  <label className="text-sm">Precio base (S/)<input required type="number" min="0" step="0.01" className={control} defaultValue={(Number(values.tarifa_referencial_minor) / 100).toFixed(2)} onChange={event => change("tarifa_referencial_minor", String(Math.round(Number(event.target.value) * 100)))}/></label>
  <label className="text-sm">Peajes (S/)<input required type="number" min="0" step="0.01" className={control} defaultValue={(Number(values.peajes_minor) / 100).toFixed(2)} onChange={event => change("peajes_minor", String(Math.round(Number(event.target.value) * 100)))}/></label>
  <label className="text-sm">Estado<select className={control} value={values.estado} onChange={event => change("estado", event.target.value)}><option value="activa">Activa</option><option value="inactiva">Inactiva</option></select></label>
  </fieldset>
  <fieldset disabled={loading || adding} className="rounded-lg border p-4"><legend className="px-2 font-semibold">Ciudades disponibles</legend><div className="flex flex-wrap gap-2"><input aria-label="Nombre de nueva ciudad" maxLength={100} className={`${control} flex-1`} placeholder="Registrar una nueva ciudad" value={newCity} onChange={event => setNewCity(event.target.value)}/><button type="button" disabled={!newCity.trim() || !cities.isSuccess} onClick={() => void addCity()} className="rounded border px-3 py-2 text-sm disabled:opacity-50">{adding ? "Guardando…" : "Añadir ciudad"}</button></div>{cities.isLoading && <p className="mt-2 text-sm">Cargando ciudades…</p>}{cities.isError && <p role="alert" className="mt-2 text-sm text-red-700">{getApiError(cities.error)} <button type="button" onClick={() => void cities.refetch()} className="underline">Reintentar</button></p>}{cities.isSuccess && !cities.data.length && <p className="mt-2 text-sm">Registra las ciudades del recorrido para comenzar.</p>}</fieldset>
  <fieldset disabled={loading || adding} className="space-y-3"><legend className="mb-3 font-semibold">Paradas intermedias</legend>{stops.length === 0 && <p className="text-sm text-[#68736d]">Ruta directa, sin paradas intermedias.</p>}{stops.map((stop, index) => <div key={index} className="flex flex-wrap items-end gap-2 rounded-lg border p-3"><span className="py-2 text-sm">{index + 1}.</span><label className="min-w-40 flex-1 text-sm">Ciudad<select required className={control} value={stop.ciudad_id || ""} onChange={event => setStops(current => current.map((row, i) => i === index ? { ...row, ciudad_id: Number(event.target.value) } : row))}><option value="">Selecciona ciudad</option>{cityOptions(true)}</select></label><label className="w-32 text-sm">Espera (min)<input required type="number" min="0" step="1" className={control} value={stop.tiempo_espera} onChange={event => setStops(current => current.map((row, i) => i === index ? { ...row, tiempo_espera: Number(event.target.value) } : row))}/></label><button type="button" aria-label="Subir parada" disabled={index === 0} onClick={() => move(index, -1)} className="rounded border p-2 disabled:opacity-30">↑</button><button type="button" aria-label="Bajar parada" disabled={index === stops.length - 1} onClick={() => move(index, 1)} className="rounded border p-2 disabled:opacity-30">↓</button><button type="button" onClick={() => setStops(current => current.filter((_, i) => i !== index).map((row, i) => ({ ...row, orden: i + 1 })))} className="rounded border p-2 text-sm text-red-700">Quitar</button></div>)}<button type="button" disabled={!cities.isSuccess || stops.length >= 50} onClick={() => setStops(current => [...current, { ciudad_id: 0, orden: current.length + 1, tiempo_espera: 0 }])} className="rounded border px-3 py-2 text-sm">Añadir parada</button><p className="rounded-lg bg-[#EFF6FF] p-3 text-sm">{[cityName(values.origen_id), ...stops.map(stop => cityName(stop.ciudad_id)), cityName(values.destino_id)].join(" → ")}</p></fieldset>
  <label className="block text-sm">Notas<textarea className={control} rows={3} value={values.notas ?? ""} onChange={event => change("notas", event.target.value)}/></label>{(error || message) && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error || message}</p>}<div className="flex justify-end gap-2"><button type="button" disabled={loading} onClick={onCancel} className="rounded border px-4 py-2">Cancelar</button><button disabled={loading || adding || !cities.isSuccess} className="rounded bg-[#2563EB] px-4 py-2 text-white disabled:opacity-50">{loading ? "Guardando…" : "Guardar ruta"}</button></div></form></div></main>;
}
