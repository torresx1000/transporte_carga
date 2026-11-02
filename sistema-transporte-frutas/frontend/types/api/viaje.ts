import type { ApiRecord } from "@/types/api/common";

export type ApiViaje = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type ViajeCreate = Record<string, unknown>;
export type ViajeUpdate = Partial<ViajeCreate>;

