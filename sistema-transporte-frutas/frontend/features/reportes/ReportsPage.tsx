"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  FileBarChart,
  Package,
  RotateCcw,
  Truck,
  Users,
} from "lucide-react";
import { useDashboardReport, useFuelConsumptionReport } from "@/hooks/useReportes";
import { useCatalog } from "@/features/transporte/data";
import { api } from "@/lib/api/client";
import { createResourceService, type ResourceName } from "@/services/resource.service";
import { getApiError } from "@/lib/api/errors";
import { ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";

const reportTypes: { value: ResourceName; label: string }[] = [
  { value: "viajes", label: "Viajes" },
  { value: "cargas", label: "Cargas" },
  { value: "pagos", label: "Pagos" },
  { value: "gastos", label: "Gastos" },
  { value: "combustible", label: "Combustible" },
  { value: "mantenimiento", label: "Mantenimiento" },
  { value: "documentos", label: "Documentos" },
  { value: "retornos", label: "Retornos" },
];

type DashboardData = {
  clientes?: number;
  cargas?: number;
  cargas_en_transito?: number;
  viajes?: number;
  retornos?: number;
};

type FuelRow = {
  vehiculo_id: string;
  litros: number;
  costo_centimos: number;
};

type ReportVehicle = {
  id: string;
  placa: string;
  codigo_flota?: string;
  tipo?: string;
};

type VehicleCostItem = {
  id: string;
  tipo: string;
  fecha?: string | null;
  viaje_id?: string | null;
  viaje_codigo?: string | null;
  concepto?: string | null;
  detalle?: string | null;
  litros_milesimas?: number;
  monto_centimos: number;
};

type VehicleCostReport = {
  vehiculo_id: string;
  placa: string;
  total_centimos: number;
  cantidad_registros: number;
  items: VehicleCostItem[];
};

const currency = (cents: number) =>
  `S/ ${(cents / 100).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function ReportsPage({ initialForm = false }: { initialForm?: boolean }) {
  const dashboard = useDashboardReport();
  const fuel = useFuelConsumptionReport();
  const vehicles = useCatalog<ReportVehicle>("vehiculos");
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [created, setCreated] = useState(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const vehicleCosts = useQuery({
    queryKey: ["reportes", "costos-vehiculo", selectedVehicleId],
    queryFn: async () =>
      (await api.get<VehicleCostReport>(`/reportes/costos-vehiculo/${selectedVehicleId}`)).data,
    enabled: Boolean(selectedVehicleId),
  });

  async function exportModule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setCreated(false);
    setGenerating(true);
    const form = new FormData(event.currentTarget);
    const resourceName = String(form.get("module")) as ResourceName;
    const name = String(form.get("name") || resourceName);

    try {
      const result = await createResourceService(resourceName).list({ page: 1, page_size: 100 });
      const keys = Array.from(new Set(result.items.flatMap((row) => Object.keys(row))));
      const csv = [
        keys.join(","),
        ...result.items.map((row) =>
          keys.map((key) => `"${String(row[key] ?? "").replaceAll('"', '""')}"`).join(","),
        ),
      ].join("\n");
      const url = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${name.replace(/[^\p{L}\p{N}-]+/gu, "-")}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      setCreated(true);
    } catch (cause) {
      setError(getApiError(cause));
    } finally {
      setGenerating(false);
    }
  }

  const fuelRows = Array.isArray(fuel.data) ? (fuel.data as FuelRow[]) : [];
  const fuelTotalLiters = fuelRows.reduce((total, row) => total + Number(row.litros || 0), 0);
  const fuelTotalCost = fuelRows.reduce((total, row) => total + Number(row.costo_centimos || 0), 0);
  const data = dashboard.data as DashboardData | undefined;
  const selectedVehicle = vehicles.data?.find((vehicle) => vehicle.id === selectedVehicleId);

  if (initialForm) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10">
        <div className="mx-auto max-w-[800px]">
          <div className="mb-6 flex items-center gap-2 text-xs text-[#87918c]">
            <Link href="/reportes" className="inline-flex items-center gap-1.5">
              <ArrowLeft size={14} /> Reportes
            </Link>
            <span>/</span>
            <span>Nuevo reporte</span>
          </div>
          <h1 className="text-[27px] font-semibold">Exportar registros</h1>
          <p className="mt-1 text-sm text-[#7a8580]">
            Selecciona un módulo para descargar sus datos actuales.
          </p>
          <form
            onSubmit={exportModule}
            className="mt-6 space-y-4 rounded-xl border border-[#e8ece9] bg-white p-6"
          >
            <label className="block text-xs font-medium">
              Nombre del archivo
              <input
                name="name"
                required
                defaultValue="reporte-operativo"
                className="mt-1.5 h-10 w-full rounded-lg border border-[#e5eae6] px-3"
              />
            </label>
            <label className="block text-xs font-medium">
              Datos a exportar
              <select
                name="module"
                className="mt-1.5 h-10 w-full rounded-lg border border-[#e5eae6] bg-white px-3"
              >
                {reportTypes.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
            {created && (
              <p role="status" className="text-xs text-emerald-700">
                Archivo generado con registros consultados a la API.
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Link href="/reportes" className="rounded-lg border px-4 py-2 text-xs">
                Cancelar
              </Link>
              <button
                disabled={generating}
                className="inline-flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2 text-xs text-white disabled:opacity-60"
              >
                <Download size={14} />
                {generating ? "Consultando…" : "Descargar CSV"}
              </button>
            </div>
          </form>
        </div>
      </main>
    );
  }

  if (dashboard.isLoading) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] p-8">
        <TableSkeleton />
      </main>
    );
  }
  if (dashboard.isError) {
    return (
      <main className="min-h-screen bg-[#f7f8fa] p-8">
        <ErrorState
          message={getApiError(dashboard.error)}
          onRetry={() => void dashboard.refetch()}
        />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10">
      <div className="mx-auto max-w-[1440px]">
        <header className="mb-7 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-2 text-xs text-[#87918c]">Administración / Finanzas / Reportes</p>
            <h1 className="text-[28px] font-semibold tracking-[-.8px]">Reportes</h1>
            <p className="mt-1 text-sm text-[#7a8580]">
              Indicadores operativos y costos calculados con los registros disponibles.
            </p>
          </div>
          <Link
            href="/reportes/nuevo"
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#2563EB] px-4 text-sm font-medium text-white shadow-sm transition hover:bg-[#1D4ED8]"
          >
            <FileBarChart size={16} /> Exportar datos
          </Link>
        </header>

        <section className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-5">
          <Metric title="Clientes" value={data?.clientes ?? 0} icon={<Users size={17} />} />
          <Metric title="Cargas registradas" value={data?.cargas ?? 0} icon={<Package size={17} />} />
          <Metric
            title="Cargas en tránsito"
            value={data?.cargas_en_transito ?? 0}
            icon={<Truck size={17} />}
          />
          <Metric title="Viajes" value={data?.viajes ?? 0} icon={<Truck size={17} />} />
          <Metric title="Retornos" value={data?.retornos ?? 0} icon={<RotateCcw size={17} />} />
        </section>

        <section className="mb-6 overflow-hidden rounded-xl border border-[#e8ece9] bg-white shadow-[0_1px_2px_rgba(20,40,30,.03)]">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#edf0ee] px-5 py-4 sm:px-6">
            <div>
              <h2 className="text-[15px] font-semibold text-[#28332e]">
                Combustible abastecido por vehículo
              </h2>
              <p className="mt-0.5 text-xs text-[#89938e]">
                Litros y costo total de los abastecimientos registrados por unidad.
              </p>
            </div>
            <div className="flex gap-5">
              <Summary
                label="Litros reportados"
                value={
                  fuel.isLoading
                    ? "—"
                    : fuel.isError
                      ? "No disponible"
                      : `${fuelTotalLiters.toLocaleString("es-PE")} L`
                }
              />
              <Summary
                label="Costo registrado"
                value={fuel.isLoading ? "—" : fuel.isError ? "No disponible" : currency(fuelTotalCost)}
              />
            </div>
          </div>
          {fuel.isLoading ? (
            <div className="p-5">
              <TableSkeleton rows={3} />
            </div>
          ) : fuel.isError ? (
            <div className="p-5">
              <ErrorState message={getApiError(fuel.error)} onRetry={() => void fuel.refetch()} />
            </div>
          ) : fuelRows.length === 0 ? (
            <p className="py-10 text-center text-sm text-[#89938e]">
              No hay consumo de combustible registrado.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left">
                <thead className="bg-[#fafbfa] text-[10px] font-semibold uppercase tracking-[.08em] text-[#909a95]">
                  <tr>
                    {["Placa", "Código de flota", "Litros abastecidos", "Costo registrado", "Detalle"].map((heading) => (
                      <th key={heading} className="px-5 py-3">{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f0f2f1]">
                  {fuelRows.map((row) => {
                    const vehicle = vehicles.data?.find(
                      (item) => String(item.id) === String(row.vehiculo_id),
                    );
                    return (
                      <tr key={row.vehiculo_id} className="transition hover:bg-[#fbfcfb]">
                        <td className="px-5 py-3.5 text-sm font-semibold text-[#28332e]">
                          {vehicles.isLoading
                            ? "Buscando placa…"
                            : vehicle?.placa || "Placa no disponible"}
                        </td>
                        <td className="px-5 py-3.5 text-xs text-[#66736c]">
                          {vehicle?.codigo_flota || "—"}
                        </td>
                        <td className="px-5 py-3.5 text-sm text-[#56625c]">
                          {Number(row.litros || 0).toLocaleString("es-PE")} litros
                        </td>
                        <td className="px-5 py-3.5 text-sm font-medium text-[#28332e]">
                          {currency(Number(row.costo_centimos || 0))}
                        </td>
                        <td className="px-5 py-3.5">
                          <button
                            type="button"
                            onClick={() => setSelectedVehicleId(row.vehiculo_id)}
                            className="text-xs font-medium text-[#2563EB] hover:underline"
                          >
                            Ver detalle de costos
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="mb-6 overflow-hidden rounded-xl border border-[#e8ece9] bg-white shadow-[0_1px_2px_rgba(20,40,30,.03)]">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-[#edf0ee] px-5 py-4 sm:px-6">
            <div>
              <h2 className="text-[15px] font-semibold text-[#28332e]">Costos acumulados por vehículo</h2>
              <p className="mt-0.5 text-xs text-[#89938e]">
                Combustible y gastos relacionados directamente con la unidad o sus viajes.
              </p>
            </div>
            <label className="w-full text-xs font-medium text-[#59655f] sm:max-w-sm">
              Vehículo
              <select
                value={selectedVehicleId}
                onChange={(event) => setSelectedVehicleId(event.target.value)}
                disabled={vehicles.isLoading || vehicles.isError}
                className="mt-1.5 h-10 w-full rounded-lg border border-[#e7ebe8] bg-white px-3 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#DBEAFE] disabled:bg-[#f7f8fa]"
              >
                <option value="">
                  {vehicles.isLoading ? "Cargando vehículos…" : "Selecciona una unidad"}
                </option>
                {vehicles.data?.map((vehicle) => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.placa}
                    {vehicle.codigo_flota ? ` · Flota ${vehicle.codigo_flota}` : ""}
                    {vehicle.tipo ? ` · ${vehicle.tipo}` : ""}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {vehicles.isError ? (
            <div className="p-5">
              <ErrorState
                message={getApiError(vehicles.error)}
                onRetry={() => void vehicles.refetch()}
              />
            </div>
          ) : !selectedVehicleId ? (
            <p className="py-9 text-center text-sm text-[#89938e]">
              Selecciona un vehículo o usa «Ver costos» en la tabla de combustible para consultar su detalle.
            </p>
          ) : vehicleCosts.isLoading ? (
            <div className="p-5">
              <TableSkeleton rows={3} />
            </div>
          ) : vehicleCosts.isError ? (
            <div className="p-5">
              <ErrorState
                message={getApiError(vehicleCosts.error)}
                onRetry={() => void vehicleCosts.refetch()}
              />
            </div>
          ) : vehicleCosts.data ? (
            <>
              <div className="grid gap-3 border-b border-[#edf0ee] p-5 sm:grid-cols-3 sm:px-6">
                <Summary
                  label="Vehículo"
                  value={vehicleCosts.data.placa}
                  detail={selectedVehicle?.codigo_flota
                    ? `Código de flota ${selectedVehicle.codigo_flota}`
                    : "Placa de la unidad"}
                />
                <Summary
                  label="Registros de costo"
                  value={String(vehicleCosts.data.cantidad_registros)}
                  detail="Combustible y gastos"
                />
                <Summary
                  label="Total acumulado"
                  value={currency(vehicleCosts.data.total_centimos)}
                  detail="Según registros disponibles"
                />
              </div>
              <div className="flex justify-end px-5 pt-4 sm:px-6">
                <button
                  type="button"
                  onClick={() => downloadVehicleCosts(vehicleCosts.data)}
                  className="inline-flex items-center gap-2 rounded-lg border border-[#e6eae7] px-3 py-2 text-xs font-medium text-[#59655f] transition hover:bg-[#f8faf9]"
                >
                  <Download size={14} /> Descargar CSV
                </button>
              </div>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[900px] text-left">
                  <thead className="bg-[#fafbfa] text-[10px] font-semibold uppercase tracking-[.08em] text-[#909a95]">
                    <tr>
                      {["Fecha", "Tipo", "Viaje", "Concepto", "Detalle", "Importe"].map((heading) => (
                        <th key={heading} className="px-5 py-3">{heading}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f0f2f1]">
                    {vehicleCosts.data.items.map((item) => (
                      <tr key={`${item.tipo}-${item.id}`} className="transition hover:bg-[#fbfcfb]">
                        <td className="whitespace-nowrap px-5 py-3.5 text-xs text-[#56625c]">
                          {formatDate(item.fecha)}
                        </td>
                        <td className="px-5 py-3.5 text-xs text-[#56625c]">
                          {item.tipo === "combustible" ? "Combustible" : "Gasto"}
                        </td>
                        <td className="px-5 py-3.5 text-xs text-[#56625c]">
                          {item.viaje_codigo || item.viaje_id || "Sin viaje"}
                        </td>
                        <td className="px-5 py-3.5 text-xs text-[#56625c]">
                          {item.concepto || "—"}
                        </td>
                        <td className="max-w-[360px] px-5 py-3.5 text-xs text-[#66736c]">
                          {item.detalle || "—"}
                        </td>
                        <td className="whitespace-nowrap px-5 py-3.5 text-xs font-medium text-[#28332e]">
                          {currency(item.monto_centimos)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!vehicleCosts.data.items.length && (
                  <p className="py-8 text-center text-sm text-[#89938e]">
                    Este vehículo todavía no tiene costos registrados.
                  </p>
                )}
              </div>
            </>
          ) : null}
        </section>

        <section className="rounded-xl border border-[#e8ece9] bg-white p-5 shadow-[0_1px_2px_rgba(20,40,30,.03)] sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-[15px] font-semibold text-[#28332e]">Retornos</h2>
              <p className="mt-0.5 text-xs text-[#89938e]">
                Cantidad de registros de retorno disponibles en el sistema.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-semibold text-[#28332e]">{data?.retornos ?? 0}</span>
              <Link href="/retornos" className="text-xs font-medium text-[#2563EB] hover:underline">
                Abrir retornos →
              </Link>
            </div>
          </div>
        </section>
        <p className="mt-5 text-[11px] text-[#9ba49f]">
          Los totales reflejan únicamente los movimientos registrados; los abastecimientos y gastos
          históricos sin vínculo al vehículo o al viaje pueden no aparecer en el consolidado.
        </p>
      </div>
    </main>
  );
}

function Metric({ title, value, icon }: { title: string; value: number; icon: React.ReactNode }) {
  return (
    <article className="rounded-xl border border-[#e8ece9] bg-white p-4">
      <div className="flex items-center justify-between text-[#7a8580]">
        <span className="text-xs font-medium">{title}</span>
        <span className="text-[#43845e]">{icon}</span>
      </div>
      <strong className="mt-4 block text-2xl font-semibold text-[#28332e]">{value}</strong>
      <p className="mt-1 text-[11px] text-[#89938e]">Registros activos</p>
    </article>
  );
}

function Summary({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-medium uppercase tracking-[.08em] text-[#89938e]">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-[#28332e]" title={value}>{value}</p>
      {detail && <p className="mt-0.5 truncate text-[10px] text-[#89938e]" title={detail}>{detail}</p>}
    </div>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const dateOnly = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3])).toLocaleDateString("es-PE")
    : new Date(value).toLocaleDateString("es-PE");
}

function downloadVehicleCosts(report: VehicleCostReport) {
  const headers = ["Vehículo", "ID vehículo", "Fecha", "Tipo", "Viaje", "Concepto", "Detalle", "Litros", "Importe S/"];
  const rows = report.items.map((item) => [
    report.placa,
    report.vehiculo_id,
    item.fecha ?? "",
    item.tipo,
    item.viaje_codigo ?? item.viaje_id ?? "",
    item.concepto ?? "",
    item.detalle ?? "",
    item.litros_milesimas == null ? "" : (item.litros_milesimas / 1000).toString(),
    (item.monto_centimos / 100).toFixed(2),
  ]);
  const csv = [headers, ...rows]
    .map((row) => row.map((value) => JSON.stringify(String(value))).join(","))
    .join("\n");
  const url = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `costos-vehiculo-${report.placa}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
