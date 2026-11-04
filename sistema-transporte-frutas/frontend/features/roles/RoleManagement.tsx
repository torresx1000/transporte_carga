"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Save, Shield, Trash2, UserPlus, X } from "lucide-react";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { useAuthStore } from "@/lib/auth/authStore";

type Permission = { key: string; module: string; module_label: string; label: string };
type Role = {
  id: string;
  slug: string;
  name: string;
  description: string;
  permissions: string[];
  is_system: boolean;
  users_count: number;
};
type RoleUser = { id: string; email: string; name: string };
type AssignableUser = RoleUser & { permission_role_id: string | null; is_admin: boolean };
type AssignableClient = { id: string; name: string; document: string | null };
type AuditEntry = {
  id: string;
  actor_email: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
};

const button = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50";

export default function RoleManagement() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const [selectedId, setSelectedId] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [draftPermissions, setDraftPermissions] = useState<string[]>([]);
  const [userToAssign, setUserToAssign] = useState("");
  const [clientToAssign, setClientToAssign] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const myPermissions = useQuery({
    queryKey: ["auth", "permissions"],
    queryFn: async () => (await api.get<{ role: string; permissions: string[] }>("/roles/me")).data,
  });
  const isAdmin = myPermissions.data?.role === "admin";
  const permissions = useMemo(() => new Set(myPermissions.data?.permissions ?? []), [myPermissions.data?.permissions]);
  const canCreate = isAdmin || permissions.has("roles.crear");
  const canEdit = isAdmin || permissions.has("roles.editar");
  const canDelete = isAdmin || permissions.has("roles.eliminar");
  const canManagePermissions = isAdmin || permissions.has("permisos.gestionar");
  const canAssignRoles = isAdmin || permissions.has("usuarios.asignar_roles");
  const canView = isAdmin || permissions.has("roles.ver") || canManagePermissions;
  const catalog = useQuery({
    queryKey: ["roles", "catalog"],
    queryFn: async () => (await api.get<Permission[]>("/roles/catalog")).data,
    enabled: canView,
  });
  const rolesQuery = useQuery({
    queryKey: ["roles"],
    queryFn: async () => (await api.get<Role[]>("/roles")).data,
    enabled: canView,
  });
  const usersQuery = useQuery({
    queryKey: ["roles", "users"],
    queryFn: async () => (await api.get<AssignableUser[]>("/roles/users")).data,
    enabled: isAdmin || Boolean(myPermissions.data?.permissions.includes("usuarios.asignar_roles")),
    retry: false,
  });
  const clientsQuery = useQuery({
    queryKey: ["roles", "clients"],
    queryFn: async () => (await api.get<AssignableClient[]>("/roles/clients")).data,
    enabled: canAssignRoles,
    retry: false,
  });
  const selectedRoleId = selectedId || rolesQuery.data?.[0]?.id;
  const membersQuery = useQuery({
    queryKey: ["roles", "members", selectedRoleId],
    queryFn: async () => (await api.get<RoleUser[]>(`/roles/${selectedRoleId}/users`)).data,
    enabled: Boolean(selectedRoleId),
    retry: false,
  });
  const audit = useQuery({
    queryKey: ["roles", "audit"],
    queryFn: async () => (await api.get<AuditEntry[]>("/roles/audit")).data,
    enabled: canView,
    retry: false,
  });

  const selectedRole = rolesQuery.data?.find((role) => role.id === selectedId);
  const selectedRoleProtected = selectedRole?.slug === "admin" || selectedRole?.slug === "sin-acceso";
  const catalogItems = useMemo(() => catalog.data ?? [], [catalog.data]);
  const groupedPermissions = useMemo(() => {
    const groups = new Map<string, Permission[]>();
    for (const item of catalogItems) {
      const current = groups.get(item.module) ?? [];
      current.push(item);
      groups.set(item.module, current);
    }
    return [...groups.entries()].map(([key, items]) => ({
      key,
      label: items[0]?.module_label ?? key,
      items: items.sort((a, b) => a.label.localeCompare(b.label, "es")),
    })).sort((a, b) => a.label.localeCompare(b.label, "es"));
  }, [catalogItems]);
  const groupedMembers = membersQuery.data ?? [];

  function selectRole(role: Role) {
    setSelectedId(role.id);
    setName(role.name);
    setDescription(role.description);
    setDraftPermissions(role.permissions);
    setClientToAssign("");
    setCreating(false);
    setError("");
    setNotice("");
  }

  function startCreate() {
    setSelectedId("");
    setCreating(true);
    setName("");
    setDescription("");
    setDraftPermissions([]);
    setError("");
    setNotice("");
  }

  function togglePermission(key: string) {
    setDraftPermissions((current) => current.includes(key)
      ? current.filter((permission) => permission !== key)
      : [...current, key]);
  }

  async function saveRole(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (creating) {
        const response = await api.post<Role>("/roles", {
          name,
          description,
          permissions: canManagePermissions ? draftPermissions : [],
        });
        await queryClient.invalidateQueries({ queryKey: ["roles"] });
        setSelectedId(response.data.id);
        setCreating(false);
        setNotice("Rol creado.");
      } else if (selectedRole) {
        const data: Record<string, unknown> = {};
        if (canEdit) {
          data.name = name;
          data.description = description;
        }
        if (canManagePermissions) data.permissions = draftPermissions;
        await api.patch(`/roles/${selectedRole.id}`, data);
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["roles"] }),
          queryClient.invalidateQueries({ queryKey: ["roles", "audit"] }),
          queryClient.invalidateQueries({ queryKey: ["auth", "permissions"] }),
        ]);
        setNotice("Cambios guardados.");
      }
    } catch (cause) {
      setError(getApiError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function removeRole() {
    if (!selectedRole || !window.confirm(`¿Eliminar el rol "${selectedRole.name}"?`)) return;
    setBusy(true);
    setError("");
    try {
      await api.delete(`/roles/${selectedRole.id}`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["roles"] }),
        queryClient.invalidateQueries({ queryKey: ["roles", "audit"] }),
      ]);
      setSelectedId("");
      setNotice("Rol eliminado.");
    } catch (cause) {
      setError(getApiError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function assignRole(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedRole || !userToAssign) return;
    if (selectedRole.slug === "cliente" && !clientToAssign) {
      setError("Selecciona el cliente que se vinculará a esta cuenta.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.put(
        `/roles/${selectedRole.id}/users/${userToAssign}`,
        selectedRole.slug === "cliente" ? { client_id: clientToAssign } : undefined,
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["roles"] }),
        queryClient.invalidateQueries({ queryKey: ["roles", "users"] }),
        queryClient.invalidateQueries({ queryKey: ["roles", "members"] }),
        queryClient.invalidateQueries({ queryKey: ["roles", "audit"] }),
      ]);
      setUserToAssign("");
      setClientToAssign("");
      setNotice("Rol asignado. Los permisos se aplicarán en las siguientes solicitudes del usuario.");
    } catch (cause) {
      setError(getApiError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function unassignRole(member: RoleUser) {
    if (!selectedRole) return;
    setBusy(true);
    setError("");
    try {
      await api.delete(`/roles/${selectedRole.id}/users/${member.id}`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["roles"] }),
        queryClient.invalidateQueries({ queryKey: ["roles", "users"] }),
        queryClient.invalidateQueries({ queryKey: ["roles", "members"] }),
        queryClient.invalidateQueries({ queryKey: ["roles", "audit"] }),
      ]);
      setNotice(`Se retiró el rol de ${member.email}.`);
    } catch (cause) {
      setError(getApiError(cause));
    } finally {
      setBusy(false);
    }
  }

  if (myPermissions.isLoading) {
    return <p role="status" className="rounded-xl border bg-white p-8 text-center text-sm text-slate-500">Verificando permisos…</p>;
  }

  if (myPermissions.isError) {
    return <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">No se pudieron verificar tus permisos.</p>;
  }

  if (!canView && !canCreate) {
    return <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">No tienes permiso para consultar roles.</p>;
  }

  if (canView && (rolesQuery.isLoading || catalog.isLoading)) {
    return <p role="status" className="rounded-xl border bg-white p-8 text-center text-sm text-slate-500">Cargando roles y permisos…</p>;
  }

  if (canView && (rolesQuery.isError || catalog.isError)) {
    return <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">
      No se pudieron cargar los roles o el catálogo de permisos.
      <button type="button" className="ml-2 underline" onClick={() => { void rolesQuery.refetch(); void catalog.refetch(); }}>Reintentar</button>
    </div>;
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 text-xs text-slate-500">Administración / Roles y permisos</div>
          <h1 className="text-2xl font-semibold text-slate-900">Roles y permisos</h1>
          <p className="mt-1 text-sm text-slate-600">Define el acceso por módulo y consulta quién tiene asignado cada rol.</p>
        </div>
        {canCreate && <button type="button" onClick={startCreate} className={`${button} bg-blue-600 text-white hover:bg-blue-700`}><Plus size={16}/>Crear rol</button>}
      </header>

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="h-fit rounded-xl border border-slate-200 bg-white p-3">
          <h2 className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Roles existentes</h2>
          <div className="space-y-1">
            {canView ? (rolesQuery.data ?? []).map((role) => (
              <button key={role.id} type="button" onClick={() => selectRole(role)} className={`w-full rounded-lg px-3 py-3 text-left ${selectedRole?.id === role.id && !creating ? "bg-blue-50 text-blue-800" : "hover:bg-slate-50"}`}>
                <span className="flex items-center justify-between gap-2 text-sm font-medium"><span>{role.name}</span>{role.slug === "admin" && <Shield size={14} aria-label="Rol protegido"/>}</span>
                <span className="mt-1 block text-xs text-slate-500">{role.users_count} usuarios · {role.permissions.length} permisos</span>
              </button>
            )) : <p className="px-3 py-2 text-xs text-slate-500">No tienes permiso para consultar roles existentes.</p>}
          </div>
        </aside>

        <section className="space-y-6">
          {(creating || selectedRole) ? (
            <form onSubmit={(event) => void saveRole(event)} className="space-y-5 rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{creating ? "Crear rol" : selectedRole?.name}</h2>
                  {!creating && <p className="text-xs text-slate-500">{selectedRole?.slug}{selectedRole?.is_system ? " · Rol del sistema" : ""}</p>}
                </div>
                {!creating && selectedRole?.slug !== "admin" && canDelete && <button type="button" disabled={busy || selectedRole?.is_system} onClick={() => void removeRole()} className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-700 disabled:opacity-40"><Trash2 size={15}/>Eliminar rol</button>}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium">Nombre
                  <input required minLength={2} maxLength={120} value={creating || canEdit && !selectedRoleProtected ? name : selectedRole?.name ?? ""} readOnly={!creating && (!canEdit || selectedRoleProtected)} onChange={(event) => setName(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 read-only:bg-slate-50"/>
                </label>
                <label className="text-sm font-medium">Descripción
                  <input maxLength={500} value={creating || canEdit && !selectedRoleProtected ? description : selectedRole?.description ?? ""} readOnly={!creating && (!canEdit || selectedRoleProtected)} onChange={(event) => setDescription(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 read-only:bg-slate-50"/>
                </label>
              </div>

              <div>
                {selectedRole?.slug === "sin-acceso" && <p className="mb-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">Este rol está protegido y siempre debe permanecer sin permisos.</p>}
                <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-semibold">Permisos por módulo</h3>
                  <span className="text-xs text-slate-500">{draftPermissions.length} seleccionados</span>
                </div>
                {!canManagePermissions && <p className="mb-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">Puedes consultar estos permisos, pero no tienes autorización para asignarlos.</p>}
                <div className="space-y-4">
                  {groupedPermissions.map((group) => (
                    <fieldset key={group.key} className="rounded-lg border border-slate-200 p-4" disabled={!canManagePermissions || selectedRoleProtected}>
                      <legend className="px-2 text-sm font-semibold">{group.label}</legend>
                      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {group.items.map((permission) => (
                          <label key={permission.key} className="flex items-start gap-2 rounded-md p-2 text-sm hover:bg-slate-50">
                            <input type="checkbox" checked={draftPermissions.includes(permission.key)} onChange={() => togglePermission(permission.key)} className="mt-0.5 accent-blue-600"/>
                            <span><span className="block">{permission.label}</span><code className="text-[10px] text-slate-400">{permission.key}</code></span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  ))}
                </div>
              </div>

              {creating && !canManagePermissions && <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">Se creará sin permisos. Se requiere `permisos.gestionar` para asignarlos.</p>}
              {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
              {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
              <div className="flex justify-end">
                {(creating && canCreate || !creating && !selectedRoleProtected && (canEdit || canManagePermissions)) && <button disabled={busy} className={`${button} bg-blue-600 text-white hover:bg-blue-700`}><Save size={15}/>{busy ? "Guardando…" : "Guardar cambios"}</button>}
              </div>
            </form>
          ) : <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">Selecciona un rol o crea uno nuevo.</div>}

          {selectedRole && <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="font-semibold">Usuarios con este rol</h2>
            {canAssignRoles && selectedRole.slug !== "admin" && <form onSubmit={(event) => void assignRole(event)} className="mt-4 flex flex-wrap gap-2">
              <select aria-label="Seleccionar usuario" required value={userToAssign} onChange={(event) => setUserToAssign(event.target.value)} className="min-w-64 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
                <option value="">Selecciona un usuario</option>
                {(usersQuery.data ?? []).filter((item) => !item.is_admin && item.id !== user?.id && (selectedRole.slug === "cliente" || item.permission_role_id !== selectedRole.id)).map((item) => <option key={item.id} value={item.id}>{item.name ? `${item.name} · ` : ""}{item.email}</option>)}
              </select>
              {selectedRole.slug === "cliente" && <select aria-label="Seleccionar cliente" required value={clientToAssign} onChange={(event) => setClientToAssign(event.target.value)} className="min-w-64 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
                <option value="">Selecciona el cliente vinculado</option>
                {(clientsQuery.data ?? []).map((client) => <option key={client.id} value={client.id}>{client.name}{client.document ? ` · ${client.document}` : ""}</option>)}
              </select>}
              <button disabled={busy || !userToAssign || selectedRole.slug === "admin" || selectedRole.slug === "cliente" && (!clientToAssign || clientsQuery.isLoading)} className={`${button} border border-slate-300 text-slate-700 hover:bg-slate-50`}><UserPlus size={15}/>Asignar rol</button>
            </form>}
            {usersQuery.isError && canAssignRoles && <p role="alert" className="mt-3 text-sm text-red-700">No se pudo cargar la lista de usuarios para asignar roles.</p>}
            {clientsQuery.isError && selectedRole.slug === "cliente" && <p role="alert" className="mt-3 text-sm text-red-700">No se pudo cargar la lista de clientes.</p>}
            {membersQuery.isError && <p role="alert" className="mt-3 text-sm text-red-700">No se pudo consultar la lista de usuarios de este rol.</p>}
            <ul className="mt-4 divide-y divide-slate-100">
              {groupedMembers.map((member) => <li key={member.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                <span>{member.name || member.email}<span className="ml-2 text-xs text-slate-500">{member.name ? member.email : ""}</span></span>
                {canAssignRoles && selectedRole.slug !== "admin" && <button type="button" disabled={busy || member.id === user?.id} onClick={() => void unassignRole(member)} aria-label={`Retirar rol a ${member.email}`} className="rounded-md p-2 text-slate-500 hover:bg-red-50 hover:text-red-700 disabled:opacity-40"><X size={15}/></button>}
              </li>)}
              {!groupedMembers.length && <li className="py-4 text-sm text-slate-500">No hay usuarios asignados a este rol.</li>}
            </ul>
          </section>}

          {audit.data?.length ? <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="font-semibold">Historial de cambios</h2>
            <ul className="mt-3 divide-y divide-slate-100">
              {audit.data.slice(0, 20).map((entry) => <li key={entry.id} className="py-3 text-sm">
                <div className="flex flex-wrap justify-between gap-2"><span className="font-medium">{entry.action.replaceAll("_", " ")}</span><time className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString("es-PE")}</time></div>
                <p className="mt-1 text-xs text-slate-600">{entry.actor_email} · {JSON.stringify(entry.details)}</p>
              </li>)}
            </ul>
          </section> : null}
        </section>
      </div>
    </div>
  );
}
