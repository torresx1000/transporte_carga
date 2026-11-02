"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

export function useDashboardReport() {
  return useQuery({ queryKey: ["reportes", "dashboard"], queryFn: async () => (await api.get("/reportes/dashboard")).data, refetchInterval: 60_000 });
}
export function useFuelConsumptionReport() {
  return useQuery({ queryKey: ["reportes", "consumo-combustible"], queryFn: async () => (await api.get("/reportes/consumo-combustible")).data });
}
export function useCrateBalanceReport() {
  return useQuery({ queryKey: ["reportes", "jabas-pendientes"], queryFn: async () => (await api.get("/reportes/jabas-pendientes")).data });
}
