export function canReactivateInactiveClient(role: string | undefined, status: string): boolean {
  return role === "admin" && status === "inactivo";
}

export function canRestoreArchivedClient(role: string | undefined, archivedClientId: string | null): boolean {
  return role === "admin" && Boolean(archivedClientId);
}
