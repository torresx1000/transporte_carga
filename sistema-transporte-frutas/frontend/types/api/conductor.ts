import type { ApiRecord } from "@/types/api/common";

export type ApiConductor = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type ConductorCreate = Record<string, unknown>;
export type ConductorUpdate = Partial<ConductorCreate>;

