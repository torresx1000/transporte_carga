"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { CalendarDays, ChartNoAxesColumn, Check, CircleHelp, LoaderCircle, MoreHorizontal, Truck, Fuel, Wallet } from "lucide-react";
import { useDashboardReport } from "@/hooks/useReportes";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { useCatalog } from "@/features/transporte/data";

type DashboardRecord = Record<string, unknown>;
type DashboardPage = { items: DashboardRecord[]; total: number; pages?: number };
type DashboardRow = { id: string; time: string; destination: string; client: string; product?: string; quantity?: string; state: string; vehicle: string; driver: string; initials: string };
type MonthlyFinance = { key: string; label: string; revenue: number; costs: number };
type MonthlyValue = { key: string; label: string; value: number };
const EMPTY_RECORDS: DashboardRecord[] = [];
const REFRESH_INTERVAL_MS = 60_000;

export default function Dashboard() {
  const [activityTab, setActivityTab] = useState<"Recogidas" | "Entregas">("Recogidas");
  const [notice, setNotice] = useState("");
  const [refreshProgress, setRefreshProgress] = useState(0);
  const refreshCycleStart = useRef(0);
  const [chartMonth, setChartMonth] = useState("");
  const dashboardQuery = useDashboardReport();
  const tripsQuery = useQuery({ queryKey: ["dashboard", "viajes"], queryFn: async () => { const items = await fetchAllDashboardRecords("viajes"); return { items, total: items.length }; }, refetchInterval: REFRESH_INTERVAL_MS });
  const loadsQuery = useQuery({ queryKey: ["dashboard", "cargas"], queryFn: async () => (await api.get<DashboardPage>("/cargas", { params: { page: 1, page_size: 100 } })).data, refetchInterval: REFRESH_INTERVAL_MS });
  const alertsQuery = useQuery({ queryKey: ["documentos", "por-vencer"], queryFn: async () => (await api.get("/documentos/por-vencer", { params: { dias: 30 } })).data as Array<Record<string, unknown>>, refetchInterval: 60_000 });
  const clientsQuery = useCatalog<DashboardRecord>("clientes", { refetchInterval: REFRESH_INTERVAL_MS });
  const vehiclesQuery = useCatalog<DashboardRecord>("vehiculos", { refetchInterval: REFRESH_INTERVAL_MS });
  const driversQuery = useCatalog<DashboardRecord>("conductores", { refetchInterval: REFRESH_INTERVAL_MS });
  const routesQuery = useCatalog<DashboardRecord>("rutas", { refetchInterval: REFRESH_INTERVAL_MS });
  const chartsQuery = useQuery({ queryKey: ["dashboard", "charts"], queryFn: async () => {
    const [payments, expenses, fuelings] = await Promise.all([
      fetchAllDashboardRecords("pagos"), fetchAllDashboardRecords("gastos"), fetchAllDashboardRecords("combustible"),
    ]);
    return { payments, expenses, fuelings };
  }, refetchInterval: REFRESH_INTERVAL_MS });
  useEffect(() => {
    refreshCycleStart.current = Date.now();
    const timer = window.setInterval(() => {
      const now = Date.now();
      const elapsed = now - refreshCycleStart.current;
      if (elapsed >= REFRESH_INTERVAL_MS) {
        refreshCycleStart.current += Math.floor(elapsed / REFRESH_INTERVAL_MS) * REFRESH_INTERVAL_MS;
      }
      setRefreshProgress(((now - refreshCycleStart.current) / REFRESH_INTERVAL_MS) * 100);
    }, 250);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const now = new Date();
      setChartMonth(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);
  const loads = loadsQuery.data?.items ?? [];
  const tripsSource = tripsQuery.data?.items ?? EMPTY_RECORDS;
  const clients = clientsQuery.data ?? [];
  const vehicles = vehiclesQuery.data ?? [];
  const drivers = driversQuery.data ?? [];
  const routes = routesQuery.data ?? [];
  const chartRecords = chartsQuery.data;
  const monthlyFinance = useMemo(() => buildFinanceSeries(chartMonth, chartRecords?.payments ?? [], chartRecords?.expenses ?? [], chartRecords?.fuelings ?? []), [chartMonth, chartRecords]);
  const monthlyTrips = useMemo(() => buildMonthlySeries(chartMonth, tripsSource, ["fecha_salida_programada", "salida_real", "created_at"]), [chartMonth, tripsSource]);
  const monthlyFuel = useMemo(() => buildMonthlySeries(chartMonth, chartRecords?.fuelings ?? [], ["fecha_consumo", "created_at"], "litros_milesimas", 1000), [chartMonth, chartRecords]);
  const financeTotals = useMemo(() => monthlyFinance.reduce((totals, month) => ({ revenue: totals.revenue + month.revenue, costs: totals.costs + month.costs }), { revenue: 0, costs: 0 }), [monthlyFinance]);
  const trips = tripsSource.map((trip): DashboardRow => {
    const tripId = value(trip, "id");
    const route = routes.find((item) => value(item, "id") === value(trip, "ruta_id", "route_id"));
    const vehicle = vehicles.find((item) => value(item, "id") === value(trip, "vehiculo_id", "vehicle_id"));
    const driver = drivers.find((item) => value(item, "id") === value(trip, "conductor_id", "driver_id"));
    const linkedLoads = loads.filter((load) => belongsToTrip(load, tripId) || arrayOfStrings(trip.cargas_ids).includes(value(load, "id")));
    const clientNames = [...new Set(linkedLoads.map((load) => clients.find((item) => value(item, "id") === value(load, "cliente_id", "client_id"))).map((item) => item ? value(item, "nombre", "name") : "").filter(Boolean))];
    const driverName = value(driver, "nombre", "name") || value(trip, "conductor", "driver") || "—";
    const origin = value(route, "origen", "origin") || value(trip, "origen", "origin") || "—";
    const destination = value(route, "destino", "destination") || value(trip, "destino", "destination") || "—";
    return { id: value(trip, "codigo", "code", "id") || "—", state: statusLabel(value(trip, "estado", "status")), destination: `${origin} → ${destination}`, client: clientNames.join(", ") || value(trip, "cliente", "client") || "—", time: formatDateTime(value(trip, "fecha_entrega_estimada", "scheduled_end_at", "eta")), vehicle: value(vehicle, "placa", "plate") || value(trip, "vehiculo", "vehicle") || "—", driver: driverName, initials: initials(driverName) };
  });
  const clientName = (id: string) => value(clients.find((client) => value(client, "id") === id), "nombre", "name") || "—";
  const tripForLoad = (load: DashboardRecord) => tripsSource.find((trip) => belongsToTrip(load, value(trip, "id")) || arrayOfStrings(trip.cargas_ids).includes(value(load, "id")));
  const activityRows = (rows: DashboardRecord[], kind: "pickup" | "delivery"): DashboardRow[] => rows.slice(0, 4).map((load) => {
    const trip = tripForLoad(load);
    const vehicle = vehicles.find((item) => value(item, "id") === value(trip, "vehiculo_id", "vehicle_id"));
    const driver = drivers.find((item) => value(item, "id") === value(trip, "conductor_id", "driver_id"));
    const driverName = value(driver, "nombre", "name") || value(trip, "conductor", "driver") || "—";
    return { id: value(load, "codigo", "code", "id") || "—", time: formatDateTime(value(load, kind === "pickup" ? "fecha_recojo" : "fecha_entrega", kind === "pickup" ? "pickup_date" : "delivery_date", kind === "pickup" ? "hora_recojo" : "hora_entrega", "created_at")), destination: value(load, "destino", "destination") || "—", client: clientName(value(load, "cliente_id", "client_id")), product: value(load, "producto", "product"), quantity: [value(load, "cantidad", "quantity"), value(load, "unidad", "unit")].filter(Boolean).join(" "), state: statusLabel(value(load, "estado", "status")), vehicle: value(vehicle, "placa", "plate") || value(trip, "vehiculo", "vehicle") || "—", driver: driverName, initials: initials(driverName) };
  });
  const pickups = activityRows(loads, "pickup");
  const deliveries = activityRows(loads.filter((load) => /entregad|completad/i.test(value(load, "estado", "status"))), "delivery");
  const transitTrips = trips.filter((trip) => /tr[aá]nsito|curso/i.test(trip.state)).length;
  const completedLoads = loads.filter((load) => /entregad|completad/i.test(value(load, "estado", "status"))).length;
  const upcomingTrips = trips.filter((trip) => /programad/i.test(trip.state)).length;
  const expiring = alertsQuery.data ?? [];
  const isFetching = dashboardQuery.isFetching || tripsQuery.isFetching || loadsQuery.isFetching || alertsQuery.isFetching || clientsQuery.isFetching || vehiclesQuery.isFetching || driversQuery.isFetching || routesQuery.isFetching || chartsQuery.isFetching;
  const detailsLoading = clientsQuery.isLoading || vehiclesQuery.isLoading || driversQuery.isLoading || routesQuery.isLoading;
  const showNotice = (message: string) => { setNotice(message); window.setTimeout(() => setNotice(""), 2500); };

  return <main className="mx-auto max-w-[1800px] p-3.5 sm:p-5">
        <section className="mb-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
          <Metric icon={<Truck size={16} />} label="Viajes en tránsito" value={String(transitTrips).padStart(2,"0")} onClick={() => showNotice("Resumen de viajes en tránsito.")} />
          <Metric icon={<Check size={16} />} label="Cargas finalizadas" value={String(completedLoads).padStart(2,"0")} period="Total" onClick={() => showNotice("Cargas finalizadas según los registros disponibles.")} />
          <Metric icon={<CalendarDays size={16} />} label="Próximos viajes" value={String(upcomingTrips).padStart(2,"0")} period="Programados" onClick={() => showNotice("Viajes programados según los registros disponibles.")} />
          <Metric icon={<ChartNoAxesColumn size={16} />} label="Clientes" value={String(dashboardQuery.data?.clientes ?? "—")} period="Total" onClick={() => showNotice("Total de clientes registrados.")} />
        </section>

        {alertsQuery.isError ? <p className="mb-4 text-xs text-red-600">{getApiError(alertsQuery.error)}</p> : expiring.length > 0 ? <section className="mb-4 grid gap-3 md:grid-cols-2">{expiring.slice(0,2).map((item,index)=><Alert key={String(item.id ?? index)} icon={<span className="text-red-500"><CircleHelp size={16}/></span>} title={String(item.nombre ?? item.tipo ?? "Documento por vencer")} description={String(item.vence_en ?? "Vencimiento próximo")} onClick={()=>showNotice("Documento con vencimiento próximo.")}/>)}</section> : null}

        <div className="grid gap-3 xl:grid-cols-[minmax(0,2.08fr)_minmax(330px,1.08fr)]">
          <div className="min-w-0 space-y-3">
            <section className="overflow-hidden rounded-lg border border-[#dfe6f0] bg-white shadow-[0_1px_2px_rgba(16,42,76,.10)]"><div className="flex h-[42px] items-center justify-between border-b border-[#e1e7f0] px-3"><h2 className="text-[12px] font-semibold">Actividad de hoy</h2><div className="flex rounded-md bg-[#f0f4f9] p-0.5">{(["Recogidas", "Entregas"] as const).map((tab) => <button key={tab} onClick={() => setActivityTab(tab)} className={`rounded px-2.5 py-1 text-[9px] ${activityTab === tab ? "bg-white font-medium text-[#23416f] shadow-sm" : "text-[#7c8eaa]"}`}>{tab}</button>)}</div></div><div className="overflow-x-auto"><table className="w-full min-w-[860px] text-left"><thead><tr className="h-[35px] border-b border-[#e2e8f1] text-[10px] text-[#536d91]">{["ID / Carga", "Fecha", "Destino", "Cliente", "Producto / cantidad", "Estado", "Vehículo", "Conductor"].map((h) => <th key={h} className="px-3 font-medium">{h}</th>)}</tr></thead><tbody>{detailsLoading || loadsQuery.isLoading ? <tr><td colSpan={8} className="p-6 text-center text-xs text-slate-500">Cargando detalles de cargas…</td></tr> : (activityTab === "Recogidas" ? pickups : deliveries).map((row) => <tr key={row.id} className="h-[42px] border-b border-[#e8edf4] text-[10px] last:border-0 hover:bg-[#fafcff]"><td className="px-3 font-medium"><span className="mr-2 inline-block size-1.5 rounded-full bg-[#2864ed]" />{row.id}</td><td className="px-3">{row.time}</td><td className="px-3">{row.destination}</td><td className="px-3">{row.client}</td><td className="px-3">{[row.product, row.quantity].filter(Boolean).join(" · ") || "—"}</td><td className="px-3"><Pill value={row.state} /></td><td className="px-3">{row.vehicle}</td><td className="px-3"><span className="inline-flex items-center gap-1.5"><Initials value={row.initials} />{row.driver}</span></td></tr>)}</tbody></table></div></section>

            <section className="overflow-hidden rounded-lg border border-[#dfe6f0] bg-white shadow-[0_1px_2px_rgba(16,42,76,.10)]"><div className="flex h-[42px] items-center justify-between border-b border-[#e1e7f0] px-3"><h2 className="text-[12px] font-semibold">Últimos viajes</h2><Link href="/viajes" className="text-[9px] font-medium text-[#2864ed] hover:underline">Ver todos</Link></div><div className="overflow-x-auto"><table className="w-full min-w-[730px] text-left"><thead><tr className="h-[35px] border-b border-[#e2e8f1] text-[10px] text-[#536d91]">{["ID", "Estado", "Ruta", "Cliente", "ETA", "Vehículo", "Conductor"].map((h) => <th key={h} className="px-3 font-medium">{h}</th>)}</tr></thead><tbody>{tripsQuery.isLoading || detailsLoading ? <tr><td colSpan={7} className="p-6 text-center text-xs text-slate-500">Cargando viajes…</td></tr> : tripsQuery.isError ? <tr><td colSpan={7} className="p-6 text-center text-xs text-red-600">{getApiError(tripsQuery.error)}</td></tr> : trips.length ? trips.slice(0,4).map((row) => <tr key={row.id} className="h-[42px] border-b border-[#e8edf4] text-[10px] last:border-0 hover:bg-[#fafcff]"><td className="px-3 font-medium">{row.id}</td><td className="px-3"><Pill value={row.state} /></td><td className="px-3">{row.destination}</td><td className="px-3">{row.client}</td><td className="px-3">{row.time}</td><td className="px-3">{row.vehicle}</td><td className="px-3"><span className="inline-flex items-center gap-1.5"><Initials value={row.initials} />{row.driver}</span></td></tr>) : <tr><td colSpan={7} className="p-6 text-center text-xs text-slate-500">No hay viajes registrados.</td></tr>}</tbody></table></div></section>
          </div>

          <div className="space-y-3">
            <section className="rounded-lg border border-[#dfe6f0] bg-white p-3.5 shadow-[0_1px_2px_rgba(16,42,76,.10)]"><div className="flex items-center justify-between"><h2 className="text-[12px] font-semibold">Costos y rentabilidad</h2><Link href="/reportes" className="text-[9px] text-[#2864ed] hover:underline">Ver más</Link></div>{chartsQuery.isError?<p className="mt-3 rounded-md bg-red-50 p-3 text-xs text-red-700">No se pudieron cargar los registros financieros.</p>:<div className="mt-3 grid grid-cols-2 gap-2 border-y border-[#dfe6f0] py-4"><div className="rounded-md bg-blue-50 p-3"><p className="text-[9px] text-blue-700">Ingresos · 6 meses</p><p className="mt-1 text-sm font-semibold text-blue-900">{formatMoney(financeTotals.revenue)}</p></div><div className="rounded-md bg-rose-50 p-3"><p className="text-[9px] text-rose-700">Costos · 6 meses</p><p className="mt-1 text-sm font-semibold text-rose-900">{formatMoney(financeTotals.costs)}</p></div><div className="col-span-2 flex items-center justify-between px-1 text-[10px]"><span className="text-slate-500">Resultado del periodo</span><strong className={financeTotals.revenue-financeTotals.costs>=0?"text-emerald-700":"text-red-700"}>{formatMoney(financeTotals.revenue-financeTotals.costs)}</strong></div></div>}</section>

            <section className="rounded-lg border border-[#dfe6f0] bg-white p-3.5 shadow-[0_1px_2px_rgba(16,42,76,.10)]"><div className="flex items-center justify-between"><h2 className="text-[12px] font-semibold">Seguimiento en vivo</h2><button onClick={() => showNotice("No hay endpoint de ubicación GPS conectado todavía.")} className="text-[9px] text-[#2864ed] hover:underline">Estado</button></div><div className="mt-3 flex h-[154px] items-center justify-center rounded-md border border-[#e4eaf2] bg-[#f5f7fa] px-6 text-center text-xs text-[#8091aa]">El seguimiento GPS se mostrará cuando exista una fuente de ubicación en el backend.</div></section>
          </div>
        </div>
        <section className="mt-3 grid gap-3 lg:grid-cols-2" aria-label="Gráficos del panel">
          <MonthlyComparisonChart data={monthlyFinance} loading={chartsQuery.isLoading} error={chartsQuery.isError}/>
          <MonthlyChartCard title="Viajes por mes" subtitle="Viajes según su fecha de salida" icon={<Truck size={15}/>} data={monthlyTrips} loading={tripsQuery.isLoading} error={tripsQuery.isError} color="#2563eb" format={(value)=>String(value)} emptyText="No hay viajes con fecha de salida para graficar."/>
          <MonthlyChartCard title="Consumo de combustible" subtitle="Litros por fecha de consumo" icon={<Fuel size={15}/>} data={monthlyFuel} loading={chartsQuery.isLoading} error={chartsQuery.isError} color="#0f9f81" format={(value)=>`${value.toLocaleString("es-PE",{maximumFractionDigits:1})} L`} emptyText="No hay consumos registrados para graficar."/>
          <FleetStatusChart vehicles={vehicles} loading={vehiclesQuery.isLoading} error={vehiclesQuery.isError}/>
        </section>
        <div className="mt-4 flex items-center gap-2.5" role="status" aria-live="polite">
          <p className="flex min-h-4 items-center gap-1.5 text-[10px] text-[#96a4b8]">{dashboardQuery.isError ? getApiError(dashboardQuery.error) : isFetching ? <><LoaderCircle size={12} className="animate-spin" aria-hidden="true"/><span>Actualizando información…</span></> : "Datos del panel consultados desde la API · actualización cada 60 segundos"}</p>
          <div className="h-1 w-20 overflow-hidden rounded-full bg-[#e4eaf2]" role="progressbar" aria-label="Progreso hasta la próxima actualización" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(refreshProgress)}>
            <div className="h-full rounded-full bg-[#2864ed] transition-[width] duration-200 ease-linear" style={{ width: `${refreshProgress}%` }} />
          </div>
        </div>
      {notice && <div role="status" className="fixed bottom-5 right-5 z-50 rounded-lg bg-[#1c3458] px-4 py-2.5 text-xs text-white shadow-lg">{notice}</div>}
    </main>;
}

function Metric({ icon, label, value, detail, period, negative, onClick }: { icon: React.ReactNode; label: string; value: string; detail?: string; period?: string; negative?: boolean; onClick: () => void }) { return <button onClick={onClick} className="min-h-[123px] rounded-lg border border-[#dfe6f0] bg-white p-3.5 text-left shadow-[0_1px_2px_rgba(16,42,76,.10)] transition hover:border-[#b9cbed] hover:shadow-sm"><div className="flex items-start justify-between"><span className="flex size-8 items-center justify-center rounded-md bg-[#eef4ff] text-[#2864ed]">{icon}</span>{period && <span className="text-[9px] text-[#7d91af]">{period}</span>}</div><p className="mt-3 text-[10px] text-[#647b9e]">{label}</p><div className="mt-0.5 flex items-center gap-2"><strong className="text-[19px] font-semibold leading-tight tracking-[-.4px] text-[#132b50]">{value}</strong>{detail && <span className={`text-[9px] ${negative ? "text-red-500" : "text-emerald-600"}`}>{detail}</span>}</div></button>; }
async function fetchAllDashboardRecords(resource: string): Promise<DashboardRecord[]> {
  const pageSize = 100;
  const first = (await api.get<DashboardPage>(`/${resource}`, { params: { page: 1, page_size: pageSize } })).data;
  const records = [...first.items];
  const pageCount = first.pages ?? Math.ceil(first.total / pageSize);
  for (let page = 2; page <= pageCount; page++) {
    const result = (await api.get<DashboardPage>(`/${resource}`, { params: { page, page_size: pageSize } })).data;
    records.push(...result.items);
  }
  return records;
}
function monthWindow(endKey: string) {
  if (!/^\d{4}-\d{2}$/.test(endKey)) return [];
  const [year, month] = endKey.split("-").map(Number);
  return Array.from({ length: 6 }, (_, index) => {
    const date = new Date(year, month - 1 - (5 - index), 1);
    return { key: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`, label: date.toLocaleDateString("es-PE", { month: "short" }).replace(".", "") };
  });
}
function recordDate(record: DashboardRecord, dateFields: string[]) {
  const nested = record.data && typeof record.data === "object" ? record.data as DashboardRecord : record;
  return value(nested, ...dateFields);
}
function monthKey(raw: string) { const match = raw.match(/^(\d{4})-(\d{2})/); if (match) return `${match[1]}-${match[2]}`; const parsed = new Date(raw); return Number.isNaN(parsed.getTime()) ? "" : `${parsed.getFullYear()}-${String(parsed.getMonth()+1).padStart(2,"0")}`; }
function recordNumber(record: DashboardRecord, fields: string[]) {
  const nested = record.data && typeof record.data === "object" ? record.data as DashboardRecord : record;
  for (const field of fields) { const amount = Number(nested[field]); if (Number.isFinite(amount)) return amount; }
  return 0;
}
function buildMonthlySeries(endKey: string, records: DashboardRecord[], dateFields: string[], amountField?: string, divisor = 1): MonthlyValue[] {
  const months = monthWindow(endKey);
  const counts = new Map(months.map(({ key }) => [key, 0]));
  for (const record of records) {
    const key = monthKey(recordDate(record, dateFields));
    if (counts.has(key)) counts.set(key, (counts.get(key) ?? 0) + (amountField ? recordNumber(record, [amountField]) / divisor : 1));
  }
  return months.map(({ key, label }) => ({ key, label, value: counts.get(key) ?? 0 }));
}
function buildFinanceSeries(endKey: string, payments: DashboardRecord[], expenses: DashboardRecord[], fuelings: DashboardRecord[]): MonthlyFinance[] {
  const months = monthWindow(endKey);
  const result = new Map(months.map(({ key, label }) => [key, { key, label, revenue: 0, costs: 0 }]));
  for (const payment of payments) {
    const nested = payment.data && typeof payment.data === "object" ? payment.data as DashboardRecord : payment;
    if (/anulad|cancelad/i.test(value(nested, "estado", "status"))) continue;
    const bucket = result.get(monthKey(recordDate(payment, ["fecha_pago", "created_at"])));
    if (bucket) bucket.revenue += recordNumber(payment, ["monto_centimos", "amount"]);
  }
  for (const expense of expenses) {
    const bucket = result.get(monthKey(recordDate(expense, ["fecha", "created_at"])));
    if (bucket) bucket.costs += recordNumber(expense, ["monto_centimos", "amount"]);
  }
  for (const fueling of fuelings) {
    const bucket = result.get(monthKey(recordDate(fueling, ["fecha_consumo", "created_at"])));
    if (bucket) bucket.costs += recordNumber(fueling, ["precio_centimos", "price_cents"]);
  }
  return [...result.values()];
}
function formatMoney(cents: number) { return `S/ ${(cents / 100).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }
function ChartFrame({ title, subtitle, icon, children }: { title: string; subtitle: string; icon: React.ReactNode; children: React.ReactNode }) {
  return <section className="overflow-hidden rounded-lg border border-[#dfe6f0] bg-white p-4 shadow-[0_1px_2px_rgba(16,42,76,.10)]"><div className="flex items-center gap-2"><span className="flex size-7 items-center justify-center rounded-md bg-blue-50 text-blue-600">{icon}</span><div><h2 className="text-xs font-semibold text-slate-800">{title}</h2><p className="text-[10px] text-slate-500">{subtitle}</p></div></div>{children}</section>;
}
function MonthlyComparisonChart({ data, loading, error }: { data: MonthlyFinance[]; loading: boolean; error: boolean }) {
  const max = Math.max(...data.flatMap((point) => [point.revenue, point.costs]), 1);
  return <ChartFrame title="Ingresos y costos" subtitle="Pagos registrados frente a gastos y combustible · últimos 6 meses" icon={<Wallet size={15}/>}>
    <div className="mt-4 flex items-center gap-4 text-[10px]"><span className="inline-flex items-center gap-1.5 text-slate-600"><i className="size-2 rounded-sm bg-blue-600"/>Ingresos</span><span className="inline-flex items-center gap-1.5 text-slate-600"><i className="size-2 rounded-sm bg-rose-500"/>Costos</span></div>
    {loading ? <ChartMessage>Consultando registros…</ChartMessage> : error ? <ChartMessage danger>No se pudieron consultar los registros financieros.</ChartMessage> : data.length === 0 ? <ChartMessage>Esperando datos para mostrar los últimos seis meses.</ChartMessage> : <div className="mt-2 flex h-36 items-end gap-2 border-b border-slate-200 px-1 sm:gap-4">{data.map((point) => <div key={point.key} className="flex h-full min-w-0 flex-1 flex-col justify-end"><div className="flex h-[118px] items-end justify-center gap-1 border-b border-dashed border-slate-100">{([[point.revenue,"bg-blue-600","Ingresos"],[point.costs,"bg-rose-500","Costos"]] as const).map(([amount,color,label])=><div key={label} title={`${label}: ${formatMoney(amount)}`} className={`w-3 rounded-t-sm sm:w-5 ${color} transition-[height]`} style={{height:amount?`${Math.max(3,amount/max*100)}%`:"0%"}}/>)}</div><span className="mt-2 truncate text-center text-[9px] capitalize text-slate-500">{point.label}</span></div>)}</div>}
  </ChartFrame>;
}
function MonthlyChartCard({ title, subtitle, icon, data, loading, error, color, format, emptyText }: { title: string; subtitle: string; icon: React.ReactNode; data: MonthlyValue[]; loading: boolean; error: boolean; color: string; format: (value: number) => string; emptyText: string }) {
  const max = Math.max(...data.map((point) => point.value), 1);
  return <ChartFrame title={title} subtitle={subtitle} icon={icon}>{loading ? <ChartMessage>Consultando registros…</ChartMessage> : error ? <ChartMessage danger>No se pudo consultar la información.</ChartMessage> : data.length === 0 ? <ChartMessage>{emptyText}</ChartMessage> : <><div className="mt-4 flex h-36 items-end gap-2 border-b border-slate-200 px-1 sm:gap-4">{data.map((point) => <div key={point.key} className="flex h-full min-w-0 flex-1 flex-col justify-end"><div className="relative flex h-[118px] items-end justify-center border-b border-dashed border-slate-100"><div title={format(point.value)} className="w-6 rounded-t-md transition-[height] sm:w-9" style={{height:point.value?`${Math.max(3,point.value/max*100)}%`:"0%",backgroundColor:color}}/></div><span className="mt-2 truncate text-center text-[9px] capitalize text-slate-500">{point.label}</span></div>)}</div><p className="mt-2 text-right text-[9px] text-slate-400">{data.reduce((sum,point)=>sum+point.value,0).toLocaleString("es-PE",{maximumFractionDigits:1})} {title.toLowerCase().includes("viajes")?"viajes":"litros"} en el periodo</p></>}</ChartFrame>;
}
function FleetStatusChart({ vehicles, loading, error }: { vehicles: DashboardRecord[]; loading: boolean; error: boolean }) {
  const categories = [
    { label: "Disponible", color: "#2563eb", test: (state: string) => /disponible|activo|operativo/.test(state) },
    { label: "En viaje", color: "#0f9f81", test: (state: string) => /viaje|tr[aá]nsito/.test(state) },
    { label: "Mantenimiento", color: "#f59e0b", test: (state: string) => /mantenimiento/.test(state) },
    { label: "Inactivo", color: "#94a3b8", test: (state: string) => /inactivo|descanso|baja/.test(state) },
  ].map((category) => ({ ...category, value: vehicles.filter((vehicle) => category.test(value(vehicle, "estado", "status").toLocaleLowerCase("es"))).length }));
  const total = categories.reduce((sum, category) => sum + category.value, 0);
  const circumference = 2 * Math.PI * 42;
  let offset = 0;
  return <ChartFrame title="Estado de la flota" subtitle="Distribución actual de vehículos" icon={<Truck size={15}/>}>{loading ? <ChartMessage>Consultando vehículos…</ChartMessage> : error ? <ChartMessage danger>No se pudo consultar la flota.</ChartMessage> : <div className="mt-3 flex items-center justify-center gap-6 py-2"><div className="relative size-32 shrink-0"><svg viewBox="0 0 100 100" className="size-full -rotate-90" role="img" aria-label={`Estado de ${total} vehículos`}>{categories.map((category) => { const dash = total ? category.value / total * circumference : 0; const currentOffset = offset; offset += dash; return <circle key={category.label} cx="50" cy="50" r="42" fill="none" stroke={category.color} strokeWidth="12" strokeDasharray={`${dash} ${circumference-dash}`} strokeDashoffset={-currentOffset}/>; })}</svg><span className="absolute inset-0 flex flex-col items-center justify-center"><strong className="text-2xl text-slate-800">{total}</strong><span className="text-[9px] text-slate-500">vehículos</span></span></div><ul className="space-y-2">{categories.map((category)=><li key={category.label} className="flex items-center gap-2 text-[11px] text-slate-600"><i className="size-2 rounded-full" style={{backgroundColor:category.color}}/><span>{category.label}</span><strong className="ml-auto pl-3 text-slate-800">{category.value}</strong></li>)}</ul></div>}</ChartFrame>;
}
function ChartMessage({ children, danger = false }: { children: React.ReactNode; danger?: boolean }) { return <div className={`mt-3 flex h-36 items-center justify-center rounded-md text-center text-xs ${danger?"bg-red-50 text-red-700":"bg-slate-50 text-slate-500"}`}>{children}</div>; }
function Alert({ icon, title, description, onClick }: { icon: React.ReactNode; title: string; description: string; onClick: () => void }) { return <button onClick={onClick} className="flex h-[61px] items-center gap-3 rounded-lg border border-[#dfe6f0] bg-white px-3 text-left shadow-[0_1px_2px_rgba(16,42,76,.10)] hover:border-[#c6d4e8]"><span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-[#f5f8fd]">{icon}</span><span className="min-w-0 flex-1"><span className="block truncate text-[10px] font-medium text-[#1b3357]">{title}</span><span className="mt-0.5 block text-[9px] text-[#8193ae]">{description}</span></span><MoreHorizontal size={15} className="rotate-[-45deg] shrink-0 text-[#7288a8]" /></button>; }
function Pill({ value }: { value: string }) { const palette: Record<string, string> = { "En tránsito": "bg-[#eef8ff] text-[#1681bb]", Recogido: "bg-[#edfbf2] text-[#00a45b]", Programado: "bg-[#fff8e9] text-[#e69a19]", Entregado: "bg-[#edfbf2] text-[#00a45b]", Entregada: "bg-[#edfbf2] text-[#00a45b]", Completado: "bg-[#edfbf2] text-[#00a45b]", Cancelado: "bg-[#fff0f0] text-[#e25656]", "Pendiente de programación": "bg-[#fff8e9] text-[#e69a19]", Asignada: "bg-[#eef4ff] text-[#2864ed]", Incidencia: "bg-[#fff0f0] text-[#e25656]" }; return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-1 text-[9px] leading-none ${palette[value] ?? "bg-slate-100 text-slate-600"}`}>{value}</span>; }
function Initials({ value }: { value: string }) { return <span className="flex size-[21px] items-center justify-center rounded-full bg-[#edf3ff] text-[8px] font-medium text-[#2864ed]">{value}</span>; }
function value(record: DashboardRecord | undefined, ...keys: string[]): string { for (const key of keys) { const item = record?.[key]; if (item !== undefined && item !== null && String(item).trim()) return String(item); } return ""; }
function belongsToTrip(load: DashboardRecord, tripId: string): boolean { if (!tripId) return false; if (value(load, "viaje_id", "trip_id") === tripId) return true; return Array.isArray(load.etapas) && (load.etapas as DashboardRecord[]).some((stage) => value(stage, "viaje_id", "id_viaje") === tripId); }
function arrayOfStrings(value: unknown): string[] { return Array.isArray(value) ? value.map((item) => String(item)) : []; }
function statusLabel(value: string): string { const labels: Record<string, string> = { en_transito: "En tránsito", en_curso: "En curso", programado: "Programado", entregado: "Entregado", entregada: "Entregada", completado: "Completado", pendiente_programacion: "Pendiente de programación", pendiente: "Pendiente", asignada: "Asignada", cancelado: "Cancelado", cancelada: "Cancelada", incidencia: "Incidencia", recogido: "Recogido" }; return (labels[value.toLowerCase()] ?? value) || "—"; }
function formatDateTime(raw: string): string { if (!raw || raw === "—") return "—"; if (/^\d{1,2}:\d{2}/.test(raw)) return raw.slice(0, 5); const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(raw); const parsed = new Date(dateOnly ? `${raw}T12:00:00` : raw); if (Number.isNaN(parsed.getTime())) return raw; return parsed.toLocaleString("es-PE", { timeZone: "America/Lima", dateStyle: "short", ...(dateOnly ? {} : { timeStyle: "short" }) }); }
function initials(name: string): string { return name && name !== "—" ? name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "—"; }
