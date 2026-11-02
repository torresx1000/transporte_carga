"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getApiError } from "@/lib/api/errors";
import { createResourceService, type ResourceName, type ResourceRecord } from "@/services/resource.service";

export function useResourceList(resource: ResourceName, params: { page?: number; page_size?: number; q?: string; estado?: string; tipo?: string } = {}) {
  const service = createResourceService(resource);
  return useQuery({ queryKey: [resource, "list", params], queryFn: () => service.list(params) });
}
export function useResourceDetail(resource: ResourceName, id: string) {
  const service = createResourceService(resource);
  return useQuery({ queryKey: [resource, "detail", id], queryFn: () => service.get(id), enabled: Boolean(id) });
}
export function useResourceCreate(resource: ResourceName) {
  const queryClient = useQueryClient(); const service = createResourceService(resource);
  return useMutation({ mutationFn: (payload: ResourceRecord) => service.create(payload), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: [resource] }); toast.success("Registro creado correctamente"); }, onError: (error) => toast.error(getApiError(error)) });
}
export function useResourceUpdate(resource: ResourceName) {
  const queryClient = useQueryClient(); const service = createResourceService(resource);
  return useMutation({ mutationFn: ({ id, payload }: { id: string; payload: ResourceRecord }) => service.update(id, payload), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: [resource] }); toast.success("Cambios guardados"); }, onError: (error) => toast.error(getApiError(error)) });
}
export function useResourceDelete(resource: ResourceName) {
  const queryClient = useQueryClient(); const service = createResourceService(resource);
  return useMutation({ mutationFn: (id: string) => service.remove(id), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: [resource] }); toast.success("Registro eliminado"); }, onError: (error) => toast.error(getApiError(error)) });
}

export function useResourceReactivate(resource: ResourceName) {
  const queryClient = useQueryClient(); const service = createResourceService(resource);
  return useMutation({ mutationFn: (id: string) => service.reactivate(id), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: [resource] }); toast.success("Registro reactivado"); }, onError: (error) => toast.error(getApiError(error)) });
}
