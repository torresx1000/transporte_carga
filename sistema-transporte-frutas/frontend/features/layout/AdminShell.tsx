"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, Boxes, BriefcaseBusiness, ChartNoAxesColumn, ChevronLeft, ClipboardList,
  FileText, Fuel, LayoutDashboard, MapPin, Menu, Plus, Route, Search,
  ShieldCheck, Truck, UserRound, Users, Wallet, Wrench, X, Bell,
} from "lucide-react";
import { useAuthStore } from "@/lib/auth/authStore";
import { canAccessAdminPath, canViewModule, hasPermission } from "@/lib/auth/roleAccess";
import { api } from "@/lib/api/client";

const navigation = [
  { title: "Principal", items: [{ label: "Panel principal", href: "/", icon: LayoutDashboard }] },
  { title: "Operaciones", items: [
    { label: "Clientes", href: "/clientes", icon: Users },
    { label: "Cargas", href: "/cargas", icon: Boxes },
    { label: "Cotizaciones", href: "/cotizaciones", icon: ClipboardList },
    { label: "Rutas", href: "/rutas", icon: Route },
    { label: "Viajes", href: "/viajes", icon: MapPin },
    { label: "Retornos", href: "/retornos", icon: Activity },
  ] },
  { title: "Flota", items: [
    { label: "Vehículos", href: "/vehiculos", icon: Truck },
    { label: "Conductores", href: "/conductores", icon: UserRound },
    { label: "Combustible", href: "/combustible", icon: Fuel },
    { label: "Mantenimiento", href: "/mantenimiento", icon: Wrench },
    { label: "Documentos", href: "/documentos", icon: FileText },
  ] },
  { title: "Finanzas", items: [
    { label: "Pagos", href: "/pagos", icon: Wallet },
    { label: "Gastos", href: "/gastos", icon: ChartNoAxesColumn },
    { label: "Reportes", href: "/reportes", icon: ChartNoAxesColumn },
  ] },
  { title: "Administración", items: [
    { label: "Usuarios", href: "/usuarios", icon: Users },
    { label: "Roles y permisos", href: "/roles", icon: ShieldCheck },
  ] },
];
const allNavigation = navigation.flatMap((group) => group.items);
const pageTitle: Record<string, string> = Object.fromEntries(allNavigation.map(({ href, label }) => [href, label]));

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const permissionsQuery = useQuery({
    queryKey: ["auth", "permissions"],
    queryFn: async () => (await api.get<{ role: string; permissions: string[] }>("/roles/me")).data,
    enabled: Boolean(user),
    refetchInterval: 15_000,
  });
  const permissions = useMemo(() => permissionsQuery.data?.permissions ?? [], [permissionsQuery.data?.permissions]);
  const visibleNavigation = useMemo(() => navigation.map((group) => ({
    ...group,
    items: group.items.filter(({ href }) => {
      const moduleName = href.split("/").filter(Boolean)[0];
      return moduleName ? canViewModule(permissions, moduleName) : permissions.length > 0;
    }),
  })).filter((group) => group.items.length), [permissions]);
  const visibleItems = visibleNavigation.flatMap((group) => group.items);
  const matches = visibleItems.filter((item) => item.label.toLocaleLowerCase("es").includes(search.trim().toLocaleLowerCase("es")));
  const activeHref = [...allNavigation].sort((a, b) => b.href.length - a.href.length).find(({ href }) => href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`))?.href;
  const title = pathname.includes("/nuevo") || pathname.includes("/nueva") ? `${pageTitle[activeHref ?? ""] ?? ""} · Nuevo` : pageTitle[activeHref ?? ""] ?? "Panel administrativo";
  const accessResolved = permissionsQuery.isSuccess;
  const hasPageAccess = canAccessAdminPath(pathname, permissions);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setCollapsed(window.localStorage.getItem("transfrutas-sidebar-collapsed") === "true");
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (accessResolved && !hasPageAccess) router.replace("/sin-permiso");
  }, [accessResolved, hasPageAccess, router]);

  function toggleCollapsed() {
    const next = !collapsed;
    window.localStorage.setItem("transfrutas-sidebar-collapsed", String(next));
    setCollapsed(next);
  }
  function showNotice(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2800);
  }
  function goToFirstMatch() {
    if (matches[0]) { router.push(matches[0].href); setSearchOpen(false); }
  }
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    clearSession();
    router.replace("/login");
  }

  return <div className="min-h-screen bg-[#f8fafc] text-slate-800">
    {mobileOpen && <button aria-label="Cerrar menú" onClick={() => setMobileOpen(false)} className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden" />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex ${collapsed ? "w-20" : "w-64"} flex-col border-r border-slate-200 bg-white shadow-sm transition-[width,transform] duration-200 ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
      <div className={`flex h-16 shrink-0 items-center border-b border-slate-100 ${collapsed ? "justify-center px-2" : "gap-3 px-5"}`}>
        <Link href="/" aria-label="TransFrutas, panel principal" className="flex min-w-0 items-center gap-3" onClick={() => setMobileOpen(false)}>
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm"><Truck size={21}/></span>
          {!collapsed && <span className="min-w-0"><span className="block truncate text-[15px] font-bold tracking-tight text-slate-800">TransFrutas</span><span className="block text-[10px] text-slate-500">Logística y transporte</span></span>}
        </Link>
        <button aria-label="Cerrar menú" onClick={() => setMobileOpen(false)} className="ml-auto rounded p-1 text-slate-400 lg:hidden"><X size={18}/></button>
      </div>
      <nav aria-label="Navegación principal" className="scrollbar-thin flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {visibleNavigation.map((group) => <section key={group.title}>
          {!collapsed && <h2 className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[.11em] text-slate-400">{group.title}</h2>}
          <ul className="space-y-1">{group.items.map(({ label, href, icon: Icon }) => {
            const active = activeHref === href;
            return <li key={href}><Link href={href} title={collapsed ? label : undefined} aria-current={active ? "page" : undefined} onClick={() => setMobileOpen(false)} className={`relative flex h-10 items-center gap-3 rounded-lg px-3 text-[13px] font-medium transition ${collapsed ? "justify-center px-2" : ""} ${active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"}`}>
              {active && <span className="absolute bottom-2 left-0 top-2 w-[3px] rounded-r bg-blue-600"/>}<Icon size={17} strokeWidth={1.8}/>{!collapsed && <span>{label}</span>}
            </Link></li>;
          })}</ul>
        </section>)}
      </nav>
      <div className="border-t border-slate-100 p-3">
        {!collapsed && <div className="mb-2 flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2"><BriefcaseBusiness size={15} className="text-blue-600"/><span className="min-w-0"><span className="block text-[9px] text-slate-400">Empresa</span><span className="block truncate text-[11px] font-medium text-slate-700">Agro Transporte SAC</span></span><ShieldCheck size={14} className="ml-auto text-emerald-600"/></div>}
        <button onClick={toggleCollapsed} className="flex h-9 w-full items-center justify-center gap-2 rounded-lg text-[11px] text-slate-500 transition hover:bg-slate-50 hover:text-slate-800" title={collapsed ? "Expandir menú" : "Contraer menú"}><ChevronLeft className={`size-4 transition-transform ${collapsed ? "rotate-180" : ""}`}/>{!collapsed && "Contraer menú"}</button>
      </div>
    </aside>

    <div className={`min-h-screen transition-[padding] duration-200 ${collapsed ? "lg:pl-20" : "lg:pl-64"}`}>
      <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
        <div className="flex min-w-0 items-center gap-3"><button onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Abrir menú"><Menu size={19}/></button><div className="min-w-0"><h1 className="truncate text-sm font-semibold text-slate-800 sm:text-base">{title}</h1><p className="text-[10px] text-slate-500">Panel administrativo</p></div></div>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <div className="relative hidden sm:block"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"/><input value={search} onChange={(event) => { setSearch(event.target.value); setSearchOpen(true); }} onFocus={() => setSearchOpen(true)} onKeyDown={(event) => { if (event.key === "Enter") goToFirstMatch(); if (event.key === "Escape") setSearchOpen(false); }} placeholder="Buscar módulos…" aria-label="Buscar módulos" className="h-9 w-56 rounded-full border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs outline-none transition focus:border-blue-300 focus:bg-white focus:ring-2 focus:ring-blue-100 md:w-64"/>
            {searchOpen && search.trim() && <div className="absolute right-0 top-11 z-50 w-72 overflow-hidden rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl">{matches.length ? matches.slice(0, 6).map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={() => { setSearchOpen(false); setSearch(""); setMobileOpen(false); }} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-xs text-slate-700 hover:bg-blue-50 hover:text-blue-700"><Icon size={15}/>{label}<span className="ml-auto text-[10px] text-slate-400">Abrir</span></Link>) : <p className="px-3 py-3 text-xs text-slate-500">No hay módulos que coincidan.</p>}</div>}
          </div>
          {hasPermission(permissions, "viajes.crear") && <Link href="/viajes/nuevo" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3 text-xs font-medium text-white shadow-sm transition hover:bg-blue-700"><Plus size={15}/><span className="hidden md:inline">Nuevo viaje</span><span className="md:hidden">Viaje</span></Link>}
          <button aria-label="Notificaciones" onClick={() => showNotice("Las notificaciones aún no están conectadas a la API.")} className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-blue-600"><Bell size={17}/></button>
          <button title={`${user?.email ?? "Usuario"} · Cerrar sesión`} aria-label="Cerrar sesión" onClick={() => void logout()} className="flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-[11px] font-semibold text-white shadow-sm">{(user?.email?.slice(0, 2) ?? "AD").toUpperCase()}</button>
        </div>
      </header>
      {!accessResolved ? <div role="status" className="m-6 rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">{permissionsQuery.isError ? "No se pudieron verificar los permisos. Recarga para volver a intentar." : "Verificando permisos…"}</div> : hasPageAccess ? children : null}
    </div>
    {notice && <div role="status" className="fixed bottom-5 right-5 z-50 rounded-lg bg-slate-900 px-4 py-3 text-xs text-white shadow-xl">{notice}</div>}
  </div>;
}
