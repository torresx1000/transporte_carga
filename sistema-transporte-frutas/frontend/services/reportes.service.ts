import { api } from "@/lib/api/client";

export const reportesService = {
  async dashboard() { return (await api.get("/reportes/dashboard")).data; },
  async fuelConsumption() { return (await api.get("/reportes/consumo-combustible")).data; },
  async crateBalances() { return (await api.get("/reportes/jabas-pendientes")).data; },
  async tripProfitability(id: string) { return (await api.get(`/reportes/rentabilidad-viaje/${id}`)).data; },
};
