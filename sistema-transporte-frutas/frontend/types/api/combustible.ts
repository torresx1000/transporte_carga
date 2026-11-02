import type { ApiRecord } from "@/types/api/common";

export type ApiCombustible = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type CombustibleCreate = Record<string, unknown>;
export type CombustibleUpdate = Partial<CombustibleCreate>;

