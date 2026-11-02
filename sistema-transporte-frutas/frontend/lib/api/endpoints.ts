// NEXT_PUBLIC_API_URL ya incluye el prefijo /api/v1. Mantener aquí solo
// las rutas relativas evita solicitar /api/v1/api/v1/... y recibir 404.
const api = (path: string) => path;

export const endpoints = {
  auth: { login: "/api/auth/login", refresh: "/api/auth/refresh", logout: "/api/auth/logout" },
  clientes: api("/clientes"), cargas: api("/cargas"), conductores: api("/conductores"),
  vehiculos: api("/vehiculos"), rutas: api("/rutas"), cotizaciones: api("/cotizaciones"),
  retornos: api("/retornos"), viajes: api("/viajes"), documentos: api("/documentos"),
  gastos: api("/gastos"), combustible: api("/combustible"), mantenimiento: api("/mantenimiento"),
  pagos: api("/pagos"), reportes: api("/reportes"), usuarios: api("/usuarios"),
  configuracion: api("/configuracion"), portal: api("/portal"),
};
