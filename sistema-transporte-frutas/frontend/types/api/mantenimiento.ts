import type { ApiRecord } from "@/types/api/common";

export type ApiMantenimiento = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type MantenimientoCreate = Record<string, unknown>;
export type MantenimientoUpdate = Partial<MantenimientoCreate>;

