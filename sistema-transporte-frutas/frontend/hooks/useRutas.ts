"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "rutas";
export const useRutasList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateRutas = () => useResourceCreate(resource);
export const useUpdateRutas = () => useResourceUpdate(resource);
export const useDeleteRutas = () => useResourceDelete(resource);

