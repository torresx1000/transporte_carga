"use client";

import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, Check, ChevronDown, Eye, FileDown, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { exportRoutePdf, exportRoutesPdf, exportVehiclesPdf } from "@/features/export/record-pdf";
import { useAuth } from "@/lib/auth/useAuth";
import { getApiError, getApiFieldErrors } from "@/lib/api/errors";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";
import { useResourceCreate, useResourceDelete, useResourceDetail, useResourceList, useResourceReactivate, useResourceUpdate } from "@/hooks/useResources";
import { createResourceService, type ResourceRecord } from "@/services/resource.service";
import { resourceConfigs, type ResourceConfig, type ResourceField, type ResourceKey } from "@/features/operaciones/resource-config";

import RouteEditor from "@/features/rutas/RouteEditor";

const PAGE_SIZE = 20;
const controlClass = "h-10 w-full rounded-lg border border-[#e5eae6] bg-white px-3 text-sm text-[#47534d] outline-none placeholder:text-[#a8b0ac] focus:border-[#2563EB] focus:ring-2 focus:ring-[#DBEAFE]";
const allStates = "Todos los estados";

export default function SchemaResourceWorkspace(props: { resource: Extract<ResourceKey, "conductores" | "vehiculos" | "rutas">; initialForm?: boolean; editId?: string }) { return <Suspense fallback={<TableSkeleton/>}><SchemaResourceContent {...props}/></Suspense>; }

function SchemaResourceContent({ resource, initialForm = false, editId: suppliedEditId = "" }: { resource: Extract<ResourceKey, "conductores" | "vehiculos" | "rutas">; initialForm?: boolean; editId?: string }) {
  const searchParams = useSearchParams();
  const editId = suppliedEditId || searchParams.get("editar") || "";
  const config = resourceConfigs[resource];
  const router = useRouter();
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState("");
  const [confirmId, setConfirmId] = useState("");
  const [message, setMessage] = useState("");
  const [exporting, setExporting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [archivedId, setArchivedId] = useState("");
  const listParams = useMemo(() => ({
    page,
    page_size: PAGE_SIZE,
    q: query.trim() || undefined,
    estado: status || undefined,
    tipo: type || undefined,
  }), [page, query, status, type]);
  const listQuery = useResourceList(resource, listParams);
  const detailQuery = useResourceDetail(resource, selectedId);
  const editQuery = useResourceDetail(resource, editId);
  const createMutation = useResourceCreate(resource);
  const updateMutation = useResourceUpdate(resource);
  const deleteMutation = useResourceDelete(resource);
  const reactivateMutation = useResourceReactivate(resource);
  const rows = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const pages = Math.max(1, listQuery.data?.pages ?? Math.ceil(total / PAGE_SIZE));

  function changeFilters(change: () => void) {
    change();
    setPage(1);
  }

  async function exportCatalog() {
    if (resource !== "rutas" && resource !== "vehiculos") return;
    setExporting(true);
    setMessage("");
    const params = {
      page: 1,
      page_size: 100,
      q: query.trim() || undefined,
      estado: status || undefined,
      tipo: resource === "vehiculos" ? type || undefined : undefined,
    };
    try {
      const service = createResourceService(resource);
      const firstPage = await service.list(params);
      const records = [...firstPage.items];
      for (let currentPage = 2; currentPage <= firstPage.pages; currentPage += 1) {
        const nextPage = await service.list({ ...params, page: currentPage });
        records.push(...nextPage.items);
      }
      if (records.length === 0) {
        setMessage("No hay registros que coincidan con los filtros para exportar.");
      } else if (resource === "rutas") {
        exportRoutesPdf(records);
      } else {
        exportVehiclesPdf(records);
      }
    } catch (error) {
      setMessage(getApiError(error));
    } finally {
      setExporting(false);
    }
  }

  function editRecord(id: string) {
    router.push(`/${resource}/${resource === "rutas" ? "nueva" : "nuevo"}?editar=${encodeURIComponent(id)}`);
  }

  async function save(values: ResourceRecord) {
    setMessage("");
    setFieldErrors({});
    setArchivedId("");
    try {
      if (editId) await updateMutation.mutateAsync({ id: editId, payload: values });
      else await createMutation.mutateAsync(values);
      router.push(`/${resource}`);
    } catch (error) {
      setMessage(getApiError(error));
      setFieldErrors(getApiFieldErrors(error));
      const payload = getErrorPayload(error);
      if (payload?.code === "RESOURCE_ARCHIVED" && typeof payload.details === "object" && payload.details !== null && "record_id" in payload.details && typeof payload.details.record_id === "string") {
        setArchivedId(payload.details.record_id);
      }
    }
  }

  async function reactivateArchived() {
    try {
      await reactivateMutation.mutateAsync(archivedId);
      router.push(`/${resource}`);
    } catch (error) {
      setMessage(getApiError(error));
    }
  }

  if (initialForm) {
    if (editId && editQuery.isLoading) return <main className="min-h-screen bg-[#f7f8fa] p-8"><TableSkeleton /></main>;
    if (editId && editQuery.isError) return <main className="min-h-screen bg-[#f7f8fa] p-8"><ErrorState message={getApiError(editQuery.error)} onRetry={() => void editQuery.refetch()} /></main>;
    if(resource === "rutas") return <RouteEditor key={editId} initial={editQuery.data} loading={createMutation.isPending || updateMutation.isPending} message={message} onSave={values => void save(values)} onCancel={() => router.push("/rutas")}/>;
    return <RegistrationPage key={`${resource}:${editId}`} config={config} initial={editQuery.data} loading={createMutation.isPending || updateMutation.isPending} message={message} fieldErrors={fieldErrors} archivedId={archivedId} canReactivate={user?.role === "admin"} reactivatePending={reactivateMutation.isPending} onReactivate={() => void reactivateArchived()} onCancel={() => router.push(`/${resource}`)} onSave={(values) => void save(values)} />;
  }

  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10"><div className="mx-auto max-w-[1440px]">
    <header className="mb-7 flex items-start justify-between gap-4"><div><div className="mb-2 flex items-center gap-2 text-xs text-[#87918c]"><span>Administración</span><span>/</span><span>Flota</span><span>/</span><span className="text-[#47534d]">{config.title}</span></div><h1 className="text-[28px] font-semibold tracking-[-.8px]">{config.title}</h1><p className="mt-1 text-sm text-[#7a8580]">{config.description}</p></div><div className="flex shrink-0 flex-wrap justify-end gap-2">{(resource === "rutas" || resource === "vehiculos") && <button type="button" title="Exporta todos los registros coincidentes, incluidas las demás páginas" disabled={exporting || total === 0} onClick={() => void exportCatalog()} className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#dce7df] bg-white px-4 text-sm font-medium text-[#2563EB] shadow-sm hover:bg-[#f4f9f6] disabled:cursor-not-allowed disabled:opacity-50"><FileDown size={16}/>{exporting ? "Preparando PDF…" : "Exportar todo a PDF"}</button>}<Link href={`/${resource}/${resource === "rutas" ? "nueva" : "nuevo"}`} className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#2563EB] px-4 text-sm font-medium text-white shadow-sm hover:bg-[#1D4ED8]"><Plus size={17} />Nuevo {config.singular}</Link></div></header>
    <section className="mb-5 flex flex-col gap-3 rounded-xl border border-[#e8ece9] bg-white p-4 sm:flex-row"><label className="relative min-w-0 flex-1"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9aa39f]" /><input value={query} onChange={(event) => changeFilters(() => setQuery(event.target.value))} placeholder={config.searchPlaceholder} className={`${controlClass} pl-9`} /></label><FilterSelect label="Estado" value={status} options={config.statuses} onChange={(value) => changeFilters(() => setStatus(value))} allLabel={allStates} />{config.hasTypeFilter && <FilterSelect label="Tipo" value={type} options={config.fields.find((field) => field.key === "tipo")?.options ?? []} onChange={(value) => changeFilters(() => setType(value))} allLabel="Todos los tipos" />}</section>
    {listQuery.isLoading ? <TableSkeleton /> : listQuery.isError ? <ErrorState message={getApiError(listQuery.error)} onRetry={() => void listQuery.refetch()} /> : <section className="overflow-hidden rounded-xl bg-white p-4"><div className="flex items-center justify-between border-b border-[#edf0ee] px-5 py-4"><div><h2 className="text-[15px] font-semibold">{config.listTitle}</h2><p className="mt-0.5 text-xs text-[#89938e]">{total} registros encontrados</p></div></div>{rows.length === 0 ? <EmptyState title="No hay registros para mostrar" description="Cambia los filtros o registra un nuevo elemento." /> : <><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="text-[#64716b]"><tr>{config.columns.map((column) => <th key={column.key} className="p-3">{column.label}</th>)}<th className="p-3 text-right">Acciones</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id} className="border-t hover:bg-[#fbfcfb]">{config.columns.map((column) => <td key={column.key} className="p-3 text-sm text-[#47534d]">{column.key === "estado" ? <Status value={row[column.key] ?? ""} /> : column.key === "placa_remolque" ? (row.tiene_remolque === "true" ? row.placa_remolque || "Sí" : "No") : formatCell(column.key, row[column.key] ?? "", row.moneda ?? "PEN")}</td>)}<td className="p-3"><div className="flex justify-end gap-1"><button title="Ver detalle" onClick={() => setSelectedId(row.id ?? "")} className="rounded-md p-2 text-[#7c8781] hover:bg-[#EFF6FF]"><Eye size={16} /></button>{resource === "rutas" && <button title="Exportar PDF" onClick={() => exportRoutePdf(row)} className="rounded-md p-2 text-[#7c8781] hover:bg-[#EFF6FF]"><FileDown size={15} /></button>}<button title="Editar" onClick={() => editRecord(row.id ?? "")} className="rounded-md p-2 text-[#7c8781] hover:bg-[#EFF6FF]"><Pencil size={15} /></button>{user?.role === "admin" && <button title="Dar de baja" onClick={() => setConfirmId(row.id ?? "")} className="rounded-md p-2 text-[#7c8781] hover:bg-[#fff0f0] hover:text-[#bc6560]"><Trash2 size={15} /></button>}</div></td></tr>)}</tbody></table></div><footer className="flex items-center justify-between border-t border-[#edf0ee] px-5 py-3 text-xs text-[#77817b]"><span>Página {page} de {pages} · {total} registros</span><div className="flex gap-2"><button disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} className="rounded-md border border-[#e5e9e6] px-3 py-1.5 disabled:opacity-40">Anterior</button><button disabled={page >= pages} onClick={() => setPage((current) => Math.min(pages, current + 1))} className="rounded-md border border-[#e5e9e6] px-3 py-1.5 disabled:opacity-40">Siguiente</button></div></footer></>}</section>}
    {selectedId && <DetailPanel config={config} row={detailQuery.data} loading={detailQuery.isLoading} error={detailQuery.isError ? getApiError(detailQuery.error) : ""} onRetry={() => void detailQuery.refetch()} onClose={() => setSelectedId("")} onEdit={() => { const id = selectedId; setSelectedId(""); editRecord(id); }} />}
    {confirmId && <div className="fixed inset-0 z-40 flex items-center justify-center bg-[#17211e]/35 p-4"><section className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl"><h2 className="text-base font-semibold">¿Dar de baja este registro?</h2><p className="mt-2 text-sm leading-6 text-[#78837d]">El registro se ocultará de los listados activos y conservará su información para una posible reactivación.</p><div className="mt-6 flex justify-end gap-2"><button onClick={() => setConfirmId("")} className="rounded-lg border border-[#e5e9e6] px-3.5 py-2 text-sm">Cancelar</button><button disabled={deleteMutation.isPending} onClick={() => void deleteMutation.mutateAsync(confirmId).then(() => setConfirmId("")).catch((error) => setMessage(getApiError(error)))} className="rounded-lg bg-[#b9443d] px-3.5 py-2 text-sm font-medium text-white">Confirmar baja</button></div></section></div>}
    {message && !initialForm && <div role="alert" className="fixed bottom-5 right-5 z-50 rounded-lg bg-[#8c2f2a] px-4 py-3 text-sm text-white shadow-lg">{message}</div>}
  </div></main>;
}

function RegistrationPage({ config, initial, loading, message, fieldErrors, archivedId, canReactivate, reactivatePending, onReactivate, onCancel, onSave }: { config: ResourceConfig; initial?: ResourceRecord; loading: boolean; message: string; fieldErrors: Record<string, string>; archivedId: string; canReactivate: boolean; reactivatePending: boolean; onReactivate: () => void; onCancel: () => void; onSave: (values: ResourceRecord) => void }) {
  const [values, setValues] = useState<ResourceRecord>(() => Object.fromEntries(config.fields.map((field) => [field.key, initial?.[field.key] ?? field.defaultValue ?? ""])));
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = { ...values };
    const statusField = config.fields.find((field) => field.key === config.statusKey);
    if (!payload[config.statusKey] && statusField?.defaultValue) payload[config.statusKey] = statusField.defaultValue;
    onSave(payload);
  }
  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10"><div className="mx-auto max-w-[1000px]"><button type="button" onClick={onCancel} className="mb-6 inline-flex items-center gap-1.5 text-xs text-[#65716b] hover:text-[#2563EB]"><ArrowLeft size={14} />{config.title}</button><div className="mb-6"><h1 className="text-[27px] font-semibold tracking-[-.8px]">{initial ? `Editar ${config.singular}` : `Nuevo ${config.singular}`}</h1><p className="mt-1 text-sm text-[#7a8580]">Completa los datos para guardar el registro.</p></div><form onSubmit={submit} className="rounded-xl border border-[#e8ece9] bg-white p-5 shadow-sm sm:p-6"><p className="mb-5 rounded-lg bg-[#f7f9f8] px-3 py-2.5 text-xs text-[#68736d]">La carga de fotos y archivos estará disponible próximamente.</p><div className="grid gap-4 sm:grid-cols-2">{config.fields.filter((field) => field.key !== "placa_remolque" || values.tiene_remolque === "true").map((field) => <SchemaField key={field.key} field={field} value={values[field.key] ?? ""} error={fieldErrors[field.key]} onChange={(value) => setValues((current) => ({ ...current, [field.key]: value }))} resource={config.title === "Vehículos" ? "vehiculos" : config.title === "Rutas" ? "rutas" : "conductores"} />)}</div>{message && <p role="alert" className="mt-5 rounded-lg bg-[#fff1ef] px-3 py-2.5 text-sm text-[#a43c34]">{message}</p>}{archivedId && <div className="mt-3 rounded-lg border border-[#f1d5ad] bg-[#fff9ef] p-3 text-sm text-[#76501c]"><p>Este código pertenece a un registro dado de baja.</p>{canReactivate ? <button type="button" disabled={reactivatePending} onClick={onReactivate} className="mt-2 font-semibold underline disabled:opacity-50">Reactivar el registro existente</button> : <p className="mt-1 text-xs">Solicita a un administrador que lo reactive.</p>}</div>}<footer className="mt-6 flex justify-end gap-2 border-t border-[#edf0ee] pt-4"><button type="button" onClick={onCancel} className="rounded-lg border border-[#e1e6e2] px-4 py-2.5 text-xs font-medium text-[#59655f]">Cancelar</button><button type="submit" disabled={loading} className="inline-flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-xs font-medium text-white disabled:opacity-60"><Check size={15} />{loading ? "Guardando…" : initial ? "Guardar cambios" : `Registrar ${config.singular}`}</button></footer></form></div></main>;
}

function SchemaField({ resource, field, value, error, onChange }: { resource: ResourceKey; field: ResourceField; value: string; error?: string; onChange: (value: string) => void }) {
  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState("");
  async function suggest() {
    setSuggesting(true);
    setSuggestError("");
    try { onChange(await createResourceService(resource).suggestCode()); }
    catch { setSuggestError("No se pudo sugerir un código. Puedes escribirlo manualmente."); }
    finally { setSuggesting(false); }
  }
  const inputClass = `${controlClass} ${error ? "border-[#d66a60] focus:border-[#d66a60] focus:ring-[#fde5e2]" : ""}`;
  return <label className={`block ${field.type === "textarea" ? "sm:col-span-2" : ""}`}><span className="mb-1.5 block text-xs font-medium text-[#56625c]">{field.label}{field.required && <b className="ml-1 text-[#cf6f63]">*</b>}</span><div className="flex gap-2">{field.type === "select" || field.type === "boolean" ? <div className="relative flex-1"><select required={field.required} value={value} onChange={(event) => onChange(event.target.value)} className={`${inputClass} appearance-none pr-9`}>{field.type === "boolean" ? <><option value="true">Sí</option><option value="false">No</option></> : <><option value="">Selecciona una opción</option>{field.options?.map((option) => <option key={option} value={option}>{option}</option>)}</>}</select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-3 text-[#929c97]" /></div> : field.type === "textarea" ? <textarea required={field.required} value={value} onChange={(event) => onChange(event.target.value)} placeholder={field.label} rows={3} className={`${inputClass} h-auto flex-1 py-3`} /> : <input required={field.required} type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"} min={field.type === "number" ? 0 : undefined} step={field.type === "number" ? "any" : undefined} value={value} onChange={(event) => onChange(event.target.value)} placeholder={field.label} className={inputClass} />}{field.suggestCode && <button type="button" onClick={() => void suggest()} disabled={suggesting} className="shrink-0 rounded-lg border border-[#dce7df] px-3 text-xs font-medium text-[#2563EB] disabled:opacity-50">{suggesting ? "…" : "Sugerir"}</button>}</div>{error && <span className="mt-1 block text-[11px] text-[#b9443d]">{error}</span>}{suggestError && <span className="mt-1 block text-[11px] text-[#a66a14]">{suggestError}</span>}</label>;
}

function DetailPanel({ config, row, loading, error, onRetry, onClose, onEdit }: { config: ResourceConfig; row?: ResourceRecord; loading: boolean; error: string; onRetry: () => void; onClose: () => void; onEdit: () => void }) {
  return <div className="fixed inset-0 z-30 flex justify-end bg-[#17211e]/35" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="flex h-full w-full max-w-[520px] flex-col overflow-y-auto bg-white shadow-2xl"><header className="flex items-center justify-between border-b border-[#edf0ee] px-6 py-4"><div><p className="text-[10px] font-medium uppercase tracking-[.1em] text-[#939d98]">Detalle · {config.singular}</p><p className="mt-0.5 text-xs text-[#68736d]">{row?.[config.codeKey] ?? ""}</p></div><button onClick={onClose} className="rounded-lg p-2 text-[#7c8781]"><X size={19} /></button></header>{loading ? <div className="p-6"><TableSkeleton /></div> : error ? <div className="p-6"><ErrorState message={error} onRetry={onRetry} /></div> : row ? <><div className="border-b border-[#edf0ee] px-6 py-6"><div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold">{row[config.columns[1]?.key] || row[config.codeKey]}</h2><Status value={row[config.statusKey] ?? ""} /></div><p className="mt-1 text-xs text-[#89938e]">{row[config.codeKey]}</p></div><div className="grid flex-1 content-start gap-5 px-6 py-5 sm:grid-cols-2">{config.fields.map((field) => { const value = row[field.key]; if (!value) return null; return <div key={field.key}><p className="text-[10px] text-[#9aa39f]">{field.label}</p><p className="mt-1 break-words text-xs font-medium text-[#49564f]">{formatCell(field.key, value, row.moneda ?? "PEN")}</p></div>; })}</div><footer className="sticky bottom-0 flex justify-end gap-2 border-t border-[#edf0ee] bg-white px-6 py-4"><button onClick={onClose} className="rounded-lg border border-[#e5e9e6] px-4 py-2 text-xs text-[#59655f]">Cerrar</button><button onClick={onEdit} className="rounded-lg bg-[#2563EB] px-4 py-2 text-xs font-medium text-white">Editar</button></footer></> : null}</aside></div>;
}

function FilterSelect({ label, value, options, onChange, allLabel }: { label: string; value: string; options: string[]; onChange: (value: string) => void; allLabel: string }) {
  return <label className="relative"><span className="sr-only">Filtrar por {label}</span><select value={value} onChange={(event) => onChange(event.target.value)} className={`${controlClass} appearance-none pr-9 sm:w-[190px]`}><option value="">{allLabel}</option>{options.map((option) => <option key={option}>{option}</option>)}</select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-3 text-[#929c97]" /></label>;
}

function Status({ value }: { value: string }) {
  const label = value === "disponible" ? "Disponible" : value === "en_viaje" ? "En viaje" : value === "mantenimiento" ? "Mantenimiento" : value === "descanso" ? "Descanso" : value === "inactivo" ? "Inactivo" : value === "inactiva" ? "Inactiva" : value === "activa" ? "Activa" : value;
  const color = ["disponible", "activa"].includes(value) ? "bg-[#eaf5ee] text-[#37825b]" : value === "en_viaje" ? "bg-[#edf5ff] text-[#507bb5]" : value === "inactivo" || value === "inactiva" ? "bg-[#f0f1f1] text-[#7d8782]" : "bg-[#fff6e8] text-[#b7812d]";
  return <span className={`inline-flex whitespace-nowrap items-center rounded-full px-2.5 py-1 text-[10px] font-medium ${color}`}>{label}</span>;
}

function formatCell(key: string, value: string, currency: string): string {
  if (key === "tiene_remolque") return value === "true" ? "Sí" : "No";

  if (key === "paradas") { try { return (JSON.parse(value) as { ciudad: string; tiempo_espera: number }[]).map(stop => `${stop.ciudad} (${stop.tiempo_espera} min)`).join(" → "); } catch { return value; } }
  if (key === "peajes_minor" || key === "tarifa_referencial_minor") return new Intl.NumberFormat("es-PE", { style: "currency", currency, minimumFractionDigits: 2 }).format(Number(value) / 100);
  if (key === "capacidad_kg") return `${Number(value).toLocaleString("es-PE")} kg`;
  if (key === "duracion_minutos") return `${value} min`;
  if (key === "distancia_km") return `${Number(value).toLocaleString("es-PE")} km`;
  return value;
}

function getErrorPayload(error: unknown): { code?: unknown; details?: unknown } | null {
  if (typeof error !== "object" || error === null || !("response" in error)) return null;
  const response = error.response;
  if (typeof response !== "object" || response === null || !("data" in response)) return null;
  const data = response.data;
  return typeof data === "object" && data !== null ? data as { code?: unknown; details?: unknown } : null;
}
