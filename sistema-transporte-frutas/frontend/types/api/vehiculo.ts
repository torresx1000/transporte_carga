import type { ApiRecord } from "@/types/api/common";

export type ApiVehiculo = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type VehiculoCreate = Record<string, unknown>;
export type VehiculoUpdate = Partial<VehiculoCreate>;

