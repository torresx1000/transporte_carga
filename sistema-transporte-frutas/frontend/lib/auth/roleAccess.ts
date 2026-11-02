export type Role = "admin" | "operador" | "chofer" | "cliente" | string;

export function getRoleLandingPath(role: Role | undefined): string {
  if (role === "cliente") return "/cliente";
  if (role === "chofer") return "/acceso-pendiente";
  return "/";
}

export function filterAdminNavigation<T extends { href: string }>(items: readonly T[], role: Role | undefined): T[] {
  if (role === "admin") return [...items];
  if (role === "operador") return items.filter(({ href }) => href !== "/usuarios" && href !== "/configuracion");
  return [];
}

export function isOperatorRestrictedPath(path: string): boolean {
  return ["/usuarios", "/configuracion"].some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}
