export type Role = "admin" | "operador" | "chofer" | "cliente" | string;

export function getRoleLandingPath(role: Role | undefined): string {
  if (role === "cliente") return "/cliente";
  if (role === "chofer") return "/acceso-pendiente";
  return "/";
}

export function hasPermission(permissions: readonly string[], permission: string): boolean {
  return permissions.includes("*") || permissions.includes(permission);
}

export function canViewModule(
  permissions: readonly string[],
  module: string,
): boolean {
  if (module === "roles") {
    return ["roles.ver", "roles.crear", "permisos.gestionar"].some((permission) =>
      hasPermission(permissions, permission),
    );
  }
  return hasPermission(permissions, `${module}.ver`);
}

export function canAccessAdminPath(
  path: string,
  permissions: readonly string[],
): boolean {
  if (path === "/") return permissions.length > 0;
  const moduleName = path.split("/").filter(Boolean)[0];
  if (!moduleName) return permissions.length > 0;
  return canViewModule(permissions, moduleName);
}
