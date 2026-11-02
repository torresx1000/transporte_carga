"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "combustible";
export const useCombustibleList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateCombustible = () => useResourceCreate(resource);
export const useUpdateCombustible = () => useResourceUpdate(resource);
export const useDeleteCombustible = () => useResourceDelete(resource);

