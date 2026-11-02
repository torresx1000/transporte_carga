"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "retornos";
export const useRetornosList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateRetornos = () => useResourceCreate(resource);
export const useUpdateRetornos = () => useResourceUpdate(resource);
export const useDeleteRetornos = () => useResourceDelete(resource);

