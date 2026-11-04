import { NextRequest, NextResponse } from "next/server";
import { getRoleLandingPath } from "@/lib/auth/roleAccess";

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const isPortal = path === "/cliente" || path.startsWith("/cliente/");
  const isDriverPending = path === "/acceso-pendiente";
  const isForbidden = path === "/sin-permiso";
  const isAdmin =
    path === "/" ||
    [
      "/clientes",
      "/cargas",
      "/conductores",
      "/vehiculos",
      "/rutas",
      "/viajes",
      "/cotizaciones",
      "/pagos",
      "/gastos",
      "/combustible",
      "/mantenimiento",
      "/documentos",
      "/retornos",
      "/reportes",
      "/usuarios",
      "/roles",
      "/configuracion",
    ].some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
  const authenticated = request.cookies.get("tf_session")?.value === "1";
  const role = request.cookies.get("tf_role")?.value;
  if ((isPortal || isAdmin || isDriverPending) && !authenticated) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", path);
    return NextResponse.redirect(login);
  }
  if (isForbidden && role === "admin")
    return NextResponse.redirect(new URL("/", request.url));
  if (path === "/login" && authenticated)
    return NextResponse.redirect(
      new URL(getRoleLandingPath(role), request.url),
    );
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/login",
    "/acceso-pendiente",
    "/sin-permiso",
    "/clientes/:path*",
    "/cargas/:path*",
    "/conductores/:path*",
    "/vehiculos/:path*",
    "/rutas/:path*",
    "/viajes/:path*",
    "/cotizaciones/:path*",
    "/pagos/:path*",
    "/gastos/:path*",
    "/combustible/:path*",
    "/mantenimiento/:path*",
    "/documentos/:path*",
    "/retornos/:path*",
    "/reportes/:path*",
    "/usuarios/:path*",
    "/roles/:path*",
    "/configuracion/:path*",
    "/cliente/:path*",
  ],
};
