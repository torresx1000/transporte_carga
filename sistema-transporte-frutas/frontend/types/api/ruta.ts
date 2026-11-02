import type { ApiRecord } from "@/types/api/common";

export type ApiRuta = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type RutaCreate = Record<string, unknown>;
export type RutaUpdate = Partial<RutaCreate>;

