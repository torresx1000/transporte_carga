import type { ApiRecord } from "@/types/api/common";

export type ApiDocumento = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type DocumentoCreate = Record<string, unknown>;
export type DocumentoUpdate = Partial<DocumentoCreate>;

