import type { ApiRecord } from "@/types/api/common";

export type ApiPago = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type PagoCreate = Record<string, unknown>;
export type PagoUpdate = Partial<PagoCreate>;

