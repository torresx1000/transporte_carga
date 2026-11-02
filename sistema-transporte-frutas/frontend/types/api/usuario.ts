import type { ApiRecord } from "@/types/api/common";

export type ApiUsuario = ApiRecord & { codigo?: string; estado?: string; data?: Record<string, unknown> };
export type UsuarioCreate = Record<string, unknown>;
export type UsuarioUpdate = Partial<UsuarioCreate>;

