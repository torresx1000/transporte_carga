"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "usuarios";
export const useUsuariosList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateUsuarios = () => useResourceCreate(resource);
export const useUpdateUsuarios = () => useResourceUpdate(resource);
export const useDeleteUsuarios = () => useResourceDelete(resource);

