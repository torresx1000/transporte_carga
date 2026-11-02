import type { ApiRecord } from "@/types/api/common";

export type ApiRetorno = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type RetornoCreate = Record<string, unknown>;
export type RetornoUpdate = Partial<RetornoCreate>;

