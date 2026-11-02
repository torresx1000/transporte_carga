"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "mantenimiento";
export const useMantenimientoList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateMantenimiento = () => useResourceCreate(resource);
export const useUpdateMantenimiento = () => useResourceUpdate(resource);
export const useDeleteMantenimiento = () => useResourceDelete(resource);

