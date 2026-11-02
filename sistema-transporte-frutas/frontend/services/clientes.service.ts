import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { components, paths } from "@/types/api/schema";
import type { ClientPayload, ClientUpdatePayload } from "@/types/api/cliente";
import type { Client } from "@/types/client";

export type ClientFilters = NonNullable<paths["/api/v1/clientes"]["get"]["parameters"]["query"]>;
export type ClientPage = components["schemas"]["PageResponse_ClienteResponse_"];
export type ApiClientRecord = components["schemas"]["ClienteResponse"];

function toClientView(record: ApiClientRecord): Client {
  return { ...record, name: record.nombre };
}

export const clientesService = {
  async list(filters: ClientFilters = {}): Promise<Omit<ClientPage, "items"> & { items: Client[] }> {
    const { data } = await api.get<ClientPage>(endpoints.clientes, { params: filters });
    return { ...data, items: data.items.map(toClientView) };
  },
  async get(id: string): Promise<Client> {
    const { data } = await api.get<ApiClientRecord>(`${endpoints.clientes}/${id}`);
    return toClientView(data);
  },
  async getCrateHistory(id: string) {
    const { data } = await api.get<components["schemas"]["ClienteCrateHistoryResponse"]>(`${endpoints.clientes}/${id}/estado-jabas`);
    return data;
  },
  async create(payload: ClientPayload): Promise<Client> {
    const { data } = await api.post<ApiClientRecord>(endpoints.clientes, payload);
    return toClientView(data);
  },
  async update(id: string, payload: ClientUpdatePayload): Promise<Client> {
    const { data } = await api.patch<ApiClientRecord>(`${endpoints.clientes}/${id}`, payload);
    return toClientView(data);
  },
  async reactivate(id: string): Promise<Client> {
    const { data } = await api.post<ApiClientRecord>(`${endpoints.clientes}/${id}/reactivar`);
    return toClientView(data);
  },
  async remove(id: string): Promise<void> {
    await api.delete(`${endpoints.clientes}/${id}`);
  },
};
