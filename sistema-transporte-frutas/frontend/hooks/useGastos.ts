"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "gastos";
export const useGastosList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateGastos = () => useResourceCreate(resource);
export const useUpdateGastos = () => useResourceUpdate(resource);
export const useDeleteGastos = () => useResourceDelete(resource);

