export const queryKeys = {
  clientes: { all: ["clientes"] as const, lists: () => ["clientes", "list"] as const, list: (filters: unknown) => ["clientes", "list", filters] as const, detail: (id: string) => ["clientes", "detail", id] as const },
  reportes: { dashboard: ["reportes", "dashboard"] as const },
};
