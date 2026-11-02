export type ApiPage<T> = { total: number; items: T[]; page: number; pages: number };
export type ApiRecord = { id: string; data?: Record<string, unknown>; created_at?: string; updated_at?: string; created_by?: string | null };
