"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "conductores";
export const useConductoresList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateConductores = () => useResourceCreate(resource);
export const useUpdateConductores = () => useResourceUpdate(resource);
export const useDeleteConductores = () => useResourceDelete(resource);

