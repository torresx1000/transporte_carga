import type { ApiRecord } from "@/types/api/common";

export type ApiConfiguracion = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type ConfiguracionCreate = Record<string, unknown>;
export type ConfiguracionUpdate = Partial<ConfiguracionCreate>;

