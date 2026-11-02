"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, FolderOpen, Search, Upload, X } from "lucide-react";
import { ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";
import { useCatalog } from "@/features/transporte/data";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";

type VehicleFolder = { id: string; placa: string; codigo_flota?: string };
type TripFolder = { id: string; codigo: string; vehiculo_id?: string; estado?: string };
type LibraryFile = {
  id: string;
  nombre: string;
  tipo: string;
  propietario_tipo: string;
  propietario_id: string;
  propietario_nombre: string;
  carpeta: string;
  tamano: number;
  fecha: string;
  descargable: boolean;
};

const folderLabels: Record<string, string> = {
  todos: "Todos los archivos",
  vehiculo: "Vehículos",
  viaje: "Viajes",
};
const inputClass = "h-10 w-full rounded-lg border border-[#dce4df] bg-white px-3 text-sm outline-none focus:border-[#2563EB]";

export default function DocumentsWorkspace({ initialUpload = false }: { initialUpload?: boolean }) {
  const vehicles = useCatalog<VehicleFolder>("vehiculos");
  const trips = useCatalog<TripFolder>("viajes");
  const cache = useQueryClient();
  const [folder, setFolder] = useState("todos");
  const [ownerId, setOwnerId] = useState("");
  const [search, setSearch] = useState("");
  const [uploadOpen, setUploadOpen] = useState(initialUpload);
  const [uploadType, setUploadType] = useState<"vehiculo" | "viaje">("vehiculo");
  const [uploadOwnerId, setUploadOwnerId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const owners = uploadType === "vehiculo" ? vehicles.data ?? [] : trips.data ?? [];
  const library = useQuery({
    queryKey: ["documentos", "biblioteca", folder, ownerId, search],
    queryFn: async () =>
      (
        await api.get<LibraryFile[]>("/documentos/biblioteca", {
          params: {
            carpeta: folder,
            propietario_id: ownerId || undefined,
            q: search.trim() || undefined,
          },
        })
      ).data,
  });
  const files = useMemo(() => library.data ?? [], [library.data]);
  const totalSize = useMemo(() => files.reduce((total, file) => total + file.tamano, 0), [files]);

  function chooseFolder(next: string) {
    setFolder(next);
    setOwnerId("");
  }

  async function uploadFile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const file = new FormData(formElement).get("archivo");
    if (!(file instanceof File) || file.size === 0 || !uploadOwnerId) {
      setError("Selecciona una carpeta y un archivo.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("El archivo supera 10 MB.");
      return;
    }
    setUploading(true);
    setError("");
    const body = new FormData();
    body.append("archivo", file);
    try {
      await api.post(
        `/documentos/biblioteca?propietario_tipo=${uploadType}&propietario_id=${encodeURIComponent(uploadOwnerId)}`,
        body,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      await cache.invalidateQueries({ queryKey: ["documentos", "biblioteca"] });
      formElement.reset();
      if (folder === uploadType) setOwnerId(uploadOwnerId);
      setUploadOpen(false);
    } catch (cause) {
      setError(getApiError(cause));
    } finally {
      setUploading(false);
    }
  }

  async function downloadFile(file: LibraryFile) {
    setError("");
    try {
      const response = await api.get(
        `/documentos/biblioteca/${encodeURIComponent(file.id)}/archivo`,
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = file.nombre;
      link.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setError(getApiError(cause));
    }
  }

  const ownerLabel = (owner: VehicleFolder | TripFolder) =>
    "placa" in owner
      ? [owner.codigo_flota, owner.placa].filter(Boolean).join(" · ")
      : owner.codigo;

  return (
    <main className="min-h-screen bg-[#f7f8fa] px-5 py-8 text-[#17211e] sm:px-8 lg:px-10">
      <div className="mx-auto max-w-[1440px]">
        <header className="mb-7 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs text-[#87918c]">
              <span>Administración</span><span>/</span><span className="text-[#47534d]">Documentos</span>
            </div>
            <h1 className="text-[28px] font-semibold tracking-[-.8px]">Biblioteca de documentos</h1>
            <p className="mt-1 text-sm text-[#7a8580]">
              Encuentra archivos por vehículo o viaje, incluidos los adjuntos en sus gastos, cargas y combustible.
            </p>
          </div>
          <button
            type="button"
            onClick={() => { setError(""); setUploadOpen((open) => !open); }}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#2563EB] px-4 text-sm font-medium text-white hover:bg-[#1D4ED8]"
          >
            {uploadOpen ? <X size={16}/> : <Upload size={16}/>}
            {uploadOpen ? "Cerrar carga" : "Subir archivo"}
          </button>
        </header>

        {uploadOpen && (
          <form onSubmit={(event) => void uploadFile(event)} className="mb-6 grid gap-3 rounded-xl border border-[#e8ece9] bg-white p-5 sm:grid-cols-4 sm:items-end">
            <label className="text-sm">Guardar en
              <select value={uploadType} onChange={(event) => { setUploadType(event.target.value as "vehiculo" | "viaje"); setUploadOwnerId(""); }} className={`${inputClass} mt-1`}>
                <option value="vehiculo">Vehículo</option>
                <option value="viaje">Viaje</option>
              </select>
            </label>
            <label className="text-sm">Carpeta
              <select required value={uploadOwnerId} onChange={(event) => setUploadOwnerId(event.target.value)} className={`${inputClass} mt-1`}>
                <option value="">Selecciona {uploadType === "vehiculo" ? "un vehículo" : "un viaje"}</option>
                {owners.map((owner) => <option key={owner.id} value={owner.id}>{ownerLabel(owner)}</option>)}
              </select>
            </label>
            <label className="text-sm sm:col-span-2">Archivo (máximo 10 MB)
              <input required name="archivo" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt" className={`${inputClass} mt-1 py-1.5`}/>
            </label>
            <div className="sm:col-span-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-gray-500">PDF, imágenes, documentos y hojas de cálculo. Los adjuntos existentes no se mueven.</p>
              <button disabled={uploading} className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#dce4df] px-4 text-sm font-medium text-[#2563EB] disabled:opacity-50">
                <Upload size={15}/>{uploading ? "Subiendo…" : "Guardar archivo"}
              </button>
            </div>
          </form>
        )}

        <section className="overflow-hidden rounded-xl border border-[#e8ece9] bg-white">
          <div className="flex flex-col gap-4 border-b border-[#edf0ee] p-5">
            <div className="flex flex-wrap gap-2">
              {Object.entries(folderLabels).map(([key, label]) => (
                <button key={key} type="button" onClick={() => chooseFolder(key)} className={`rounded-lg px-3 py-2 text-sm ${folder === key ? "bg-[#DBEAFE] font-semibold text-[#1D4ED8]" : "border border-gray-200 text-gray-600 hover:bg-gray-50"}`}>
                  {key === "todos" ? <FileText size={15} className="mr-2 inline"/> : <FolderOpen size={15} className="mr-2 inline"/>}{label}
                </button>
              ))}
            </div>
            {folder !== "todos" && (
              <label className="max-w-xl text-sm">Abrir carpeta de {folder === "vehiculo" ? "vehículo" : "viaje"}
                <select value={ownerId} onChange={(event) => setOwnerId(event.target.value)} className={`${inputClass} mt-1`}>
                  <option value="">Todos los archivos directos de {folderLabels[folder].toLocaleLowerCase("es")}</option>
                  {(folder === "vehiculo" ? vehicles.data ?? [] : trips.data ?? []).map((owner) => (
                    <option key={owner.id} value={owner.id}>{ownerLabel(owner)}</option>
                  ))}
                </select>
              </label>
            )}
            <label className="relative block w-full sm:max-w-xl">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
              <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por nombre o tipo de archivo…" className={`${inputClass} pl-9`}/>
            </label>
          </div>
          {error && <p role="alert" className="mx-5 mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {library.isLoading ? <TableSkeleton/> : library.isError ? <div className="p-5"><ErrorState message={getApiError(library.error)} onRetry={() => void library.refetch()}/></div> : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-4 text-xs text-gray-500">
                <span>{files.length} archivos</span>
                <span>{(totalSize / (1024 * 1024)).toLocaleString("es-PE", { maximumFractionDigits: 2 })} MB en esta vista</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-gray-50 text-xs text-gray-500"><tr>{["Nombre", "Carpeta", "Relacionado con", "Fecha", "Tamaño", ""].map((label) => <th key={label} className="px-4 py-3">{label}</th>)}</tr></thead>
                  <tbody className="divide-y divide-gray-100">
                    {files.map((file) => (
                      <tr key={file.id} className="hover:bg-gray-50/70">
                        <td className="px-4 py-3"><div className="flex items-center gap-2 font-medium"><FileText size={16} className="shrink-0 text-[#2563EB]"/>{file.nombre}</div><p className="pl-6 text-xs text-gray-400">{file.tipo.replaceAll("_", " ")}</p></td>
                        <td className="px-4 py-3">{file.carpeta}</td>
                        <td className="px-4 py-3">{file.propietario_nombre}</td>
                        <td className="whitespace-nowrap px-4 py-3">{new Date(file.fecha).toLocaleDateString("es-PE")}</td>
                        <td className="whitespace-nowrap px-4 py-3">{(file.tamano / 1024).toLocaleString("es-PE", { maximumFractionDigits: 0 })} KB</td>
                        <td className="px-4 py-3 text-right">{file.descargable && <button type="button" aria-label={`Descargar ${file.nombre}`} onClick={() => void downloadFile(file)} className="rounded-lg p-2 text-[#2563EB] hover:bg-blue-50"><Download size={17}/></button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!files.length && <p className="p-10 text-center text-sm text-gray-500">No hay archivos en esta carpeta todavía.</p>}
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
