"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Building2, Check, ChevronDown, FileText, Paperclip, UserRound } from "lucide-react";
import { useCliente, useCreateCliente, useReactivateCliente, useUpdateCliente } from "@/hooks/useClientes";
import { getApiError, getApiFieldErrors } from "@/lib/api/errors";
import { useAuthStore } from "@/lib/auth/authStore";
import { canRestoreArchivedClient } from "@/features/clientes/clientAccess";

const schema = z.object({
  tipo: z.enum(["Empresa", "Persona natural"]),
  estado: z.enum(["activo", "inactivo"]),
  nombre: z.string().trim().min(2, "Ingresa el nombre del cliente"),
  nombre_comercial: z.string().optional(),
  tipo_documento: z.enum(["RUC", "DNI", "CE"]),
  documento: z.string().trim().min(8, "Ingresa un documento válido"),
  contacto: z.string().optional(),
  telefono: z.string().trim().min(6, "Ingresa un teléfono válido"),
  correo: z.union([z.literal(""), z.string().email("Ingresa un correo válido")]),
  departamento: z.string().min(1, "Selecciona un departamento"),
  direccion: z.string().optional(),
  notas: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function ClientForm() {
  const params = useSearchParams();
  const router = useRouter();
  const id = params.get("editar") ?? "";
  const clientQuery = useCliente(id, Boolean(id));
  const createMutation = useCreateCliente();
  const updateMutation = useUpdateCliente();
  const reactivateMutation = useReactivateCliente();
  const role = useAuthStore((state) => state.user?.role);
  const [archivedClientId, setArchivedClientId] = useState<string | null>(null);
  const pending = createMutation.isPending || updateMutation.isPending;
  const { register, handleSubmit, reset, setError, control: formControl, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { tipo: "Empresa", estado: "activo", nombre: "", nombre_comercial: "", tipo_documento: "RUC", documento: "", contacto: "", telefono: "", correo: "", departamento: "", direccion: "", notas: "" },
  });
  const kind = useWatch({ control: formControl, name: "tipo" });

  useEffect(() => {
    if (!clientQuery.data) return;
    const client = clientQuery.data;
    reset({ tipo: client.tipo ?? "Empresa", estado: client.estado, nombre: client.nombre, nombre_comercial: client.nombre_comercial ?? "", tipo_documento: client.tipo_documento ?? "RUC", documento: client.documento ?? "", contacto: client.contacto ?? "", telefono: client.telefono ?? "", correo: client.correo ?? "", departamento: client.departamento ?? "", direccion: client.direccion ?? "", notas: client.notas ?? "" });
  }, [clientQuery.data, reset]);

  async function submit(values: FormValues) {
    setArchivedClientId(null);
    try {
      const payload = { ...values, ubicacion: values.departamento };
      if (id) await updateMutation.mutateAsync({ id, payload });
      else await createMutation.mutateAsync(payload);
      router.push("/clientes");
    } catch (error) {
      const apiError = error as { response?: { data?: { code?: unknown; details?: unknown } } };
      const details = apiError.response?.data?.details;
      if (apiError.response?.data?.code === "CLIENT_DOCUMENT_ARCHIVED" && typeof details === "object" && details !== null && "client_id" in details && typeof details.client_id === "string") {
        setArchivedClientId(details.client_id);
      }
      const fieldErrors = getApiFieldErrors(error);
      for (const [field, message] of Object.entries(fieldErrors)) {
        if (field in values) setError(field as keyof FormValues, { type: "server", message });
      }
      if (Object.keys(fieldErrors).length === 0) setError("root.server", { type: "server", message: getApiError(error) });
    }
  }

  async function reactivateArchivedClient() {
    if (!archivedClientId || role !== "admin") return;
    try {
      await reactivateMutation.mutateAsync(archivedClientId);
      router.push("/clientes");
    } catch {
      // The mutation reports the API error through the shared toast handler.
    }
  }

  const client = clientQuery.data;
  if (id && clientQuery.isLoading) return <main className="min-h-screen bg-[#f7f8fa] px-5 py-10 text-sm text-[#7a8580]">Cargando datos del cliente…</main>;
  if (id && clientQuery.isError) return <main className="min-h-screen bg-[#f7f8fa] px-5 py-10 text-sm text-red-600">{getApiError(clientQuery.error)} <button onClick={() => void clientQuery.refetch()} className="underline">Reintentar</button></main>;

  return <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10"><div className="mx-auto max-w-[1000px]">
    <div className="mb-6 flex items-center gap-2 text-xs text-[#87918c]"><Link href="/clientes" className="inline-flex items-center gap-1.5 hover:text-[#2563EB]"><ArrowLeft size={14} />Clientes</Link><span>/</span><span className="text-[#47534d]">{client ? "Editar cliente" : "Nuevo cliente"}</span></div>
    <div className="mb-6"><h1 className="text-[27px] font-semibold tracking-[-.8px]">{client ? "Editar cliente" : "Nuevo cliente"}</h1><p className="mt-1 text-sm text-[#7a8580]">{client ? "Actualiza los datos y documentos del cliente." : "Registra un nuevo cliente en tu cartera."}</p></div>
    <form onSubmit={handleSubmit(submit)} className="space-y-5">
      <section className="rounded-xl border border-[#e8ece9] bg-white p-5 shadow-[0_1px_2px_rgba(20,40,30,.02)] sm:p-6"><div className="mb-5 flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-lg bg-[#eaf5ee] text-[#43845e]"><Building2 size={18} /></span><div><h2 className="text-sm font-semibold">Información general</h2><p className="mt-0.5 text-xs text-[#8a958f]">Datos principales para identificar al cliente.</p></div></div>
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Tipo de cliente" required error={errors.tipo?.message}><select {...register("tipo")} className={control}><option>Empresa</option><option>Persona natural</option></select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-9 text-[#929c97]" /></Field><Field label="Estado" error={errors.estado?.message}><select {...register("estado")} className={control}><option value="activo">Activo</option><option value="inactivo">Inactivo</option></select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-9 text-[#929c97]" /></Field>
          <Field label={kind === "Empresa" ? "Razón social" : "Nombres y apellidos"} required error={errors.nombre?.message}><input {...register("nombre")} placeholder={kind === "Empresa" ? "Nombre legal de la empresa" : "Nombre completo"} className={control} /></Field><Field label="Nombre comercial" error={errors.nombre_comercial?.message}><input {...register("nombre_comercial")} placeholder="Nombre con el que opera" className={control} /></Field>
          <Field label="Tipo de documento" required error={errors.tipo_documento?.message}><select {...register("tipo_documento")} className={control}><option>RUC</option><option>DNI</option><option>CE</option></select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-9 text-[#929c97]" /></Field><Field label="Número de documento" required error={errors.documento?.message}><input {...register("documento")} placeholder="Ingresa el número" className={control} /></Field>
        </div>
      </section>
      <section className="rounded-xl border border-[#e8ece9] bg-white p-5 shadow-[0_1px_2px_rgba(20,40,30,.02)] sm:p-6"><div className="mb-5 flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-lg bg-[#eff3fa] text-[#6d82ae]"><UserRound size={18} /></span><div><h2 className="text-sm font-semibold">Contacto y ubicación</h2><p className="mt-0.5 text-xs text-[#8a958f]">¿Con quién coordinamos y dónde se encuentra?</p></div></div><div className="grid gap-4 sm:grid-cols-2"><Field label="Persona de contacto" error={errors.contacto?.message}><input {...register("contacto")} placeholder="Nombre del contacto principal" className={control} /></Field><Field label="Teléfono" required error={errors.telefono?.message}><input {...register("telefono")} type="tel" placeholder="+51 900 000 000" className={control} /></Field><Field label="Correo electrónico" error={errors.correo?.message}><input {...register("correo")} type="email" placeholder="correo@empresa.com" className={control} /></Field><Field label="Departamento" required error={errors.departamento?.message}><select {...register("departamento")} className={control}><option value="">Selecciona un departamento
      </option>{[
    "Amazonas",
    "Áncash",
    "Apurímac",
    "Arequipa",
    "Ayacucho",
    "Cajamarca",
    "Callao",
    "Cusco",
    "Huancavelica",
    "Huánuco",
    "Ica",
    "Junín",
    "La Libertad",
    "Lambayeque",
    "Lima",
    "Loreto",
    "Madre de Dios",
    "Moquegua",
    "Pasco",
    "Piura",
    "Puno",
    "San Martín",
    "Tacna",
    "Tumbes",
    "Ucayali"
].map((item) => <option key={item}>{item}</option>)}</select><ChevronDown size={14} className="pointer-events-none absolute right-3 top-9 text-[#929c97]" /></Field><div className="sm:col-span-2"><Field label="Dirección" error={errors.direccion?.message}><input {...register("direccion")} placeholder="Av., calle, número, referencia" className={control} /></Field></div></div></section>
      
      <section className="rounded-xl border border-[#e8ece9] bg-white p-5 shadow-[0_1px_2px_rgba(20,40,30,.02)] sm:p-6"><div className="mb-5 flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-lg bg-[#fff4e7] text-[#b88549]"><Paperclip size={18} /></span><div><h2 className="text-sm font-semibold">Fotos y documentos</h2><p className="mt-0.5 text-xs text-[#8a958f]">Disponible próximamente. Los archivos todavía no se guardan.</p></div></div><div className="grid gap-5 md:grid-cols-2"><div><p className="mb-2 text-xs font-medium text-[#56625c]">Foto del cliente o empresa</p><button type="button" disabled className="flex w-full cursor-not-allowed flex-col items-center justify-center rounded-xl border border-dashed border-[#dce3de] bg-[#fbfcfb] px-5 py-7 text-center text-xs text-[#9ba49f]">Carga de fotos disponible próximamente</button></div><div><p className="mb-2 text-xs font-medium text-[#56625c]">Documentos adjuntos</p><button type="button" disabled className="flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-dashed border-[#dce3de] bg-[#fbfcfb] px-4 py-3.5 text-xs text-[#9ba49f]"><FileText size={16} /> Carga de archivos disponible próximamente</button></div></div></section>
      <section className="rounded-xl border border-[#e8ece9] bg-white p-5 shadow-[0_1px_2px_rgba(20,40,30,.02)] sm:p-6"><div className="mb-3 flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-lg bg-[#f2effa] text-[#8170ae]"><FileText size={18} /></span><div><h2 className="text-sm font-semibold">Notas internas</h2><p className="mt-0.5 text-xs text-[#8a958f]">Información adicional para tu equipo.</p></div></div><textarea {...register("notas")} rows={3} placeholder="Escribe aquí observaciones o indicaciones..." className={`${control} h-auto resize-y py-3`} /></section>
      {errors.root?.server?.message && <p role="alert" className="text-sm text-red-600">{errors.root.server.message}</p>}
      {canRestoreArchivedClient(role, archivedClientId) && <div role="status" className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 sm:flex-row sm:items-center sm:justify-between"><span>El documento pertenece a un cliente dado de baja. Puedes reactivar ese mismo registro.</span><button type="button" disabled={reactivateMutation.isPending} onClick={() => void reactivateArchivedClient()} className="rounded-lg bg-amber-700 px-3 py-2 text-xs font-medium text-white disabled:opacity-60">{reactivateMutation.isPending ? "Reactivando…" : "Reactivar cliente"}</button></div>}
      <div className="sticky bottom-0 -mx-5 flex justify-end gap-2 border-t border-[#e9edeb] bg-[#f7f8fa]/95 px-5 py-4 backdrop-blur sm:-mx-8 sm:px-8 lg:-mx-10 lg:px-10"><Link href="/clientes" className="rounded-lg border border-[#e1e6e2] bg-white px-4 py-2.5 text-xs font-medium text-[#59655f]">Cancelar</Link><button type="submit" disabled={pending} className="inline-flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-xs font-medium text-white shadow-sm disabled:opacity-70"><Check size={15} />{pending ? "Guardando…" : client ? "Guardar cambios" : "Registrar cliente"}</button></div>
    </form>
  </div></main>;
}

const control = "h-10 w-full rounded-lg border border-[#e5eae6] bg-white px-3 text-xs text-[#47534d] outline-none placeholder:text-[#a8b0ac] focus:border-[#2563EB] focus:ring-2 focus:ring-[#DBEAFE]";
function Field({ label, required, error, children }: { label: string; required?: boolean; error?: string; children: React.ReactNode }) { return <label className="relative block"><span className="mb-1.5 block text-xs font-medium text-[#56625c]">{label}{required && <span className="ml-0.5 text-[#cf6f63]">*</span>}</span>{children}{error && <span className="mt-1 block text-[11px] text-red-600">{error}</span>}</label>; }
