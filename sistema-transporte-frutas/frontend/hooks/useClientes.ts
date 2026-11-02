"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getApiError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query/keys";
import { clientesService, type ClientFilters } from "@/services/clientes.service";
import type { ClientPayload, ClientUpdatePayload } from "@/types/api/cliente";

export function useClientesList(filters: ClientFilters = {}) {
  return useQuery({ queryKey: queryKeys.clientes.list(filters), queryFn: () => clientesService.list(filters) });
}

export function useCliente(id: string, enabled = true) {
  return useQuery({ queryKey: queryKeys.clientes.detail(id), queryFn: () => clientesService.get(id), enabled: Boolean(id) && enabled });
}

export function useClientCrateHistory(id: string, enabled = true) {
  return useQuery({ queryKey: ["clientes", "crate-history", id], queryFn: () => clientesService.getCrateHistory(id), enabled: Boolean(id) && enabled });
}

export function useCreateCliente() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (payload: ClientPayload) => clientesService.create(payload), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: queryKeys.clientes.all }); toast.success("Cliente registrado"); }, onError: (error) => toast.error(getApiError(error)) });
}

export function useUpdateCliente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ClientUpdatePayload }) => clientesService.update(id, payload),
    onError: (error) => { toast.error(getApiError(error)); },
    onSuccess: (client) => { queryClient.setQueryData(queryKeys.clientes.detail(client.id), client); toast.success("Cambios guardados"); },
    onSettled: () => { void queryClient.invalidateQueries({ queryKey: queryKeys.clientes.all }); },
  });
}

export function useReactivateCliente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => clientesService.reactivate(id),
    onSuccess: (client) => {
      queryClient.setQueryData(queryKeys.clientes.detail(client.id), client);
      void queryClient.invalidateQueries({ queryKey: queryKeys.clientes.all });
      toast.success("Cliente reactivado");
    },
    onError: (error) => toast.error(getApiError(error)),
  });
}

export function useDeleteCliente() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (id: string) => clientesService.remove(id), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: queryKeys.clientes.all }); toast.success("Cliente eliminado"); }, onError: (error) => toast.error(getApiError(error)) });
}
