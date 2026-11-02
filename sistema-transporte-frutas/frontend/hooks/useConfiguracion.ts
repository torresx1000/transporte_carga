"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "configuracion";
export const useConfiguracionList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateConfiguracion = () => useResourceCreate(resource);
export const useUpdateConfiguracion = () => useResourceUpdate(resource);
export const useDeleteConfiguracion = () => useResourceDelete(resource);

