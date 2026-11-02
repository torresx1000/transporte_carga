"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useResourceCreate, useResourceUpdate } from "@/hooks/useResources";
import { createResourceService, type ResourceRecord } from "@/services/resource.service";
import { getApiError } from "@/lib/api/errors";

const serviceTypes = ["Mantenimiento preventivo", "Reparación correctiva", "Neumáticos y alineación", "Sistema eléctrico", "Otros"];
const control = "mt-1 w-full rounded-lg border border-[#dce4df] bg-white px-3 py-2 text-sm";
const labels = { programado: "Programado", en_proceso: "En proceso", completado: "Completado", cancelado: "Cancelado" };

export default function MaintenanceForm({ initial, onCancel, onSaved }: { initial?: ResourceRecord | null; onCancel: () => void; onSaved: () => void }) {
  const [values, setValues] = useState<Record<string, string>>(() => ({ estado: "programado", prioridad: "normal", costo_centimos: "0", ...initial }));
  const [error, setError] = useState("");
  const create = useResourceCreate("mantenimiento");
  const update = useResourceUpdate("mantenimiento");
  const pending = create.isPending || update.isPending;
  const vehicles = useQuery({ queryKey: ["vehiculos", "maintenance-options"], queryFn: async () => {
    const service = createResourceService("vehiculos");
    const first = await service.list({ page: 1, page_size: 100 });
    const result = [...first.items];
    for (let page = 2; page <= first.pages; page++) result.push(...(await service.list({ page, page_size: 100 })).items);
    return result;
  } });
  const options = (vehicles.data ?? []).filter(vehicle => vehicle.estado !== "inactivo" || vehicle.id === initial?.vehiculo_id);
  const hasSelected = options.some(vehicle => vehicle.id === values.vehiculo_id);
  const duration = values.fecha_inicio && values.fecha_fin ? (new Date(values.fecha_fin).getTime() - new Date(values.fecha_inicio).getTime()) / 3600000 : null;
  const change = (key: string, value: string) => setValues(current => ({ ...current, [key]: value }));

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setError("");
    if (duration !== null && (!Number.isFinite(duration) || duration < 0)) { setError("El fin debe ser posterior o igual al inicio del mantenimiento."); return; }
    if (values.fecha_ingreso && values.fecha_inicio && new Date(values.fecha_inicio) < new Date(values.fecha_ingreso)) { setError("El inicio no puede ser anterior al ingreso al taller."); return; }
    const payload = { ...values };
    for (const field of ["fecha_ingreso", "fecha_inicio", "fecha_fin"]) {
      if (payload[field]) payload[field] = new Date(payload[field]).toISOString();
    }
    try {
      if (initial?.id) await update.mutateAsync({ id: initial.id, payload });
      else await create.mutateAsync(payload);
      onSaved();
    } catch (cause) { setError(getApiError(cause)); }
  }

  function input(key: string, label: string, type = "text", required = false) {
    let value = values[key] ?? "";
    if (type === "datetime-local" && value && /Z$|[+-]\d\d:\d\d$/.test(value)) {
      const date = new Date(value);
      if (!Number.isNaN(date.getTime())) value = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    }
    return <label className="text-sm" key={key}>{label}{required ? " *" : ""}<input className={control} type={type} value={value} onChange={event => change(key, event.target.value)} required={required} min={type === "number" ? (key === "duracion_estimada_horas" ? "0.01" : "0") : undefined} max={key === "duracion_estimada_horas" ? "8760" : undefined} step={key === "duracion_estimada_horas" ? "0.01" : type === "number" ? "1" : undefined} /></label>;
  }

  return <div className="fixed inset-0 z-40 overflow-y-auto bg-[#17211e]/40 p-4"><section role="dialog" aria-modal="true" aria-label="Orden de mantenimiento" className="mx-auto my-4 max-w-3xl rounded-xl bg-white p-6 shadow-xl"><h1 className="text-xl font-semibold">{initial?.id ? "Editar orden de mantenimiento" : "Nueva orden de mantenimiento"}</h1><p className="mt-1 text-sm text-[#68736d]">Selecciona el vehículo y registra el servicio y su tiempo estimado. Los campos con * son obligatorios.</p><form onSubmit={submit} className="mt-6 space-y-6"><fieldset disabled={pending} className="grid gap-4 sm:grid-cols-2">
    <legend className="mb-3 font-semibold">Vehículo y servicio</legend>
    <label className="text-sm">Vehículo *<select required className={control} value={values.vehiculo_id ?? ""} onChange={event => change("vehiculo_id", event.target.value)} disabled={vehicles.isLoading || vehicles.isError}><option value="">{vehicles.isLoading ? "Cargando vehículos…" : "Selecciona un vehículo"}</option>{initial?.vehiculo_id && !hasSelected && <option value={initial.vehiculo_id}>{initial.vehiculo_placa || initial.vehiculo_id} (vehículo actual)</option>}{options.map(vehicle => <option key={vehicle.id} value={vehicle.id}>{vehicle.placa} · {vehicle.codigo_flota || vehicle.tipo || "Vehículo"}</option>)}</select></label>
    <label className="text-sm">Tipo de servicio *<select required className={control} value={values.tipo ?? ""} onChange={event => change("tipo", event.target.value)}><option value="">Selecciona un servicio</option>{values.tipo && !serviceTypes.includes(values.tipo) && <option>{values.tipo}</option>}{serviceTypes.map(type => <option key={type}>{type}</option>)}</select></label>
    {vehicles.isError && <div role="alert" className="text-sm text-red-700 sm:col-span-2">{getApiError(vehicles.error)} <button type="button" className="underline" onClick={() => void vehicles.refetch()}>Reintentar</button></div>}
    {vehicles.isSuccess && options.length === 0 && <p className="text-sm text-amber-800 sm:col-span-2">No hay vehículos activos. Registra o activa un vehículo para crear la orden.</p>}
    {input("kilometraje", "Kilometraje de ingreso (km)", "number")}
    <label className="text-sm">Prioridad<select className={control} value={values.prioridad} onChange={event => change("prioridad", event.target.value)}>{["baja", "normal", "alta", "urgente"].map(value => <option key={value}>{value}</option>)}</select></label>
    </fieldset><fieldset disabled={pending} className="grid gap-4 sm:grid-cols-2"><legend className="mb-3 font-semibold">Tiempo de mantenimiento</legend>
    {input("duracion_estimada_horas", "Duración estimada (horas)", "number", true)}
    {input("fecha_programada", "Fecha programada", "date")}
    {input("fecha_ingreso", "Ingreso al taller", "datetime-local")}
    {input("fecha_inicio", "Inicio del trabajo", "datetime-local")}
    {input("fecha_fin", "Fin del trabajo", "datetime-local")}
    <div className="rounded-lg bg-[#EFF6FF] p-3 text-sm"><p>Duración real</p><strong>{duration !== null && duration >= 0 ? `${duration.toLocaleString("es-PE", { maximumFractionDigits: 2 })} horas` : "Se calcula al registrar inicio y fin"}</strong></div>
    </fieldset><fieldset disabled={pending} className="grid gap-4 sm:grid-cols-2"><legend className="mb-3 font-semibold">Detalle de la orden</legend>
    {[ ["descripcion", "Motivo / descripción del servicio"], ["diagnostico", "Diagnóstico"], ["trabajo_realizado", "Trabajo realizado"], ["observaciones", "Observaciones"] ].map(([key, label]) => <label key={key} className="text-sm sm:col-span-2">{label}<textarea rows={2} className={control} value={values[key] ?? ""} onChange={event => change(key, event.target.value)} /></label>)}
    {input("costo_centimos", "Costo total (céntimos PEN)", "number")}
    <label className="text-sm">Estado<select className={control} value={values.estado} onChange={event => change("estado", event.target.value)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    </fieldset>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<footer className="flex justify-end gap-3 border-t pt-4"><button type="button" disabled={pending} onClick={onCancel} className="rounded-lg border px-4 py-2 text-sm">Cancelar</button><button type="submit" disabled={pending || vehicles.isLoading || vehicles.isError || !values.vehiculo_id} className="rounded-lg bg-[#2563EB] px-4 py-2 text-sm text-white disabled:opacity-50">{pending ? "Guardando…" : initial?.id ? "Guardar cambios" : "Crear orden"}</button></footer></form></section></div>;
}
