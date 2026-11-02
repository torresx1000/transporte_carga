import type { ApiRecord } from "@/types/api/common";

export type ApiGasto = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type GastoCreate = Record<string, unknown>;
export type GastoUpdate = Partial<GastoCreate>;

