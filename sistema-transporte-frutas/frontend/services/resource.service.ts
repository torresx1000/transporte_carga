import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { components } from "@/types/api/schema";

export type ResourceName =
  | "viajes"
  | "pagos"
  | "combustible"
  | "gastos"
  | "mantenimiento"
  | "documentos"
  | "usuarios"
  | "clientes"
  | "conductores"
  | "vehiculos"
  | "rutas"
  | "cotizaciones"
  | "retornos"
  | "cargas"
  | "configuracion";
export type ResourceRecord = Record<string, string> & { id?: string };
type Page<T> = { total: number; items: T[]; page: number; pages: number };
type SchemaResource =
  | components["schemas"]["ConductorResponse"]
  | components["schemas"]["VehiculoResponse"]
  | components["schemas"]["RutaResponse"];
const endpointFor = (resource: ResourceName) => endpoints[resource];
const directBodyResources: ResourceName[] = [
  "cargas",
  "viajes",
  "clientes",
  "conductores",
  "vehiculos",
  "rutas",
];

function unwrap(
  value: Record<string, unknown>,
  resource: ResourceName,
): ResourceRecord {
  const nested =
    value.data && typeof value.data === "object"
      ? (value.data as Record<string, unknown>)
      : {};
  const result = { ...nested, ...value };
  delete result.data;
  const flat = Object.fromEntries(
    Object.entries(result).map(([key, item]) => [
      key,
      item == null ? "" : resource === "rutas" && key === "paradas" ? JSON.stringify(item) : String(item),
    ]),
  ) as ResourceRecord;
  if (resource === "usuarios") {
    if ("active" in result) flat.status = result.active ? "Activo" : "Suspendido";
    flat.role_label = String(result.role_name ?? resourceRole(flat.role));
  }
  return flat;
}

function resourceRole(role?: string) {
  return (
    (
      {
        admin: "Administrador",
        operador: "Operaciones",
        chofer: "Conductor",
        cliente: "Cliente",
      } as Record<string, string>
    )[role ?? ""] ??
    role ??
    ""
  );
}
function toPayload(
  resource: ResourceName,
  input: ResourceRecord,
): Record<string, unknown> {
  const payload: Record<string, unknown> = { ...input };
  delete payload.id;
  delete payload.file;
  delete payload.created_at;
  delete payload.updated_at;
  delete payload.created_by;
  if (["conductores", "vehiculos", "rutas"].includes(resource)) {
    const dateFields =
      resource === "conductores"
        ? ["licencia_vence", "examen_medico_vence"]
        : [];
    const optionalTextFields =
      resource === "conductores"
        ? ["telefono", "correo"]
        : resource === "vehiculos"
          ? ["vin", "placa_remolque"]
          : ["notas"];
    for (const field of dateFields)
      if (payload[field] === "") payload[field] = null;
    for (const field of optionalTextFields)
      if (payload[field] === "") payload[field] = null;
    if (resource === "vehiculos" && String(payload.tiene_remolque).toLowerCase() === "false")
      payload.placa_remolque = null;
    for (const field of [
      "origen_id",
      "destino_id",
      "capacidad_kg",
      "distancia_km",
      "duracion_minutos",
      "peajes_minor",
      "tarifa_referencial_minor",
    ]) {
      if (payload[field] === "") delete payload[field];
      else if (payload[field] !== undefined)
        payload[field] = Number(payload[field]);
    }
    if (resource === "rutas" && typeof payload.paradas === "string") {
      payload.paradas = JSON.parse(payload.paradas || "[]");
    }
  }
  if (resource === "usuarios") {
    payload.role =
      (
        {
          Administrador: "admin",
          Operaciones: "operador",
          "Solo lectura": "operador",
          Finanzas: "operador",
          Conductor: "chofer",
          Cliente: "cliente",
        } as Record<string, string>
      )[String(payload.role)] ??
      payload.role ??
      "operador";
    if ("status" in payload) {
      payload.active = payload.status === "Activo";
      delete payload.status;
    }
  }
  if (["pagos", "gastos"].includes(resource) && payload.amount !== undefined) {
    payload.monto_centimos = Math.round(Number(payload.amount) * 100);
    delete payload.amount;
  }
  if (resource === "combustible") {
    if (payload.liters !== undefined) {
      payload.litros_milesimas = Math.round(
        Number(String(payload.liters).replace(/[^\d.]/g, "")) * 1000,
      );
      delete payload.liters;
    }
    if (payload.price !== undefined) {
      payload.precio_centimos = Math.round(Number(payload.price) * 100);
      delete payload.price;
    }
    if (payload.odometer !== undefined)
      payload.odometer = Number(payload.odometer);
  }
  return payload;
}

export function createResourceService(resource: ResourceName) {
  const endpoint = endpointFor(resource);
  return {
    async list(
      params: {
        page?: number;
        page_size?: number;
        q?: string;
        estado?: string;
        tipo?: string;
      } = {},
    ) {
      const { data } = await api.get<
        Page<Record<string, unknown>> | Record<string, unknown>[]
      >(endpoint, { params });
      if (Array.isArray(data))
        return {
          total: data.length,
          items: data.map((item) => unwrap(item, resource)),
          page: 1,
          pages: 1,
        };
      return {
        ...data,
        items: (data.items ?? []).map((item) =>
          unwrap(item as Record<string, unknown>, resource),
        ),
      } as Page<ResourceRecord>;
    },
    async get(id: string) {
      const { data } = await api.get<Record<string, unknown>>(
        `${endpoint}/${id}`,
      );
      return unwrap(data, resource);
    },
    async create(payload: ResourceRecord) {
      const body = toPayload(resource, payload);
      const { data } =
        resource === "usuarios" || directBodyResources.includes(resource)
          ? await api.post<SchemaResource | Record<string, unknown>>(
              endpoint,
              body,
            )
          : await api.post<Record<string, unknown>>(endpoint, { data: body });
      return unwrap(data, resource);
    },
    async update(id: string, payload: ResourceRecord) {
      const body = toPayload(resource, payload);
      const { data } =
        resource === "usuarios" || directBodyResources.includes(resource)
          ? await api.patch<SchemaResource | Record<string, unknown>>(
              `${endpoint}/${id}`,
              body,
            )
          : await api.patch<Record<string, unknown>>(`${endpoint}/${id}`, {
              data: body,
            });
      return unwrap(data, resource);
    },
    async suggestCode() {
      const { data } = await api.get<{ code: string }>(
        `${endpoint}/siguiente-codigo`,
      );
      return data.code;
    },
    async reactivate(id: string) {
      const { data } = await api.post<SchemaResource | Record<string, unknown>>(
        `${endpoint}/${id}/reactivar`,
      );
      return unwrap(data, resource);
    },
    async remove(id: string) {
      await api.delete(`${endpoint}/${id}`);
    },
  };
}
