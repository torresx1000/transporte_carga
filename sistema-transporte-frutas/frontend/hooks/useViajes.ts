"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "viajes";
export const useViajesList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateViajes = () => useResourceCreate(resource);
export const useUpdateViajes = () => useResourceUpdate(resource);
export const useDeleteViajes = () => useResourceDelete(resource);

