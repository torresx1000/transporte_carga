"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "pagos";
export const usePagosList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreatePagos = () => useResourceCreate(resource);
export const useUpdatePagos = () => useResourceUpdate(resource);
export const useDeletePagos = () => useResourceDelete(resource);

