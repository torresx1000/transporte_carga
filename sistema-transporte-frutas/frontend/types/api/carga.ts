import type { ApiRecord } from "@/types/api/common";

export type ApiCarga = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type CargaCreate = Record<string, unknown>;
export type CargaUpdate = Partial<CargaCreate>;

