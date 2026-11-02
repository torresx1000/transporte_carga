import type { ApiRecord } from "@/types/api/common";

export type ApiCotizacion = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type CotizacionCreate = Record<string, unknown>;
export type CotizacionUpdate = Partial<CotizacionCreate>;

