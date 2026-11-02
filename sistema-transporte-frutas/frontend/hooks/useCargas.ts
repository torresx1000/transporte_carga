"use client";

import { useResourceCreate, useResourceDelete, useResourceDetail, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "cargas";
export const useCargasList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCarga = (id: string) => useResourceDetail(resource, id);
export const useCreateCargas = () => useResourceCreate(resource);
export const useUpdateCargas = () => useResourceUpdate(resource);
export const useDeleteCargas = () => useResourceDelete(resource);
